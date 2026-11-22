from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from services.report_service import ReportService
from schemas.report import EntireReportEvaluation

router = APIRouter(prefix="/reports", tags=["Reports"])


class GenerateReportRequest(BaseModel):
    target_role: Optional[str] = None


@router.post("/generate/{session_id}", response_model=EntireReportEvaluation)
def generate_report_endpoint(session_id: str, req: Optional[GenerateReportRequest] = None):
    """
    POST /api/v1/reports/generate/{session_id}
    Triggers the Entire Report Evaluation LLM tool for the given session,
    compiles all question/follow-up improvements and scores, saves to Sessions/{session_id}.json,
    and returns the structured report.
    """
    try:
        custom_role = req.target_role if req else None
        return ReportService.evaluate_entire_report(session_id, custom_role)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=f"Session not found: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate session report: {str(e)}")


@router.get("/{session_id}", response_model=Dict[str, Any])
def get_report_endpoint(session_id: str):
    """
    GET /api/v1/reports/{session_id}
    Retrieves the persisted session report from Sessions/{session_id}.json.
    """
    report = ReportService.load_session_report(session_id)
    if not report:
        # If not already generated, generate it on demand
        try:
            generated = ReportService.evaluate_entire_report(session_id)
            return generated.model_dump()
        except KeyError:
            raise HTTPException(status_code=404, detail="Session report not found.")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Report generation error: {str(e)}")
    return report
