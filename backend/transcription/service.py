from __future__ import annotations

import json
import os
from pathlib import Path

from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq

from backend.transcription.transcribe import transcribe_audio


def _get_llm() -> ChatGroq:
    return ChatGroq(
        model="llama-3.1-8b-instant",
        groq_api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.2,
    )


def _fallback_topic_tags(transcript: str) -> list[str]:
    words = []
    for raw_word in transcript.replace("\n", " ").split():
        word = raw_word.strip(".,!?():;\"'").lower()
        if len(word) < 5 or not word.isalpha():
            continue
        if word not in words:
            words.append(word)
        if len(words) == 5:
            break
    return [word.title() for word in words] or ["Lecture"]


def _fallback_notes(transcript: str) -> list[str]:
    sentences = [
        sentence.strip()
        for sentence in transcript.replace("\n", " ").split(".")
        if sentence.strip()
    ]
    return sentences[:5] or ["Transcript captured successfully."]


def _fallback_key_points(transcript: str) -> list[str]:
    sentences = [
        sentence.strip()
        for sentence in transcript.replace("\n", " ").split(".")
        if sentence.strip()
    ]
    return sentences[:3] or ["Lecture content was extracted successfully."]


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


def generate_lecture_artifacts(transcript: str) -> dict:
    prompt = PromptTemplate.from_template(
        """
You are an academic assistant helping students revise a lecture.

Analyze the transcript below and return valid JSON with this exact schema:
{{
  "summary": "2-4 sentence summary",
  "key_points": ["point 1", "point 2", "point 3"],
  "bullet_notes": ["note 1", "note 2", "note 3"],
  "topic_tags": ["tag1", "tag2", "tag3"]
}}

Rules:
- Keep key_points crisp and high-signal.
- Keep bullet_notes concise and useful for revision.
- Keep topic_tags short, title-cased, and limited to 3-6 tags.
- Return JSON only, with double quotes.

Transcript:
{transcript}
"""
    )

    chain = prompt | _get_llm()
    response = chain.invoke({"transcript": transcript[:12000]})

    payload = _safe_json_load(response.content)
    if not payload:
        payload = {
            "summary": "Lecture transcript processed successfully.",
            "key_points": _fallback_key_points(transcript),
            "bullet_notes": _fallback_notes(transcript),
            "topic_tags": _fallback_topic_tags(transcript),
        }

    summary = str(payload.get("summary", "")).strip() or "Lecture transcript processed successfully."
    key_points = [
        str(item).strip()
        for item in payload.get("key_points", [])
        if str(item).strip()
    ] or _fallback_key_points(transcript)
    bullet_notes = [
        str(item).strip()
        for item in payload.get("bullet_notes", [])
        if str(item).strip()
    ] or _fallback_notes(transcript)
    topic_tags = [
        str(item).strip()
        for item in payload.get("topic_tags", [])
        if str(item).strip()
    ] or _fallback_topic_tags(transcript)

    return {
        "summary": summary,
        "key_points": key_points[:5],
        "bullet_notes": bullet_notes[:8],
        "topic_tags": topic_tags[:6],
    }


def process_lecture_audio(
    audio_path: str | Path,
    model_size: str = "base",
    language: str | None = None,
) -> dict:
    transcript_result = transcribe_audio(
        str(audio_path),
        model_size=model_size,
        language=language,
    )
    transcript = transcript_result["transcript"]
    artifacts = generate_lecture_artifacts(transcript)

    return {
        "transcript": transcript,
        "detected_language": transcript_result["language"],
        "summary": artifacts["summary"],
        "key_points": artifacts["key_points"],
        "bullet_notes": artifacts["bullet_notes"],
        "topic_tags": artifacts["topic_tags"],
    }
