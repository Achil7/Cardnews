import argparse
import asyncio

from src.logging_config import setup_logging
from src.scheduler.pipeline import run_pipeline
from src.scheduler.meme_pipeline import run_meme_pipeline


def run_once(test: bool = False):
    asyncio.run(run_pipeline(test=test))


def run_meme(test: bool = False):
    asyncio.run(run_meme_pipeline(test=test))


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
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test mode: generate only 1 cardnews",
    )
    parser.add_argument(
        "--meme",
        action="store_true",
        help="Run meme/humor pipeline instead of news",
    )
    args = parser.parse_args()

    if args.daemon:
        run_daemon()
    elif args.meme:
        run_meme(test=args.test)
    else:
        run_once(test=args.test)
