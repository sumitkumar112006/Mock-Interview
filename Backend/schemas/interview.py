from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class JDMatchResult(BaseModel):
    match_score: int = Field(ge=0, le=100)
    matching_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    overall_fit: str = "Moderate Fit"
    summary: str = ""
    recommendations: List[str] = Field(default_factory=list)


class InterviewRound(BaseModel):
    round_name: str
    topics: List[str] = Field(default_factory=list)
    question_count: int
    estimated_minutes: int


class InterviewPlan(BaseModel):
    plan_id: str
    target_role: str
    difficulty_level: str = "Mid-Level"
    rounds: List[InterviewRound] = Field(default_factory=list)
    total_questions: int = 5
    total_duration_minutes: int = 25


class InterviewQuestion(BaseModel):
    question_id: str
    question_number: int
    round_name: str
    topic: str
    question_text: str
    intent: str
    difficulty: str
    time_limit_minutes: int = 3
    expected_points: List[str] = Field(default_factory=list)
    source: Optional[str] = None


class AnswerEvaluation(BaseModel):
    evaluation_id: str
    question_id: str
    score: int = Field(ge=0, le=100)
    relevance_score: int = Field(ge=0, le=100)
    completeness_score: int = Field(ge=0, le=100)
    star_alignment: Dict[str, str] = Field(default_factory=dict)
    strengths: List[str] = Field(default_factory=list)
    areas_for_improvement: List[str] = Field(default_factory=list)
    feedback: str
    needs_followup: bool = False
    suggested_followup: Optional[str] = None


class FollowupQuestion(BaseModel):
    followup_id: str
    original_question_id: str
    followup_text: str
    intent: str
    focus_topic: str


class InterviewSession(BaseModel):
    session_id: str
    target_role: str
    status: str = "IN_PROGRESS"  # IN_PROGRESS, PAUSED, COMPLETED
    current_question_index: int = 0
    plan: InterviewPlan
    questions: List[InterviewQuestion] = Field(default_factory=list)
    history: List[Dict[str, Any]] = Field(default_factory=list)
    progress_percentage: int = 0
    started_at: str
    ended_at: Optional[str] = None
    final_summary: Optional[Dict[str, Any]] = None
