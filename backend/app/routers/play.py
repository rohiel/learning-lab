"""Gameplay endpoints (Phase 3a).

- POST /api/session/start     select + LOCK questions, return them (no answer key)
- POST /api/answer            grade one answer server-side, Socratic hint if wrong
- POST /api/session/complete  finalize: score + update weak-spots/retention
- POST /api/help              "I'm stuck" chat anchored to the hidden solution
- POST /api/work/analyze      Supernote image analysis (multipart)
- GET  /api/writing/prompt    fetch the pre-generated writing prompt for a day
- POST /api/writing/review    review a writing submission
"""
import base64
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import require_api_key
from ..db import get_db
from ..grading import ask_help
from ..models import Answer, QuestionPool, Session as SessionModel, Student
from ..progress import get_weak_spots
from ..ratelimit import limiter
from ..review import review_writing
from ..schemas import (
    ActiveSessionResponse,
    AnswerRequest,
    AnswerResponse,
    HelpRequest,
    HelpResponse,
    QuestionPublic,
    SessionCompleteRequest,
    SessionCompleteResponse,
    SessionStartRequest,
    SessionStartResponse,
    StudentPublic,
    WorkAnalyzeResponse,
    WritingPromptPublic,
    WritingReviewRequest,
    WritingReviewResponse,
)
from ..services import existing_writing_prompt
from ..sessions import (
    finalize_session,
    get_session_answers,
    get_session_questions,
    record_answer,
    start_or_resume_session,
)
from ..vision import analyze_work

router = APIRouter(tags=["play"])


def _session_or_404(db, session_id) -> SessionModel:
    s = db.get(SessionModel, session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    return s


@router.get("/students", response_model=list[StudentPublic], dependencies=[Depends(require_api_key)])
def list_students(db: Session = Depends(get_db)):
    rows = db.scalars(select(Student).order_by(Student.id)).all()
    return [
        StudentPublic(id=r.id, name=r.name, current_week=r.current_week, current_day=r.current_day)
        for r in rows
    ]


@router.get("/session/active/{student_id}", dependencies=[Depends(require_api_key)])
def active_session(student_id: int, db: Session = Depends(get_db)):
    """The latest in-progress practice/test session, for the home-screen resume
    banner. Returns null when there's nothing to resume."""
    sess = db.scalars(
        select(SessionModel)
        .where(
            SessionModel.student_id == student_id,
            SessionModel.completed_at.is_(None),
            SessionModel.mode.in_(["practice", "test"]),
        )
        .order_by(SessionModel.started_at.desc())
    ).first()
    if not sess or not sess.selected_question_ids:
        return None
    answered = db.scalar(select(func.count()).select_from(Answer).where(Answer.session_id == sess.id)) or 0
    return ActiveSessionResponse(
        session_id=sess.id, subject=sess.subject, week=sess.week, day=sess.day,
        mode=sess.mode, answered=answered, total=len(sess.selected_question_ids),
    )


@router.post("/session/start", response_model=SessionStartResponse, dependencies=[Depends(require_api_key)])
def session_start(req: SessionStartRequest, db: Session = Depends(get_db)):
    student = db.get(Student, req.student_id)
    if not student:
        raise HTTPException(status_code=404, detail=f"No student with id {req.student_id}")

    sess, created = start_or_resume_session(db, student, req.subject, req.week, req.day, req.mode)
    if sess is None:
        raise HTTPException(
            status_code=409,
            detail="No question pool prepared for that day. Generate it first (POST /api/admin/generate-day).",
        )

    questions = get_session_questions(db, sess)
    answered = [
        {"question_id": a.question_id, "correct": a.correct, "given": a.given}
        for a in get_session_answers(db, sess)
    ]
    db.commit()
    return SessionStartResponse(
        session_id=sess.id,
        resumed=not created,
        mode=sess.mode,
        subject=sess.subject,
        week=sess.week,
        day=sess.day,
        questions=[QuestionPublic.from_row(q) for q in questions],
        answered=answered,
    )


@router.post("/answer", response_model=AnswerResponse)
@limiter.limit("60/minute")
def answer(request: Request, req: AnswerRequest, db: Session = Depends(get_db), _: bool = Depends(require_api_key)):
    sess = _session_or_404(db, req.session_id)
    if sess.completed_at:
        raise HTTPException(status_code=409, detail="Session already completed")
    if req.question_id not in (sess.selected_question_ids or []):
        raise HTTPException(status_code=400, detail="Question is not part of this session")
    q = db.get(QuestionPool, req.question_id)
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")

    result = record_answer(db, sess, q, req.given, needed_help=req.needed_help)
    db.commit()
    return AnswerResponse(**result)


@router.post("/session/complete", response_model=SessionCompleteResponse, dependencies=[Depends(require_api_key)])
def session_complete(req: SessionCompleteRequest, db: Session = Depends(get_db)):
    sess = _session_or_404(db, req.session_id)
    if sess.completed_at:  # idempotent
        return SessionCompleteResponse(
            score=sess.score or 0, total=sess.total or 0, max_level=sess.max_level or 1,
            weak_skills=[], retention_passed=[],
        )
    result = finalize_session(db, sess)
    db.commit()
    return SessionCompleteResponse(**result)


@router.post("/help", response_model=HelpResponse)
@limiter.limit("30/minute")
def help_chat(request: Request, req: HelpRequest, db: Session = Depends(get_db), _: bool = Depends(require_api_key)):
    sess = _session_or_404(db, req.session_id)
    q = db.get(QuestionPool, req.question_id)
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")

    problem_context = (q.passage + "\n\n" + q.question) if q.passage else q.question
    reply = ask_help(
        problem_context=problem_context,
        subject=sess.subject,
        history=[m.model_dump() for m in req.history],
        off_topic_count=req.off_topic_count,
        solution=q.solution,
        answer=q.answer,
        choices=q.choices,
    )
    sess.help_requests = (sess.help_requests or 0) + 1
    db.commit()
    return HelpResponse(reply=reply, help_requests=sess.help_requests)


@router.post("/work/analyze", response_model=WorkAnalyzeResponse)
@limiter.limit("10/minute")
def work_analyze(
    request: Request,
    file: UploadFile = File(...),
    problem_context: str = Form(""),
    _: bool = Depends(require_api_key),
):
    data = file.file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty image upload")
    image_b64 = base64.b64encode(data).decode()
    feedback = analyze_work(image_b64, file.content_type or "image/png", problem_context)
    return WorkAnalyzeResponse(feedback=feedback)


@router.get("/writing/prompt", response_model=WritingPromptPublic, dependencies=[Depends(require_api_key)])
def writing_prompt(
    student_id: int = Query(...),
    week: int = Query(..., ge=1, le=8),
    day: int = Query(..., ge=1, le=7),
    db: Session = Depends(get_db),
):
    row = existing_writing_prompt(db, student_id, week, day)
    if not row:
        raise HTTPException(status_code=404, detail="No writing prompt prepared for that day")
    return WritingPromptPublic.from_row(row)


@router.post("/writing/review", response_model=WritingReviewResponse)
@limiter.limit("20/minute")
def writing_review(request: Request, req: WritingReviewRequest, db: Session = Depends(get_db), _: bool = Depends(require_api_key)):
    student = db.get(Student, req.student_id)
    if not student:
        raise HTTPException(status_code=404, detail=f"No student with id {req.student_id}")

    prompt, target_words = req.prompt, req.target_words
    if prompt is None or target_words is None:
        wp = existing_writing_prompt(db, req.student_id, req.week, req.day)
        if wp:
            prompt = prompt or wp.prompt
            target_words = target_words or wp.target_words

    weak = get_weak_spots(db, req.student_id, "english")
    result = review_writing(req.text, prompt or "", target_words or [], weak)

    # log a lightweight writing session (feeds the X/2-this-week counter)
    db.add(
        SessionModel(
            student_id=req.student_id,
            subject="english",
            week=req.week,
            day=req.day,
            mode="writing",
            score=int(result["meta"].get("targetsUsed", 0) or 0),
            total=len(target_words or []),
            completed_at=datetime.now(timezone.utc),
        )
    )
    db.commit()
    return WritingReviewResponse(feedback=result["feedback"], meta=result["meta"])
