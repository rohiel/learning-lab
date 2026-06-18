from datetime import datetime, timezone

from fastapi.testclient import TestClient

HEADERS = {"X-API-Key": "test-secret"}


def test_progress_flag_and_summary():
    from app.db import SessionLocal
    from app.main import app
    from app.models import Student

    with TestClient(app) as client:
        db = SessionLocal()
        s = Student(name="PR1", current_week=1, current_day=1)
        db.add(s)
        db.commit()
        sid = s.id
        db.close()

        pr = client.get(f"/api/progress/{sid}", headers=HEADERS)
        assert pr.status_code == 200
        assert pr.json()["days"] == [] and pr.json()["help_total"] == 0

        # manually flag a day done
        f = client.post("/api/progress/flag", headers=HEADERS, json={"student_id": sid, "subject": "math", "week": 1, "day": 2, "done": True})
        assert f.status_code == 200 and f.json()["done"] is True
        pr2 = client.get(f"/api/progress/{sid}", headers=HEADERS).json()
        day2 = [d for d in pr2["days"] if d["day"] == 2][0]
        assert day2["done"] is True and day2["manual"] is True

        # un-flag it
        client.post("/api/progress/flag", headers=HEADERS, json={"student_id": sid, "subject": "math", "week": 1, "day": 2, "done": False})
        pr3 = client.get(f"/api/progress/{sid}", headers=HEADERS).json()
        day2b = [d for d in pr3["days"] if d["day"] == 2][0]
        assert day2b["done"] is False

        # flag a whole week done
        client.post("/api/progress/flag", headers=HEADERS, json={"student_id": sid, "subject": "english", "week": 1, "done": True})
        pr4 = client.get(f"/api/progress/{sid}", headers=HEADERS).json()
        assert any(w["complete"] for w in pr4["weeks"])


def test_review_endpoint(monkeypatch):
    from app.db import SessionLocal
    from app.main import app
    from app.models import Session as SessionModel, Student
    from app.routers import progress as progress_router

    with TestClient(app) as client:
        db = SessionLocal()
        s = Student(name="PR2", current_week=1, current_day=1)
        db.add(s)
        db.commit()
        sid = s.id
        db.close()

        # nothing to review yet
        assert client.get(f"/api/review/{sid}", headers=HEADERS).status_code == 409

        db = SessionLocal()
        db.add(SessionModel(student_id=sid, subject="math", week=1, day=1, mode="practice", score=8, total=10, max_level=3, completed_at=datetime.now(timezone.utc)))
        db.commit()
        db.close()

        monkeypatch.setattr(progress_router, "parent_review", lambda log: "She's improving on decimals.")
        rv = client.get(f"/api/review/{sid}", headers=HEADERS)
        assert rv.status_code == 200 and "improving" in rv.json()["review"] and rv.json()["sessions"] == 1
