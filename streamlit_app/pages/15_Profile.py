import os

import pandas as pd
import requests
import streamlit as st
from ui import apply_theme, chip_row, hero, section_title

API_BASE_URL = os.getenv("STUDY_GENIE_API_URL", "http://localhost:8000")

apply_theme("Profile")
hero(
    "Your Profile",
    "Account details and your real activity across Study Genie.",
    eyebrow="Account",
    chips=["Saved Materials", "Quiz History", "Attendance", "Demo Risk Profile"],
)

auth_user = st.session_state.get("auth_user")

if not auth_user:
    st.info("Log in to see your profile and activity.")
    if st.button("Go to Log In", type="primary"):
        st.switch_page("pages/14_Login.py")
    st.stop()


def _error_detail(exc: requests.RequestException) -> str:
    response = getattr(exc, "response", None)
    if response is None:
        return "Could not reach the backend API."
    try:
        return response.json().get("detail", response.text)
    except ValueError:
        return response.text or f"Request failed with status {response.status_code}."


try:
    response = requests.get(f"{API_BASE_URL}/auth/profile/{auth_user['user_id']}", timeout=30)
    response.raise_for_status()
    profile = response.json()
except requests.RequestException as exc:
    st.error(f"Could not load your profile: {_error_detail(exc)}")
    st.stop()

user = profile["user"]
activity = profile["activity"]

with st.container(border=True):
    header_col, action_col = st.columns([3, 1])
    with header_col:
        section_title(user["name"], user["email"])
        chip_row([f"Member since {user['created_at'][:10]}", f"Demo profile: {user['demo_student_id']}"])
    with action_col:
        if st.button("Log Out", use_container_width=True):
            st.session_state.pop("auth_user", None)
            st.switch_page("home_page.py")

st.caption(
    "Saved materials, quiz attempts, and attendance below are 100% your real activity. "
    "Risk score and doubt topics are backed by a simulated classroom profile linked to your account."
)

section_title("Activity Summary")
metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
metric_col1.metric("Saved Materials", activity["saved_materials_count"])
metric_col2.metric("Quiz Attempts", activity["quiz_attempts_count"])
metric_col3.metric(
    "Avg Quiz Score",
    f"{activity['avg_quiz_percentage']:.1f}%" if activity["avg_quiz_percentage"] is not None else "—",
)
metric_col4.metric("Attendance Marked Present", activity["attendance_present_count"])

if st.button("View My Study Plan", type="primary"):
    st.switch_page("pages/13_Study_Plan.py")

section_title("Recent Saved Materials")
if activity["saved_materials"]:
    st.dataframe(
        pd.DataFrame(activity["saved_materials"]).rename(
            columns={
                "material_id": "Material ID",
                "saved_at": "Saved At",
                "course_name": "Course",
                "flashcard_count": "Flashcards",
                "quiz_count": "MCQs",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.caption("No saved study materials yet. Generate one from the Flashcards & Quiz page.")

section_title("Recent Quiz Attempts")
if activity["recent_quiz_attempts"]:
    st.dataframe(
        pd.DataFrame(activity["recent_quiz_attempts"]).rename(
            columns={
                "material_id": "Material ID",
                "attempted_at": "Attempted At",
                "score": "Score",
                "total_questions": "Total Questions",
                "percentage": "Percentage",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.caption("No quiz attempts yet.")

section_title("Top Doubt Topics (Demo Data)", "Based on your linked demo classroom profile.")
if activity["top_doubt_topics"]:
    chip_row([f"{item['topic']} ({item['total_questions']})" for item in activity["top_doubt_topics"]])
else:
    st.caption("No doubt activity recorded for your demo profile.")

section_title("Classroom Doubt Frequency (Demo Data)", "How often the wider classroom asks doubts per topic, and which topics generate disproportionate doubt volume.")
try:
    doubt_response = requests.get(f"{API_BASE_URL}/analytics/doubt-frequency", timeout=30)
    doubt_response.raise_for_status()
    doubt_payload = doubt_response.json()
    if doubt_payload["high_doubt_topics"]:
        chip_row([f"High doubt: {topic}" for topic in doubt_payload["high_doubt_topics"]])
    st.dataframe(
        pd.DataFrame(doubt_payload["topic_summary"]).rename(
            columns={
                "topic": "Topic",
                "total_questions": "Total Questions",
                "unique_students": "Unique Students",
                "interactions": "Interactions",
                "avg_questions_per_interaction": "Avg Questions / Interaction",
                "trend": "Trend",
                "high_doubt": "High Doubt Area",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )
except requests.RequestException as exc:
    st.error(f"Could not load classroom doubt frequency: {_error_detail(exc)}")
