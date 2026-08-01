import asyncio
import logging
import sys
import time

from sqlalchemy import select

from collectors.metrics_exporter import (
    start_worker_metrics_server,
)
from collectors.scheduler import CollectorScheduler
from core.config import settings
from core.database import AsyncSessionLocal
from models.node import Node
from services.alert_service import evaluate_node_telemetry_alerts
from services.report_scheduler_service import execute_due_report_schedules
from services.status_broadcaster import broadcast_status_deltas

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s [%(levelname)s] [Worker] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("collector-worker")

RUNNING = True

# How often the worker evaluates alert rules and runs the report cron engine.
ALERT_EVALUATION_INTERVAL_SECONDS = 60
REPORT_CRON_INTERVAL_SECONDS = 60


async def write_health_heartbeat():
    """Write heartbeat status to signal worker liveness."""
    while RUNNING:
        try:
            with open("/tmp/worker_heartbeat", "w") as f:
                f.write(str(int(time.time())))
        except Exception:
            pass
        await asyncio.sleep(5)


async def evaluate_alerts_cycle() -> None:
    """
    Evaluate alert rules against current node telemetry.
    Uses the metrics exported in the in-process Prometheus registry so it works
    offline / without a running Prometheus server.
    """
    from collectors.metrics_exporter import (
        CPU_USAGE,
        DISK_USAGE_PERCENT,
        RAM_USAGE_PERCENT,
    )

    async with AsyncSessionLocal() as db:
        try:
            stmt = select(Node).where(Node.status.is_not(None))
            result = await db.execute(stmt)
            nodes = list(result.scalars().all())

            for node in nodes:
                node_id = str(node.id)
                cpu = None
                ram = None
                disk = None
                try:
                    cpu_gauge = CPU_USAGE._metrics.get((node_id,))
                    ram_gauge = RAM_USAGE_PERCENT._metrics.get((node_id,))
                    disk_gauge = DISK_USAGE_PERCENT._metrics.get((node_id,))
                    if cpu_gauge:
                        cpu = float(cpu_gauge._value.get()) * 100.0
                    if ram_gauge:
                        ram = float(ram_gauge._value.get())
                    if disk_gauge:
                        disk = float(disk_gauge._value.get())
                except Exception:
                    pass

                await evaluate_node_telemetry_alerts(
                    db,
                    node,
                    cpu_usage=cpu,
                    ram_usage=ram,
                    disk_usage=disk,
                )
            await db.commit()
        except Exception as exc:
            await db.rollback()
            logger.error(f"Error during alert evaluation cycle: {exc}")


async def report_cron_cycle() -> None:
    """
    Execute any due automated report delivery schedules (cron engine).
    """
    async with AsyncSessionLocal() as db:
        try:
            executed = await execute_due_report_schedules(db)
            if executed:
                logger.info(f"Executed {len(executed)} due report schedule(s).")
        except Exception as exc:
            await db.rollback()
            logger.error(f"Error during report cron cycle: {exc}")


async def main():
    logger.info("Starting Infrastructure Monitoring Collector Worker...")
    poll_interval = max(30, min(60, settings.STATUS_POLL_INTERVAL_SECONDS))
    scan_interval = settings.INVENTORY_SCAN_INTERVAL_SECONDS
    logger.info(
        f"Status Poll Interval: {poll_interval}s, Inventory Scan Interval: {scan_interval}s"
    )

    # K-1: Bootstrap the Prometheus exporter so Prometheus can scrape worker:8001
    start_worker_metrics_server(port=8001)
    logger.info("Prometheus exporter listening on :8001/metrics")

    scheduler = CollectorScheduler(max_concurrency=10, max_retries=2)
    heartbeat_task = asyncio.create_task(write_health_heartbeat())

    try:
        while RUNNING:
            logger.debug("Running scheduled collector polling cycle...")
            try:
                async with AsyncSessionLocal() as db:
                    await scheduler.poll_all_targets(db)
            except Exception as e:
                logger.error(f"Error during collector polling cycle: {e}")

            # K-2: Broadcast live status deltas to connected WebSocket clients
            try:
                async with AsyncSessionLocal() as db:
                    await broadcast_status_deltas(db)
            except Exception as e:
                logger.error(f"Error during status delta broadcast: {e}")

            # K-3: Evaluate alert rules automatically
            await evaluate_alerts_cycle()

            # K-4: Run the automated report cron engine
            await report_cron_cycle()

            await asyncio.sleep(poll_interval)
    except asyncio.CancelledError:
        logger.info("Collector Worker shutdown requested.")
    finally:
        heartbeat_task.cancel()
        logger.info("Collector Worker stopped cleanly.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user.")
