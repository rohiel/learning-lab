"""Reads a student's weak-spot / retention / practiced-vocab context.

Maps the `weak_spots` table onto the prompt inputs the original app fed the
generator (weakSpots + retentionQueue), and derives practiced vocabulary from
completed English work (for writing prompts). For a brand-new student these are
empty, so generation falls into its "probe and find them" path — exactly like
day 1 in tutor_app.html.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Answer, QuestionPool, Session as SessionModel, WeakSpot


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


def get_practiced_words(db: Session, student_id: int) -> list[str]:
    """Skills/vocab from English questions the student has actually answered.

    Feeds the writing-prompt target words (the original used English session
    skills as `practicedWords`). Empty for a new student -> writing uses its
    built-in default word list.
    """
    try:
        rows = db.scalars(
            select(QuestionPool.skill)
            .join(Answer, Answer.question_id == QuestionPool.id)
            .join(SessionModel, SessionModel.id == Answer.session_id)
            .where(
                SessionModel.student_id == student_id,
                QuestionPool.subject == "english",
                QuestionPool.skill.isnot(None),
            )
        ).all()
    except Exception:
        return []
    return list(dict.fromkeys(rows))[-30:]
