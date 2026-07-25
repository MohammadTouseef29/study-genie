from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, timezone

import bcrypt
from sqlalchemy import text

from backend.db import get_engine

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _find_by_email(email: str) -> dict | None:
    email_lower = email.strip().lower()
    with get_engine().connect() as conn:
        row = conn.execute(
            text("SELECT * FROM users WHERE lower(email) = :email"),
            {"email": email_lower},
        ).mappings().first()
    return dict(row) if row else None


def _assign_demo_student_id(user_id: str) -> str:
    """Deterministically maps a real account to one of the existing simulated
    students, so risk/study-plan/analytics features work immediately without
    needing months of real tracked activity. Stable for the life of the account."""
    with get_engine().connect() as conn:
        student_ids = sorted(
            row[0]
            for row in conn.execute(text("SELECT DISTINCT student_id FROM student_activity"))
        )
    if not student_ids:
        return "S0001"
    index = int(hashlib.sha256(user_id.encode("utf-8")).hexdigest(), 16) % len(student_ids)
    return student_ids[index]


def _public_user(user: dict) -> dict:
    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "name": user["name"],
        "demo_student_id": user["demo_student_id"],
        "created_at": user["created_at"].isoformat() if hasattr(user["created_at"], "isoformat") else user["created_at"],
    }


def signup(email: str, password: str, name: str) -> dict:
    email = email.strip()
    name = name.strip()

    if not EMAIL_RE.match(email):
        raise ValueError("Enter a valid email address.")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")
    if not name:
        raise ValueError("Name is required.")

    if _find_by_email(email):
        raise ValueError("An account with this email already exists.")

    user_id = uuid.uuid4().hex
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    demo_student_id = _assign_demo_student_id(user_id)
    created_at = datetime.now(timezone.utc)

    with get_engine().begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO users (user_id, email, name, password_hash, demo_student_id, created_at)
                VALUES (:user_id, :email, :name, :password_hash, :demo_student_id, :created_at)
                """
            ),
            {
                "user_id": user_id,
                "email": email,
                "name": name,
                "password_hash": password_hash,
                "demo_student_id": demo_student_id,
                "created_at": created_at,
            },
        )

    return _public_user(
        {
            "user_id": user_id,
            "email": email,
            "name": name,
            "demo_student_id": demo_student_id,
            "created_at": created_at,
        }
    )


def login(email: str, password: str) -> dict:
    user = _find_by_email(email)
    if not user or not bcrypt.checkpw(password.encode("utf-8"), user["password_hash"].encode("utf-8")):
        raise ValueError("Incorrect email or password.")
    return _public_user(user)


def get_user(user_id: str) -> dict:
    with get_engine().connect() as conn:
        row = conn.execute(
            text("SELECT * FROM users WHERE user_id = :user_id"),
            {"user_id": user_id},
        ).mappings().first()
    if not row:
        raise FileNotFoundError(f"No account found: {user_id}")
    return _public_user(dict(row))


def get_profile(user_id: str) -> dict:
    user = get_user(user_id)
    student_id = user["demo_student_id"]

    with get_engine().connect() as conn:
        saved_materials_count = conn.execute(
            text("SELECT count(*) FROM study_materials WHERE student_id = :sid AND saved_at IS NOT NULL"),
            {"sid": student_id},
        ).scalar_one()

        saved_materials = [
            dict(row)
            for row in conn.execute(
                text(
                    """
                    SELECT material_id, saved_at, course_name,
                           jsonb_array_length(flashcards) AS flashcard_count,
                           jsonb_array_length(quiz) AS quiz_count
                    FROM study_materials
                    WHERE student_id = :sid AND saved_at IS NOT NULL
                    ORDER BY saved_at DESC
                    LIMIT 5
                    """
                ),
                {"sid": student_id},
            ).mappings()
        ]

        attempts_stats = conn.execute(
            text(
                "SELECT count(*) AS attempts, avg(percentage) AS avg_percentage "
                "FROM quiz_attempts WHERE student_id = :sid"
            ),
            {"sid": student_id},
        ).mappings().first()
        quiz_attempts_count = attempts_stats["attempts"] or 0
        avg_quiz_percentage = (
            round(float(attempts_stats["avg_percentage"]), 1) if attempts_stats["avg_percentage"] is not None else None
        )

        recent_attempts = [
            dict(row)
            for row in conn.execute(
                text(
                    """
                    SELECT material_id, attempted_at, score, total_questions, percentage
                    FROM quiz_attempts
                    WHERE student_id = :sid
                    ORDER BY attempted_at DESC
                    LIMIT 5
                    """
                ),
                {"sid": student_id},
            ).mappings()
        ]

        attendance_present_count = conn.execute(
            text(
                "SELECT count(*) FROM attendance_log WHERE student_id = :sid AND status = 'present'"
            ),
            {"sid": student_id},
        ).scalar_one()

        doubt_topics = [
            dict(row)
            for row in conn.execute(
                text(
                    """
                    SELECT topic, sum(question_count) AS total_questions
                    FROM doubt_interactions
                    WHERE student_id = :sid
                    GROUP BY topic
                    ORDER BY total_questions DESC
                    LIMIT 3
                    """
                ),
                {"sid": student_id},
            ).mappings()
        ]

    for entry in saved_materials:
        entry["saved_at"] = entry["saved_at"].isoformat() if entry["saved_at"] else None
    for entry in recent_attempts:
        entry["attempted_at"] = entry["attempted_at"].isoformat() if entry["attempted_at"] else None

    return {
        "user": user,
        "activity": {
            "saved_materials_count": saved_materials_count,
            "saved_materials": saved_materials,
            "quiz_attempts_count": quiz_attempts_count,
            "avg_quiz_percentage": avg_quiz_percentage,
            "recent_quiz_attempts": recent_attempts,
            "attendance_present_count": attendance_present_count,
            "top_doubt_topics": doubt_topics,
        },
    }
