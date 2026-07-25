from __future__ import annotations

from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from backend.analytics.service import get_doubt_frequency_data
from backend.attendance.service import (
    delete_enrollment,
    enroll_student,
    get_photo_url,
    get_session_detail,
    list_attendance_history,
    list_roster,
    mark_attendance,
)
from backend.auth.service import get_profile, login as auth_login, signup as auth_signup
from backend.rag.loader import load_pdf
from backend.rag.qa_pipeline import get_answer
from backend.rag.vector_store import chunk_documents, count_documents, create_vector_store
from backend.study_materials.service import (
    evaluate_quiz,
    generate_from_pdfs,
    generate_from_transcript,
    list_saved_materials,
    load_saved_material,
    save_generated_material,
)
from backend.study_plan.service import build_study_plan
from backend.transcription.service import process_lecture_audio
from backend.transcription.transcribe import transcribe_audio

load_dotenv()


class ChatMessage(BaseModel):
    role: str
    content: str


class SignupRequest(BaseModel):
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=8)
    name: str = Field(..., min_length=1)


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=1)


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1)
    chat_history: list[ChatMessage] = Field(default_factory=list)
    top_k: int = Field(default=7, ge=1, le=15)


class TranscriptStudyMaterialRequest(BaseModel):
    transcript: str = Field(..., min_length=20)
    source_name: str = "Transcript Input"
    student_id: str | None = None


class SaveStudyMaterialRequest(BaseModel):
    material: dict
    student_id: str = Field(..., min_length=1)
    course_id: str = Field(..., min_length=1)
    course_name: str = Field(..., min_length=1)


class QuizSubmissionRequest(BaseModel):
    material_id: str = Field(..., min_length=1)
    student_id: str = Field(..., min_length=1)
    course_id: str = Field(..., min_length=1)
    answers: list[str]


app = FastAPI(title="Study Genie API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "Study Genie backend is running"}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "knowledge_base_ready": count_documents() > 0,
    }


@app.post("/auth/signup", status_code=201)
def signup(request: SignupRequest):
    try:
        return auth_signup(email=request.email, password=request.password, name=request.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/auth/login")
def login(request: LoginRequest):
    try:
        return auth_login(email=request.email, password=request.password)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@app.get("/auth/profile/{user_id}")
def profile(user_id: str):
    try:
        return get_profile(user_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/rag/ingest")
async def ingest_pdfs(files: list[UploadFile] = File(...)):
    pdf_files = [file for file in files if file.filename and file.filename.lower().endswith(".pdf")]
    if not pdf_files:
        raise HTTPException(status_code=400, detail="Upload at least one PDF file.")

    all_documents = []

    with TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        for upload in pdf_files:
            destination = tmp_path / Path(upload.filename).name
            content = await upload.read()
            destination.write_bytes(content)
            all_documents.extend(load_pdf(str(destination)))

    if not all_documents:
        raise HTTPException(status_code=400, detail="No readable content found in the uploaded PDFs.")

    chunks = chunk_documents(all_documents)
    create_vector_store(chunks)

    return {
        "message": "Knowledge base created successfully.",
        "documents_indexed": len(all_documents),
        "chunks_indexed": len(chunks),
        "files_processed": [file.filename for file in pdf_files],
    }


@app.post("/rag/query")
def rag_query(request: QueryRequest):
    if count_documents() == 0:
        raise HTTPException(status_code=400, detail="Knowledge base not found. Upload PDFs first.")

    chat_history = [message.model_dump() for message in request.chat_history]
    answer, sources = get_answer(
        request.question,
        chat_history=chat_history,
        top_k=request.top_k,
    )

    return {
        "answer": answer,
        "sources": sources,
    }


@app.post("/transcription/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    model_size: str = Form("base"),
    language: str = Form(""),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Audio filename is missing.")

    with TemporaryDirectory() as tmp_dir:
        suffix = Path(file.filename).suffix or ".tmp"
        temp_audio_path = Path(tmp_dir) / f"audio{suffix}"
        temp_audio_path.write_bytes(await file.read())

        result = transcribe_audio(
            str(temp_audio_path),
            model_size=model_size,
            language=language or None,
        )

    return {
        "filename": file.filename,
        "transcript": result["transcript"],
        "detected_language": result["language"],
    }


@app.post("/transcription/process")
async def process_transcription(
    file: UploadFile = File(...),
    model_size: str = Form("base"),
    language: str = Form(""),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Audio filename is missing.")

    with TemporaryDirectory() as tmp_dir:
        suffix = Path(file.filename).suffix or ".tmp"
        temp_audio_path = Path(tmp_dir) / f"audio{suffix}"
        temp_audio_path.write_bytes(await file.read())

        result = process_lecture_audio(
            str(temp_audio_path),
            model_size=model_size,
            language=language or None,
        )

    return {
        "filename": file.filename,
        **result,
    }


@app.post("/study-materials/from-transcript")
def study_materials_from_transcript(request: TranscriptStudyMaterialRequest):
    return generate_from_transcript(
        transcript=request.transcript,
        source_name=request.source_name,
        student_id=request.student_id,
    )


@app.post("/study-materials/from-pdf")
async def study_materials_from_pdf(files: list[UploadFile] = File(...), student_id: str = Form("")):
    pdf_files = [file for file in files if file.filename and file.filename.lower().endswith(".pdf")]
    if not pdf_files:
        raise HTTPException(status_code=400, detail="Upload at least one PDF file.")

    with TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        pdf_paths = []

        for upload in pdf_files:
            destination = tmp_path / Path(upload.filename).name
            destination.write_bytes(await upload.read())
            pdf_paths.append(str(destination))

        result = generate_from_pdfs(
            pdf_paths=pdf_paths,
            source_name=", ".join(file.filename for file in pdf_files),
            student_id=student_id or None,
        )

    return result


@app.post("/study-materials/save")
def save_study_materials(request: SaveStudyMaterialRequest):
    return save_generated_material(
        material=request.material,
        student_id=request.student_id,
        course_id=request.course_id,
        course_name=request.course_name,
    )


@app.get("/study-materials/saved")
def get_saved_study_materials():
    return {"materials": list_saved_materials()}


@app.get("/study-materials/{material_id}")
def get_saved_study_material(material_id: str):
    try:
        return load_saved_material(material_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/study-materials/submit-quiz")
def submit_quiz(request: QuizSubmissionRequest):
    try:
        return evaluate_quiz(
            material_id=request.material_id,
            answers=request.answers,
            student_id=request.student_id,
            course_id=request.course_id,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/analytics/doubt-frequency")
def doubt_frequency(student_id: str | None = None):
    return get_doubt_frequency_data(student_id=student_id)


@app.get("/study-plan/{student_id}")
def study_plan(
    student_id: str,
    days: int = 5,
    daily_minutes: int = 60,
    exam_date: str | None = None,
    priority_topic: str | None = None,
    goal: str = "Master my weak topics",
):
    parsed_exam_date = None
    if exam_date:
        try:
            parsed_exam_date = date.fromisoformat(exam_date)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="exam_date must be in YYYY-MM-DD format.") from exc

    try:
        return build_study_plan(
            student_id,
            days=days,
            daily_minutes=daily_minutes,
            exam_date=parsed_exam_date,
            priority_topic=priority_topic,
            goal=goal,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/attendance/enroll")
async def attendance_enroll(
    student_id: str = Form(...),
    name: str = Form(...),
    file: UploadFile = File(...),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Photo filename is missing.")

    image_bytes = await file.read()
    try:
        return enroll_student(student_id=student_id, name=name, image_bytes=image_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/attendance/roster")
def attendance_roster():
    return {"roster": list_roster()}


@app.get("/attendance/roster/{student_id}/photo")
def attendance_roster_photo(student_id: str):
    try:
        photo_url = get_photo_url(student_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return RedirectResponse(photo_url)


@app.delete("/attendance/roster/{student_id}")
def attendance_delete_enrollment(student_id: str):
    try:
        delete_enrollment(student_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"message": f"Removed enrollment for {student_id}."}


@app.post("/attendance/mark")
async def attendance_mark(
    course_id: str = Form(...),
    course_name: str = Form(""),
    session_label: str = Form(""),
    session_date: str = Form(""),
    file: UploadFile = File(...),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Classroom photo filename is missing.")

    image_bytes = await file.read()
    try:
        return mark_attendance(
            course_id=course_id,
            course_name=course_name,
            session_label=session_label,
            session_date=session_date,
            image_bytes=image_bytes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/attendance/history")
def attendance_history(course_id: str | None = None):
    return {"sessions": list_attendance_history(course_id=course_id)}


@app.get("/attendance/history/{session_id}")
def attendance_session_detail(session_id: str):
    records = get_session_detail(session_id)
    if not records:
        raise HTTPException(status_code=404, detail=f"No attendance session found: {session_id}")
    return {"session_id": session_id, "records": records}
