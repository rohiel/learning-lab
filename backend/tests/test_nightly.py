from datetime import datetime, timezone

from app import services
from app.models import Session as SessionModel, Student
from app.nightly import advance_day, decide_next_day, run_nightly
from app.services import is_writing_day

CANNED = [{"type": "fill", "question": "Q", "answer": "1", "solution": "s", "level": 1, "skill": "x"}]
WRITING = {"prompt": "p", "targetWords": ["a", "b", "c"], "lines": 5}


def _student(db, week=2, day=4):
    s = Student(name="T", current_week=week, current_day=day)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def _completed(db, student_id, subject, week, day, score, total, help_requests=0):
    sess = SessionModel(
        student_id=student_id, subject=subject, week=week, day=day, mode="practice",
        score=score, total=total, help_requests=help_requests,
        completed_at=datetime.now(timezone.utc),
    )
    db.add(sess)
    db.commit()


def test_advance_day_wraps():
    assert advance_day(1, 1) == (1, 2)
    assert advance_day(1, 7) == (2, 1)
    assert advance_day(8, 7) == (8, 7)  # capped


def test_is_writing_day():
    assert is_writing_day(3) and is_writing_day(6)
    assert not is_writing_day(1) and not is_writing_day(7)


def test_decide_bootstrap(db_session):
    s = _student(db_session, week=2, day=4)
    t = decide_next_day(db_session, s, "math")
    assert (t.week, t.day, t.reason) == (2, 4, "bootstrap")


def test_decide_advance_on_good_score(db_session):
    s = _student(db_session)
    _completed(db_session, s.id, "math", 1, 1, score=11, total=12)
    t = decide_next_day(db_session, s, "math")
    assert (t.week, t.day, t.reason) == (1, 2, "advance")


def test_decide_reinforce_on_low_score(db_session):
    s = _student(db_session)
    _completed(db_session, s.id, "math", 1, 2, score=4, total=12)  # 33%
    t = decide_next_day(db_session, s, "math")
    assert (t.week, t.day, t.reason) == (1, 2, "reinforce")


def test_decide_reinforce_on_many_help_requests(db_session):
    s = _student(db_session)
    _completed(db_session, s.id, "english", 1, 1, score=10, total=12, help_requests=5)
    t = decide_next_day(db_session, s, "english")
    assert t.reason == "reinforce"


def test_run_nightly_prepares_both_subjects(db_session, monkeypatch):
    monkeypatch.setattr(services, "generate_day_pool", lambda **k: list(CANNED))
    monkeypatch.setattr(services, "generate_writing_prompt", lambda **k: dict(WRITING))
    _student(db_session, week=2, day=4)  # day 4 -> not a writing day
    summary = run_nightly(db_session)
    assert len(summary) == 2
    assert {item["subject"] for item in summary} == {"math", "english"}
    assert all(item["pool_count"] == 1 for item in summary)
    assert all(item["writing_prompt"] is False for item in summary)


def test_run_nightly_generates_writing_on_writing_day(db_session, monkeypatch):
    monkeypatch.setattr(services, "generate_day_pool", lambda **k: list(CANNED))
    monkeypatch.setattr(services, "generate_writing_prompt", lambda **k: dict(WRITING))
    _student(db_session, week=1, day=3)  # day 3 -> writing day
    summary = run_nightly(db_session)
    english = next(i for i in summary if i["subject"] == "english")
    math = next(i for i in summary if i["subject"] == "math")
    assert english["day"] == 3 and english["writing_prompt"] is True
    assert math["writing_prompt"] is False  # writing is english-only
