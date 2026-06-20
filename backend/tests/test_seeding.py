from app import services
from app.models import QuestionPool, Student, WritingPrompt
from app.seeding import seed_initial_pools

CANNED = [{"type": "fill", "question": "Q", "answer": "1", "solution": "s", "level": 1, "skill": "x"}]
WRITING = {"prompt": "p", "targetWords": ["a", "b", "c"], "lines": 5}


# Class name is what is_timeout_error() keys on.
class APITimeoutError(Exception):
    pass


def _student(db, name="Anam"):
    s = Student(name=name, current_week=1, current_day=1)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def test_seed_initial_pools_success(db_session, monkeypatch):
    monkeypatch.setattr(services, "generate_day_pool", lambda **k: list(CANNED))
    monkeypatch.setattr(services, "generate_writing_prompt", lambda **k: dict(WRITING))
    s = _student(db_session)

    result = seed_initial_pools(db_session, s)
    assert result["succeeded"] == [1, 2, 3]
    assert result["failed"] == []
    assert len(result["prepared"]) == 6  # 2 subjects x 3 days
    assert db_session.query(QuestionPool).count() == 6

    prompts = db_session.query(WritingPrompt).all()
    assert len(prompts) == 1 and prompts[0].day == 3


def test_seed_resilient_to_one_day_timeout(db_session, monkeypatch):
    def gen(**k):
        if k["day"] == 2:
            raise APITimeoutError("timed out")
        return list(CANNED)

    monkeypatch.setattr(services, "generate_day_pool", gen)
    monkeypatch.setattr(services, "generate_writing_prompt", lambda **k: dict(WRITING))
    s = _student(db_session)

    result = seed_initial_pools(db_session, s)
    assert result["succeeded"] == [1, 3]
    assert result["failed"] == [2]
    assert result["timed_out"] is True

    # only days 1 and 3 persisted (math + english each); day 2 rolled back entirely
    assert db_session.query(QuestionPool).filter_by(day=1).count() == 2
    assert db_session.query(QuestionPool).filter_by(day=2).count() == 0
    assert db_session.query(QuestionPool).filter_by(day=3).count() == 2


def test_reseed_only_generates_missing_days(db_session, monkeypatch):
    state = {"fail_day2": True, "calls": 0}

    def gen(**k):
        state["calls"] += 1
        if k["day"] == 2 and state["fail_day2"]:
            raise APITimeoutError("timed out")
        return list(CANNED)

    monkeypatch.setattr(services, "generate_day_pool", gen)
    monkeypatch.setattr(services, "generate_writing_prompt", lambda **k: dict(WRITING))
    s = _student(db_session)

    first = seed_initial_pools(db_session, s)
    assert first["failed"] == [2]
    calls_after_first = state["calls"]  # 6: days 1,3 ok + day 2 both subjects attempted

    # now day 2 succeeds; re-running should ONLY generate day 2 (days 1,3 exist)
    state["fail_day2"] = False
    second = seed_initial_pools(db_session, s)
    assert second["failed"] == []
    assert state["calls"] - calls_after_first == 2  # only math+english for day 2
    assert db_session.query(QuestionPool).filter_by(day=2).count() == 2
