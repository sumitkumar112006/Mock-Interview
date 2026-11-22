import os
import json
import re
import time
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from schemas.report import (
    EntireReportEvaluation,
    CategoryScores,
    QuestionReportItem,
    FollowupReportItem,
    ReportLLMOutput,
    validate_question_structure
)
from tools.context import get_global_jd, get_global_resume
from ai.llm.llm_manager import LLMManager


class ReportService:
    """
    Evaluates the complete interview session report across all attempted questions,
    candidate responses, follow-up answers, and competency dimensions.
    Persists the structured report to the Sessions/ folder as a JSON document.
    """

    SESSIONS_DIR = Path("Sessions")

    @classmethod
    def _ensure_sessions_dir(cls) -> Path:
        """Ensure Sessions directory exists at project root or backend root."""
        base_dirs = [
            Path.cwd() / "Sessions",
            Path(__file__).resolve().parent.parent / "Sessions",
            Path(__file__).resolve().parent.parent.parent / "Sessions"
        ]
        target_dir = base_dirs[0]
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir

    @classmethod
    def get_session_file_path(cls, session_id: str) -> Path:
        sessions_dir = cls._ensure_sessions_dir()
        safe_id = re.sub(r"[^a-zA-Z0-9_\-]", "_", session_id)
        return sessions_dir / f"{safe_id}.json"

    @classmethod
    def build_question_report_items(cls, session) -> List[QuestionReportItem]:
        """
        Organizes session history and planned questions into structured QuestionReportItems
        with nested follow-ups.
        """
        items: List[QuestionReportItem] = []
        questions_map = {q.question_id: q for q in session.questions}

        # Track main answers and follow-ups from session.history
        # Each entry in session.history is an evaluated answer or turn record
        grouped: Dict[str, Dict[str, Any]] = {}

        for idx, q in enumerate(session.questions, start=1):
            grouped[q.question_id] = {
                "question_number": idx,
                "topic": q.topic or q.round_name or "Core Competency",
                "que": q.question_text,
                "ans": "No answer recorded.",
                "score": 0,
                "improvement": [],
                "strengths": [],
                "feedback": "",
                "follow_ups": []
            }

        for record in session.history:
            if not isinstance(record, dict):
                continue

            qid = record.get("question_id") or record.get("questionId")
            is_followup = record.get("is_followup", False)
            ans_text = record.get("answer_text") or record.get("answerText") or record.get("ans") or ""
            score = int(record.get("score", 75))
            strengths = record.get("strengths") or []
            improvements = record.get("improvement") or record.get("areas_for_improvement") or []
            feedback = record.get("feedback") or ""

            if is_followup:
                # Group under parent question
                parent_id = record.get("original_question_id") or qid
                if parent_id in grouped:
                    followup_count = len(grouped[parent_id]["follow_ups"]) + 1
                    grouped[parent_id]["follow_ups"].append(
                        FollowupReportItem(
                            followup_number=followup_count,
                            que=record.get("question_text") or record.get("followup_text") or "Follow-up question",
                            ans=ans_text,
                            score=score,
                            improvement=improvements,
                            strengths=strengths
                        )
                    )
            else:
                if qid in grouped:
                    grouped[qid]["ans"] = ans_text
                    grouped[qid]["score"] = score
                    grouped[qid]["strengths"] = strengths
                    grouped[qid]["improvement"] = improvements
                    grouped[qid]["feedback"] = feedback
                else:
                    # Unplanned question
                    idx = len(grouped) + 1
                    grouped[qid] = {
                        "question_number": idx,
                        "topic": record.get("topic", "Technical Assessment"),
                        "que": record.get("question_text", "Interview question"),
                        "ans": ans_text,
                        "score": score,
                        "improvement": improvements,
                        "strengths": strengths,
                        "feedback": feedback,
                        "follow_ups": []
                    }

        for qid, data in grouped.items():
            # Validate each question structure strictly with Pydantic before adding
            items.append(validate_question_structure(data))

        items.sort(key=lambda x: x.question_number)
        return items

    @classmethod
    def evaluate_entire_report(
        cls,
        session_id: str,
        custom_target_role: Optional[str] = None
    ) -> EntireReportEvaluation:
        """
        Evaluates the entire interview session, generates comprehensive report metrics,
        and saves the complete JSON to Sessions/{session_id}.json.
        """
        start_report_time = time.perf_counter()
        from services.interview_service import InterviewService
        session = InterviewService.get_session(session_id)
        target_role = custom_target_role or session.target_role or "Software Engineer"
        seniority = getattr(session.plan, "difficulty_level", "Mid-Level") if session.plan else "Mid-Level"

        jd_text = get_global_jd() or "Standard industry requirements for " + target_role
        resume_text = get_global_resume() or "Candidate resume"

        question_items = cls.build_question_report_items(session)

        # Prepare summary of answers for the LLM prompt
        questions_summary = []
        for q in question_items:
            q_dict = {
                "question_number": q.question_number,
                "topic": q.topic,
                "question": q.que,
                "candidate_answer": q.ans,
                "score": q.score,
                "strengths": q.strengths,
                "improvement": q.improvement,
                "follow_ups": [
                    {
                        "followup_number": f.followup_number,
                        "question": f.que,
                        "candidate_answer": f.ans,
                        "score": f.score,
                        "improvement": f.improvement
                    }
                    for f in q.follow_ups
                ]
            }
            questions_summary.append(q_dict)

        report_prompt = f"""You are a Principal Technical Interviewer and Hiring Committee Chair.
You are evaluating the ENTIRE completed interview session for a candidate to produce a comprehensive hiring report.

TARGET ROLE: {target_role}
SENIORITY LEVEL: {seniority}

JOB DESCRIPTION CONTEXT:
\"\"\"{jd_text[:1500]}\"\"\"

CANDIDATE RESUME CONTEXT:
\"\"\"{resume_text[:1500]}\"\"\"

INTERVIEW SESSION PERFORMANCE & ALL ATTEMPTED QUESTIONS:
{json.dumps(questions_summary, indent=2)}

Perform a holistic evaluation of the candidate's answers and technical depth across all questions and follow-ups.
Return ONLY valid JSON matching this exact schema (no markdown, no extra commentary):
{{
  "hiring_decision": "<Strong Hire | Hire | Weak Hire | No Hire>",
  "overall_score": <integer from 40 to 100>,
  "summary": "<3-4 sentences synthesizing the candidate's performance, technical domain authority, and problem-solving maturity>",
  "category_scores": {{
    "technical_correctness": <integer 40-100>,
    "system_design_scalability": <integer 40-100>,
    "problem_solving_adaptability": <integer 40-100>,
    "communication_clarity": <integer 40-100>
  }},
  "key_strengths": [
    "<major strength 1 demonstrated across answers>",
    "<major strength 2 demonstrated across answers>",
    "<major strength 3>"
  ],
  "key_improvements": [
    "<most critical recurring technical gap or omission 1>",
    "<most critical recurring technical gap 2>"
  ],
  "actionable_recommendations": [
    "<concrete recommendation or study topic 1 to reach next seniority level>",
    "<concrete recommendation 2>",
    "<concrete recommendation 3>"
  ]
}}"""

        raw_llm = LLMManager.call_llm(
            prompt=report_prompt,
            system_instruction="You are an elite, objective technical hiring committee chair. Provide authoritative, deeply technical candidate evaluations in strict valid JSON.",
            temperature=0.2,
            max_tokens=1200,
            context_name="EntireReportEvaluation"
        )

        hiring_decision = "Hire"
        overall_score = 80
        summary = "Candidate demonstrated solid grasp of core engineering principles with good communication."
        cat_scores = CategoryScores(
            technical_correctness=82,
            system_design_scalability=78,
            problem_solving_adaptability=80,
            communication_clarity=82
        )
        key_strengths = ["Clear explanation of core technical decisions."]
        key_improvements = ["Could deepen coverage of edge-cases and error mitigation."]
        actionable_recs = ["Review distributed consistency and system failure modes."]

        if raw_llm:
            try:
                clean_json = raw_llm.strip()
                if clean_json.startswith("```"):
                    clean_json = re.sub(r"^```(?:json)?\s*", "", clean_json)
                    clean_json = re.sub(r"\s*```$", "", clean_json)

                data = json.loads(clean_json)
                # Strict validation of LLM output via Pydantic
                llm_output = ReportLLMOutput.model_validate(data)
                hiring_decision = llm_output.hiring_decision
                overall_score = llm_output.overall_score
                summary = llm_output.summary
                cat_scores = llm_output.category_scores
                key_strengths = llm_output.key_strengths or key_strengths
                key_improvements = llm_output.key_improvements or key_improvements
                actionable_recs = llm_output.actionable_recommendations or actionable_recs
            except Exception as e:
                print(f"[ReportService] Pydantic LLM validation warning: {e}. Using aggregated calculations.")

        # If LLM score is default, calculate weighted average from individual question scores
        scores = [q.score for q in question_items if q.score > 0]
        if scores and overall_score == 80:
            overall_score = int(sum(scores) / len(scores))

        report_id = f"rep_{uuid.uuid4().hex[:10]}"
        generated_at = datetime.now(timezone.utc).isoformat()
        file_path = cls.get_session_file_path(session_id)

        report = EntireReportEvaluation(
            report_id=report_id,
            session_id=session_id,
            generated_at=generated_at,
            target_role=target_role,
            seniority_level=seniority,
            hiring_decision=hiring_decision,
            overall_score=overall_score,
            summary=summary,
            category_scores=cat_scores,
            key_strengths=key_strengths,
            key_improvements=key_improvements,
            actionable_recommendations=actionable_recs,
            questions=question_items,
            saved_path=str(file_path)
        )

        # Save complete report to Sessions/{session_id}.json
        cls.save_session_report(session_id, report.model_dump())
        total_report_ms = round((time.perf_counter() - start_report_time) * 1000, 1)
        print(f"⏱️ [ReportService] Entire session report generated in {total_report_ms}ms")
        return report

    @classmethod
    def save_session_report(cls, session_id: str, report_dict: Dict[str, Any]) -> str:
        """
        Persists report dictionary to Sessions/{session_id}.json.
        """
        file_path = cls.get_session_file_path(session_id)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)
        print(f"📁 [ReportService] Session report saved successfully at: {file_path}")
        return str(file_path)

    @classmethod
    def load_session_report(cls, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a saved session report from Sessions/{session_id}.json.
        """
        file_path = cls.get_session_file_path(session_id)
        if not file_path.exists():
            return None
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
