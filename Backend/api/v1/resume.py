from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from schemas.candidate import ResumeUploadResponse, ResumeAnalysisResponse
from services.resume_service import ResumeService
from tools.context import set_global_resume

router = APIRouter(prefix="/resume", tags=["Resume"])


@router.post("/upload", response_model=ResumeUploadResponse)
async def upload_and_parse_resume(file: UploadFile = File(...)):
    """
    POST /api/v1/resume/upload
    Uploads a resume file (PDF, DOCX, TXT) and parses skills, contact info, and text.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename must be provided."
        )

    ext = file.filename.lower().split(".")[-1] if "." in file.filename else ""
    if ext not in ["pdf", "docx", "doc", "txt", "md"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '.{ext}'. Supported: PDF, DOCX, DOC, TXT, MD."
        )

    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
    content = await file.read()

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded resume file is empty."
        )

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds maximum allowed limit of 10MB."
        )

    try:
        parsed_data = ResumeService.parse_resume(file.filename, content)
        # Store in global context so every tool and agent can access it
        set_global_resume(
            content=parsed_data.raw_text,
            filename=file.filename,
            parsed_data=parsed_data.model_dump()
        )
        return ResumeUploadResponse(
            status="success",
            message="Resume parsed successfully",
            data=parsed_data
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to parse resume: {str(e)}"
        )


@router.post("/analyze", response_model=ResumeAnalysisResponse)
async def analyze_candidate_resume(
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None)
):
    """
    POST /api/v1/resume/analyze
    Analyzes candidate resume (from uploaded file or raw text).
    Returns skills depth, seniority level, experience years, education, projects, and interview focus recommendations.
    """
    try:
        if file and file.filename:
            content = await file.read()
            if not content:
                raise HTTPException(status_code=400, detail="Uploaded file is empty.")
            parsed = ResumeService.parse_resume(file.filename, content)
            set_global_resume(parsed.raw_text, filename=file.filename, parsed_data=parsed.model_dump())
            analysis = ResumeService.analyze_resume(parsed)
        elif text and text.strip():
            set_global_resume(text.strip())
            analysis = ResumeService.analyze_resume(text.strip())
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either a file or text content must be provided for resume analysis."
            )

        return ResumeAnalysisResponse(
            status="success",
            message="Resume analyzed successfully",
            data=analysis
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to analyze resume: {str(e)}"
        )
