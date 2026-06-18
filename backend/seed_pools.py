"""Seed Week 1, Days 1-3 question pools (both subjects) so you can test the app
immediately.

Run from the backend/ directory (needs ANTHROPIC_API_KEY set in the env/.env):

    python seed_pools.py

This calls the Anthropic API to generate ~25-35 questions per day per subject,
so it takes a few minutes. It's idempotent — already-generated days are skipped.
"""
from sqlalchemy import select

from app.db import SessionLocal, init_db
from app.models import Student
from app.seeding import seed_initial_pools


def main() -> None:
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

        print(f"Seeding Week 1, Days 1-3 (math + english) for student id={student.id} ...")
        print("Calling the Anthropic API — this can take a few minutes.")
        summary = seed_initial_pools(db, student)
        for item in summary:
            extra = " +writing prompt" if item.get("writing_prompt") else ""
            status = "generated" if item["regenerated"] else "already existed"
            print(
                f"  {item['subject']:7} W{item['week']} D{item['day']}: "
                f"{item['pool_count']} questions ({status}){extra}"
            )
        print("Done. The app can now READ these pools with zero live generation.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
