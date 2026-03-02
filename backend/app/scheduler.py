"""Background scheduler for daily job ingestion.
Uses APScheduler to run all ingestion sources every morning at a configurable time.

How it works:
- On app startup, a CronTrigger schedules `run_all_ingestion()` daily
- Default schedule: every day at 6:00 AM UTC (configurable via SCHEDULER_HOUR env var)
- The job runs sequentially through all sources: greenhouse, remoteok, arbeitnow, himalayas, jobicy, ashby
- Each source is wrapped in try/except so one failure doesn't stop others
- Logs results to stdout and the ingestion_runs table

To change the schedule time, set SCHEDULER_HOUR in .env (0-23, UTC):
  SCHEDULER_HOUR=8   # runs at 8 AM UTC

To disable the scheduler entirely:
  SCHEDULER_ENABLED=false
"""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.db.database import SessionLocal

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def run_all_ingestion():
    """Run ingestion from all sources. Called by the scheduler."""
    logger.info("⏰ Scheduled ingestion starting...")
    db = SessionLocal()

    sources = [
        ("greenhouse", "app.ingestion.greenhouse", "run_greenhouse_ingestion"),
        ("remoteok", "app.ingestion.remoteok", "run_remoteok_ingestion"),
        ("arbeitnow", "app.ingestion.arbeitnow", "run_arbeitnow_ingestion"),
        ("himalayas", "app.ingestion.himalayas", "run_himalayas_ingestion"),
        ("jobicy", "app.ingestion.jobicy", "run_jobicy_ingestion"),
        ("ashby", "app.ingestion.ashby", "run_ashby_ingestion"),
    ]

    total_inserted = 0
    total_updated = 0

    try:
        for name, module_path, func_name in sources:
            try:
                import importlib
                module = importlib.import_module(module_path)
                ingest_fn = getattr(module, func_name)
                run = ingest_fn(db)
                logger.info(
                    f"  ✅ {name}: fetched={run.jobs_fetched}, "
                    f"inserted={run.jobs_inserted}, updated={run.jobs_updated}"
                )
                total_inserted += run.jobs_inserted
                total_updated += run.jobs_updated
            except Exception as e:
                logger.error(f"  ❌ {name} failed: {e}")
    finally:
        db.close()

    logger.info(
        f"⏰ Scheduled ingestion complete: "
        f"inserted={total_inserted}, updated={total_updated}"
    )


def start_scheduler():
    """Start the background scheduler if enabled."""
    enabled = getattr(settings, "scheduler_enabled", True)
    if not enabled:
        logger.info("Scheduler is disabled (SCHEDULER_ENABLED=false)")
        return

    hour = getattr(settings, "scheduler_hour", 6)

    scheduler.add_job(
        run_all_ingestion,
        trigger=CronTrigger(hour=hour, minute=0),
        id="daily_ingestion",
        name="Daily job ingestion from all sources",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(f"📅 Scheduler started: daily ingestion at {hour:02d}:00 UTC")


def stop_scheduler():
    """Shut down the scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
