"""End-to-end HTTP tests with a mocked generator.

Verifies auth, persistence, per-level counts, idempotency, solution isolation,
and the Phase 2 nightly/seed/writing-prompt endpoints.
"""
from fastapi.testclient import TestClient

# A fixed "generated" pool (3 questions across levels 1, 2, 4).
CANNED = [
    {"type": "fill", "question": "Q1", "answer": "8", "solution": "SECRET-STEPS-1", "level": 1, "skill": "addition"},
    {"type": "mc", "question": "Q2", "choices": ["1", "2", "3", "4"], "answer": "2", "solution": "SECRET-2", "level": 2, "skill": "logic"},
    {"type": "fill", "question": "Q3", "answer": "1.05", "solution": "SECRET-3", "level": 4, "skill": "decimal division"},
]
WRITING = {"prompt": "Write about a glowing rock.", "targetWords": ["mineral", "specimen", "fragile"], "lines": 5}
HEADERS = {"X-API-Key": "test-secret"}


def test_generate_day_flow(monkeypatch):
    from app import services
    from app.db import SessionLocal
    from app.main import app
    from app.models import QuestionPool, Student

    monkeypatch.setattr(services, "generate_day_pool", lambda **kwargs: list(CANNED))

    with TestClient(app) as client:
        db = SessionLocal()
        student = Student(name="Anam", current_week=1, current_day=1)
        db.add(student)
        db.commit()
        sid = student.id
        db.close()

        body = {"student_id": sid, "subject": "math", "week": 1, "day": 1}

        # missing key -> 401
        assert client.post("/api/admin/generate-day", json=body).status_code == 401

        # with key -> generates
        r = client.post("/api/admin/generate-day", headers=HEADERS, json=body)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["regenerated"] is True
        assert data["total"] == 3
        assert data["per_level"] == {"1": 1, "2": 1, "4": 1}

        # idempotent: second call without force returns existing
        r2 = client.post("/api/admin/generate-day", headers=HEADERS, json=body)
        assert r2.json()["regenerated"] is False and r2.json()["total"] == 3

        # solution persisted server-side...
        db = SessionLocal()
        rows = db.query(QuestionPool).filter_by(student_id=sid).all()
        assert any("SECRET" in (row.solution or "") for row in rows)
        db.close()

        # ...and never exposed by the pool endpoint
        r3 = client.get(
            "/api/admin/pool", headers=HEADERS,
            params={"student_id": sid, "subject": "math", "week": 1, "day": 1},
        )
        assert r3.status_code == 200 and "SECRET" not in r3.text and r3.json()["total"] == 3

        assert client.get("/api/health").json() == {"status": "ok"}


def test_seed_run_nightly_and_writing_endpoints(monkeypatch):
    from app import services
    from app.db import SessionLocal
    from app.main import app
    from app.models import Student

    monkeypatch.setattr(services, "generate_day_pool", lambda **k: list(CANNED))
    monkeypatch.setattr(services, "generate_writing_prompt", lambda **k: dict(WRITING))

    with TestClient(app) as client:
        db = SessionLocal()
        student = Student(name="Anam2", current_week=1, current_day=3)
        db.add(student)
        db.commit()
        sid = student.id
        db.close()

        # seed W1 D1+D3 for both subjects
        r = client.post("/api/admin/seed", headers=HEADERS, json={"student_id": sid, "days": [1, 3]})
        assert r.status_code == 200, r.text
        assert len(r.json()["prepared"]) == 4  # 2 subjects x 2 days

        # writing prompt was created for english day 3
        rw = client.get(
            "/api/admin/writing-prompt", headers=HEADERS,
            params={"student_id": sid, "week": 1, "day": 3},
        )
        assert rw.status_code == 200 and rw.json()["lines"] == 5
        assert rw.json()["target_words"] == ["mineral", "specimen", "fragile"]

        # nightly batch runs over all students
        rn = client.post("/api/admin/run-nightly", headers=HEADERS)
        assert rn.status_code == 200 and rn.json()["students"] >= 1
        assert isinstance(rn.json()["prepared"], list)
