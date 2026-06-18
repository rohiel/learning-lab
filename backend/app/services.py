"""Reusable preparation services shared by the admin endpoints, the nightly
scheduler, and the seed script.

Keeping pool / writing-prompt creation here (not in a router) means the nightly
job and the manual triggers run the exact same, tested code path. None of these
commit — the caller owns the transaction.
"""
from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from .generation import generate_day_pool, generate_writing_prompt
from .models import QuestionPool, WritingPrompt
from .progress import get_practiced_words, get_retention_queue, get_weak_spots

# Writing is due twice a week; these are the designated writing days (1-7).
WRITING_DAYS = (3, 6)


def is_writing_day(day: int) -> bool:
    return day in WRITING_DAYS


def existing_pool(db: Session, student_id: int, subject: str, week: int, day: int):
    return db.scalars(
        select(QuestionPool).where(
            QuestionPool.student_id == student_id,
            QuestionPool.subject == subject,
            QuestionPool.week == week,
            QuestionPool.day == day,
        )
    ).all()


def existing_writing_prompt(db: Session, student_id: int, week: int, day: int):
    return db.scalar(
        select(WritingPrompt).where(
            WritingPrompt.student_id == student_id,
            WritingPrompt.week == week,
            WritingPrompt.day == day,
        )
    )


def per_level_counts(rows) -> dict[int, int]:
    return dict(sorted(Counter(r.level for r in rows).items()))


def _to_row(student_id, subject, week, day, q) -> QuestionPool:
    return QuestionPool(
        student_id=student_id,
        subject=subject,
        week=week,
        day=day,
        level=int(q.get("level") or 1),
        type=q.get("type", "fill"),
        passage=q.get("passage"),
        question=q.get("question", ""),
        choices=q.get("choices"),
        answer=str(q.get("answer", "")),
        solution=q.get("solution"),
        skill=q.get("skill"),
        retention=bool(q.get("retention")),
        connection=bool(q.get("connection")),
        has_distractor=bool(q.get("hasDistractor")),
        distractor_note=q.get("distractorNote"),
    )


def prepare_day_pool(db: Session, student, subject, week, day, force=False, count_per_level=None):
    """Ensure a day's pool exists. Returns (regenerated, rows).

    A day's pool is generated ONCE and is otherwise static. A failed generation
    NEVER destroys an existing pool. Caller commits.
    """
    existing = existing_pool(db, student.id, subject, week, day)
    if existing and not force:
        return False, existing

    weak = get_weak_spots(db, student.id, subject)
    retention = get_retention_queue(db, student.id, subject)
    questions = generate_day_pool(
        subject=subject,
        week=week,
        day=day,
        weak_spots=weak,
        retention_queue=retention,
        count_per_level=count_per_level,
    )
    rows = [_to_row(student.id, subject, week, day, q) for q in questions]
    if not rows:
        # generation failed — leave any existing pool intact
        return False, existing

    if existing and force:
        for r in existing:
            db.delete(r)
        db.flush()
    db.add_all(rows)
    return True, rows


def prepare_writing_prompt(db: Session, student, week, day, force=False):
    """Ensure a writing prompt exists for (student, week, day). Returns
    (regenerated, row). Caller commits."""
    existing = existing_writing_prompt(db, student.id, week, day)
    if existing and not force:
        return False, existing

    practiced = get_practiced_words(db, student.id)
    weak = get_weak_spots(db, student.id, "english")
    p = generate_writing_prompt(week=week, day=day, practiced_words=practiced, weak_spots=weak)
    if not p or not p.get("prompt"):
        return False, existing

    if existing and force:
        db.delete(existing)
        db.flush()
    row = WritingPrompt(
        student_id=student.id,
        week=week,
        day=day,
        prompt=p.get("prompt", ""),
        target_words=p.get("targetWords"),
        lines=int(p.get("lines") or 5),
    )
    db.add(row)
    return True, row
