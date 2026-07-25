from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from backend.db import get_engine

FEATURE_COLUMNS = [
    "attendance_rate",
    "engagement_avg",
    "engagement_std",
    "engagement_trend",
    "lectures_attended",
    "quiz_avg",
    "quiz_std",
    "quiz_attempts",
    "max_score",
    "min_score",
    "quiz_trend",
    "doubt_total",
    "avg_doubts",
    "unique_doubt_topics",
    "weak_topic_count",
    "assignment_count",
    "late_assignments",
    "missed_assignments",
    "late_submission_rate",
    "avg_delay_days",
    "max_delay_days",
    "assignment_delay_trend",
]


def _read_table(table_name: str, parse_dates: list[str] | None = None) -> pd.DataFrame:
    with get_engine().connect() as conn:
        return pd.read_sql(f"SELECT * FROM {table_name}", conn, parse_dates=parse_dates)


def build_risk_overview() -> dict:
    feature_df = _build_student_feature_frame()
    model_bundle = _train_models(feature_df)
    predictions = _build_predictions(
        feature_df=feature_df,
        model=model_bundle["best_model"],
        feature_columns=model_bundle["feature_columns"],
    )

    return {
        "summary": {
            "students": int(len(predictions)),
            "at_risk_students": int(predictions["at_risk"].sum()),
            "risk_percentage": round(predictions["at_risk"].mean() * 100, 1),
            "selected_model": model_bundle["selected_model"],
            "avg_assignment_delay_days": round(predictions["avg_delay_days"].mean(), 2),
            "late_submission_rate": round(predictions["late_submission_rate"].mean() * 100, 1),
        },
        "models": model_bundle["metrics"],
        "feature_importance": model_bundle["feature_importance"],
        "students": predictions.round(3).to_dict(orient="records"),
    }


def build_student_feature_frame() -> pd.DataFrame:
    return _build_student_feature_frame()


def _build_student_feature_frame() -> pd.DataFrame:
    activity_df = _read_table("student_activity", parse_dates=["date"])
    quiz_df = _read_table("quiz_performance", parse_dates=["date"])
    doubt_df = _read_table("doubt_interactions", parse_dates=["date"])
    assignment_df = _load_or_create_assignment_df(activity_df, quiz_df)

    activity_df = activity_df.sort_values(["student_id", "date"]).copy()
    quiz_df = quiz_df.sort_values(["student_id", "date"]).copy()
    assignment_df = assignment_df.sort_values(["student_id", "due_date"]).copy()

    activity_features = (
        activity_df.groupby("student_id")
        .agg(
            attendance_rate=("attendance", "mean"),
            engagement_avg=("engagement_score", "mean"),
            engagement_std=("engagement_score", "std"),
            lectures_attended=("attendance", "sum"),
        )
        .reset_index()
    )

    early_activity = activity_df.groupby("student_id").head(30).groupby("student_id")["engagement_score"].mean()
    late_activity = activity_df.groupby("student_id").tail(30).groupby("student_id")["engagement_score"].mean()
    activity_features["engagement_trend"] = (
        activity_features["student_id"].map(late_activity) - activity_features["student_id"].map(early_activity)
    ).fillna(0)

    quiz_features = (
        quiz_df.groupby("student_id")
        .agg(
            quiz_avg=("score", "mean"),
            quiz_std=("score", "std"),
            quiz_attempts=("score", "size"),
            max_score=("score", "max"),
            min_score=("score", "min"),
        )
        .reset_index()
    )

    early_quiz = quiz_df.groupby("student_id").head(5).groupby("student_id")["score"].mean()
    late_quiz = quiz_df.groupby("student_id").tail(5).groupby("student_id")["score"].mean()
    quiz_features["quiz_trend"] = (
        quiz_features["student_id"].map(late_quiz) - quiz_features["student_id"].map(early_quiz)
    ).fillna(0)

    topic_avg = quiz_df.groupby(["student_id", "topic"])["score"].mean().reset_index()
    weak_topic_map = (
        topic_avg.sort_values(["student_id", "score"], ascending=[True, True])
        .groupby("student_id")
        .head(2)
        .groupby("student_id")["topic"]
        .apply(list)
        .to_dict()
    )
    weak_topic_count = (
        topic_avg.assign(is_weak=topic_avg["score"] < 60)
        .groupby("student_id")["is_weak"]
        .sum()
        .to_dict()
    )

    doubt_features = (
        doubt_df.groupby("student_id")
        .agg(
            doubt_total=("question_count", "sum"),
            avg_doubts=("question_count", "mean"),
            unique_doubt_topics=("topic", "nunique"),
        )
        .reset_index()
    )

    assignment_features = _build_assignment_features(assignment_df)

    feature_df = activity_features.merge(quiz_features, on="student_id", how="inner")
    feature_df = feature_df.merge(doubt_features, on="student_id", how="left")
    feature_df = feature_df.merge(assignment_features, on="student_id", how="left")
    feature_df["doubt_total"] = feature_df["doubt_total"].fillna(0)
    feature_df["avg_doubts"] = feature_df["avg_doubts"].fillna(0)
    feature_df["unique_doubt_topics"] = feature_df["unique_doubt_topics"].fillna(0)
    feature_df["engagement_std"] = feature_df["engagement_std"].fillna(0)
    feature_df["quiz_std"] = feature_df["quiz_std"].fillna(0)
    feature_df["weak_topic_count"] = feature_df["student_id"].map(weak_topic_count).fillna(0)
    feature_df["weak_topics"] = feature_df["student_id"].map(weak_topic_map).apply(lambda x: x if isinstance(x, list) else [])

    assignment_defaults = {
        "assignment_count": 0,
        "submitted_assignments": 0,
        "late_assignments": 0,
        "missed_assignments": 0,
        "late_submission_rate": 0.0,
        "avg_delay_days": 0.0,
        "max_delay_days": 0.0,
        "assignment_delay_trend": 0.0,
    }
    for column, default_value in assignment_defaults.items():
        feature_df[column] = feature_df[column].fillna(default_value)

    feature_df["risk_score"] = _compute_risk_score(feature_df)
    threshold = feature_df["risk_score"].quantile(0.75)
    feature_df["at_risk"] = (feature_df["risk_score"] >= threshold).astype(int)
    feature_df["dropout_proxy"] = feature_df["at_risk"]

    return feature_df


def _load_or_create_assignment_df(activity_df: pd.DataFrame, quiz_df: pd.DataFrame) -> pd.DataFrame:
    engine = get_engine()
    with engine.connect() as conn:
        row_count = conn.exec_driver_sql("SELECT count(*) FROM assignment_submissions").scalar()

    if row_count:
        return _read_table("assignment_submissions", parse_dates=["due_date", "submitted_at"])

    assignment_df = _generate_assignment_submissions(activity_df, quiz_df)
    with engine.begin() as conn:
        assignment_df.to_sql("assignment_submissions", conn, if_exists="append", index=False)
    return assignment_df


def _generate_assignment_submissions(activity_df: pd.DataFrame, quiz_df: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    students = sorted(activity_df["student_id"].unique().tolist())
    topics = sorted(quiz_df["topic"].dropna().unique().tolist())
    base_dates = pd.date_range(activity_df["date"].min(), activity_df["date"].max(), periods=12)

    student_profile = (
        activity_df.groupby("student_id")
        .agg(
            attendance_rate=("attendance", "mean"),
            engagement_avg=("engagement_score", "mean"),
        )
        .reset_index()
        .merge(
            quiz_df.groupby("student_id").agg(quiz_avg=("score", "mean")).reset_index(),
            on="student_id",
            how="left",
        )
    )

    rows = []
    for assignment_index, due_date in enumerate(base_dates, start=1):
        topic = topics[(assignment_index - 1) % len(topics)]
        assignment_id = f"ASG_{assignment_index:02d}"

        for _, student in student_profile.iterrows():
            risk_pressure = (
                0.45 * (1 - student["attendance_rate"]) +
                0.30 * (1 - (student["engagement_avg"] / 100.0)) +
                0.25 * (1 - (student["quiz_avg"] / 100.0))
            )
            missed_probability = float(np.clip(0.03 + risk_pressure * 0.18, 0.03, 0.32))
            is_missed = rng.random() < missed_probability

            if is_missed:
                delay_days = int(rng.integers(7, 16))
                submitted_at = pd.NaT
                status = "missed"
            else:
                raw_delay = rng.normal(loc=risk_pressure * 6 - 0.6, scale=1.8)
                delay_days = int(np.clip(round(raw_delay), -1, 12))
                submitted_at = due_date + pd.Timedelta(days=max(delay_days, 0))
                status = "late" if delay_days > 0 else "on_time"

            rows.append(
                {
                    "student_id": student["student_id"],
                    "assignment_id": assignment_id,
                    "topic": topic,
                    "due_date": due_date,
                    "submitted_at": submitted_at,
                    "delay_days": max(delay_days, 0),
                    "status": status,
                    "is_late": int(status == "late"),
                    "is_missed": int(status == "missed"),
                    "was_submitted": int(status != "missed"),
                }
            )

    return pd.DataFrame(rows)


def _build_assignment_features(assignment_df: pd.DataFrame) -> pd.DataFrame:
    assignment_features = (
        assignment_df.groupby("student_id")
        .agg(
            assignment_count=("assignment_id", "size"),
            submitted_assignments=("was_submitted", "sum"),
            late_assignments=("is_late", "sum"),
            missed_assignments=("is_missed", "sum"),
            avg_delay_days=("delay_days", "mean"),
            max_delay_days=("delay_days", "max"),
        )
        .reset_index()
    )
    assignment_features["late_submission_rate"] = (
        assignment_features["late_assignments"] + assignment_features["missed_assignments"]
    ) / assignment_features["assignment_count"].clip(lower=1)

    early_assignment_delay = (
        assignment_df.groupby("student_id").head(4).groupby("student_id")["delay_days"].mean()
    )
    late_assignment_delay = (
        assignment_df.groupby("student_id").tail(4).groupby("student_id")["delay_days"].mean()
    )
    assignment_features["assignment_delay_trend"] = (
        assignment_features["student_id"].map(late_assignment_delay) -
        assignment_features["student_id"].map(early_assignment_delay)
    ).fillna(0)
    return assignment_features


def _compute_risk_score(feature_df: pd.DataFrame) -> pd.Series:
    attendance_component = 1 - feature_df["attendance_rate"]
    quiz_component = 1 - (feature_df["quiz_avg"] / 100.0)
    engagement_component = 1 - (feature_df["engagement_avg"] / 100.0)
    doubt_component = _min_max(feature_df["doubt_total"])
    trend_component = _min_max((-feature_df["quiz_trend"]).clip(lower=0))
    assignment_delay_component = _min_max(feature_df["avg_delay_days"])
    assignment_late_component = feature_df["late_submission_rate"].clip(0, 1)
    assignment_missed_component = _min_max(feature_df["missed_assignments"])

    return (
        0.23 * attendance_component +
        0.20 * quiz_component +
        0.15 * engagement_component +
        0.10 * doubt_component +
        0.08 * trend_component +
        0.12 * assignment_delay_component +
        0.07 * assignment_late_component +
        0.05 * assignment_missed_component
    )


def _min_max(series: pd.Series) -> pd.Series:
    span = series.max() - series.min()
    if span == 0:
        return pd.Series([0.0] * len(series), index=series.index)
    return (series - series.min()) / span


def _train_models(feature_df: pd.DataFrame) -> dict:
    X = feature_df[FEATURE_COLUMNS]
    y = feature_df["dropout_proxy"]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.25,
        random_state=42,
        stratify=y,
    )

    logistic_model = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("classifier", LogisticRegression(max_iter=1000, class_weight="balanced")),
        ]
    )
    forest_model = RandomForestClassifier(
        n_estimators=250,
        random_state=42,
        class_weight="balanced",
        min_samples_leaf=2,
    )

    models = {
        "Logistic Regression": logistic_model,
        "Random Forest": forest_model,
    }

    metrics = []
    fitted_models = {}
    for model_name, model in models.items():
        model.fit(X_train, y_train)
        probabilities = model.predict_proba(X_test)[:, 1]
        predictions = (probabilities >= 0.5).astype(int)
        metrics.append(
            {
                "model": model_name,
                "roc_auc": round(roc_auc_score(y_test, probabilities), 3),
                "precision": round(precision_score(y_test, predictions, zero_division=0), 3),
                "recall": round(recall_score(y_test, predictions, zero_division=0), 3),
                "f1": round(f1_score(y_test, predictions, zero_division=0), 3),
            }
        )
        fitted_models[model_name] = model

    metrics.sort(key=lambda item: (item["roc_auc"], item["f1"]), reverse=True)
    selected_model = metrics[0]["model"]
    best_model = fitted_models[selected_model]

    return {
        "feature_columns": FEATURE_COLUMNS,
        "metrics": metrics,
        "selected_model": selected_model,
        "best_model": best_model,
        "feature_importance": _extract_feature_importance(best_model, selected_model, FEATURE_COLUMNS),
    }


def _extract_feature_importance(model, model_name: str, feature_columns: list[str]) -> list[dict]:
    if model_name == "Random Forest":
        importances = model.feature_importances_
    else:
        importances = abs(model.named_steps["classifier"].coef_[0])

    importance_df = pd.DataFrame({"feature": feature_columns, "importance": importances})
    importance_df = importance_df.sort_values("importance", ascending=False)
    return importance_df.head(10).round(4).to_dict(orient="records")


def _build_predictions(feature_df: pd.DataFrame, model, feature_columns: list[str]) -> pd.DataFrame:
    probabilities = model.predict_proba(feature_df[feature_columns])[:, 1]
    predictions = feature_df.copy()
    predictions["risk_probability"] = probabilities
    predictions["at_risk"] = (predictions["risk_probability"] >= 0.5).astype(int)
    predictions["risk_level"] = predictions["risk_probability"].apply(_risk_level)
    predictions["weak_topics_label"] = predictions["weak_topics"].apply(lambda items: ", ".join(items) if items else "None")
    predictions["recommendation"] = predictions.apply(_recommendation, axis=1)

    return predictions[
        [
            "student_id",
            "attendance_rate",
            "engagement_avg",
            "quiz_avg",
            "quiz_trend",
            "doubt_total",
            "assignment_count",
            "late_assignments",
            "missed_assignments",
            "late_submission_rate",
            "avg_delay_days",
            "max_delay_days",
            "assignment_delay_trend",
            "risk_score",
            "risk_probability",
            "risk_level",
            "at_risk",
            "weak_topics_label",
            "recommendation",
        ]
    ].sort_values(["at_risk", "risk_probability"], ascending=[False, False])


def _risk_level(probability: float) -> str:
    if probability >= 0.7:
        return "High"
    if probability >= 0.45:
        return "Medium"
    return "Low"


def _recommendation(row: pd.Series) -> str:
    suggestions = []
    if row["attendance_rate"] < 0.75:
        suggestions.append("Improve class attendance consistency.")
    if row["engagement_avg"] < 55:
        suggestions.append("Increase classroom participation and engagement.")
    if row["quiz_avg"] < 60:
        suggestions.append("Focus on revising low-scoring quiz concepts.")
    if row["quiz_trend"] < 0:
        suggestions.append("Recent quiz trend is declining; schedule targeted revision.")
    if row["late_submission_rate"] >= 0.35:
        suggestions.append("Assignment submissions are frequently delayed; adopt a weekly deadline planner.")
    if row["missed_assignments"] >= 2:
        suggestions.append("Multiple missed assignments detected; prioritize pending coursework recovery.")
    if row["weak_topics_label"] != "None":
        suggestions.append(f"Prioritize weak topics: {row['weak_topics_label']}.")
    if not suggestions:
        suggestions.append("Maintain current performance and continue steady revision.")
    return " ".join(suggestions)
