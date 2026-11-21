"""
Global Context for Interview Tools and Agents.
Stores the active Job Description (JD) and Candidate Resume content
in globally accessible variables so every tool and agent can access them.
"""
from typing import Dict, Any, List, Optional

# =====================================================================
# Shared Global Variables Accessible by Every Tool & Agent
# =====================================================================
GLOBAL_JD_CONTENT: str = ""
GLOBAL_RESUME_CONTENT: str = ""
GLOBAL_QUESTIONS: List[Dict[str, Any]] = []

# Global metadata container for full interview context
INTERVIEW_CONTEXT: Dict[str, Any] = {
    "jd_content": "",
    "resume_content": "",
    "jd_filename": None,
    "resume_filename": None,
    "detected_skills": [],
    "parsed_resume": {},
    "questions": [],
}


def set_global_jd(
    content: str,
    filename: Optional[str] = None,
    detected_skills: Optional[List[str]] = None
) -> None:
    """
    Store the Job Description content in the global variable and context.
    """
    global GLOBAL_JD_CONTENT
    GLOBAL_JD_CONTENT = content or ""
    INTERVIEW_CONTEXT["jd_content"] = GLOBAL_JD_CONTENT
    if filename:
        INTERVIEW_CONTEXT["jd_filename"] = filename
    if detected_skills is not None:
        INTERVIEW_CONTEXT["detected_skills"] = detected_skills
    print(f"📋 [GLOBAL CONTEXT] GLOBAL_JD_CONTENT updated ({len(GLOBAL_JD_CONTENT)} chars, file: {filename})")


def get_global_jd() -> str:
    """
    Retrieve the current global Job Description content.
    """
    return GLOBAL_JD_CONTENT or INTERVIEW_CONTEXT.get("jd_content", "")


def set_global_resume(
    content: str,
    filename: Optional[str] = None,
    parsed_data: Optional[Dict[str, Any]] = None
) -> None:
    """
    Store the Candidate Resume content in the global variable and context.
    """
    global GLOBAL_RESUME_CONTENT
    GLOBAL_RESUME_CONTENT = content or ""
    INTERVIEW_CONTEXT["resume_content"] = GLOBAL_RESUME_CONTENT
    if filename:
        INTERVIEW_CONTEXT["resume_filename"] = filename
    if parsed_data is not None:
        INTERVIEW_CONTEXT["parsed_resume"] = parsed_data
    print(f"📄 [GLOBAL CONTEXT] GLOBAL_RESUME_CONTENT updated ({len(GLOBAL_RESUME_CONTENT)} chars, file: {filename})")


def get_global_resume() -> str:
    """
    Retrieve the current global Candidate Resume content.
    """
    return GLOBAL_RESUME_CONTENT or INTERVIEW_CONTEXT.get("resume_content", "")


def set_global_questions(questions: List[Dict[str, Any]]) -> None:
    """
    Store the generated interview questions in the global variable and context.
    """
    global GLOBAL_QUESTIONS
    GLOBAL_QUESTIONS = questions or []
    INTERVIEW_CONTEXT["questions"] = GLOBAL_QUESTIONS
    print(f"🎯 [GLOBAL CONTEXT] GLOBAL_QUESTIONS updated ({len(GLOBAL_QUESTIONS)} questions stored)")


def get_global_questions() -> List[Dict[str, Any]]:
    """
    Retrieve the current global interview questions.
    """
    return GLOBAL_QUESTIONS or INTERVIEW_CONTEXT.get("questions", [])


def get_interview_context() -> Dict[str, Any]:
    """
    Retrieve the complete shared interview context dictionary.
    """
    return {
        "jd_content": get_global_jd(),
        "resume_content": get_global_resume(),
        "questions": get_global_questions(),
        "jd_filename": INTERVIEW_CONTEXT.get("jd_filename"),
        "resume_filename": INTERVIEW_CONTEXT.get("resume_filename"),
        "detected_skills": INTERVIEW_CONTEXT.get("detected_skills", []),
        "parsed_resume": INTERVIEW_CONTEXT.get("parsed_resume", {})
    }


def clear_interview_context() -> None:
    """
    Reset all global context variables for a clean interview session.
    """
    global GLOBAL_JD_CONTENT, GLOBAL_RESUME_CONTENT, GLOBAL_QUESTIONS
    GLOBAL_JD_CONTENT = ""
    GLOBAL_RESUME_CONTENT = ""
    GLOBAL_QUESTIONS = []
    INTERVIEW_CONTEXT["jd_content"] = ""
    INTERVIEW_CONTEXT["resume_content"] = ""
    INTERVIEW_CONTEXT["questions"] = []
    INTERVIEW_CONTEXT["jd_filename"] = None
    INTERVIEW_CONTEXT["resume_filename"] = None
    INTERVIEW_CONTEXT["detected_skills"] = []
    INTERVIEW_CONTEXT["parsed_resume"] = {}
    print("🧹 [GLOBAL CONTEXT] Interview context cleared.")
