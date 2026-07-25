from __future__ import annotations

import pandas as pd

from backend.db import get_engine


def get_doubt_frequency_data(student_id: str | None = None) -> dict:
    with get_engine().connect() as conn:
        doubt_df = pd.read_sql("SELECT * FROM doubt_interactions", conn, parse_dates=["date"])

    topic_totals = (
        doubt_df.groupby("topic")
        .agg(
            total_questions=("question_count", "sum"),
            unique_students=("student_id", "nunique"),
            interactions=("question_count", "size"),
        )
        .reset_index()
    )
    topic_totals["avg_questions_per_interaction"] = (
        topic_totals["total_questions"] / topic_totals["interactions"]
    ).round(2)

    median_line = doubt_df.sort_values("date")["date"].median()
    early = doubt_df[doubt_df["date"] < median_line].groupby("topic")["question_count"].sum()
    late = doubt_df[doubt_df["date"] >= median_line].groupby("topic")["question_count"].sum()
    topic_totals["trend"] = topic_totals["topic"].map(
        lambda topic: "rising" if late.get(topic, 0) > early.get(topic, 0) else "falling"
    )

    high_doubt_threshold = topic_totals["total_questions"].quantile(0.75)
    topic_totals["high_doubt"] = topic_totals["total_questions"] >= high_doubt_threshold

    topic_summary = (
        topic_totals.sort_values("total_questions", ascending=False)
        .round(2)
        .to_dict(orient="records")
    )
    high_doubt_topics = [row["topic"] for row in topic_summary if row["high_doubt"]]

    student_breakdown: list[dict] = []
    if student_id:
        student_df = doubt_df[doubt_df["student_id"] == student_id]
        student_breakdown = (
            student_df.groupby("topic")["question_count"]
            .sum()
            .reset_index()
            .rename(columns={"question_count": "total_questions"})
            .sort_values("total_questions", ascending=False)
            .to_dict(orient="records")
        )

    return {
        "topic_summary": topic_summary,
        "high_doubt_topics": high_doubt_topics,
        "student_id": student_id,
        "student_breakdown": student_breakdown,
        "student_ids": sorted(doubt_df["student_id"].unique().tolist()),
    }
