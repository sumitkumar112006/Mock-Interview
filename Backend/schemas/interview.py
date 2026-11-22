from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class Difficulty(str, Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"
    expert = "expert"


DIFFICULTY_GUIDE = {
    Difficulty.beginner: {
        "label": "Beginner",
        "questions": "Ask about fundamentals and what the candidate built. Use simple, single-concept questions "
                     "with no ambiguity. System design means a small, single-service scenario.",
        "evaluation": "Reward correct basics and clear reasoning. Do not expect trade-offs, scale numbers or "
                      "production experience. Do not penalize missing advanced topics.",
    },
    Difficulty.intermediate: {
        "label": "Intermediate",
        "questions": "Ask about practical implementation choices, debugging and common trade-offs. "
                     "System design covers one or two components with moderate scale.",
        "evaluation": "Expect correct reasoning, some trade-offs and concrete examples. "
                      "Minor gaps in edge cases are acceptable.",
    },
    Difficulty.advanced: {
        "label": "Advanced",
        "questions": "Ask about design decisions under constraints, performance, failure modes and ownership. "
                     "Include real ambiguity and ask them to justify choices.",
        "evaluation": "Expect trade-offs, edge cases, measurable results and clear ownership. "
                      "Vague answers score low.",
    },
    Difficulty.expert: {
        "label": "Expert",
        "questions": "Ask about architecture at scale, consistency, cost, org-level trade-offs, mentoring "
                     "and technical strategy. Use open-ended problems without a single right answer.",
        "evaluation": "Expect deep reasoning, alternatives considered, risks and mitigation, and leadership "
                      "impact. Surface-level answers score low.",
    },
}


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
    difficulty: Difficulty = Difficulty.intermediate
    difficulty_level: str = "Intermediate"
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
    improvement: List[str] = Field(default_factory=list)
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
