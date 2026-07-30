import asyncio
import random

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from collectors.base import BaseCollectorAdapter
from collectors.docker_collector import DockerTLSCollectorAdapter
from collectors.fake_collector import FakeCollectorAdapter
from collectors.ssh_collector import SSHCollectorAdapter
from collectors.winrm_collector import WinRMCollectorAdapter
from models.collector import CollectorTarget, TargetType
from services.collector_service import (
    process_collector_failure,
    process_collector_success,
    process_discovery_result,
)


class CollectorScheduler:
    """
    Worker Scheduler for Infrastructure Monitoring.
    Manages periodic polling jobs, bounded concurrency execution,
    and retry handling with backoff and jitter.
    """

    def __init__(self, max_concurrency: int = 10, max_retries: int = 2):
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.max_retries = max_retries

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

    async def execute_poll_target(self, db: AsyncSession, target: CollectorTarget) -> bool:
        """Poll a single target with bounded concurrency and retry backoff/jitter."""
        async with self.semaphore:
            adapter = self.create_adapter(target)
            canonical_id = f"{target.target_type}_{target.host}"

            for attempt in range(self.max_retries + 1):
                try:
                    # 1. Run test/status check
                    success = await adapter.test_connection()
                    if success:
                        # 2. Run discovery update
                        discovery = await adapter.discover()
                        await process_discovery_result(db, discovery)
                        await process_collector_success(db, discovery.canonical_identity)
                        return True
                    else:
                        error_msg = "Connection or authentication failed"
                except Exception as e:
                    error_msg = str(e)

                # Retry backoff with jitter if not final attempt
                if attempt < self.max_retries:
                    backoff = (2 ** attempt) * 0.5 + random.uniform(0.1, 0.5)
                    await asyncio.sleep(backoff)

            # Final failure after retries exhausted -> process failure transition
            await process_collector_failure(db, canonical_id, error_msg)
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
