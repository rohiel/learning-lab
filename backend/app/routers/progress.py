"""Progress + parent-review endpoints (Phase 3a).

- GET  /api/progress/{student_id}        home-screen summary
- GET  /api/progress/{student_id}/day    saved questions + answers for a day (review modal)
- POST /api/progress/flag                manual mark a day/week done or undone
- GET  /api/review/{student_id}          parent review analysis
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import require_api_key
from ..db import get_db
from ..models import ProgressFlag
from ..progress_report import build_day_records, build_progress, build_review_log
from ..review import parent_review
from ..schemas import (
    DayRecordsResponse,
    ProgressFlagRequest,
    ProgressResponse,
    ReviewResponse,
    Subject,
)

router = APIRouter(tags=["progress"])


@router.get("/progress/{student_id}", response_model=ProgressResponse, dependencies=[Depends(require_api_key)])
def progress(student_id: int, db: Session = Depends(get_db)):
    data = build_progress(db, student_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"No student with id {student_id}")
    return data


@router.get("/progress/{student_id}/day", response_model=DayRecordsResponse, dependencies=[Depends(require_api_key)])
def progress_day(
    student_id: int,
    subject: Subject = Query(...),
    week: int = Query(..., ge=1, le=8),
    day: int = Query(..., ge=1, le=7),
    db: Session = Depends(get_db),
):
    data = build_day_records(db, student_id, subject, week, day)
    if data is None:
        raise HTTPException(status_code=404, detail="No completed session with records for that day")
    return data


@router.post("/progress/flag", dependencies=[Depends(require_api_key)])
def progress_flag(req: ProgressFlagRequest, db: Session = Depends(get_db)):
    kind = "week" if req.day is None else "day"
    conds = [
        ProgressFlag.student_id == req.student_id,
        ProgressFlag.subject == req.subject,
        ProgressFlag.week == req.week,
        ProgressFlag.kind == kind,
        ProgressFlag.day.is_(None) if req.day is None else ProgressFlag.day == req.day,
    ]
    existing = db.scalar(select(ProgressFlag).where(*conds))
    if existing:
        existing.done = req.done
    else:
        db.add(
            ProgressFlag(
                student_id=req.student_id,
                subject=req.subject,
                week=req.week,
                day=req.day,
                kind=kind,
                done=req.done,
            )
        )
    db.commit()
    return {"ok": True, "subject": req.subject, "week": req.week, "day": req.day, "kind": kind, "done": req.done}


@router.get("/review/{student_id}", response_model=ReviewResponse, dependencies=[Depends(require_api_key)])
def review(student_id: int, db: Session = Depends(get_db)):
    log, n = build_review_log(db, student_id)
    if n == 0:
        raise HTTPException(status_code=409, detail="No completed sessions yet to review")
    text = parent_review(log)
    return ReviewResponse(review=text, sessions=n)
