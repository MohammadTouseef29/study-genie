from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone

from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from sqlalchemy import text

from backend.db import get_engine
from backend.rag.loader import load_pdf
from backend.rag.vector_store import chunk_documents


def _get_llm() -> ChatGroq:
    return ChatGroq(
        model="llama-3.1-8b-instant",
        groq_api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.2,
    )


def _build_context_from_pdfs(pdf_paths: list[str]) -> str:
    all_documents = []
    for path in pdf_paths:
        all_documents.extend(load_pdf(path))

    chunks = chunk_documents(all_documents)
    selected_chunks = chunks[:10]
    return "\n\n".join(chunk.page_content for chunk in selected_chunks)


def _fallback_topic_tags(source_text: str) -> list[str]:
    words = []
    for raw_word in source_text.replace("\n", " ").split():
        word = raw_word.strip(".,!?():;\"'").lower()
        if len(word) < 5 or not word.isalpha():
            continue
        if word not in words:
            words.append(word)
        if len(words) == 5:
            break
    return [word.title() for word in words] or ["General"]


def _fallback_flashcards(source_text: str) -> list[dict]:
    sentences = [
        sentence.strip()
        for sentence in source_text.replace("\n", " ").split(".")
        if sentence.strip()
    ]
    cards = []
    for index, sentence in enumerate(sentences[:5], start=1):
        cards.append(
            {
                "question": f"What is a key point from concept {index}?",
                "answer": sentence,
                "topic": "General",
            }
        )
    return cards or [
        {
            "question": "What was processed?",
            "answer": "Study material content was processed successfully.",
            "topic": "General",
        }
    ]


def _fallback_quiz(topic_tags: list[str]) -> list[dict]:
    topic = topic_tags[0] if topic_tags else "General"
    return [
        {
            "question": f"Which option best relates to {topic}?",
            "options": [topic, "Unrelated concept", "Random guess", "None of the above"],
            "answer": topic,
            "explanation": f"{topic} is the closest match to the generated topic mapping.",
            "topic": topic,
            "difficulty": "Medium",
        }
    ]


def _safe_json_load(text: str) -> dict | None:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


def _get_difficulty_bias(student_id: str | None) -> tuple[str, str]:
    """Looks at a student's recent quiz_attempts history and returns
    (bias, reason) where bias is 'easy' | 'balanced' | 'hard'."""
    if not student_id:
        return "balanced", "No prior quiz history available; using a balanced difficulty mix."

    with get_engine().connect() as conn:
        percentages = [
            row[0]
            for row in conn.execute(
                text(
                    """
                    SELECT percentage FROM quiz_attempts
                    WHERE student_id = :sid
                    ORDER BY attempted_at DESC
                    LIMIT 5
                    """
                ),
                {"sid": student_id},
            )
        ]

    if not percentages:
        return "balanced", "No prior quiz history available; using a balanced difficulty mix."

    avg_percentage = sum(percentages) / len(percentages)

    if avg_percentage >= 80:
        return "hard", f"Recent quiz average is {avg_percentage:.0f}%, so questions are skewed harder."
    if avg_percentage < 50:
        return "easy", f"Recent quiz average is {avg_percentage:.0f}%, so questions are skewed easier."
    return "balanced", f"Recent quiz average is {avg_percentage:.0f}%, so a balanced difficulty mix is used."


_DIFFICULTY_INSTRUCTIONS = {
    "easy": "The student has been struggling recently (low recent quiz scores). Make most MCQs Easy, a few Medium, and none Hard, so they can rebuild confidence.",
    "balanced": "Use a balanced mix of difficulty across the MCQs: roughly a third Easy, a third Medium, a third Hard.",
    "hard": "The student has been performing very well recently (high recent quiz scores). Make most MCQs Hard, a few Medium, and none Easy, to keep them challenged.",
}


def generate_study_materials(
    source_text: str,
    source_type: str,
    source_name: str,
    student_id: str | None = None,
) -> dict:
    difficulty_bias, difficulty_reason = _get_difficulty_bias(student_id)

    prompt = PromptTemplate.from_template(
        """
You are an academic study assistant.

Using the study material below, return valid JSON with this exact schema:
{{
  "topic_tags": ["Topic 1", "Topic 2", "Topic 3"],
  "flashcards": [
    {{"question": "question", "answer": "answer", "topic": "topic"}}
  ],
  "quiz": [
    {{
      "question": "mcq question",
      "options": ["A", "B", "C", "D"],
      "answer": "correct option text",
      "explanation": "short explanation",
      "topic": "topic",
      "difficulty": "Easy | Medium | Hard"
    }}
  ]
}}

Rules:
- Generate 5-8 flashcards.
- Generate 5-8 MCQs.
- Keep options distinct and plausible.
- Add one difficulty tag per MCQ: Easy, Medium, or Hard.
- Adaptive difficulty instruction: {difficulty_instruction}
- Keep answers strictly grounded in the source.
- Return JSON only.

Source type: {source_type}
Source name: {source_name}
Study material:
{source_text}
"""
    )

    chain = prompt | _get_llm()
    response = chain.invoke(
        {
            "source_type": source_type,
            "source_name": source_name,
            "source_text": source_text[:12000],
            "difficulty_instruction": _DIFFICULTY_INSTRUCTIONS[difficulty_bias],
        }
    )
    payload = _safe_json_load(response.content)

    if not payload:
        topic_tags = _fallback_topic_tags(source_text)
        flashcards = _fallback_flashcards(source_text)
        quiz = _fallback_quiz(topic_tags)
    else:
        topic_tags = [
            str(item).strip()
            for item in payload.get("topic_tags", [])
            if str(item).strip()
        ] or _fallback_topic_tags(source_text)
        flashcards = [
            {
                "question": str(item.get("question", "")).strip(),
                "answer": str(item.get("answer", "")).strip(),
                "topic": str(item.get("topic", topic_tags[0])).strip() or topic_tags[0],
            }
            for item in payload.get("flashcards", [])
            if str(item.get("question", "")).strip() and str(item.get("answer", "")).strip()
        ] or _fallback_flashcards(source_text)
        quiz = [
            {
                "question": str(item.get("question", "")).strip(),
                "options": [str(option).strip() for option in item.get("options", []) if str(option).strip()],
                "answer": str(item.get("answer", "")).strip(),
                "explanation": str(item.get("explanation", "")).strip(),
                "topic": str(item.get("topic", topic_tags[0])).strip() or topic_tags[0],
                "difficulty": str(item.get("difficulty", "Medium")).strip().title() or "Medium",
            }
            for item in payload.get("quiz", [])
            if str(item.get("question", "")).strip() and str(item.get("answer", "")).strip()
        ] or _fallback_quiz(topic_tags)

    material_id = uuid.uuid4().hex[:12]
    generated_at = datetime.now(timezone.utc)
    _store_topic_mapping(
        material_id=material_id,
        generated_at=generated_at,
        source_type=source_type,
        source_name=source_name,
        topic_tags=topic_tags,
        flashcards=flashcards,
        quiz=quiz,
    )

    return {
        "material_id": material_id,
        "generated_at": generated_at.isoformat(),
        "source_type": source_type,
        "source_name": source_name,
        "topic_tags": topic_tags[:6],
        "flashcards": flashcards[:8],
        "quiz": quiz[:8],
        "difficulty_bias": difficulty_bias,
        "difficulty_reason": difficulty_reason,
    }


def save_generated_material(
    material: dict,
    student_id: str,
    course_id: str,
    course_name: str,
) -> dict:
    student_id = student_id.strip() or "unknown_student"
    course_id = course_id.strip() or "unknown_course"
    course_name = course_name.strip() or "Unknown Course"

    saved_at = datetime.now(timezone.utc)
    stored_material = {
        **material,
        "student_id": student_id,
        "course_id": course_id,
        "course_name": course_name,
        "saved_at": saved_at.isoformat(),
    }

    with get_engine().begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO study_materials
                    (material_id, generated_at, source_type, source_name, topic_tags,
                     flashcards, quiz, difficulty_bias, difficulty_reason,
                     student_id, course_id, course_name, saved_at)
                VALUES
                    (:material_id, :generated_at, :source_type, :source_name, CAST(:topic_tags AS jsonb),
                     CAST(:flashcards AS jsonb), CAST(:quiz AS jsonb), :difficulty_bias, :difficulty_reason,
                     :student_id, :course_id, :course_name, :saved_at)
                ON CONFLICT (material_id) DO UPDATE SET
                    student_id = EXCLUDED.student_id,
                    course_id = EXCLUDED.course_id,
                    course_name = EXCLUDED.course_name,
                    saved_at = EXCLUDED.saved_at
                """
            ),
            {
                "material_id": material["material_id"],
                "generated_at": material["generated_at"],
                "source_type": material["source_type"],
                "source_name": material["source_name"],
                "topic_tags": json.dumps(material["topic_tags"]),
                "flashcards": json.dumps(material["flashcards"]),
                "quiz": json.dumps(material["quiz"]),
                "difficulty_bias": material.get("difficulty_bias"),
                "difficulty_reason": material.get("difficulty_reason"),
                "student_id": student_id,
                "course_id": course_id,
                "course_name": course_name,
                "saved_at": saved_at,
            },
        )

    return stored_material


def load_saved_material(material_id: str) -> dict:
    with get_engine().connect() as conn:
        row = conn.execute(
            text("SELECT * FROM study_materials WHERE material_id = :mid"),
            {"mid": material_id},
        ).mappings().first()

    if not row:
        raise FileNotFoundError(f"Saved study material not found: {material_id}")

    material = dict(row)
    material["generated_at"] = material["generated_at"].isoformat() if material["generated_at"] else None
    material["saved_at"] = material["saved_at"].isoformat() if material["saved_at"] else None
    return material


def list_saved_materials() -> list[dict]:
    with get_engine().connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT material_id, saved_at, student_id, course_id, course_name,
                       source_type, source_name, topic_tags,
                       jsonb_array_length(flashcards) AS flashcard_count,
                       jsonb_array_length(quiz) AS quiz_count,
                       quiz
                FROM study_materials
                WHERE saved_at IS NOT NULL
                ORDER BY saved_at DESC
                """
            )
        ).mappings()

        materials = []
        for row in rows:
            entry = dict(row)
            quiz_items = entry.pop("quiz") or []
            entry["saved_at"] = entry["saved_at"].isoformat() if entry["saved_at"] else None
            entry["difficulty_mix"] = ", ".join(item.get("difficulty", "Medium") for item in quiz_items)
            materials.append(entry)
        return materials


def evaluate_quiz(
    material_id: str,
    answers: list[str],
    student_id: str,
    course_id: str,
) -> dict:
    material = load_saved_material(material_id)
    quiz_items = material.get("quiz", [])
    if len(answers) != len(quiz_items):
        raise ValueError("Answer count does not match quiz length.")

    results = []
    score = 0
    for index, (answer, item) in enumerate(zip(answers, quiz_items), start=1):
        correct_answer = item["answer"].strip()
        selected_answer = (answer or "").strip()
        is_correct = selected_answer == correct_answer
        if is_correct:
            score += 1
        results.append(
            {
                "question_number": index,
                "question": item["question"],
                "topic": item["topic"],
                "selected_answer": selected_answer,
                "correct_answer": correct_answer,
                "is_correct": is_correct,
                "explanation": item.get("explanation", ""),
                "difficulty": item.get("difficulty", "Medium"),
            }
        )

    percentage = round((score / len(quiz_items)) * 100, 1) if quiz_items else 0.0
    attempted_at = datetime.now(timezone.utc)
    final_student_id = student_id.strip() or material.get("student_id", "unknown_student")
    final_course_id = course_id.strip() or material.get("course_id", "unknown_course")

    _store_quiz_attempt(
        material_id=material_id,
        attempted_at=attempted_at,
        student_id=final_student_id,
        course_id=final_course_id,
        score=score,
        total_questions=len(quiz_items),
        percentage=percentage,
    )

    return {
        "material_id": material_id,
        "student_id": final_student_id,
        "course_id": final_course_id,
        "attempted_at": attempted_at.isoformat(),
        "score": score,
        "total_questions": len(quiz_items),
        "percentage": percentage,
        "results": results,
    }


def generate_from_transcript(
    transcript: str,
    source_name: str = "Transcript Input",
    student_id: str | None = None,
) -> dict:
    return generate_study_materials(
        source_text=transcript,
        source_type="transcript",
        source_name=source_name,
        student_id=student_id,
    )


def generate_from_pdfs(
    pdf_paths: list[str],
    source_name: str = "Uploaded PDFs",
    student_id: str | None = None,
) -> dict:
    context = _build_context_from_pdfs(pdf_paths)
    return generate_study_materials(
        source_text=context,
        source_type="pdf",
        source_name=source_name,
        student_id=student_id,
    )


def _store_topic_mapping(
    material_id: str,
    generated_at: datetime,
    source_type: str,
    source_name: str,
    topic_tags: list[str],
    flashcards: list[dict],
    quiz: list[dict],
) -> None:
    rows = []
    for topic in topic_tags:
        flashcard_count = sum(1 for item in flashcards if item.get("topic") == topic)
        quiz_count = sum(1 for item in quiz if item.get("topic") == topic)
        rows.append(
            {
                "material_id": material_id,
                "generated_at": generated_at,
                "source_type": source_type,
                "source_name": source_name,
                "topic": topic,
                "flashcard_count": flashcard_count,
                "quiz_count": quiz_count,
            }
        )

    if not rows:
        return

    with get_engine().begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO study_material_topic_mapping
                    (material_id, generated_at, source_type, source_name, topic, flashcard_count, quiz_count)
                VALUES
                    (:material_id, :generated_at, :source_type, :source_name, :topic, :flashcard_count, :quiz_count)
                """
            ),
            rows,
        )


def _store_quiz_attempt(
    material_id: str,
    attempted_at: datetime,
    student_id: str,
    course_id: str,
    score: int,
    total_questions: int,
    percentage: float,
) -> None:
    with get_engine().begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO quiz_attempts
                    (material_id, attempted_at, student_id, course_id, score, total_questions, percentage)
                VALUES
                    (:material_id, :attempted_at, :student_id, :course_id, :score, :total_questions, :percentage)
                """
            ),
            {
                "material_id": material_id,
                "attempted_at": attempted_at,
                "student_id": student_id,
                "course_id": course_id,
                "score": score,
                "total_questions": total_questions,
                "percentage": percentage,
            },
        )
