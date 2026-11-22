from typing import Dict, Any, Optional
from services.report_service import ReportService


def generate_session_report(
    session_id: str,
    custom_target_role: Optional[str] = None
) -> Dict[str, Any]:
    """
    generate_session_report:
    Evaluates the complete interview session using the Entire Report Evaluation LLM tool,
    compiles all question performances, scores, improvements, and recommendations,
    and saves the complete structured JSON report to the Sessions/ directory.
    """
    report = ReportService.evaluate_entire_report(
        session_id=session_id,
        custom_target_role=custom_target_role
    )
    return report.model_dump()


def get_session_report(session_id: str) -> Optional[Dict[str, Any]]:
    """
    get_session_report:
    Retrieves an existing session report from Sessions/{session_id}.json.
    """
    return ReportService.load_session_report(session_id)
