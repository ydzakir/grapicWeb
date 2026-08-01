import asyncio
import logging
import random

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from collectors.base import BaseCollectorAdapter
from collectors.docker_collector import DockerTLSCollectorAdapter
from collectors.fake_collector import FakeCollectorAdapter
from collectors.metrics_exporter import update_node_metrics
from collectors.ssh_collector import SSHCollectorAdapter
from collectors.winrm_collector import WinRMCollectorAdapter
from models.collector import CollectorTarget, TargetType
from services.collector_service import (
    process_collector_failure,
    process_collector_success,
    process_discovery_result,
)

logger = logging.getLogger("collector-scheduler")


class CollectorScheduler:
    """
    Worker Scheduler for Infrastructure Monitoring.
    Manages periodic polling jobs, bounded concurrency execution,
    retry handling with backoff/jitter, metrics publishing, and alert wiring.
    """

    def __init__(self, max_concurrency: int = 10, max_retries: int = 2):
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.max_retries = max_retries
        # Map target_id -> last discovery canonical identity so failure lookups
        # land on the exact node the adapter produced (idempotency contract).
        self._canonical_identity_cache: dict[str, str] = {}

    def create_adapter(self, target: CollectorTarget) -> BaseCollectorAdapter:
        """Instantiate appropriate adapter for target."""
        poll_interval = int((target.metadata_ or {}).get("poll_interval_seconds", 60))
        # Ensure interval is within valid 30-60s range
        if poll_interval < 30 or poll_interval > 60:
            poll_interval = 60

        if target.target_type == TargetType.SSH:
            return SSHCollectorAdapter(
                target_host=target.host,
                target_port=target.port,
                credential_ref=target.credential_reference,
            )
        elif target.target_type == TargetType.WINRM:
            return WinRMCollectorAdapter(
                target_host=target.host,
                target_port=target.port,
                credential_ref=target.credential_reference,
            )
        elif target.target_type == TargetType.DOCKER_TLS:
            return DockerTLSCollectorAdapter(
                target_host=target.host,
                target_port=target.port,
                credential_ref=target.credential_reference,
            )
        else:
            simulate_mode = (target.metadata_ or {}).get("simulate_failure_mode")
            return FakeCollectorAdapter(
                target_host=target.host,
                target_port=target.port,
                credential_ref=target.credential_reference,
                simulate_failure_mode=simulate_mode,
            )

    def canonical_identity_for_target(self, target: CollectorTarget) -> str:
        """Best-effort canonical identity derived from the target config.

        Used as a fallback when no discovery result has been cached yet. The
        authoritative identity comes from the adapter's discovery result.
        """
        prefix = {
            TargetType.SSH: "ssh",
            TargetType.WINRM: "winrm",
            TargetType.DOCKER_TLS: "docker_host",
        }.get(target.target_type, "fake_host")
        return f"{prefix}_{target.host}"

    async def collect_and_publish_metrics(
        self,
        adapter: BaseCollectorAdapter,
        node_id: str,
        node_status: str,
    ) -> None:
        """Collect normalized metrics from an adapter and publish them to the
        in-process Prometheus registry so Prometheus can scrape worker:8001.

        Metrics are keyed by the stable database node UUID so the metrics query
        API (`/api/v1/metrics?node_id=<uuid>`) can resolve them.

        Failure to collect/publish must not break the polling cycle, so it is
        guarded and logged.
        """
        try:
            metrics = await adapter.collect_metrics()
        except Exception as exc:
            logger.warning(
                "Metrics collection failed for %s: %s", node_id, exc
            )
            return

        update_node_metrics(
            node_id=node_id,
            status=node_status,
            cpu_usage_ratio=(
                round(metrics.cpu_usage_percent / 100.0, 4)
                if metrics.cpu_usage_percent is not None
                else None
            ),
            ram_usage_percent=metrics.ram_usage_percent,
            disk_usage_percent=metrics.disk_usage_percent,
            network_in_bytes=metrics.network_rx_bytes,
            network_out_bytes=metrics.network_tx_bytes,
        )

    async def execute_poll_target(self, db: AsyncSession, target: CollectorTarget) -> bool:
        """Poll a single target with bounded concurrency and retry backoff/jitter."""
        async with self.semaphore:
            adapter = self.create_adapter(target)
            target_key = str(target.id)

            for attempt in range(self.max_retries + 1):
                try:
                    # 1. Run test/status check
                    success = await adapter.test_connection()
                    if success:
                        # 2. Run discovery update
                        discovery = await adapter.discover()
                        await process_discovery_result(db, discovery)
                        # Cache the authoritative identity produced by discovery
                        self._canonical_identity_cache[target_key] = discovery.canonical_identity
                        node = await process_collector_success(
                            db, discovery.canonical_identity
                        )

                        # 3. Publish metrics to Prometheus (best-effort), keyed by node UUID
                        if node is not None:
                            await self.collect_and_publish_metrics(
                                adapter=adapter,
                                node_id=str(node.id),
                                node_status="up",
                            )
                        return True
                    else:
                        error_msg = "Connection or authentication failed"
                except Exception as e:
                    error_msg = str(e)

                # Retry backoff with jitter if not final attempt
                if attempt < self.max_retries:
                    backoff = (2 ** attempt) * 0.5 + random.uniform(0.1, 0.5)
                    await asyncio.sleep(backoff)

            # Final failure after retries exhausted -> process failure transition.
            # Prefer the last known discovery identity so the correct node is marked
            # UNKNOWN then DOWN (Rules: >2 minutes consecutive failure window).
            canonical_id = self._canonical_identity_cache.get(
                target_key, self.canonical_identity_for_target(target)
            )
            node = await process_collector_failure(db, canonical_id, error_msg)
            # Publish failure status to Prometheus (best-effort), keyed by node UUID
            if node is not None:
                await self.collect_and_publish_metrics(
                    adapter=adapter,
                    node_id=str(node.id),
                    node_status=node.status.value,
                )
            return False

    async def poll_all_targets(self, db: AsyncSession) -> list[bool]:
        """Poll all enabled collector targets concurrently."""
        stmt = select(CollectorTarget).where(CollectorTarget.enabled.is_(True))
        result = await db.execute(stmt)
        targets = list(result.scalars().all())

        if not targets:
            return []

        tasks = [self.execute_poll_target(db, target) for target in targets]
        return list(await asyncio.gather(*tasks, return_exceptions=False))
