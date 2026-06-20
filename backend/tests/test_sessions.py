from app import sessions
from app.models import Answer, QuestionPool, Student, WeakSpot
from app.sessions import (
    finalize_session,
    get_session_questions,
    record_answer,
    select_session_questions,
    session_count,
    start_or_resume_session,
)


def _student(db):
    s = Student(name="T", current_week=1, current_day=1)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def _pool(db, student_id, subject="math", week=1, day=1, per_level=5):
    for lvl in range(1, 6):
        for i in range(per_level):
            db.add(
                QuestionPool(
                    student_id=student_id, subject=subject, week=week, day=day, level=lvl,
                    type="fill", question=f"L{lvl}Q{i}", answer=f"ans-{lvl}-{i}",
                    solution="sol", skill=f"skill{lvl}",
                )
            )
    db.commit()


def test_select_is_ordered_easy_to_hard(db_session):
    s = _student(db_session)
    _pool(db_session, s.id, per_level=6)  # 30 questions
    pool = db_session.query(QuestionPool).all()
    chosen = select_session_questions(pool, 12)
    levels = [c.level for c in chosen]
    assert len(chosen) == 12
    assert levels == sorted(levels)  # non-decreasing easy->hard
    assert levels[0] == 1  # starts easy


def test_start_locks_and_resumes(db_session):
    s = _student(db_session)
    _pool(db_session, s.id)
    sess, created = start_or_resume_session(db_session, s, "math", 1, 1, "practice")
    db_session.commit()
    assert created is True
    ids = sess.selected_question_ids
    assert len(ids) == session_count("practice", 1)

    sess2, created2 = start_or_resume_session(db_session, s, "math", 1, 1, "practice")
    assert created2 is False
    assert sess2.id == sess.id and sess2.selected_question_ids == ids  # SAME locked set


def test_start_without_pool_returns_none(db_session):
    s = _student(db_session)
    sess, _ = start_or_resume_session(db_session, s, "math", 1, 1, "practice")
    assert sess is None


def test_record_answer_correct_then_wrong(db_session, monkeypatch):
    s = _student(db_session)
    _pool(db_session, s.id)
    sess, _ = start_or_resume_session(db_session, s, "math", 1, 1, "practice")
    db_session.commit()
    qs = get_session_questions(db_session, sess)

    monkeypatch.setattr(sessions, "grade_answer", lambda *a, **k: {"correct": True, "reason": ""})
    res = record_answer(db_session, sess, qs[0], qs[0].answer)
    db_session.commit()
    assert res["correct"] is True and res["hint"] is None and res["correct_answer"] == qs[0].answer

    monkeypatch.setattr(sessions, "grade_answer", lambda *a, **k: {"correct": False, "reason": "nope"})
    monkeypatch.setattr(sessions, "get_hint", lambda *a, **k: "think about it")
    res2 = record_answer(db_session, sess, qs[1], "wrong")
    db_session.commit()
    assert res2["correct"] is False and res2["hint"] == "think about it"
    assert db_session.query(Answer).count() == 2


def test_finalize_updates_weak_spots(db_session):
    s = _student(db_session)
    _pool(db_session, s.id)
    sess, _ = start_or_resume_session(db_session, s, "math", 1, 1, "practice")
    db_session.commit()
    qs = get_session_questions(db_session, sess)
    q_wrong = next(q for q in qs if q.level == 3)
    q_right = next(q for q in qs if q.level == 2)
    db_session.add(Answer(session_id=sess.id, question_id=q_wrong.id, given="x", correct=False, tries=1))
    db_session.add(Answer(session_id=sess.id, question_id=q_right.id, given="y", correct=True, tries=1))
    db_session.commit()

    result = finalize_session(db_session, sess)
    db_session.commit()
    assert result["total"] == 2 and result["score"] == 1 and result["max_level"] == 3

    learning = {w.skill for w in db_session.query(WeakSpot).filter_by(status="learning")}
    short_term = {w.skill for w in db_session.query(WeakSpot).filter_by(status="short_term")}
    assert q_wrong.skill in learning  # missed -> weak spot
    assert q_right.skill in short_term  # correct at level>=2 -> retention queue
    assert sess.completed_at is not None
