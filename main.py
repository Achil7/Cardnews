import argparse
import asyncio

from src.logging_config import setup_logging
from src.scheduler.pipeline import run_pipeline


def run_once():
    asyncio.run(run_pipeline())


def run_daemon():
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from loguru import logger

    async def _daemon():
        scheduler = AsyncIOScheduler(timezone="UTC")
        scheduler.add_job(run_pipeline, "cron", hour=4, minute=0, id="run_utc_04")
        scheduler.add_job(run_pipeline, "cron", hour=23, minute=0, id="run_utc_23")
        scheduler.start()
        logger.info("Scheduler started: UTC 04:00 (KST 13:00), UTC 23:00 (KST 08:00)")
        while True:
            await asyncio.sleep(3600)

    asyncio.run(_daemon())


if __name__ == "__main__":
    from config import settings

    setup_logging(settings.log_level)

    parser = argparse.ArgumentParser(description="Cardnews pipeline")
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run as daemon with APScheduler (UTC 04:00, 23:00)",
    )
    args = parser.parse_args()

    if args.daemon:
        run_daemon()
    else:
        run_once()
