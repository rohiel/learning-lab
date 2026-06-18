"""APScheduler wiring for the nightly pre-generation job.

A single cron job runs at SCHEDULER_HOUR in SCHEDULER_TZ (default 8 PM
America/New_York — DST-aware, so it's always ~8 PM her time). The job reads each
student's progress and pre-generates tomorrow's pool, so the morning app just
READS.
"""
import logging

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .config import settings
from .db import SessionLocal
from .nightly import run_nightly

log = logging.getLogger("tutor.scheduler")

_scheduler: BackgroundScheduler | None = None


def run_nightly_job() -> None:
    """Entry point the scheduler invokes. Owns its own DB session."""
    db = SessionLocal()
    try:
        summary = run_nightly(db)
        prepared = sum(1 for s in summary if "error" not in s)
        errors = [s for s in summary if "error" in s]
        log.info("Nightly run complete: %d prepared, %d errors", prepared, len(errors))
        for e in errors:
            log.warning("Nightly item failed: %s", e)
    except Exception:
        log.exception("Nightly run failed")
    finally:
        db.close()


def build_scheduler() -> BackgroundScheduler:
    """Construct (but do not start) the scheduler with the nightly job."""
    tz = pytz.timezone(settings.scheduler_tz)
    sched = BackgroundScheduler(timezone=tz)
    sched.add_job(
        run_nightly_job,
        CronTrigger(hour=settings.scheduler_hour, minute=0, timezone=tz),
        id="nightly-pregen",
        replace_existing=True,
        misfire_grace_time=3600,  # if the host was asleep at 8 PM, still run within the hour
    )
    return sched


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = build_scheduler()
        _scheduler.start()
        log.info(
            "Scheduler started: nightly pre-gen at %02d:00 %s",
            settings.scheduler_hour,
            settings.scheduler_tz,
        )
    return _scheduler


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
