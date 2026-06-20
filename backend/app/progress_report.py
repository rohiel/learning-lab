"""Aggregations for the home screen, the per-day review modal, and the parent
review — derived entirely from sessions / answers / weak_spots / progress_flags.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import (
    Answer,
    ProgressFlag,
    QuestionPool,
    Session as SessionModel,
    Student,
    WeakSpot,
)

_SUBJECTS = ("math", "english")


def _bucket_weak_spots(rows):
    weak = {s: [] for s in _SUBJECTS}
    retention = {s: [] for s in _SUBJECTS}
    mastered = {s: [] for s in _SUBJECTS}
    for r in rows:
        if r.subject not in weak:
            continue
        if r.status == "learning":
            weak[r.subject].append(r.skill)
        elif r.status in ("short_term", "long_term"):
            retention[r.subject].append(r.skill)
        elif r.status == "mastered":
            mastered[r.subject].append(r.skill)
    return weak, retention, mastered


def build_progress(db: Session, student_id: int):
    student = db.get(Student, student_id)
    if not student:
        return None

    sessions = db.scalars(select(SessionModel).where(SessionModel.student_id == student_id)).all()
    flags = db.scalars(select(ProgressFlag).where(ProgressFlag.student_id == student_id)).all()
    answered_session_ids = set(
        db.scalars(
            select(Answer.session_id).where(Answer.session_id.in_([s.id for s in sessions]))
        ).all()
    ) if sessions else set()

    day_map: dict = {}
    week_map: dict = {}
    writing_this_week: dict = {}

    for s in sessions:
        if s.mode == "practice" and s.completed_at:
            d = day_map.setdefault((s.subject, s.week, s.day), {"done": False, "manual": False, "has_records": False})
            d["done"] = True
            if s.id in answered_session_ids:
                d["has_records"] = True
        elif s.mode == "test" and s.completed_at:
            w = week_map.setdefault((s.subject, s.week), {"complete": False, "manual": False})
            w["complete"] = True
        elif s.mode == "writing" and s.completed_at:
            writing_this_week[s.week] = writing_this_week.get(s.week, 0) + 1

    for f in flags:
        if f.kind == "day" and f.day is not None:
            d = day_map.setdefault((f.subject, f.week, f.day), {"done": False, "manual": False, "has_records": False})
            if f.done:
                d["done"] = True
                d["manual"] = True
        elif f.kind == "week":
            w = week_map.setdefault((f.subject, f.week), {"complete": False, "manual": False})
            if f.done:
                w["complete"] = True
                w["manual"] = True

    days = [{"subject": k[0], "week": k[1], "day": k[2], **v} for k, v in sorted(day_map.items())]
    weeks = [{"subject": k[0], "week": k[1], **v} for k, v in sorted(week_map.items())]

    weak, retention, mastered = _bucket_weak_spots(
        db.scalars(select(WeakSpot).where(WeakSpot.student_id == student_id)).all()
    )

    return {
        "student": {
            "id": student.id,
            "name": student.name,
            "current_week": student.current_week,
            "current_day": student.current_day,
        },
        "days": days,
        "weeks": weeks,
        "weak_spots": weak,
        "retention": retention,
        "mastered": mastered,
        "help_total": sum((s.help_requests or 0) for s in sessions),
        "writing_this_week": writing_this_week,
    }


def build_day_records(db: Session, student_id: int, subject: str, week: int, day: int):
    sess = db.scalars(
        select(SessionModel)
        .where(
            SessionModel.student_id == student_id,
            SessionModel.subject == subject,
            SessionModel.week == week,
            SessionModel.day == day,
            SessionModel.mode == "practice",
            SessionModel.completed_at.isnot(None),
        )
        .order_by(SessionModel.started_at.desc())
    ).first()
    if not sess:
        return None

    answers = db.scalars(select(Answer).where(Answer.session_id == sess.id)).all()
    qmap = (
        {q.id: q for q in db.scalars(select(QuestionPool).where(QuestionPool.id.in_([a.question_id for a in answers]))).all()}
        if answers
        else {}
    )
    records = []
    for a in answers:
        q = qmap.get(a.question_id)
        if not q:
            continue
        records.append(
            {
                "question": q.question,
                "level": q.level,
                "skill": q.skill,
                "type": q.type,
                "passage": q.passage,
                "given": a.given,
                "correct": a.correct,
                "expected": q.answer,
            }
        )
    return {"subject": subject, "week": week, "day": day, "score": sess.score, "total": sess.total, "records": records}


def build_review_log(db: Session, student_id: int, limit: int = 12):
    """Compact log shaped like the original parentReview input."""
    sessions = db.scalars(
        select(SessionModel)
        .where(SessionModel.student_id == student_id, SessionModel.completed_at.isnot(None))
        .order_by(SessionModel.started_at.desc())
    ).all()[:limit]

    log_sessions = []
    for s in sessions:
        answers = db.scalars(select(Answer).where(Answer.session_id == s.id)).all()
        qmap = (
            {q.id: q for q in db.scalars(select(QuestionPool).where(QuestionPool.id.in_([a.question_id for a in answers]))).all()}
            if answers
            else {}
        )
        weak_skills = sorted(
            {qmap[a.question_id].skill for a in answers if not a.correct and qmap.get(a.question_id) and qmap[a.question_id].skill}
        )
        retention_results = [
            {"skill": qmap[a.question_id].skill, "correct": a.correct}
            for a in answers
            if qmap.get(a.question_id) and qmap[a.question_id].retention
        ]
        log_sessions.append(
            {
                "subject": s.subject,
                "week": s.week,
                "day": s.day,
                "mode": s.mode,
                "score": s.score,
                "total": s.total,
                "maxLevel": s.max_level,
                "helpRequests": s.help_requests,
                "weakSkills": weak_skills,
                "retentionResults": retention_results,
            }
        )

    weak, retention, mastered = _bucket_weak_spots(
        db.scalars(select(WeakSpot).where(WeakSpot.student_id == student_id)).all()
    )
    log = {
        "sessions": log_sessions,
        "weakSpots": weak,
        "mastered": mastered,
        "retentionQueue": retention,
    }
    return log, len(log_sessions)
