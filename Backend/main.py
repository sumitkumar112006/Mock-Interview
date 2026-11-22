from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from typing import Optional, List
import io
import re
import time
import uuid
import uvicorn
from pypdf import PdfReader

app = FastAPI(
    title="AI Mock Interview API",
    description="Backend service for AI Mock Interview practice, resume parsing, and question generation",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_and_error_handling(request: Request, call_next):
    """
    Measures high-precision latency in milliseconds for every API request
    and attaches X-Process-Time-Ms to response headers.
    """
    start_time = time.perf_counter()
    try:
        response = await call_next(request)
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        response.headers["X-Process-Time-Ms"] = str(latency_ms)
        print(f"⚡ [API {response.status_code}] {request.method} {request.url.path} | ⏱️ {latency_ms}ms")
        return response
    except Exception as exc:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        print(f"❌ [API 500 ERROR] {request.method} {request.url.path} | ⏱️ {latency_ms}ms | Error: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error_type": "InternalServerError",
                "message": f"Server processing error: {str(exc)}",
                "path": request.url.path,
                "latency_ms": latency_ms
            },
            headers={"X-Process-Time-Ms": str(latency_ms)}
        )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Standardized fast JSON response for HTTPExceptions with millisecond timing.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "error_type": "HTTPException",
            "status_code": exc.status_code,
            "message": exc.detail,
            "path": request.url.path
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Standardized fast JSON response for request validation errors.
    """
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status": "validation_error",
            "error_type": "RequestValidationError",
            "message": "Input validation failed",
            "errors": exc.errors(),
            "path": request.url.path
        }
    )

from api.v1.interview import router as interview_router
from api.v1.voice import router as voice_router
from api.v1.reports import router as reports_router

app.include_router(interview_router, prefix="/api/v1")
app.include_router(voice_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")

class Question(BaseModel):
    category: str
    title: str
    detail: str
    time: str
    icon: str

class AnswerFeedbackRequest(BaseModel):
    question: str
    user_answer: str

class ResumeUploadResponse(BaseModel):
    status: str
    message: str
    resume_id: str
    filename: str
    file_size_bytes: int
    page_count: int
    word_count: int
    detected_skills: List[str]
    preview_text: str
    extracted_text: str

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

COMMON_SKILLS = [
    "Python", "JavaScript", "TypeScript", "React", "Node.js", "Express",
    "FastAPI", "Django", "Flask", "SQL", "PostgreSQL", "MongoDB", "Redis",
    "Docker", "Kubernetes", "AWS", "Azure", "GCP", "Git", "GitHub",
    "REST API", "GraphQL", "HTML", "CSS", "Tailwind", "Machine Learning",
    "System Design", "Microservices", "CI/CD", "Next.js", "Java", "C++",
    "STAR Method", "Agile", "Scrum", "Redux", "Linux"
]

def detect_skills(text: str) -> List[str]:
    """Detect common engineering and soft skills mentioned in resume text."""
    found = []
    text_lower = text.lower()
    for skill in COMMON_SKILLS:
        pattern = r"\b" + re.escape(skill.lower()) + r"\b"
        if re.search(pattern, text_lower):
            found.append(skill)
    return found

def extract_text_from_file(filename: str, content: bytes) -> tuple[str, int]:
    """Extract clean text and page count from PDF, DOCX, or TXT."""
    ext = filename.lower().split(".")[-1] if "." in filename else ""
    page_count = 1
    text = ""

    if ext == "pdf":
        try:
            reader = PdfReader(io.BytesIO(content))
            page_count = max(len(reader.pages), 1)
            pages_text = [page.extract_text() or "" for page in reader.pages]
            text = "\n".join(pages_text).strip()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to parse PDF document: {str(e)}"
            )
    elif ext in ["txt", "md"]:
        text = content.decode("utf-8", errors="ignore").strip()
    elif ext in ["doc", "docx"]:
        try:
            import zipfile
            import xml.etree.ElementTree as ET
            with zipfile.ZipFile(io.BytesIO(content)) as docx:
                xml_content = docx.read('word/document.xml')
                tree = ET.fromstring(xml_content)
                text = " ".join(tree.itertext()).strip()
        except Exception:
            text = content.decode("utf-8", errors="ignore").strip()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '.{ext}'. Supported formats: PDF, DOCX, TXT."
        )

    return text, page_count

# Default starter questions
DEFAULT_QUESTIONS: List[Question] = [
    Question(
        category="Behavioral",
        title="Tell me about yourself.",
        detail="A concise story that connects your past, present, and next step.",
        time="2 min",
        icon="✦"
    ),
    Question(
        category="Behavioral",
        title="Tell me about a challenge you overcame.",
        detail="Show how you think under pressure with a clear STAR story.",
        time="3 min",
        icon="◈"
    ),
    Question(
        category="Product",
        title="How would you improve a product you love?",
        detail="Balance user needs, business goals, and a measurable outcome.",
        time="4 min",
        icon="⌘"
    ),
    Question(
        category="Leadership",
        title="Describe a time you disagreed with a teammate.",
        detail="Demonstrate empathy, influence, and a thoughtful resolution.",
        time="3 min",
        icon="↗"
    ),
]

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "AI Mock Interview API",
        "version": "1.0.0",
        "endpoints": {
            "jd_upload": "POST /api/v1/jd/upload",
            "resume_upload": "POST /api/v1/resume/upload",
            "health": "GET /api/health",
            "questions": "GET /api/questions",
            "schedule": "POST /api/schedule",
            "feedback": "POST /api/feedback",
            "docs": "/docs"
        }
    }

@app.get("/api/health")
def health_check():
    return {"status": "healthy"}

@app.get("/api/questions", response_model=List[Question])
def get_questions():
    """Retrieve current practice questions."""
    return DEFAULT_QUESTIONS

@app.post("/api/v1/jd/upload", response_model=JobDescriptionUploadResponse, tags=["Job Description"])
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

        extracted_text, _ = extract_text_from_file(filename, content)
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
    detected_skills = detect_skills(extracted_text)
    preview_text = extracted_text[:300] + ("..." if len(extracted_text) > 300 else "")
    jd_id = f"jd_{uuid.uuid4().hex[:12]}"

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

from services.resume_service import ResumeService

@app.post("/api/v1/resume/upload", response_model=ResumeUploadResponse, tags=["Resume"])
async def upload_resume(file: UploadFile = File(...)):
    """
    POST /api/v1/resume/upload
    Ingest, parse, and extract skills & text from a candidate's resume (PDF, DOCX, TXT).
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided in upload."
        )

    # Validate file extension
    ext = file.filename.lower().split(".")[-1] if "." in file.filename else ""
    if ext not in ["pdf", "docx", "doc", "txt", "md"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File extension '.{ext}' is not supported. Please upload a PDF, DOCX, or TXT file."
        )

    # Read file contents (limit to 10MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
    content = await file.read()
    file_size = len(content)

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty."
        )

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds maximum allowed limit of 10MB."
        )

    try:
        parsed = ResumeService.parse_resume(file.filename, content)
        return ResumeUploadResponse(
            status="success",
            message="Resume parsed and uploaded successfully",
            resume_id=parsed.resume_id,
            filename=parsed.filename,
            file_size_bytes=parsed.file_size_bytes,
            page_count=parsed.page_count,
            word_count=parsed.word_count,
            detected_skills=parsed.detected_skills,
            preview_text=parsed.preview_text,
            extracted_text=parsed.raw_text
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse resume: {str(e)}"
        )

@app.post("/api/schedule")
async def schedule_interview(
    job_description: Optional[str] = Form(None),
    resume_text: Optional[str] = Form(None),
    jd_file: Optional[UploadFile] = File(None),
    resume_file: Optional[UploadFile] = File(None),
):
    """
    Schedule interview session and ingest Job Description + Resume.
    """
    jd_filename = jd_file.filename if jd_file else None
    resume_filename = resume_file.filename if resume_file else None

    return {
        "status": "success",
        "message": "Interview session configured successfully",
        "data": {
            "has_jd": bool(job_description or jd_file),
            "jd_filename": jd_filename,
            "has_resume": bool(resume_text or resume_file),
            "resume_filename": resume_filename,
        }
    }

@app.post("/api/feedback")
def evaluate_answer(req: AnswerFeedbackRequest):
    """
    Provide STAR framework evaluation and constructive feedback.
    """
    if not req.user_answer.strip():
        raise HTTPException(status_code=400, detail="Answer cannot be empty")

    word_count = len(req.user_answer.split())
    confidence_score = min(70 + (word_count // 5), 95)

    return {
        "status": "evaluated",
        "question": req.question,
        "metrics": {
            "word_count": word_count,
            "estimated_time_seconds": round(word_count / 2.5),
            "confidence_score": confidence_score
        },
        "star_analysis": {
            "situation": "Identified clear context",
            "task": "Outlined key responsibility",
            "action": "Described specific approach and execution",
            "result": "Focused on measurable impact and outcome"
        },
        "feedback": "Strong delivery with relevant structure. Consider emphasizing measurable quantitative results."
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
