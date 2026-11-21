import uuid
import json
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union
from schemas.interview import (
    InterviewPlan,
    InterviewRound,
    InterviewQuestion,
    InterviewSession,
)
from ai.llm.llm_manager import LLMManager
from tools.context import (
    get_global_jd,
    get_global_resume,
    set_global_questions,
    get_global_questions,
)


SYSTEM_PROMPT = """You are a senior technical interviewer and hiring manager with 15+ years of experience.
You design interviews that test real depth, not memorized answers. Every question you write must be
traceable to something specific in the candidate's resume or the job description (JD).
You output only valid JSON, with no prose, markdown fences, or comments."""


def build_prompt(plan, jd_text: str, resume_text: str) -> str:
    return f"""Design a 5-question progressive technical interview for this candidate.

## CONTEXT
Target role: {plan.target_role}
Seniority / difficulty: {plan.difficulty_level}

<job_description>
{jd_text}
</job_description>

<candidate_resume>
{resume_text}
</candidate_resume>

## STEP 1: ANALYZE (internal, do not output)
Before writing questions, identify:
1. Top 5-8 must-have skills/technologies in the JD.
2. Resume projects, roles, and achievements that overlap with those skills (the strongest anchors).
3. Gaps: JD requirements missing or only lightly mentioned in the resume (good probing areas).
4. Claims on the resume that are vague or unquantified (worth verifying with a follow-up-style question).

## STEP 2: QUESTION STRUCTURE
Q1. Icebreaker + architecture overview
    Ask them to walk through ONE specific resume project most relevant to the JD, focusing on
    architecture, their personal role, and key technology choices. Name the project.
Q2. Deep technical problem solving + performance
    Pick a real challenge implied by a resume project or JD responsibility (e.g. slow queries,
    memory, concurrency, latency). Ask how they diagnosed and optimized it, or how they would.
Q3. Behavioral (STAR)
    Ground it in a situation plausible for their listed experience (conflict, ownership,
    tight deadline, leadership). Must reference their context, not a generic "tell me about a conflict".
Q4. System design / scalability / edge cases
    Scale up a system from the JD domain or their project: 10x traffic, failures, consistency,
    caching, data modeling. Include one concrete constraint (e.g. scale, latency, cost).
Q5. Code quality, testing, best practices
    Tie to their stack (e.g. testing strategy for their API, code review, error handling, CI/CD,
    security) and to quality practices the JD mentions.

## STEP 3: QUALITY RULES
- Each question must contain at least one concrete anchor: a named project, technology, or JD
  requirement. No generic template questions.
- Difficulty must match "{plan.difficulty_level}": adjust depth, ambiguity, and expected trade-off reasoning.
- Progression: each question should be harder or deeper than the previous (Q3 excepted).
- If the JD requires a skill the resume lacks, ask about it at an exploratory level
  ("how would you approach...") and do NOT assume they have used it.
- Never invent resume facts. Only reference what is actually written.
- Each question is 1-3 sentences, spoken-style, answerable in 2-4 minutes. One main ask per question.
- No yes/no questions, trivia, or definition-only questions ("What is REST?").
- No duplicate topics across the 5 questions.

## STEP 4: OUTPUT
Return ONLY a valid JSON array of exactly 5 objects, in order, with this schema:
[
  {{
    "round": "<Icebreaker | Technical Deep Dive | Behavioral | System Design | Code Quality>",
    "topic": "<specific topic, e.g. 'Redis caching in OrderService project'>",
    "question": "<the question to ask the candidate>",
    "intent": "<what this question assesses and why it matters for this JD>",
    "source": "<which resume item / JD requirement this question is anchored to>",
    "expected": ["<key point 1>", "<key point 2>", "<key point 3>", "<optional red flag or trade-off to listen for>"]
  }}
]
Output must be parseable by json.loads with no text before or after it."""


class InterviewService:
    """
    Core engine managing interview lifecycle: planning, starting, progression,
    adaptive question sequencing, and session completion.
    """

    _sessions: Dict[str, InterviewSession] = {}

    QUESTION_TEMPLATES = [
        {
            "round": "Technical Core",
            "topic": "Architecture & Data Flow",
            "question": "Can you walk me through the architecture of a complex application you designed or contributed to? How did data flow between the frontend and backend?",
            "intent": "Assess system comprehension, component modularity, and API design.",
            "expected": ["Data pipeline / API contract", "State management", "Error handling and caching"]
        },
        {
            "round": "Technical Deep-Dive",
            "topic": "Performance & Scalability",
            "question": "Describe a specific performance bottleneck or latency issue you encountered. What tools did you use to diagnose it, and how did you resolve it?",
            "intent": "Evaluate diagnostic ability, profiling, and optimization techniques.",
            "expected": ["Profiling tool identification", "Root cause explanation", "Measurable performance gain"]
        },
        {
            "round": "Behavioral",
            "topic": "Conflict Resolution & Collaboration",
            "question": "Tell me about a time you had a technical disagreement with a team member or stakeholder. How did you handle the situation and what was the outcome?",
            "intent": "Evaluate STAR framework delivery, empathy, compromise, and professional maturity.",
            "expected": ["Situation & Task context", "Constructive Action taken", "Measurable or positive Result"]
        },
        {
            "round": "System Design",
            "topic": "Resilience & Error Handling",
            "question": "How do you handle graceful degradation and failure modes when an external third-party service or database fails in your system?",
            "intent": "Check fault tolerance, circuit breakers, retry backoff, and fallback UI.",
            "expected": ["Circuit breaker / retry strategy", "Asynchronous queues / fallbacks", "User experience degradation"]
        },
        {
            "round": "Leadership & Process",
            "topic": "Code Quality & Mentorship",
            "question": "How do you maintain high code quality and test coverage in your team while balancing tight deadlines?",
            "intent": "Assess engineering standards, code reviews, CI/CD practices, and prioritization.",
            "expected": ["Automated test suites / CI/CD", "Thorough code reviews", "Pragmatic technical debt management"]
        }
    ]

    @classmethod
    def generate_interview_plan(
        cls,
        target_role: str = "Fullstack Software Engineer",
        seniority: str = "Mid-Level",
        skills: Optional[List[str]] = None
    ) -> InterviewPlan:
        """
        Creates a structured interview plan with calibrated rounds, duration, and question allocation.
        """
        plan_id = f"plan_{uuid.uuid4().hex[:10]}"
        skills = skills or ["React", "FastAPI", "System Design", "Databases"]

        rounds = [
            InterviewRound(
                round_name="Technical Core",
                topics=skills[:2],
                question_count=2,
                estimated_minutes=10
            ),
            InterviewRound(
                round_name="Behavioral & Problem Solving",
                topics=["STAR Method", "Cross-Functional Collaboration"],
                question_count=1,
                estimated_minutes=5
            ),
            InterviewRound(
                round_name="System Design & Scalability",
                topics=["Architecture", "Performance", "Security"],
                question_count=2,
                estimated_minutes=10
            )
        ]

        total_questions = sum(r.question_count for r in rounds)
        total_duration = sum(r.estimated_minutes for r in rounds)

        return InterviewPlan(
            plan_id=plan_id,
            target_role=target_role,
            difficulty_level=seniority,
            rounds=rounds,
            total_questions=total_questions,
            total_duration_minutes=total_duration
        )

    @classmethod
    def start_interview(
        cls,
        plan_or_role: Union[InterviewPlan, str] = "Software Engineer",
        questions: Optional[List[InterviewQuestion]] = None
    ) -> InterviewSession:
        """
        Initializes and registers a new active interview session.
        """
        session_id = f"session_{uuid.uuid4().hex[:12]}"

        if isinstance(plan_or_role, InterviewPlan):
            plan = plan_or_role
        else:
            plan = cls.generate_interview_plan(target_role=str(plan_or_role))

        # Generate custom tailored questions via LLM anchored directly to JD and Resume
        if not questions:
            questions = []
            jd_text = get_global_jd() or f"Role: {plan.target_role}\nSeniority: {plan.difficulty_level}\nRequirements: Fullstack development, architecture, performance, problem solving."
            resume_text = get_global_resume() or "Candidate with software engineering experience across frontend, backend, system architecture, and collaboration."

            prompt = build_prompt(plan, jd_text=jd_text, resume_text=resume_text)

            raw_llm = LLMManager.call_llm(
                prompt=prompt,
                system_instruction=SYSTEM_PROMPT,
                temperature=0.3,
                max_tokens=2500,
                context_name="InterviewQuestionGeneration"
            )

            parsed_list = None
            if raw_llm:
                try:
                    clean = raw_llm.strip()
                    if clean.startswith("```"):
                        clean = re.sub(r"^```(?:json)?\s*", "", clean)
                        clean = re.sub(r"\s*```$", "", clean)
                    parsed_list = json.loads(clean)
                except Exception as e:
                    print(f"[InterviewService] Question JSON parse warning: {e}")

            template_bank = parsed_list if (parsed_list and isinstance(parsed_list, list)) else cls.QUESTION_TEMPLATES

            for idx, tmpl in enumerate(template_bank[:5], start=1):
                questions.append(
                    InterviewQuestion(
                        question_id=f"q_{uuid.uuid4().hex[:8]}",
                        question_number=idx,
                        round_name=tmpl.get("round", "Technical Core"),
                        topic=tmpl.get("topic", "Engineering Fundamentals"),
                        question_text=tmpl.get("question", "Can you describe a challenging project you contributed to?"),
                        intent=tmpl.get("intent", "Evaluate problem-solving and architectural clarity."),
                        difficulty=plan.difficulty_level,
                        time_limit_minutes=3,
                        expected_points=tmpl.get("expected", ["System design", "Performance"]),
                        source=tmpl.get("source")
                    )
                )

            # Store the generated questions in the shared global variable accessible to every tool
            set_global_questions([q.model_dump() for q in questions])

            # Console output of generated questions to terminal
            print("\n" + "=" * 75)
            print("🎯 [LLM GENERATED INTERVIEW QUESTIONS]")
            print(f"💼 Role: {plan.target_role} | 📈 Seniority: {plan.difficulty_level}")
            print(f"📊 Total Questions: {len(questions)}")
            print("=" * 75)
            for q in questions:
                print(f"🔹 Q{q.question_number} [{q.round_name}] • {q.topic}")
                print(f"   ❓ Ask:      {q.question_text}")
                print(f"   🎯 Intent:   {q.intent}")
                if q.source:
                    print(f"   ⚓ Anchor:   {q.source}")
                if q.expected_points:
                    print(f"   ✅ Expected: {', '.join(q.expected_points)}")
                print("-" * 75)
            print("=" * 75 + "\n")

        started_at = datetime.now(timezone.utc).isoformat()

        session = InterviewSession(
            session_id=session_id,
            target_role=plan.target_role,
            status="IN_PROGRESS",
            current_question_index=0,
            plan=plan,
            questions=questions,
            history=[],
            progress_percentage=0,
            started_at=started_at
        )

        cls._sessions[session_id] = session
        return session

    @classmethod
    def get_session(cls, session_id: str) -> InterviewSession:
        """Retrieve an active or completed session by ID."""
        session = cls._sessions.get(session_id)
        if not session:
            raise KeyError(f"Interview session '{session_id}' not found.")
        return session

    @classmethod
    def get_current_question(cls, session_id: str) -> Optional[InterviewQuestion]:
        """Retrieve the currently active interview question."""
        session = cls.get_session(session_id)
        if session.current_question_index < len(session.questions):
            return session.questions[session.current_question_index]
        return None

    @classmethod
    def generate_next_question(
        cls,
        session_id: str,
        topic_hint: Optional[str] = None
    ) -> Optional[InterviewQuestion]:
        """
        Advances the session to the next question or returns None if interview complete.
        """
        session = cls.get_session(session_id)
        next_index = session.current_question_index + 1

        if next_index < len(session.questions):
            session.current_question_index = next_index
            total = len(session.questions)
            session.progress_percentage = int((next_index / total) * 100)
            return session.questions[next_index]

        # If at the end, mark completed
        session.current_question_index = len(session.questions)
        session.progress_percentage = 100
        session.status = "COMPLETED"
        session.ended_at = datetime.now(timezone.utc).isoformat()
        return None

    @classmethod
    def update_interview_progress(
        cls,
        session_id: str,
        answer_record: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Records the answer evaluation and updates overall interview completion status.
        """
        session = cls.get_session(session_id)

        if answer_record:
            session.history.append(answer_record)

        total_q = max(len(session.questions), 1)
        completed_q = len(session.history)
        progress = min(100, int((completed_q / total_q) * 100))
        session.progress_percentage = progress

        return {
            "session_id": session.session_id,
            "status": session.status,
            "current_question_index": session.current_question_index,
            "questions_completed": completed_q,
            "total_questions": total_q,
            "progress_percentage": progress,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }

    @classmethod
    def end_interview(cls, session_id: str) -> Dict[str, Any]:
        """
        Gracefully terminates an interview session and calculates summary metrics.
        """
        session = cls.get_session(session_id)
        session.status = "COMPLETED"
        session.ended_at = datetime.now(timezone.utc).isoformat()
        session.progress_percentage = 100

        total_questions_answered = len(session.history)
        scores = [h.get("score", 75) for h in session.history if isinstance(h, dict) and "score" in h]
        avg_score = round(sum(scores) / len(scores), 1) if scores else 80.0

        summary = {
            "session_id": session.session_id,
            "target_role": session.target_role,
            "status": "COMPLETED",
            "started_at": session.started_at,
            "ended_at": session.ended_at,
            "total_questions_planned": len(session.questions),
            "questions_answered": total_questions_answered,
            "average_performance_score": avg_score,
            "completion_rate": f"{session.progress_percentage}%"
        }
        session.final_summary = summary
        return summary
