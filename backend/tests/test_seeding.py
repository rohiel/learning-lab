from app import services
from app.models import QuestionPool, Student, WritingPrompt
from app.seeding import seed_initial_pools

CANNED = [{"type": "fill", "question": "Q", "answer": "1", "solution": "s", "level": 1, "skill": "x"}]
WRITING = {"prompt": "p", "targetWords": ["a", "b", "c"], "lines": 5}


def test_seed_initial_pools(db_session, monkeypatch):
    monkeypatch.setattr(services, "generate_day_pool", lambda **k: list(CANNED))
    monkeypatch.setattr(services, "generate_writing_prompt", lambda **k: dict(WRITING))

    s = Student(name="Anam", current_week=1, current_day=1)
    db_session.add(s)
    db_session.commit()
    db_session.refresh(s)

    summary = seed_initial_pools(db_session, s)
    # 2 subjects x 3 days
    assert len(summary) == 6
    assert db_session.query(QuestionPool).count() == 6  # 1 canned question each

    # writing prompt only for the english writing day in range (day 3)
    prompts = db_session.query(WritingPrompt).all()
    assert len(prompts) == 1 and prompts[0].day == 3
