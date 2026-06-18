"""Seed the database with the student so you can test generation immediately.

Run from the backend/ directory:  python seed.py
"""
from sqlalchemy import select

from app.db import SessionLocal, init_db
from app.models import Student


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        existing = db.scalar(select(Student).where(Student.name == "Anam"))
        if existing:
            print(f"Student already exists: id={existing.id}, week={existing.current_week}, day={existing.current_day}")
            return
        student = Student(name="Anam", current_week=1, current_day=1)
        db.add(student)
        db.commit()
        db.refresh(student)
        print(f"Seeded student 'Anam' -> id={student.id} (Week 1, Day 1)")
        print("Next: POST /api/admin/generate-day with this student_id to build a day's pool.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
