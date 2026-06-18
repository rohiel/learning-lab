"""Pydantic request/response models.

Critical: `QuestionPublic` is the ONLY question shape the frontend ever sees and
it deliberately omits `answer`, `solution`, and `distractor_note`. The grading
and help endpoints read those server-side. A precomputed `precision` flag lets
the client run the "read it back" gate without ever holding the answer.
"""
from typing import Literal, Optional

from pydantic import BaseModel, Field

from .logic import is_precision_question

Subject = Literal["math", "english"]


class GenerateDayRequest(BaseModel):
    student_id: int
    subject: Subject
    week: int = Field(ge=1, le=8)
    day: int = Field(ge=1, le=7)
    force: bool = False
    # optional override mainly for testing / quick prep; otherwise 5-7 per level.
    count_per_level: Optional[int] = Field(default=None, ge=1, le=12)


class GenerateDayResponse(BaseModel):
    student_id: int
    subject: str
    week: int
    day: int
    regenerated: bool
    total: int
    per_level: dict[int, int]


class PoolStatusResponse(BaseModel):
    student_id: int
    subject: str
    week: int
    day: int
    total: int
    per_level: dict[int, int]


class QuestionPublic(BaseModel):
    """Safe-to-send question — no answer key."""

    id: int
    type: str
    passage: Optional[str] = None
    question: str
    choices: Optional[list[str]] = None
    level: int
    skill: Optional[str] = None
    retention: bool = False
    connection: bool = False
    precision: bool = False  # whether the "read it back" gate should fire

    @classmethod
    def from_row(cls, row) -> "QuestionPublic":
        return cls(
            id=row.id,
            type=row.type,
            passage=row.passage,
            question=row.question,
            choices=row.choices,
            level=row.level,
            skill=row.skill,
            retention=bool(row.retention),
            connection=bool(row.connection),
            precision=is_precision_question(row.level, row.answer, row.skill),
        )


class WritingPromptPublic(BaseModel):
    id: int
    week: int
    day: int
    prompt: str
    target_words: Optional[list[str]] = None
    lines: int

    @classmethod
    def from_row(cls, row) -> "WritingPromptPublic":
        return cls(
            id=row.id,
            week=row.week,
            day=row.day,
            prompt=row.prompt,
            target_words=row.target_words,
            lines=row.lines,
        )


class RunNightlyResponse(BaseModel):
    students: int
    prepared: list[dict]


class SeedRequest(BaseModel):
    student_id: int
    week: int = Field(default=1, ge=1, le=8)
    days: list[int] = Field(default=[1, 2, 3])
    count_per_level: Optional[int] = Field(default=None, ge=1, le=12)


class SeedResponse(BaseModel):
    student_id: int
    prepared: list[dict]
