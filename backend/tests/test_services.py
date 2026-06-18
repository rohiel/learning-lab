from app import services
from app.models import QuestionPool, Student, WritingPrompt

CANNED = [
    {"type": "fill", "question": "Q1", "answer": "8", "solution": "s1", "level": 1, "skill": "addition"},
    {"type": "mc", "question": "Q2", "choices": ["1", "2", "3", "4"], "answer": "2", "solution": "s2", "level": 2, "skill": "logic"},
]


def _student(db):
    s = Student(name="T", current_week=1, current_day=1)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def test_prepare_day_pool_idempotent(db_session, monkeypatch):
    monkeypatch.setattr(services, "generate_day_pool", lambda **k: list(CANNED))
    s = _student(db_session)

    regen, rows = services.prepare_day_pool(db_session, s, "math", 1, 1)
    db_session.commit()
    assert regen is True and len(rows) == 2

    regen2, rows2 = services.prepare_day_pool(db_session, s, "math", 1, 1)
    assert regen2 is False and len(rows2) == 2
    assert db_session.query(QuestionPool).count() == 2  # not duplicated


def test_force_regenerates(db_session, monkeypatch):
    monkeypatch.setattr(services, "generate_day_pool", lambda **k: list(CANNED))
    s = _student(db_session)
    services.prepare_day_pool(db_session, s, "math", 1, 2)
    db_session.commit()

    regen, rows = services.prepare_day_pool(db_session, s, "math", 1, 2, force=True)
    db_session.commit()
    assert regen is True
    assert db_session.query(QuestionPool).filter_by(day=2).count() == 2  # replaced, not appended


def test_failed_regeneration_keeps_existing(db_session, monkeypatch):
    monkeypatch.setattr(services, "generate_day_pool", lambda **k: list(CANNED))
    s = _student(db_session)
    services.prepare_day_pool(db_session, s, "math", 1, 3)
    db_session.commit()

    # generation now yields nothing on a forced regen -> keep the existing pool
    monkeypatch.setattr(services, "generate_day_pool", lambda **k: [])
    regen, rows = services.prepare_day_pool(db_session, s, "math", 1, 3, force=True)
    assert regen is False and len(rows) == 2


def test_prepare_writing_prompt(db_session, monkeypatch):
    monkeypatch.setattr(
        services,
        "generate_writing_prompt",
        lambda **k: {"prompt": "Write about a glowing rock.", "targetWords": ["mineral", "specimen", "fragile"], "lines": 5},
    )
    s = _student(db_session)

    regen, row = services.prepare_writing_prompt(db_session, s, 1, 3)
    db_session.commit()
    assert regen is True and row.lines == 5 and len(row.target_words) == 3

    regen2, _ = services.prepare_writing_prompt(db_session, s, 1, 3)
    assert regen2 is False
    assert db_session.query(WritingPrompt).count() == 1
