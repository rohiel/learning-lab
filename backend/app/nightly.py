"""Nightly batch logic: decide each student's next day and pre-generate it.

Policy (per the migration spec): tonight prepares tomorrow.
- No completed sessions yet  -> bootstrap the student's current day.
- Last session went well      -> ADVANCE to the next day.
- Last session was a struggle -> REINFORCE: repeat the same day. Its static
  pool already exists, so nothing is regenerated (we honor "a day's pool is
  generated once and is otherwise static"); the reinforcement is that she
  re-does it. When she next advances, the prompt already weights ~70% toward
  her (now larger) weak-spot set.

If you'd rather reinforcement hand her FRESH problems, flip the reinforce path
to call prepare_day_pool(..., force=True) — a one-line change.
"""
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Session as SessionModel, Student
from .services import is_writing_day, prepare_day_pool, prepare_writing_prompt

STRUGGLE_SCORE_RATIO = 0.6
STRUGGLE_HELP_REQUESTS = 4


@dataclass
class PrepTarget:
    subject: str
    week: int
    day: int
    reason: str  # bootstrap | advance | reinforce


def advance_day(week: int, day: int) -> tuple[int, int]:
    if day < 7:
        return week, day + 1
    if week < 8:
        return week + 1, 1
    return 8, 7  # capped at the end of the 8-week plan


def _latest_completed(db: Session, student_id: int, subject: str):
    return db.scalars(
        select(SessionModel)
        .where(
            SessionModel.student_id == student_id,
            SessionModel.subject == subject,
            SessionModel.mode == "practice",
            SessionModel.completed_at.isnot(None),
        )
        .order_by(SessionModel.started_at.desc())
    ).first()


def _is_struggling(session) -> bool:
    if session.total:
        if (session.score or 0) / session.total < STRUGGLE_SCORE_RATIO:
            return True
    if (session.help_requests or 0) >= STRUGGLE_HELP_REQUESTS:
        return True
    return False


def decide_next_day(db: Session, student, subject: str) -> PrepTarget:
    last = _latest_completed(db, student.id, subject)
    if last is None:
        return PrepTarget(subject, student.current_week, student.current_day, "bootstrap")
    if _is_struggling(last):
        return PrepTarget(subject, last.week, last.day, "reinforce")
    nw, nd = advance_day(last.week, last.day)
    return PrepTarget(subject, nw, nd, "advance")


def prepare_for_target(db: Session, student, target: PrepTarget) -> dict:
    regenerated, rows = prepare_day_pool(db, student, target.subject, target.week, target.day)
    writing = False
    if target.subject == "english" and is_writing_day(target.day):
        _w_regen, w_row = prepare_writing_prompt(db, student, target.week, target.day)
        writing = bool(w_row)
    return {
        "student_id": student.id,
        "subject": target.subject,
        "week": target.week,
        "day": target.day,
        "reason": target.reason,
        "pool_count": len(rows),
        "regenerated": regenerated,
        "writing_prompt": writing,
    }


def run_nightly(db: Session, subjects=("math", "english")) -> list[dict]:
    """Prepare the next day for every student × subject. Resilient: one
    failure (e.g. an API error) is recorded and the run continues."""
    students = db.scalars(select(Student)).all()
    summary: list[dict] = []
    for student in students:
        for subject in subjects:
            try:
                target = decide_next_day(db, student, subject)
                summary.append(prepare_for_target(db, student, target))
            except Exception as e:  # noqa: BLE001
                summary.append({"student_id": student.id, "subject": subject, "error": str(e)})
    db.commit()
    return summary
