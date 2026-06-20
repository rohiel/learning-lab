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
    succeeded: list[int]
    failed: list[int]
    prepared: list[dict]


# ---------------------------------------------------------------------------
# Phase 3a: gameplay
# ---------------------------------------------------------------------------

class SessionStartRequest(BaseModel):
    student_id: int
    subject: Subject
    week: int = Field(ge=1, le=8)
    day: int = Field(ge=1, le=7)
    mode: Literal["practice", "test"] = "practice"


class AnsweredItem(BaseModel):
    question_id: int
    correct: bool
    given: Optional[str] = None


class SessionStartResponse(BaseModel):
    session_id: int
    resumed: bool
    mode: str
    subject: str
    week: int
    day: int
    questions: list[QuestionPublic]
    answered: list[AnsweredItem]  # already-answered questions, for resume


class AnswerRequest(BaseModel):
    session_id: int
    question_id: int
    given: str
    needed_help: bool = False


class AnswerResponse(BaseModel):
    correct: bool
    hint: Optional[str] = None
    correct_answer: str  # revealed only AFTER she answers (e.g. MC highlight)
    reason: Optional[str] = None


class SessionCompleteRequest(BaseModel):
    session_id: int


class SessionCompleteResponse(BaseModel):
    score: int
    total: int
    max_level: int
    weak_skills: list[str]
    retention_passed: list[str]


class HelpMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class HelpRequest(BaseModel):
    session_id: int
    question_id: int
    history: list[HelpMessage]
    off_topic_count: int = 0


class HelpResponse(BaseModel):
    reply: str
    help_requests: int


class WritingReviewRequest(BaseModel):
    student_id: int
    week: int = Field(ge=1, le=8)
    day: int = Field(ge=1, le=7)
    text: str
    prompt: Optional[str] = None
    target_words: Optional[list[str]] = None


class WritingReviewResponse(BaseModel):
    feedback: str
    meta: dict


class WorkAnalyzeResponse(BaseModel):
    feedback: str


class ProgressFlagRequest(BaseModel):
    student_id: int
    subject: Subject
    week: int = Field(ge=1, le=8)
    day: Optional[int] = Field(default=None, ge=1, le=7)  # None => week-level flag
    done: bool = True


class ProgressResponse(BaseModel):
    student: dict
    days: list[dict]
    weeks: list[dict]
    weak_spots: dict
    retention: dict
    mastered: dict
    help_total: int
    writing_this_week: dict


class DayRecordsResponse(BaseModel):
    subject: str
    week: int
    day: int
    score: Optional[int] = None
    total: Optional[int] = None
    records: list[dict]


class ReviewResponse(BaseModel):
    review: str
    sessions: int


class StudentPublic(BaseModel):
    id: int
    name: str
    current_week: int
    current_day: int


class ActiveSessionResponse(BaseModel):
    session_id: int
    subject: str
    week: int
    day: int
    mode: str
    answered: int
    total: int
