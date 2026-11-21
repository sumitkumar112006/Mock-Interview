import uuid
from typing import Optional, List
from pydantic import BaseModel
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from services.document_parser import DocumentParser
from services.resume_service import ResumeService
from tools.context import set_global_jd

router = APIRouter(prefix="/jd", tags=["Job Description"])


class JobDescriptionUploadResponse(BaseModel):
    status: str
    message: str
    jd_id: str
    filename: Optional[str] = None
    file_size_bytes: int
    word_count: int
    detected_skills: List[str]
    preview_text: str
    extracted_text: str


@router.post("/upload", response_model=JobDescriptionUploadResponse)
async def upload_job_description(
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None)
):
    """
    POST /api/v1/jd/upload
    Upload and parse a Job Description from file (PDF, DOCX, TXT) or raw text.
    Extracts requirements, skills, and prepares interview questions.
    """
    extracted_text = ""
    file_size = 0
    filename = None

    if file and file.filename:
        filename = file.filename
        ext = filename.lower().split(".")[-1] if "." in filename else ""
        if ext not in ["pdf", "docx", "doc", "txt", "md"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File extension '.{ext}' is not supported. Please upload a PDF, DOCX, or TXT file."
            )

        MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
        content = await file.read()
        file_size = len(content)

        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded job description file is empty."
            )

        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File size exceeds maximum allowed limit of 10MB."
            )

        extracted_text, _ = DocumentParser.parse_file(filename, content)
    elif text and text.strip():
        extracted_text = text.strip()
        file_size = len(extracted_text.encode("utf-8"))
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either a file or text content must be provided for the job description."
        )

    words = extracted_text.split()
    word_count = len(words)
    _, detected_skills = ResumeService._detect_skills(extracted_text)
    preview_text = extracted_text[:300] + ("..." if len(extracted_text) > 300 else "")
    jd_id = f"jd_{uuid.uuid4().hex[:12]}"

    # Store in global context so every tool and agent can access it
    set_global_jd(
        content=extracted_text,
        filename=filename,
        detected_skills=detected_skills
    )

    return JobDescriptionUploadResponse(
        status="success",
        message="Job description parsed and processed successfully",
        jd_id=jd_id,
        filename=filename,
        file_size_bytes=file_size,
        word_count=word_count,
        detected_skills=detected_skills,
        preview_text=preview_text,
        extracted_text=extracted_text
    )
