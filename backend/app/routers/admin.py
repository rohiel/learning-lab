"""Admin + health endpoints (Phase 1).

- GET  /api/health                 liveness (no auth)
- POST /api/admin/generate-day     manually pre-generate a day's pool
- GET  /api/admin/pool             inspect counts for a day

The generate-day endpoint is idempotent: a day's pool is generated ONCE and is
otherwise static. Pass force=true to regenerate.
"""
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import require_api_key
from ..db import get_db
from ..generation import generate_day_pool
from ..models import QuestionPool, Student
from ..progress import get_retention_queue, get_weak_spots
from ..ratelimit import limiter
from ..schemas import (
    GenerateDayRequest,
    GenerateDayResponse,
    PoolStatusResponse,
    Subject,
)

router = APIRouter(tags=["admin"])


@router.get("/health")
def health():
    return {"status": "ok"}


def _per_level_counts(rows) -> dict[int, int]:
    return dict(sorted(Counter(r.level for r in rows).items()))


@router.post("/admin/generate-day", response_model=GenerateDayResponse)
@limiter.limit("10/minute")
def generate_day(
    request: Request,
    req: GenerateDayRequest,
    db: Session = Depends(get_db),
    _: bool = Depends(require_api_key),
):
    student = db.get(Student, req.student_id)
    if not student:
        raise HTTPException(status_code=404, detail=f"No student with id {req.student_id}")

    existing = db.scalars(
        select(QuestionPool).where(
            QuestionPool.student_id == req.student_id,
            QuestionPool.subject == req.subject,
            QuestionPool.week == req.week,
            QuestionPool.day == req.day,
        )
    ).all()

    if existing and not req.force:
        # already prepared — return as-is (a day's pool is static)
        return GenerateDayResponse(
            student_id=req.student_id, subject=req.subject, week=req.week, day=req.day,
            regenerated=False, total=len(existing), per_level=_per_level_counts(existing),
        )

    if existing and req.force:
        for row in existing:
            db.delete(row)
        db.flush()

    weak = get_weak_spots(db, req.student_id, req.subject)
    retention = get_retention_queue(db, req.student_id, req.subject)

    questions = generate_day_pool(
        subject=req.subject,
        week=req.week,
        day=req.day,
        weak_spots=weak,
        retention_queue=retention,
        count_per_level=req.count_per_level,
    )

    rows: list[QuestionPool] = []
    for q in questions:
        row = QuestionPool(
            student_id=req.student_id,
            subject=req.subject,
            week=req.week,
            day=req.day,
            level=int(q.get("level") or 1),
            type=q.get("type", "fill"),
            passage=q.get("passage"),
            question=q.get("question", ""),
            choices=q.get("choices"),
            answer=str(q.get("answer", "")),
            solution=q.get("solution"),
            skill=q.get("skill"),
            retention=bool(q.get("retention")),
            connection=bool(q.get("connection")),
            has_distractor=bool(q.get("hasDistractor")),
            distractor_note=q.get("distractorNote"),
        )
        db.add(row)
        rows.append(row)

    if not rows:
        # Generation produced nothing (e.g. missing API key / all calls failed).
        db.rollback()
        raise HTTPException(
            status_code=502,
            detail="Generation produced no questions. Check ANTHROPIC_API_KEY and network egress.",
        )

    db.commit()
    return GenerateDayResponse(
        student_id=req.student_id, subject=req.subject, week=req.week, day=req.day,
        regenerated=True, total=len(rows), per_level=_per_level_counts(rows),
    )


@router.get("/admin/pool", response_model=PoolStatusResponse)
def pool_status(
    student_id: int = Query(...),
    subject: Subject = Query(...),
    week: int = Query(..., ge=1, le=8),
    day: int = Query(..., ge=1, le=7),
    db: Session = Depends(get_db),
    _: bool = Depends(require_api_key),
):
    rows = db.scalars(
        select(QuestionPool).where(
            QuestionPool.student_id == student_id,
            QuestionPool.subject == subject,
            QuestionPool.week == week,
            QuestionPool.day == day,
        )
    ).all()
    return PoolStatusResponse(
        student_id=student_id, subject=subject, week=week, day=day,
        total=len(rows), per_level=_per_level_counts(rows),
    )
