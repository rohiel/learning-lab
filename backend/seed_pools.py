"""Seed Week 1, Days 1-3 question pools (both subjects) so you can test the app
immediately.

Run from the backend/ directory (needs ANTHROPIC_API_KEY set in the env/.env):

    python seed_pools.py

Generation is slow (~1-2 min per subject/day), so this can take several minutes.
It is resilient and idempotent: each day is independent, a timeout on one day
doesn't stop the others, and re-running only generates the days still missing.
"""
import time

from sqlalchemy import select

from app.db import SessionLocal, init_db
from app.log import configure_logging
from app.models import Student
from app.seeding import seed_day

DAYS = (1, 2, 3)


def main() -> None:
    configure_logging()
    init_db()
    db = SessionLocal()
    try:
        student = db.scalar(select(Student).where(Student.name == "Anam"))
        if not student:
            student = Student(name="Anam", current_week=1, current_day=1)
            db.add(student)
            db.commit()
            db.refresh(student)
            print(f"Created student 'Anam' -> id={student.id}")

        print(f"Seeding Week 1, Days {DAYS} (math + english) for student id={student.id} ...")
        ok = 0
        for day in DAYS:
            t0 = time.monotonic()
            result = seed_day(db, student, 1, day)
            dt = time.monotonic() - t0
            if result["ok"]:
                ok += 1
                print(f"Seeding Day {day}... ✓ ({dt:.0f}s)")
            else:
                kind = "timeout" if result["timed_out"] else "error"
                print(f"Seeding Day {day}... ✗ {kind} ({dt:.0f}s) — skipping")

        tail = "Done." if ok == len(DAYS) else "Re-run to retry failed days."
        print(f"Summary: {ok}/{len(DAYS)} days seeded. {tail}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
