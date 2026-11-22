from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, status
from services.interview_service import InterviewService
from services.evaluation_service import EvaluationService
from tools.candidate.jd_tools import match_resume_with_jd
from schemas.interview import (
    InterviewPlan,
    InterviewSession,
    InterviewQuestion,
    AnswerEvaluation,
    JDMatchResult,
)

router = APIRouter(prefix="/interview", tags=["Interview"])


class CreatePlanRequest(BaseModel):
    target_role: str = "Fullstack Software Engineer"
    seniority: str = "Mid-Level"
    skills: Optional[List[str]] = None


class StartInterviewRequest(BaseModel):
    plan_or_role: str = "Fullstack Software Engineer"
    difficulty: str = "intermediate"


class SubmitAnswerRequest(BaseModel):
    question_id: str
    question_text: str
    answer_text: str
    expected_points: Optional[List[str]] = None
    difficulty: Optional[str] = None


class MatchRequest(BaseModel):
    resume_text: str
    jd_text: str


@router.post("/match", response_model=JDMatchResult)
def match_resume_jd_endpoint(req: MatchRequest):
    """
    POST /api/v1/interview/match
    Compares resume against target job description.
    """
    return match_resume_with_jd(req.resume_text, req.jd_text)


@router.post("/plan", response_model=InterviewPlan)
def create_plan_endpoint(req: CreatePlanRequest):
    """
    POST /api/v1/interview/plan
    Generate structured interview plan.
    """
    return InterviewService.generate_interview_plan(
        target_role=req.target_role,
        seniority=req.seniority,
        skills=req.skills
    )


@router.post("/start", response_model=InterviewSession)
def start_session_endpoint(req: StartInterviewRequest):
    """
    POST /api/v1/interview/start
    Start new interview session.
    """
    return InterviewService.start_interview(
        plan_or_role=req.plan_or_role,
        difficulty=req.difficulty
    )


@router.get("/{session_id}/question", response_model=Optional[InterviewQuestion])
def get_current_question_endpoint(session_id: str):
    """
    GET /api/v1/interview/{session_id}/question
    Get current question.
    """
    try:
        return InterviewService.get_current_question(session_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{session_id}/next", response_model=Optional[InterviewQuestion])
def next_question_endpoint(session_id: str):
    """
    POST /api/v1/interview/{session_id}/next
    Move to next question.
    """
    try:
        return InterviewService.generate_next_question(session_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{session_id}/answer", response_model=AnswerEvaluation)
def submit_answer_endpoint(session_id: str, req: SubmitAnswerRequest):
    """
    POST /api/v1/interview/{session_id}/answer
    Evaluate candidate response, update progress, and provide feedback.
    """
    if not req.answer_text or not req.answer_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Answer text cannot be empty. Please record audio or enter an answer."
        )

    try:
        session = InterviewService.get_session(session_id)
        target_diff = req.difficulty or getattr(session.plan, "difficulty", "intermediate")

        eval_result = EvaluationService.evaluate_candidate_answer(
            question_id=req.question_id,
            question_text=req.question_text,
            answer_text=req.answer_text,
            expected_points=req.expected_points,
            difficulty=str(target_diff)
        )
        history_record = {
            **eval_result.model_dump(),
            "question_text": req.question_text,
            "answer_text": req.answer_text,
        }
        InterviewService.update_interview_progress(session_id, history_record)
        return eval_result
    except KeyError as e:
        raise HTTPException(status_code=404, detail=f"Session or question not found: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Answer evaluation error: {str(e)}")


@router.post("/{session_id}/end")
def end_session_endpoint(session_id: str):
    """
    POST /api/v1/interview/{session_id}/end
    Conclude interview and compute performance summary.
    """
    try:
        return InterviewService.end_interview(session_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
