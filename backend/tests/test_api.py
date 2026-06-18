"""End-to-end HTTP test of the generate-day path with a mocked generator.

Verifies auth, persistence, per-level counts, idempotency, and — crucially —
that the stored `solution` stays server-side.
"""
from fastapi.testclient import TestClient

# A fixed "generated" pool (3 questions across levels 1, 2, 4).
CANNED = [
    {"type": "fill", "question": "Q1", "answer": "8", "solution": "SECRET-STEPS-1", "level": 1, "skill": "addition"},
    {"type": "mc", "question": "Q2", "choices": ["1", "2", "3", "4"], "answer": "2", "solution": "SECRET-2", "level": 2, "skill": "logic"},
    {"type": "fill", "question": "Q3", "answer": "1.05", "solution": "SECRET-3", "level": 4, "skill": "decimal division"},
]


def test_generate_day_flow(monkeypatch):
    from app.db import SessionLocal
    from app.main import app
    from app.models import QuestionPool, Student
    from app.routers import admin

    monkeypatch.setattr(admin, "generate_day_pool", lambda **kwargs: CANNED)

    with TestClient(app) as client:
        # seed a student
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
        r = client.post("/api/admin/generate-day", headers={"X-API-Key": "test-secret"}, json=body)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["regenerated"] is True
        assert data["total"] == 3
        assert data["per_level"] == {"1": 1, "2": 1, "4": 1}

        # idempotent: second call without force returns existing, not regenerated
        r2 = client.post("/api/admin/generate-day", headers={"X-API-Key": "test-secret"}, json=body)
        assert r2.json()["regenerated"] is False
        assert r2.json()["total"] == 3

        # the solution is persisted server-side...
        db = SessionLocal()
        rows = db.query(QuestionPool).filter_by(student_id=sid).all()
        assert any("SECRET" in (row.solution or "") for row in rows)
        db.close()

        # ...and the pool-status endpoint never exposes it
        r3 = client.get(
            "/api/admin/pool",
            headers={"X-API-Key": "test-secret"},
            params={"student_id": sid, "subject": "math", "week": 1, "day": 1},
        )
        assert r3.status_code == 200
        assert "SECRET" not in r3.text
        assert r3.json()["total"] == 3

        # health is open
        assert client.get("/api/health").json() == {"status": "ok"}
