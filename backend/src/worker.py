import asyncio
import logging
import sys
import time

from collectors.scheduler import CollectorScheduler
from core.config import settings
from core.database import AsyncSessionLocal

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s [%(levelname)s] [Worker] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("collector-worker")

RUNNING = True


async def write_health_heartbeat():
    """Write heartbeat status to signal worker liveness."""
    while RUNNING:
        try:
            with open("/tmp/worker_heartbeat", "w") as f:
                f.write(str(int(time.time())))
        except Exception:
            pass
        await asyncio.sleep(5)


async def main():
    logger.info("Starting Infrastructure Monitoring Collector Worker...")
    poll_interval = max(30, min(60, settings.STATUS_POLL_INTERVAL_SECONDS))
    scan_interval = settings.INVENTORY_SCAN_INTERVAL_SECONDS
    logger.info(
        f"Status Poll Interval: {poll_interval}s, Inventory Scan Interval: {scan_interval}s"
    )

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
