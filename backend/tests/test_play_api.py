from fastapi.testclient import TestClient

HEADERS = {"X-API-Key": "test-secret"}


def _seed_pool(db, student_id, subject="math", week=1, day=1, per_level=3):
    from app.models import QuestionPool

    for lvl in range(1, 6):
        for i in range(per_level):
            db.add(
                QuestionPool(
                    student_id=student_id, subject=subject, week=week, day=day, level=lvl,
                    type="fill", question=f"L{lvl}Q{i}", answer=f"a{lvl}{i}",
                    solution=f"SECRET-{lvl}-{i}", skill=f"sk{lvl}",
                )
            )
    db.commit()


def test_full_play_loop(monkeypatch):
    from app import sessions
    from app.db import SessionLocal
    from app.main import app
    from app.models import QuestionPool, Student

    monkeypatch.setattr(
        sessions, "grade_answer",
        lambda subject, question, expected, given, skill: {"correct": given == expected, "reason": ""},
    )
    monkeypatch.setattr(sessions, "get_hint", lambda *a, **k: "try again")

    with TestClient(app) as client:
        db = SessionLocal()
        s = Student(name="P1", current_week=1, current_day=1)
        db.add(s)
        db.commit()
        sid = s.id
        _seed_pool(db, sid)
        db.close()

        # start locks a set; no answer key leaks
        r = client.post("/api/session/start", headers=HEADERS, json={"student_id": sid, "subject": "math", "week": 1, "day": 1})
        assert r.status_code == 200, r.text
        data = r.json()
        sessid, qs = data["session_id"], data["questions"]
        assert len(qs) >= 1
        assert all("solution" not in q and "answer" not in q for q in qs)
        assert "SECRET" not in r.text

        # resume returns the SAME session + same locked questions
        r2 = client.post("/api/session/start", headers=HEADERS, json={"student_id": sid, "subject": "math", "week": 1, "day": 1})
        assert r2.json()["session_id"] == sessid and r2.json()["resumed"] is True
        assert [q["id"] for q in r2.json()["questions"]] == [q["id"] for q in qs]

        # answer every question correctly
        db = SessionLocal()
        for q in qs:
            row = db.get(QuestionPool, q["id"])
            ar = client.post("/api/answer", headers=HEADERS, json={"session_id": sessid, "question_id": q["id"], "given": row.answer})
            assert ar.status_code == 200, ar.text
            assert ar.json()["correct"] is True and ar.json()["correct_answer"] == row.answer
        db.close()

        # complete
        cr = client.post("/api/session/complete", headers=HEADERS, json={"session_id": sessid})
        assert cr.status_code == 200
        assert cr.json()["total"] == len(qs) and cr.json()["score"] == len(qs)

        # auth required
        assert client.post("/api/session/start", json={"student_id": sid, "subject": "math", "week": 1, "day": 1}).status_code == 401


def test_help_writing_and_work(monkeypatch):
    from app.db import SessionLocal
    from app.main import app
    from app.models import Student, WritingPrompt
    from app.routers import play

    with TestClient(app) as client:
        db = SessionLocal()
        s = Student(name="P2", current_week=1, current_day=3)
        db.add(s)
        db.commit()
        sid = s.id
        _seed_pool(db, sid, subject="math", week=1, day=1)
        db.add(WritingPrompt(student_id=sid, week=1, day=3, prompt="Write about a rock.", target_words=["mineral", "specimen", "fragile"], lines=5))
        db.commit()
        db.close()

        r = client.post("/api/session/start", headers=HEADERS, json={"student_id": sid, "subject": "math", "week": 1, "day": 1})
        sessid = r.json()["session_id"]
        qid = r.json()["questions"][0]["id"]

        # help chat increments help_requests and is anchored server-side
        monkeypatch.setattr(play, "ask_help", lambda **k: "What operation hides here?")
        hr = client.post("/api/help", headers=HEADERS, json={"session_id": sessid, "question_id": qid, "history": [{"role": "user", "content": "help"}], "off_topic_count": 0})
        assert hr.status_code == 200 and hr.json()["help_requests"] == 1 and hr.json()["reply"].startswith("What")

        # fetch the pre-generated writing prompt
        wp = client.get("/api/writing/prompt", headers=HEADERS, params={"student_id": sid, "week": 1, "day": 3})
        assert wp.status_code == 200 and wp.json()["lines"] == 5 and len(wp.json()["target_words"]) == 3

        # writing review
        monkeypatch.setattr(play, "review_writing", lambda text, prompt, target_words, weak: {"feedback": "Nice work!", "meta": {"targetsUsed": 2, "wordCount": 40}})
        wr = client.post("/api/writing/review", headers=HEADERS, json={"student_id": sid, "week": 1, "day": 3, "text": "I found a mineral specimen."})
        assert wr.status_code == 200 and wr.json()["feedback"] == "Nice work!"

        # supernote image analysis (multipart)
        monkeypatch.setattr(play, "analyze_work", lambda b64, mt, ctx: "Step 2 looks off—recheck it.")
        ana = client.post("/api/work/analyze", headers=HEADERS, files={"file": ("work.png", b"\x89PNG-fake", "image/png")}, data={"problem_context": "division"})
        assert ana.status_code == 200 and "Step 2" in ana.json()["feedback"]
