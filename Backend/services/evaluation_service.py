import re
import json
import time
import uuid
from typing import List, Optional, Dict, Any
from schemas.interview import AnswerEvaluation, FollowupQuestion, Difficulty, DIFFICULTY_GUIDE
from ai.llm.llm_manager import LLMManager


class EvaluationService:
    """
    Evaluates candidate responses using the STAR methodology, checking for
    technical depth, structural completeness, quantifiable impact, and relevance.
    Powered by LLM (qwen/qwen3.8-27b on Groq) with robust fallback heuristics.
    """

    STAR_KEYWORDS = {
        "situation": ["when i was", "at my previous", "in my last role", "our team was", "the project", "the situation"],
        "task": ["my responsibility was", "i was tasked with", "my goal was", "the objective", "needed to"],
        "action": ["i built", "i designed", "i implemented", "i analyzed", "i spearheaded", "i refactored", "i migrated", "i coordinated"],
        "result": ["as a result", "consequently", "reduced by", "increased by", "improved", "saved", "delivered", "outcome"]
    }

    @classmethod
    def evaluate_candidate_answer(
        cls,
        question_id: str,
        question_text: str,
        answer_text: str,
        expected_points: Optional[List[str]] = None,
        difficulty: Optional[str] = "intermediate"
    ) -> AnswerEvaluation:
        """
        Evaluates candidate response across relevance, STAR depth, and completeness.
        Uses LLM evaluation with comprehensive request/response logging calibrated to the target difficulty.
        """
        if not answer_text or not answer_text.strip():
            raise ValueError("Candidate answer text cannot be empty.")

        expected_points = expected_points or []
        start_eval_time = time.perf_counter()

        # Resolve difficulty rubric
        diff_key = difficulty or "intermediate"
        if isinstance(diff_key, str):
            try:
                diff_key = Difficulty(diff_key.lower())
            except ValueError:
                diff_key = Difficulty.intermediate
        guide = DIFFICULTY_GUIDE.get(diff_key, DIFFICULTY_GUIDE[Difficulty.intermediate])

        # -------------------------------------------------------------
        # 1. Attempt LLM Evaluation with Full Logging
        # -------------------------------------------------------------
        eval_prompt = f"""You are an elite, perceptive technical interviewer evaluating a candidate's spoken response.

INTERVIEW QUESTION:
"{question_text}"

TARGET DIFFICULTY LEVEL: {guide['label']}
CALIBRATED EVALUATION RUBRIC FOR THIS LEVEL:
{guide['evaluation']}

EXPECTED CORE COMPETENCIES / KEY POINTS:
{json.dumps(expected_points)}

CANDIDATE'S SPOKEN ANSWER:
"{answer_text}"

Evaluate the response objectively using the STAR framework (Situation, Task, Action, Result) calibrated to the {guide['label']} level.
Generate concise, spoken-style feedback that the interviewer will speak out loud to the candidate, followed by a sharp, highly contextual follow-up question probing deeper into technical trade-offs, architecture choices, or measurable metrics.

Return ONLY a valid JSON object matching this schema (no markdown, no extra commentary):
{{
  "score": <integer from 40 to 100>,
  "relevance_score": <integer from 40 to 100>,
  "completeness_score": <integer from 40 to 100>,
  "star_alignment": {{
    "Situation": "<Identified or Missing / Brief note>",
    "Task": "<Identified or Missing / Brief note>",
    "Action": "<Identified or Missing / Brief note>",
    "Result": "<Identified or Needs quantifiable metrics>"
  }},
  "strengths": ["<strength 1>", "<strength 2>"],
  "improvement": ["<concrete area for improvement or missing technical point 1>", "<concrete area 2>"],
  "feedback": "<2-3 sentences of natural, encouraging spoken feedback suitable to be read aloud to the candidate, noting what was strong and what needed more depth>",
  "needs_followup": true,
  "suggested_followup": "<a sharp, direct conversational follow-up question (1-2 sentences) challenging or drilling down into a specific technical choice or number they mentioned>"
}}"""

        raw_llm = LLMManager.call_llm(
            prompt=eval_prompt,
            system_instruction="You are an elite, objective technical interviewer and talent assessor. Always respond with pure valid JSON matching the requested schema.",
            temperature=0.2,
            max_tokens=900,
            context_name="AnswerEvaluation"
        )

        if raw_llm:
            try:
                # Strip code fencing if present
                clean_json = raw_llm.strip()
                if clean_json.startswith("```"):
                    clean_json = re.sub(r"^```(?:json)?\s*", "", clean_json)
                    clean_json = re.sub(r"\s*```$", "", clean_json)

                data = json.loads(clean_json)
                imp_list = data.get("improvement") or data.get("areas_for_improvement") or ["Quantify metrics further."]
                eval_latency_ms = round((time.perf_counter() - start_eval_time) * 1000, 1)
                print(f"⏱️ [EvaluationService] Question {question_id} evaluated via LLM in {eval_latency_ms}ms")
                return AnswerEvaluation(
                    evaluation_id=f"eval_{uuid.uuid4().hex[:10]}",
                    question_id=question_id,
                    score=int(data.get("score", 80)),
                    relevance_score=int(data.get("relevance_score", 85)),
                    completeness_score=int(data.get("completeness_score", 78)),
                    star_alignment=data.get("star_alignment", {
                        "Situation": "Identified",
                        "Task": "Identified",
                        "Action": "Identified",
                        "Result": "Identified"
                    }),
                    strengths=data.get("strengths", ["Clear technical communication."]),
                    areas_for_improvement=imp_list,
                    improvement=imp_list,
                    feedback=data.get("feedback", "Good explanation of system concepts and execution."),
                    needs_followup=bool(data.get("needs_followup", False)),
                    suggested_followup=data.get("suggested_followup", "How did you manage rollback strategy for that deployment?")
                )
            except Exception as e:
                print(f"[EvaluationService] JSON parse warning: {e}. Utilizing fallback heuristics.")

        # -------------------------------------------------------------
        # 2. Heuristic Rule-Based Fallback
        # -------------------------------------------------------------
        words = answer_text.strip().split()
        word_count = len(words)
        answer_lower = answer_text.lower()

        q_words = set(re.findall(r"\w+", question_text.lower()))
        ans_words = set(re.findall(r"\w+", answer_lower))
        overlap = len(q_words.intersection(ans_words))
        relevance_score = min(95, max(40, 50 + overlap * 5))

        matched_points = 0
        for pt in expected_points:
            pt_tokens = [w.lower() for w in pt.split() if len(w) > 3]
            if any(t in answer_lower for t in pt_tokens):
                matched_points += 1

        point_ratio = (matched_points / max(1, len(expected_points))) if expected_points else 0.8
        completeness_score = min(95, int(40 + min(word_count // 3, 30) + (point_ratio * 25)))

        star_alignment: Dict[str, str] = {}
        for dim, kw_list in cls.STAR_KEYWORDS.items():
            found = any(kw in answer_lower for kw in kw_list)
            star_alignment[dim.capitalize()] = "Identified" if found else "Not explicitly framed"

        strengths = []
        improvements = []

        if word_count >= 80:
            strengths.append("Provided detailed context and elaboration.")
        else:
            improvements.append("Elaborate further with specific concrete examples.")

        has_numbers = bool(re.search(r"\b\d+(?:%|x|k|ms|s|users|qps)?\b", answer_text))
        if has_numbers:
            strengths.append("Included quantifiable metrics and tangible outcomes.")
        else:
            improvements.append("Quantify the impact (e.g., % improvement, latency reduction, scale handled).")

        overall_score = int((relevance_score * 0.4) + (completeness_score * 0.6))
        needs_followup = word_count < 60 or not has_numbers

        suggested_followup = "Could you quantify the measurable outcome or scale of this solution?" if not has_numbers else "How did you handle error cases in that approach?"
        feedback = f"Solid response covering key aspects. Your answer demonstrated clarity (Score: {overall_score}/100)."
        eval_latency_ms = round((time.perf_counter() - start_eval_time) * 1000, 1)
        print(f"⏱️ [EvaluationService] Question {question_id} evaluated via Heuristic Fallback in {eval_latency_ms}ms")

        return AnswerEvaluation(
            evaluation_id=f"eval_{uuid.uuid4().hex[:10]}",
            question_id=question_id,
            score=overall_score,
            relevance_score=relevance_score,
            completeness_score=completeness_score,
            star_alignment=star_alignment,
            strengths=strengths,
            areas_for_improvement=improvements,
            improvement=improvements,
            feedback=feedback,
            needs_followup=needs_followup,
            suggested_followup=suggested_followup
        )

    @classmethod
    def generate_followup_question(
        cls,
        question_id: str,
        question_text: str,
        answer_text: str,
        evaluation: Optional[AnswerEvaluation] = None
    ) -> FollowupQuestion:
        """
        Generates an adaptive follow-up probing technical trade-offs or metric quantification.
        """
        followup_id = f"fup_{uuid.uuid4().hex[:8]}"

        if evaluation and evaluation.suggested_followup:
            prompt = evaluation.suggested_followup
            topic = "Outcome & Trade-offs"
        elif "trade-off" not in answer_text.lower():
            prompt = "What were the primary architectural trade-offs you had to balance when implementing this?"
            topic = "Architectural Trade-offs"
        elif not re.search(r"\d+", answer_text):
            prompt = "What was the measurable metric or business impact of this initiative after deployment?"
            topic = "Measurable Metrics"
        else:
            prompt = "If you had to redesign this system today to support 10x traffic, what would you change first?"
            topic = "Scalability & Resilience"

        return FollowupQuestion(
            followup_id=followup_id,
            original_question_id=question_id,
            followup_text=prompt,
            intent="Deepen candidate technical assessment and verify claimed experience.",
            focus_topic=topic
        )
