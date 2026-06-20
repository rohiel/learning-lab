"""Seed the first few days' pools so the app can be tested immediately.

Resilient: each (subject, day) is committed independently, so a timeout on one
day doesn't lose the others, and re-running only generates what's still missing
(prepare_day_pool short-circuits when a day's pool already exists).
"""
import logging

from sqlalchemy.orm import Session

from .anthropic_client import is_timeout_error
from .services import is_writing_day, prepare_day_pool, prepare_writing_prompt

log = logging.getLogger("tutor.seeding")


def seed_day(db: Session, student, week: int, day: int, subjects=("math", "english"), count_per_level=None) -> dict:
    """Prepare both subjects (+ writing on writing days) for one day. Commits each
    subject independently and never raises — returns a per-day result dict."""
    items = []
    for subject in subjects:
        rec = {"subject": subject, "week": week, "day": day}
        try:
            regenerated, rows = prepare_day_pool(db, student, subject, week, day, count_per_level=count_per_level)
            writing = False
            if subject == "english" and is_writing_day(day):
                _regen, w_row = prepare_writing_prompt(db, student, week, day)
                writing = bool(w_row)
            db.commit()
            rec.update(ok=True, pool_count=len(rows), regenerated=regenerated, writing_prompt=writing)
        except Exception as e:  # noqa: BLE001
            db.rollback()
            rec.update(ok=False, error=type(e).__name__, timeout=is_timeout_error(e))
            log.warning("seed FAILED %s W%sD%s: %s", subject, week, day, type(e).__name__)
        items.append(rec)

    ok = all(i["ok"] for i in items)
    timed_out = any(i.get("timeout") for i in items if not i["ok"])
    return {"day": day, "ok": ok, "timed_out": timed_out, "items": items}


def seed_initial_pools(
    db: Session,
    student,
    week: int = 1,
    days=(1, 2, 3),
    subjects=("math", "english"),
    count_per_level=None,
) -> dict:
    """Seed several days. Returns {prepared, succeeded, failed, timed_out}; a
    failure on one day doesn't stop the others."""
    day_results = [seed_day(db, student, week, day, subjects, count_per_level) for day in days]
    return {
        "prepared": [item for r in day_results for item in r["items"]],
        "succeeded": [r["day"] for r in day_results if r["ok"]],
        "failed": [r["day"] for r in day_results if not r["ok"]],
        "timed_out": any(r["timed_out"] for r in day_results),
    }
