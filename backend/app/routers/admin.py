"""Admin + health endpoints.

- GET  /api/health                 liveness (no auth)
- POST /api/admin/generate-day     manually pre-generate one day's pool
- GET  /api/admin/pool             inspect pool counts for a day
- POST /api/admin/run-nightly      manually trigger the nightly batch (testing/recovery)
- POST /api/admin/seed             seed Week 1 Days 1-3 for a student (resilient/partial)
- GET  /api/admin/writing-prompt   inspect a stored writing prompt

generate-day is idempotent: a day's pool is generated ONCE and is otherwise
static. Pass force=true to regenerate. On an Anthropic timeout these endpoints
return a 504 with an actionable JSON body, not a raw 500.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..anthropic_client import is_timeout_error
from ..auth import require_api_key
from ..db import get_db
from ..models import Student
from ..nightly import run_nightly
from ..ratelimit import limiter
from ..schemas import (
    GenerateDayRequest,
    GenerateDayResponse,
    PoolStatusResponse,
    RunNightlyResponse,
    SeedRequest,
    SeedResponse,
    Subject,
    WritingPromptPublic,
)
from ..seeding import seed_initial_pools
from ..services import (
    existing_pool,
    existing_writing_prompt,
    per_level_counts,
    prepare_day_pool,
)

router = APIRouter(tags=["admin"])

_TIMEOUT_HINT = "API call timed out. Try seeding one day at a time, or re-run to retry just the failed days."
_ERROR_HINT = "Generation failed. Check ANTHROPIC_API_KEY and the server logs, then retry the failed days."


@router.get("/health")
def health():
    return {"status": "ok"}


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

    try:
        regenerated, rows = prepare_day_pool(
            db, student, req.subject, req.week, req.day, force=req.force, count_per_level=req.count_per_level
        )
    except Exception as e:  # noqa: BLE001
        db.rollback()
        timeout = is_timeout_error(e)
        return JSONResponse(
            status_code=504 if timeout else 502,
            content={
                "error": "anthropic_timeout" if timeout else "anthropic_error",
                "message": _TIMEOUT_HINT if timeout else _ERROR_HINT,
                "succeeded": [],
                "failed": [req.day],
            },
        )

    if not rows:
        db.rollback()
        raise HTTPException(
            status_code=502,
            detail="Generation produced no questions. Check ANTHROPIC_API_KEY and network egress.",
        )

    db.commit()
    return GenerateDayResponse(
        student_id=req.student_id, subject=req.subject, week=req.week, day=req.day,
        regenerated=regenerated, total=len(rows), per_level=per_level_counts(rows),
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
    rows = existing_pool(db, student_id, subject, week, day)
    return PoolStatusResponse(
        student_id=student_id, subject=subject, week=week, day=day,
        total=len(rows), per_level=per_level_counts(rows),
    )


@router.post("/admin/run-nightly", response_model=RunNightlyResponse)
@limiter.limit("4/hour")
def trigger_nightly(
    request: Request,
    db: Session = Depends(get_db),
    _: bool = Depends(require_api_key),
):
    student_count = db.scalar(select(func.count(Student.id))) or 0
    prepared = run_nightly(db)
    return RunNightlyResponse(students=student_count, prepared=prepared)


@router.post("/admin/seed", response_model=SeedResponse)
@limiter.limit("4/hour")
def seed(
    request: Request,
    req: SeedRequest,
    db: Session = Depends(get_db),
    _: bool = Depends(require_api_key),
):
    student = db.get(Student, req.student_id)
    if not student:
        raise HTTPException(status_code=404, detail=f"No student with id {req.student_id}")

    result = seed_initial_pools(
        db, student, week=req.week, days=tuple(req.days), count_per_level=req.count_per_level
    )

    if result["failed"]:
        timeout = result["timed_out"]
        # Partial (or total) failure -> actionable 504/502, not a raw 500.
        return JSONResponse(
            status_code=504 if timeout else 502,
            content={
                "error": "anthropic_timeout" if timeout else "anthropic_error",
                "message": _TIMEOUT_HINT if timeout else _ERROR_HINT,
                "succeeded": result["succeeded"],
                "failed": result["failed"],
            },
        )

    return SeedResponse(
        student_id=req.student_id,
        succeeded=result["succeeded"],
        failed=result["failed"],
        prepared=result["prepared"],
    )


@router.get("/admin/writing-prompt", response_model=WritingPromptPublic)
def get_writing_prompt(
    student_id: int = Query(...),
    week: int = Query(..., ge=1, le=8),
    day: int = Query(..., ge=1, le=7),
    db: Session = Depends(get_db),
    _: bool = Depends(require_api_key),
):
    row = existing_writing_prompt(db, student_id, week, day)
    if not row:
        raise HTTPException(status_code=404, detail="No writing prompt for that day")
    return WritingPromptPublic.from_row(row)
