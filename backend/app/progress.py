"""Reads a student's weak-spot / retention context for generation.

Maps the `weak_spots` table onto the two prompt inputs the original app fed the
generator (weakSpots + retentionQueue). For a brand-new student both are empty,
so the generator falls into its "probe and find them" path — exactly like day 1
in tutor_app.html.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import WeakSpot


def get_weak_spots(db: Session, student_id: int, subject: str) -> list[str]:
    """Active weak spots to weight ~70% of questions toward."""
    rows = db.scalars(
        select(WeakSpot.skill).where(
            WeakSpot.student_id == student_id,
            WeakSpot.subject == subject,
            WeakSpot.status.in_(["learning", "short_term"]),
        )
    ).all()
    # de-dupe preserving order, keep the most recent 12 (matches the app's cap)
    return list(dict.fromkeys(rows))[-12:]


def get_retention_queue(db: Session, student_id: int, subject: str) -> list[str]:
    """Previously-learned skills to re-test for long-term retention."""
    rows = db.scalars(
        select(WeakSpot.skill).where(
            WeakSpot.student_id == student_id,
            WeakSpot.subject == subject,
            WeakSpot.status.in_(["short_term", "long_term"]),
        )
    ).all()
    return list(dict.fromkeys(rows))[:3]
