from app.config import settings
from app.scheduler import build_scheduler


def test_build_scheduler_registers_nightly_cron_job():
    sched = build_scheduler()
    sched.start()
    try:
        job = sched.get_job("nightly-pregen")
        assert job is not None
        trigger = str(job.trigger).lower()
        assert "cron" in trigger
        assert f"hour='{settings.scheduler_hour}'" in trigger
    finally:
        sched.shutdown(wait=False)
