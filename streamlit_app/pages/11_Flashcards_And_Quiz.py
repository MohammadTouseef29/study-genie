import os

import requests
import streamlit as st
from ui import apply_theme, chip_row, hero, section_title

API_BASE_URL = os.getenv("STUDY_GENIE_API_URL", "http://localhost:8000")
DEFAULT_COURSE_ID = "GENERAL"
DEFAULT_COURSE_NAME = "General Study Materials"

apply_theme("Flashcards and Quiz Generator")
hero(
    "Flashcards and Quiz Generator",
    "Generate, save, and evaluate study materials from transcript text or uploaded PDFs.",
    eyebrow="Active Recall Workspace",
    chips=["Transcript Input", "PDF Input", "Saved Sets", "Quiz Scoring"],
)


def generate_from_transcript(transcript: str, source_name: str, student_id: str) -> dict:
    response = requests.post(
        f"{API_BASE_URL}/study-materials/from-transcript",
        json={
            "transcript": transcript,
            "source_name": source_name,
            "student_id": student_id or None,
        },
        timeout=180,
    )
    response.raise_for_status()
    return response.json()


def generate_from_pdf(uploaded_files, student_id: str) -> dict:
    files = [
        (
            "files",
            (
                uploaded_file.name,
                uploaded_file.getvalue(),
                "application/pdf",
            ),
        )
        for uploaded_file in uploaded_files
    ]
    response = requests.post(
        f"{API_BASE_URL}/study-materials/from-pdf",
        files=files,
        data={"student_id": student_id or ""},
        timeout=300,
    )
    response.raise_for_status()
    return response.json()


def save_material(material: dict, student_id: str, course_id: str, course_name: str) -> dict:
    response = requests.post(
        f"{API_BASE_URL}/study-materials/save",
        json={
            "material": material,
            "student_id": student_id,
            "course_id": course_id,
            "course_name": course_name,
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def _error_detail(exc: requests.RequestException) -> str:
    response = getattr(exc, "response", None)
    if response is None:
        return "Could not reach the backend API."
    try:
        return response.json().get("detail", response.text)
    except ValueError:
        return response.text or f"Request failed with status {response.status_code}."


def submit_quiz(material_id: str, student_id: str, course_id: str, answers: list[str]) -> dict:
    response = requests.post(
        f"{API_BASE_URL}/study-materials/submit-quiz",
        json={
            "material_id": material_id,
            "student_id": student_id,
            "course_id": course_id,
            "answers": answers,
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


if "study_materials_result" not in st.session_state:
    st.session_state["study_materials_result"] = None
if "quiz_result" not in st.session_state:
    st.session_state["quiz_result"] = None

auth_user = st.session_state.get("auth_user")
student_id = auth_user["demo_student_id"] if auth_user else "guest"
course_id = DEFAULT_COURSE_ID
course_name = DEFAULT_COURSE_NAME

if auth_user:
    st.caption(f"Logged in as **{auth_user['name']}** — materials will be saved to your account.")
else:
    st.caption("Log in to save materials and quiz attempts to your account. You can still generate and try a quiz as a guest.")

source_mode = st.radio(
    "Source",
    ["Transcript", "PDF"],
    horizontal=True,
)

if source_mode == "Transcript":
    default_transcript = ""
    if "transcription_result" in st.session_state:
        default_transcript = st.session_state["transcription_result"].get("transcript", "")

    transcript = st.text_area(
        "Paste transcript text",
        value=default_transcript,
        height=220,
    )
    source_name = st.text_input("Source name", value="Transcript Input")
    run_disabled = len(transcript.strip()) < 20
    run_label = "Generate from Transcript"
else:
    uploaded_pdfs = st.file_uploader(
        "Upload one or more PDFs",
        type=["pdf"],
        accept_multiple_files=True,
    )
    run_disabled = not uploaded_pdfs
    run_label = "Generate from PDFs"

if st.button(run_label, use_container_width=True, disabled=run_disabled, type="primary"):
    with st.spinner("Generating flashcards and quiz..."):
        try:
            if source_mode == "Transcript":
                result = generate_from_transcript(transcript, source_name, student_id)
            else:
                result = generate_from_pdf(uploaded_pdfs, student_id)
            st.session_state["study_materials_result"] = result
            st.session_state["quiz_result"] = None
        except requests.RequestException:
            st.error(
                "Could not reach the backend API. Start FastAPI with "
                "`uvicorn backend.api:app --reload` and try again."
            )
            st.stop()

result = st.session_state.get("study_materials_result")

if result:
    top_left, top_right = st.columns([2, 1])

    with top_left:
        section_title("Topic Mapping", "These tags are also persisted for downstream analytics and reporting.")
        st.write(", ".join(result["topic_tags"]))
        st.caption(f"Material ID: {result['material_id']}")
        chip_row(result["topic_tags"])

    with top_right:
        st.metric("Flashcards", len(result["flashcards"]))
        st.metric("MCQs", len(result["quiz"]))

    if result.get("difficulty_bias"):
        difficulty_icon = {"easy": "🟢", "balanced": "🟡", "hard": "🔴"}.get(result["difficulty_bias"], "⚪")
        st.caption(f"{difficulty_icon} Adaptive difficulty: **{result['difficulty_bias'].title()}** — {result['difficulty_reason']}")

    is_saved = "saved_at" in result

    if st.button("Save Study Material", use_container_width=True):
        try:
            stored = save_material(result, student_id, course_id, course_name)
            st.session_state["study_materials_result"] = stored
            result = stored
            is_saved = True
            st.success("Study material saved successfully.")
        except requests.RequestException as exc:
            st.error(f"Could not save study material: {_error_detail(exc)}")
            st.stop()

    if not is_saved:
        st.caption("Save the study material before submitting the quiz so your attempt can be scored and stored.")

    section_title("Flashcards", "Use these as short active-recall prompts for revision.")
    for index, flashcard in enumerate(result["flashcards"], start=1):
        with st.container(border=True):
            st.markdown(f"**Card {index}**")
            st.markdown(f"**Topic:** `{flashcard['topic']}`")
            st.markdown(f"**Question:** {flashcard['question']}")
            st.markdown(f"**Answer:** {flashcard['answer']}")

    section_title("Quiz", "Answer every question to score the generated quiz and store the attempt.")
    answers = []
    for index, item in enumerate(result["quiz"], start=1):
        with st.container(border=True):
            st.markdown(f"**Question {index}**")
            st.markdown(f"**Topic:** `{item['topic']}`")
            st.caption(f"Difficulty: {item.get('difficulty', 'Medium')}")
            st.markdown(item["question"])
            selected = st.radio(
                f"Select answer for question {index}",
                item["options"],
                key=f"quiz_answer_{result['material_id']}_{index}",
                index=None,
            )
            answers.append(selected or "")

    if st.button("Submit Quiz", use_container_width=True, disabled=not is_saved, type="primary"):
        if not all(answer.strip() for answer in answers):
            st.warning("Answer all quiz questions before submitting.")
        else:
            try:
                st.session_state["quiz_result"] = submit_quiz(
                    material_id=result["material_id"],
                    student_id=student_id,
                    course_id=course_id,
                    answers=answers,
                )
            except requests.RequestException as exc:
                st.error(f"Could not submit quiz answers: {_error_detail(exc)}")
                st.stop()

quiz_result = st.session_state.get("quiz_result")
if quiz_result:
    section_title("Quiz Results", "Each attempt is scored and stored for later analysis.")
    score_col1, score_col2, score_col3 = st.columns(3)
    score_col1.metric("Score", quiz_result["score"])
    score_col2.metric("Total Questions", quiz_result["total_questions"])
    score_col3.metric("Percentage", f"{quiz_result['percentage']:.1f}%")

    for item in quiz_result["results"]:
        with st.container(border=True):
            status = "Correct" if item["is_correct"] else "Incorrect"
            st.markdown(f"**Question {item['question_number']} - {status}**")
            st.markdown(item["question"])
            st.markdown(f"**Selected:** {item['selected_answer']}")
            st.markdown(f"**Correct:** {item['correct_answer']}")
            st.caption(f"Difficulty: {item.get('difficulty', 'Medium')}")
            if item.get("explanation"):
                st.caption(item["explanation"])
