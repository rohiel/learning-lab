"""SQLAlchemy 2.0 models.

Portability-first so a later swap to Postgres is trivial: integer surrogate
PKs, generic column types, JSON columns (works on SQLite + Postgres), and
timezone-aware datetimes. No SQLite-specific features.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    current_week: Mapped[int] = mapped_column(Integer, default=1)
    current_day: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class QuestionPool(Base):
    __tablename__ = "question_pool"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    subject: Mapped[str] = mapped_column(String(16))
    week: Mapped[int] = mapped_column(Integer)
    day: Mapped[int] = mapped_column(Integer)
    level: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(8))  # "mc" | "fill"
    passage: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    question: Mapped[str] = mapped_column(Text)
    choices: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    answer: Mapped[str] = mapped_column(Text)
    # SERVER-ONLY: never serialized into session questions sent to the browser.
    solution: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    skill: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    retention: Mapped[bool] = mapped_column(Boolean, default=False)
    connection: Mapped[bool] = mapped_column(Boolean, default=False)
    has_distractor: Mapped[bool] = mapped_column(Boolean, default=False)
    distractor_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_pool_day", "student_id", "subject", "week", "day", "level"),
    )


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    subject: Mapped[str] = mapped_column(String(16))
    week: Mapped[int] = mapped_column(Integer)
    day: Mapped[int] = mapped_column(Integer)
    mode: Mapped[str] = mapped_column(String(16))  # practice | test | writing
    # Locked at session start so a refresh/resume returns the SAME questions.
    selected_question_ids: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_level: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    help_requests: Mapped[int] = mapped_column(Integer, default=0)


class Answer(Base):
    __tablename__ = "answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("question_pool.id"))
    given: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    correct: Mapped[bool] = mapped_column(Boolean)
    tries: Mapped[int] = mapped_column(Integer, default=1)
    needed_help: Mapped[bool] = mapped_column(Boolean, default=False)
    answered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WeakSpot(Base):
    __tablename__ = "weak_spots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    subject: Mapped[str] = mapped_column(String(16))
    skill: Mapped[str] = mapped_column(String(160))
    # learning | short_term | long_term | mastered
    status: Mapped[str] = mapped_column(String(16), default="learning")
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_tested: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_weak_lookup", "student_id", "subject", "skill"),
    )


class ProgressFlag(Base):
    __tablename__ = "progress_flags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    subject: Mapped[str] = mapped_column(String(16))
    week: Mapped[int] = mapped_column(Integer)
    day: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # null => week-level flag
    kind: Mapped[str] = mapped_column(String(8))  # "day" | "week"
    done: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class WritingPrompt(Base):
    __tablename__ = "writing_prompts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    week: Mapped[int] = mapped_column(Integer)
    day: Mapped[int] = mapped_column(Integer)
    prompt: Mapped[str] = mapped_column(Text)
    target_words: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    lines: Mapped[int] = mapped_column(Integer, default=5)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_writing_lookup", "student_id", "week", "day"),
    )
