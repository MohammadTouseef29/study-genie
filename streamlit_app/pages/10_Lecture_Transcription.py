import os

import requests
import streamlit as st
from ui import apply_theme, chip_row, hero, section_title

API_BASE_URL = os.getenv("STUDY_GENIE_API_URL", "http://localhost:8000")
LANGUAGE_OPTIONS = {
    "Auto Detect": "",
    "English": "en",
    "Hindi": "hi",
    "Spanish": "es",
    "French": "fr",
    "German": "de",
}

apply_theme("Lecture Transcription Studio")
hero(
    "Lecture Transcription Studio",
    "Convert lecture audio or video into a usable study pack with transcript text, summary notes, key points, and topic tags.",
    eyebrow="Audio Intelligence",
    chips=["Whisper Transcription", "Summary", "Key Points", "Topic Tags"],
)


def process_audio(uploaded_file, model_size: str, language: str) -> dict:
    files = {
        "file": (
            uploaded_file.name,
            uploaded_file.getvalue(),
            uploaded_file.type or "application/octet-stream",
        )
    }
    data = {
        "model_size": model_size,
        "language": language,
    }

    response = requests.post(
        f"{API_BASE_URL}/transcription/process",
        files=files,
        data=data,
        timeout=600,
    )
    response.raise_for_status()
    return response.json()


with st.container(border=True):
    section_title("Lecture Input", "Upload lecture audio or video and choose the transcription settings before generating study notes.")
    uploaded_audio = st.file_uploader(
        "Upload lecture audio or video",
        type=["mp3", "wav", "ogg", "m4a", "mp4", "mov", "mkv"],
    )
    model_size = st.selectbox(
        "Whisper model size",
        ["tiny", "base", "small", "medium"],
        index=1,
    )
    language_label = st.selectbox(
        "Lecture language",
        list(LANGUAGE_OPTIONS.keys()),
        index=0,
    )

    run_disabled = uploaded_audio is None
    if st.button("Generate Lecture Notes", use_container_width=True, disabled=run_disabled, type="primary"):
        with st.spinner("Transcribing lecture and generating study materials..."):
            try:
                st.session_state["transcription_result"] = process_audio(
                    uploaded_audio,
                    model_size=model_size,
                    language=LANGUAGE_OPTIONS[language_label],
                )
            except requests.RequestException:
                st.error(
                    "Could not reach the backend API. Start FastAPI with "
                    "`uvicorn backend.api:app --reload` and try again."
                )
                st.stop()

result = st.session_state.get("transcription_result")

if result:
    meta1, meta2 = st.columns(2)
    meta1.metric("File", result["filename"])
    meta2.metric("Detected Language", result.get("detected_language", "unknown"))
    chip_row(result["topic_tags"])

    section_title("Lecture Summary")
    st.info(result["summary"])

    points_col, tags_col = st.columns([2, 1])

    with points_col:
        section_title("Key Points")
        for point in result["key_points"]:
            st.markdown(f"- {point}")

    with tags_col:
        section_title("Topic Tags")
        for tag in result["topic_tags"]:
            st.markdown(f"`{tag}`")

    section_title("Bullet Notes")
    for note in result["bullet_notes"]:
        st.markdown(f"- {note}")

    section_title("Full Transcript")
    st.text_area(
        "Transcript",
        value=result["transcript"],
        height=320,
        label_visibility="collapsed",
    )
