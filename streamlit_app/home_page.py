import os

import requests
import streamlit as st

from ui import apply_theme, feature_card, hero_home, section_title, status_row

API_BASE_URL = os.getenv("STUDY_GENIE_API_URL", "http://localhost:8000")

apply_theme("Home", page_icon="🎓")

hero_home(
    "Study Genie",
    "An AI-powered classroom intelligence workspace that turns lectures, PDFs, activity data, and student signals into usable academic support.",
    eyebrow="Classroom Intelligence Platform",
    chips=["RAG Doubt Solver", "Lecture Notes", "Flashcards", "Attendance", "Study Plans"],
)

try:
    health = requests.get(f"{API_BASE_URL}/health", timeout=4).json()
    backend_state = "on"
    kb_state = "on" if health.get("knowledge_base_ready") else "warn"
    kb_label = "Knowledge base ready" if health.get("knowledge_base_ready") else "Knowledge base empty"
except requests.RequestException:
    backend_state = "off"
    kb_state = "off"
    kb_label = "Knowledge base unknown"

status_row(
    [
        ("Backend online" if backend_state == "on" else "Backend unreachable", backend_state),
        (kb_label, kb_state),
    ]
)

if backend_state == "off":
    st.info(f"Start the FastAPI backend to bring the workspace online: `uvicorn backend.api:app --reload` (expected at {API_BASE_URL}).")

section_title("Learn & Create", "Turn raw course material into structured study assets.")
learn_col1, learn_col2, learn_col3, learn_col4, learn_col5 = st.columns(5)

with learn_col1:
    feature_card("💬", "AI Doubt Solver", "Ask grounded questions over your uploaded PDFs with cited sources.", "/Doubt_Solver_API", "primary")

with learn_col2:
    feature_card("🎙️", "Lecture Transcription", "Turn audio into a transcript, summary, key points, and tags.", "/Lecture_Transcription", "amber")

with learn_col3:
    feature_card("🗂️", "Flashcards & Quiz", "Generate, save, and score flashcards and MCQs from any source.", "/Flashcards_And_Quiz", "teal")

with learn_col4:
    feature_card("🧑‍🤝‍🧑", "Attendance Studio", "Enroll faces once, then mark attendance from a group photo.", "/Attendance_Studio", "primary")

with learn_col5:
    feature_card("🗓️", "Study Plan", "Turn risk score and weak topics into a day-by-day study schedule.", "/Study_Plan", "amber")
