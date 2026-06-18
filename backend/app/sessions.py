"""Session lifecycle: select+lock questions, grade answers, finalize.

This is the server-authoritative game loop. The `solution` and `answer` never
leave the server — grading and help read them here. Selection picks a
level-distributed sample ordered easy->hard (mirroring the original generated
array), then LOCKS the ids on the session row so refresh/resume returns the
exact same questions.
"""
import random
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .curriculum import MODES, practice_count
from .grading import get_hint, grade_answer
from .models import Answer, QuestionPool, Session as SessionModel, WeakSpot
from .services import existing_pool

# Gentle easy->hard ramp across levels 1..5 (more low, fewer high), matching the
# original "order easy -> hard starting around level 1" feel.
LEVEL_WEIGHTS = [0.28, 0.24, 0.20, 0.16, 0.12]


def _allocate(count: int) -> list[int]:
    raw = [count * w for w in LEVEL_WEIGHTS]
    base = [int(x) for x in raw]
    order = sorted(range(5), key=lambda i: raw[i] - base[i], reverse=True)
    for i in range(count - sum(base)):
        base[order[i % 5]] += 1
    return base


def select_session_questions(pool_rows, count: int):
    """Pick `count` questions, level-distributed, ordered easy->hard."""
    count = min(count, len(pool_rows))
    by_level = {lvl: [r for r in pool_rows if r.level == lvl] for lvl in range(1, 6)}
    for lvl in by_level:
        random.shuffle(by_level[lvl])

    targets = _allocate(count)
    chosen, leftover = [], []
    for idx, lvl in enumerate(range(1, 6)):
        bucket = by_level[lvl]
        take = min(targets[idx], len(bucket))
        chosen += bucket[:take]
        leftover += bucket[take:]

    random.shuffle(leftover)
    while len(chosen) < count and leftover:
        chosen.append(leftover.pop())

    chosen.sort(key=lambda r: (r.level, random.random()))  # easy->hard, random within level
    return chosen[:count]


def session_count(mode: str, day: int) -> int:
    return practice_count(day) if mode == "practice" else MODES["test"]["count"]


def start_or_resume_session(db: Session, student, subject, week, day, mode):
    """Return (session, created). Resumes an in-progress session for the same
    slot (returning the SAME locked questions), else locks a fresh set.
    Returns (None, False) if no pool is prepared yet."""
    existing = db.scalars(
        select(SessionModel)
        .where(
            SessionModel.student_id == student.id,
            SessionModel.subject == subject,
            SessionModel.week == week,
            SessionModel.day == day,
            SessionModel.mode == mode,
            SessionModel.completed_at.is_(None),
        )
        .order_by(SessionModel.started_at.desc())
    ).first()
    if existing and existing.selected_question_ids:
        return existing, False

    pool = existing_pool(db, student.id, subject, week, day)
    if not pool:
        return None, False

    selected = select_session_questions(pool, session_count(mode, day))
    sess = SessionModel(
        student_id=student.id,
        subject=subject,
        week=week,
        day=day,
        mode=mode,
        selected_question_ids=[r.id for r in selected],
    )
    db.add(sess)
    db.flush()
    return sess, True


def get_session_questions(db: Session, session) -> list:
    ids = session.selected_question_ids or []
    rows = {r.id: r for r in db.scalars(select(QuestionPool).where(QuestionPool.id.in_(ids))).all()}
    return [rows[i] for i in ids if i in rows]  # preserve the locked order


def get_session_answers(db: Session, session) -> list:
    return db.scalars(select(Answer).where(Answer.session_id == session.id)).all()


def record_answer(db: Session, session, question, given: str, needed_help: bool = False) -> dict:
    """Grade one answer (exact/normalized first, model only if needed), record
    it, and return correctness + a Socratic hint (server-side) when wrong."""
    result = grade_answer(session.subject, question.question, question.answer, given, question.skill)
    correct = bool(result.get("correct"))

    existing = db.scalar(
        select(Answer).where(Answer.session_id == session.id, Answer.question_id == question.id)
    )
    if existing:
        existing.given = given
        existing.correct = correct
        existing.tries = (existing.tries or 1) + 1
        if needed_help:
            existing.needed_help = True
    else:
        db.add(
            Answer(
                session_id=session.id,
                question_id=question.id,
                given=given,
                correct=correct,
                tries=1,
                needed_help=needed_help,
            )
        )

    hint = None
    if not correct:
        try:
            hint = get_hint(
                session.subject,
                question.question,
                given,
                question.answer,
                question.has_distractor,
                question.distractor_note or "",
            )
        except Exception:
            hint = "Take another look — walk through it one step at a time."

    return {
        "correct": correct,
        "hint": hint,
        "correct_answer": question.answer,
        "reason": result.get("reason", ""),
    }


def _set_weak_status(db, student_id, subject, skill, status, now, only_if_absent=False):
    row = db.scalar(
        select(WeakSpot).where(
            WeakSpot.student_id == student_id,
            WeakSpot.subject == subject,
            WeakSpot.skill == skill,
        )
    )
    if row is None:
        db.add(WeakSpot(student_id=student_id, subject=subject, skill=skill, status=status, last_tested=now))
        return
    row.last_tested = now
    if only_if_absent:
        return  # a single correct doesn't clear an already-tracked weak spot
    row.status = status


def finalize_session(db: Session, session) -> dict:
    """Score the session and update weak-spots/retention/mastery (mirrors the
    original finish()). Status mapping:
      missed skill                  -> learning   (active weak spot, ~70% weighted)
      correct at level>=2 (new)     -> short_term (retention queue, re-tested)
      retention question passed     -> mastered
    """
    answers = get_session_answers(db, session)
    qids = [a.question_id for a in answers]
    qmap = (
        {q.id: q for q in db.scalars(select(QuestionPool).where(QuestionPool.id.in_(qids))).all()}
        if qids
        else {}
    )

    score = sum(1 for a in answers if a.correct)
    total = len(answers)
    levels = [qmap[a.question_id].level for a in answers if a.question_id in qmap]
    max_level = max(levels) if levels else 1
    now = datetime.now(timezone.utc)

    missed, learned, retention_passed = set(), set(), set()
    for a in answers:
        q = qmap.get(a.question_id)
        if not q or not q.skill:
            continue
        if a.correct:
            if q.retention:
                retention_passed.add(q.skill)
            elif q.level >= 2:
                learned.add(q.skill)
        else:
            missed.add(q.skill)

    for skill in missed:
        _set_weak_status(db, session.student_id, session.subject, skill, "learning", now)
    for skill in learned:
        _set_weak_status(db, session.student_id, session.subject, skill, "short_term", now, only_if_absent=True)
    for skill in retention_passed:
        _set_weak_status(db, session.student_id, session.subject, skill, "mastered", now)

    session.score = score
    session.total = total
    session.max_level = max_level
    session.completed_at = now
    return {
        "score": score,
        "total": total,
        "max_level": max_level,
        "weak_skills": sorted(missed),
        "retention_passed": sorted(retention_passed),
    }
