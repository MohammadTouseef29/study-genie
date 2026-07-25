from __future__ import annotations

from datetime import date, datetime, timezone

import pandas as pd

from backend.db import get_engine
from backend.ml.risk_service import build_risk_overview


GOAL_OPTIONS = [
    "Pass an upcoming exam",
    "Master my weak topics",
    "Quick revision before a test",
    "Build long-term understanding",
]

# (study_threshold, revise_threshold) per goal: below study_threshold -> "Study",
# below revise_threshold -> "Revise", otherwise -> "Quick Review".
GOAL_ACTION_THRESHOLDS = {
    "Pass an upcoming exam": (55, 75),
    "Master my weak topics": (55, 75),
    "Quick revision before a test": (35, 55),
    "Build long-term understanding": (65, 85),
}

GOAL_FRAMING = {
    "Pass an upcoming exam": "Prioritizing your weakest topics so you're ready in time.",
    "Master my weak topics": "Focused on the topics dragging your average down the most.",
    "Quick revision before a test": "Kept light — quick refreshers rather than deep study sessions.",
    "Build long-term understanding": "Going deep, even on topics you're already doing okay in.",
}


def _day_label(index: int) -> str:
    if index == 0:
        return "Today"
    if index == 1:
        return "Tomorrow"
    return f"In {index} days"


def _action_for_score(avg_score: float, goal: str) -> str:
    study_threshold, revise_threshold = GOAL_ACTION_THRESHOLDS.get(goal, GOAL_ACTION_THRESHOLDS["Master my weak topics"])
    if avg_score < study_threshold:
        return "Study"
    if avg_score < revise_threshold:
        return "Revise"
    return "Quick Review"


def _time_hint(daily_minutes: int, action: str) -> str:
    if action == "Study":
        return f"Spend the full {daily_minutes} minutes on core concepts and practice problems."
    if action == "Revise":
        return f"About {max(daily_minutes // 2, 15)} minutes of focused revision should reinforce this."
    return f"A quick {min(daily_minutes, 20)}-minute review will keep this fresh."


def _phrase(entry: dict) -> str:
    verb_phrase = {
        "Study": f"Focus on {entry['topic']}",
        "Revise": f"Revise {entry['topic']}",
        "Quick Review": f"Do a quick review of {entry['topic']}",
    }[entry["action"]]
    return f"{verb_phrase} {entry['day'].lower()}"


def build_study_plan(
    student_id: str,
    days: int = 5,
    daily_minutes: int = 60,
    exam_date: date | None = None,
    priority_topic: str | None = None,
    goal: str = "Master my weak topics",
) -> dict:
    student_id = student_id.strip()
    if not student_id:
        raise ValueError("Student ID is required.")
    days = max(1, min(days, 14))
    daily_minutes = max(10, min(daily_minutes, 240))
    if goal not in GOAL_ACTION_THRESHOLDS:
        goal = "Master my weak topics"

    risk_overview = build_risk_overview()
    student_row = next(
        (row for row in risk_overview["students"] if row["student_id"] == student_id),
        None,
    )
    if student_row is None:
        raise ValueError(f"No analytics data found for student: {student_id}")

    with get_engine().connect() as conn:
        quiz_df = pd.read_sql("SELECT * FROM quiz_performance", conn)
    student_quiz = quiz_df[quiz_df["student_id"] == student_id]
    if student_quiz.empty:
        raise ValueError(f"No quiz history found for student: {student_id}")

    topic_scores = student_quiz.groupby("topic")["score"].mean().sort_values()

    if priority_topic and priority_topic.strip():
        needle = priority_topic.strip().lower()
        matches = [topic for topic in topic_scores.index if needle in topic.lower()]
        if matches:
            chosen = matches[0]
            reordered = [chosen] + [topic for topic in topic_scores.index if topic != chosen]
            topic_scores = topic_scores.reindex(reordered)

    topics_to_plan = topic_scores.head(days)

    entries = []
    for index, (topic, avg_score) in enumerate(topics_to_plan.items()):
        action = _action_for_score(avg_score, goal)
        entries.append(
            {
                "day": _day_label(index),
                "topic": topic,
                "action": action,
                "avg_score": round(float(avg_score), 1),
                "reason": f"Average quiz score {avg_score:.0f}%. {_time_hint(daily_minutes, action)}",
            }
        )

    if len(entries) >= 2:
        headline = f"{_phrase(entries[0])}. {_phrase(entries[1])}."
    elif entries:
        headline = f"{_phrase(entries[0])}."
    else:
        headline = "No weak topics detected yet — keep up the steady revision."

    urgency_note = None
    if exam_date:
        days_until_exam = (exam_date - date.today()).days
        if days_until_exam >= 0:
            urgency_note = (
                f"Your exam/deadline is in {days_until_exam} day(s) — "
                f"this plan is paced to be ready in time."
                if days_until_exam >= days
                else (
                    f"Your exam/deadline is in only {days_until_exam} day(s), sooner than this "
                    f"{days}-day plan — consider increasing your daily study time."
                )
            )

    return {
        "student_id": student_id,
        "risk_level": student_row["risk_level"],
        "risk_probability": student_row["risk_probability"],
        "at_risk": bool(student_row["at_risk"]),
        "headline": headline,
        "plan": entries,
        "days_covered": days,
        "daily_minutes": daily_minutes,
        "priority_topic": priority_topic or None,
        "goal": goal,
        "goal_note": GOAL_FRAMING[goal],
        "urgency_note": urgency_note,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
