import os
from datetime import date

import requests
import streamlit as st
from ui import apply_theme, chip_row, hero, require_login, section_title

API_BASE_URL = os.getenv("STUDY_GENIE_API_URL", "http://localhost:8000")

apply_theme("Personalized Study Plan")
hero(
    "Personalized Study Plan",
    "Turns each student's risk score and weak topics into a concrete day-by-day study schedule. "
    "The plan adapts day by day as your quiz scores in each subject change.",
    eyebrow="Adaptive Guidance",
    chips=["Risk-Aware", "Weak Topic Targeting", "Day-By-Day Plan", "API Backed"],
)

auth_user = require_login("your study plan")

DAILY_MINUTES_OPTIONS = {
    "15-30 min": 25,
    "30-60 min": 45,
    "60-90 min": 75,
    "90+ min": 100,
}

GOAL_OPTIONS = [
    "Pass an upcoming exam",
    "Master my weak topics",
    "Quick revision before a test",
    "Build long-term understanding",
]


def _error_detail(exc: requests.RequestException) -> str:
    response = getattr(exc, "response", None)
    if response is None:
        return "Could not reach the backend API."
    try:
        return response.json().get("detail", response.text)
    except ValueError:
        return response.text or f"Request failed with status {response.status_code}."


def get_study_plan(
    student_id: str,
    plan_days: int,
    daily_minutes: int,
    exam_date: date | None,
    priority_topic: str,
    goal: str,
) -> dict:
    params = {"days": plan_days, "daily_minutes": daily_minutes, "goal": goal}
    if exam_date:
        params["exam_date"] = exam_date.isoformat()
    if priority_topic.strip():
        params["priority_topic"] = priority_topic.strip()

    response = requests.get(f"{API_BASE_URL}/study-plan/{student_id}", params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def render_plan(plan_result: dict):
    section_title("Your Plan", "Generated from live risk scoring and per-topic quiz performance.")

    risk_state = {"High": "🔴", "Medium": "🟠", "Low": "🟢"}.get(plan_result["risk_level"], "⚪")
    st.info(f"{risk_state} **{plan_result['headline']}**")

    if plan_result.get("goal_note"):
        st.caption(f"🎯 Goal: **{plan_result['goal']}** — {plan_result['goal_note']}")

    if plan_result.get("urgency_note"):
        st.warning(plan_result["urgency_note"])

    chip_row(
        [
            f"Risk Level: {plan_result['risk_level']}",
            f"Risk Probability: {plan_result['risk_probability'] * 100:.0f}%",
            "At Risk" if plan_result["at_risk"] else "Stable",
            f"{plan_result['days_covered']}-Day Plan",
            f"{plan_result['daily_minutes']} min/day",
        ]
    )

    section_title("Day-By-Day Schedule")
    action_accent = {"Study": "🟥", "Revise": "🟨", "Quick Review": "🟩"}
    for entry in plan_result["plan"]:
        with st.container(border=True):
            day_col, topic_col, score_col = st.columns([1, 2, 1])
            with day_col:
                st.markdown(f"**{entry['day']}**")
                st.caption(f"{action_accent.get(entry['action'], '⬜')} {entry['action']}")
            with topic_col:
                st.markdown(f"**{entry['topic']}**")
                st.caption(entry["reason"])
            with score_col:
                st.metric("Avg Score", f"{entry['avg_score']:.0f}%")


with st.container(border=True):
    section_title("Tell Us About Your Study Plan", "A few quick questions so we can tailor your schedule.")

    goal = st.selectbox("What is your goal?", GOAL_OPTIONS)

    q1, q2 = st.columns(2)
    with q1:
        plan_days = st.selectbox("How many days should this plan cover?", [3, 5, 7], index=1)
    with q2:
        daily_minutes_label = st.selectbox("How much time can you study per day?", list(DAILY_MINUTES_OPTIONS.keys()), index=1)

    q3, q4 = st.columns(2)
    with q3:
        has_exam = st.checkbox("I have an upcoming exam or deadline")
        exam_date = st.date_input("Exam/deadline date", value=date.today(), disabled=not has_exam) if has_exam else None
    with q4:
        priority_topic = st.text_input("A specific topic you're most worried about? (optional)")

    if st.button("Build My Plan", type="primary", use_container_width=True):
        try:
            st.session_state["my_study_plan"] = get_study_plan(
                auth_user["demo_student_id"],
                plan_days,
                DAILY_MINUTES_OPTIONS[daily_minutes_label],
                exam_date,
                priority_topic,
                goal,
            )
        except requests.RequestException as exc:
            st.error(f"Could not build your study plan: {_error_detail(exc)}")
            st.session_state["my_study_plan"] = None

if st.session_state.get("my_study_plan"):
    render_plan(st.session_state["my_study_plan"])
else:
    st.caption("Answer the questions above and click Build My Plan to generate your schedule.")
