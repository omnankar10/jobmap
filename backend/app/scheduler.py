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
import sys
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.db.database import SessionLocal

# Configure logging to output to stdout (visible in Docker logs)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("scheduler")

scheduler = BackgroundScheduler()


def run_all_ingestion():
    """Run ingestion from all sources. Called by the scheduler."""
    print(f"[{datetime.utcnow().isoformat()}] ⏰ Scheduled ingestion starting...", flush=True)
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
    total_fetched = 0

    try:
        for name, module_path, func_name in sources:
            try:
                import importlib
                module = importlib.import_module(module_path)
                ingest_fn = getattr(module, func_name)
                run = ingest_fn(db)
                msg = (
                    f"  ✅ {name}: fetched={run.jobs_fetched}, "
                    f"inserted={run.jobs_inserted}, updated={run.jobs_updated}"
                )
                print(msg, flush=True)
                logger.info(msg)
                total_inserted += run.jobs_inserted
                total_updated += run.jobs_updated
                total_fetched += run.jobs_fetched
            except Exception as e:
                msg = f"  ❌ {name} failed: {e}"
                print(msg, flush=True)
                logger.error(msg)
    finally:
        db.close()

    summary = (
        f"⏰ Scheduled ingestion complete: "
        f"fetched={total_fetched}, inserted={total_inserted}, updated={total_updated}"
    )
    print(f"[{datetime.utcnow().isoformat()}] {summary}", flush=True)
    logger.info(summary)


def start_scheduler():
    """Start the background scheduler if enabled."""
    enabled = getattr(settings, "scheduler_enabled", True)
    if not enabled:
        print("📅 Scheduler is DISABLED (SCHEDULER_ENABLED=false)", flush=True)
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
    print(f"📅 Scheduler started: daily ingestion at {hour:02d}:00 UTC", flush=True)
    print(f"📅 Next run: {scheduler.get_job('daily_ingestion').next_run_time}", flush=True)


def stop_scheduler():
    """Shut down the scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        print("📅 Scheduler stopped", flush=True)
