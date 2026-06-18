"""Seed the first few days' pools so the app can be tested immediately.

Generates Week 1, Days 1-3 for both subjects (plus the writing prompt on the
writing day in that range) using the same service path the nightly job uses.
"""
from sqlalchemy.orm import Session

from .services import is_writing_day, prepare_day_pool, prepare_writing_prompt


def seed_initial_pools(
    db: Session,
    student,
    week: int = 1,
    days=(1, 2, 3),
    subjects=("math", "english"),
    count_per_level=None,
) -> list[dict]:
    summary: list[dict] = []
    for subject in subjects:
        for day in days:
            regenerated, rows = prepare_day_pool(
                db, student, subject, week, day, count_per_level=count_per_level
            )
            writing = False
            if subject == "english" and is_writing_day(day):
                _regen, w_row = prepare_writing_prompt(db, student, week, day)
                writing = bool(w_row)
            summary.append(
                {
                    "subject": subject,
                    "week": week,
                    "day": day,
                    "pool_count": len(rows),
                    "regenerated": regenerated,
                    "writing_prompt": writing,
                }
            )
    db.commit()
    return summary
