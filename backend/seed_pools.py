"""Seed question pools for testing.

Run from the backend/ directory (needs ANTHROPIC_API_KEY set in the env/.env):

    python seed_pools.py                 # Week 1, Days 1-3, student "Anam"
    python seed_pools.py --days 2        # just retry day 2
    python seed_pools.py --days 1 2 3    # explicit
    python seed_pools.py --week 2 --days 1 --count-per-level 2   # quick/cheap

Generation is slow (~1-2 min per subject/day). It's resilient and idempotent:
each day is independent, a timeout on one day doesn't stop the others, and
re-running only generates the days still missing.
"""
import argparse
import time

from sqlalchemy import select

from app.db import SessionLocal, init_db
from app.log import configure_logging
from app.models import Student
from app.seeding import seed_day


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed question pools.")
    parser.add_argument("--week", type=int, default=1, help="week number 1-8 (default 1)")
    parser.add_argument("--days", type=int, nargs="+", default=[1, 2, 3],
                        help="day numbers, e.g. --days 2  or  --days 1 2 3 (default 1 2 3)")
    parser.add_argument("--student", default="Anam", help="student name (default Anam)")
    parser.add_argument("--count-per-level", type=int, default=None,
                        help="override 5-7 questions per level (smaller = cheaper test)")
    args = parser.parse_args()

    configure_logging()
    init_db()
    db = SessionLocal()
    try:
        student = db.scalar(select(Student).where(Student.name == args.student))
        if not student:
            student = Student(name=args.student, current_week=1, current_day=1)
            db.add(student)
            db.commit()
            db.refresh(student)
            print(f"Created student {args.student!r} -> id={student.id}")

        days = [d for d in args.days if 1 <= d <= 7]
        print(f"Seeding Week {args.week}, Days {days} (math + english) for student id={student.id} ...")
        ok = 0
        for day in days:
            t0 = time.monotonic()
            result = seed_day(db, student, args.week, day, count_per_level=args.count_per_level)
            dt = time.monotonic() - t0
            if result["ok"]:
                ok += 1
                print(f"Seeding Day {day}... ✓ ({dt:.0f}s)")
            else:
                kind = "timeout" if result["timed_out"] else "error"
                print(f"Seeding Day {day}... ✗ {kind} ({dt:.0f}s) — skipping")

        tail = "Done." if ok == len(days) else "Re-run to retry failed days."
        print(f"Summary: {ok}/{len(days)} days seeded. {tail}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
