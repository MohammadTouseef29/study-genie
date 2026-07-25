import os

import requests
import streamlit as st
from ui import apply_theme, chat_bubble, chip_row, hero, info_card, section_title

apply_theme("AI Doubt Solver")

API_BASE_URL = os.getenv("STUDY_GENIE_API_URL", "http://localhost:8000")


def build_knowledge_base(uploaded_files):
    files = [
        (
            "files",
            (
                uploaded_file.name,
                uploaded_file.getvalue(),
                "application/pdf",
            ),
        )
        for uploaded_file in uploaded_files
    ]

    response = requests.post(
        f"{API_BASE_URL}/rag/ingest",
        files=files,
        timeout=180,
    )
    response.raise_for_status()
    return response.json()


def ask_question(question, chat_history):
    response = requests.post(
        f"{API_BASE_URL}/rag/query",
        json={
            "question": question,
            "chat_history": chat_history,
            "top_k": 7,
        },
        timeout=180,
    )
    response.raise_for_status()
    return response.json()


if "kb_ready_api" not in st.session_state:
    try:
        health = requests.get(f"{API_BASE_URL}/health", timeout=10).json()
        st.session_state.kb_ready_api = bool(health.get("knowledge_base_ready"))
    except requests.RequestException:
        st.session_state.kb_ready_api = False

if "chat_history_api" not in st.session_state:
    st.session_state.chat_history_api = []

hero(
    "AI Doubt Solver",
    "Upload course PDFs, build a shared knowledge base, and ask grounded questions with source citations.",
    eyebrow="RAG Assistant",
    chips=["Multi-PDF Upload", "Source Citations", "Chat History", "API Backed"],
)

left_col, right_col = st.columns([1, 2])

with left_col:
    section_title("Knowledge Base", "Load lecture handouts, slides, or notes before starting the conversation.")

    with st.container(border=True):
        uploaded_files = st.file_uploader(
            "Upload one or more PDFs",
            type=["pdf"],
            accept_multiple_files=True,
            key="api_pdf_uploader",
        )

        if uploaded_files:
            st.write("Uploaded files:")
            for file in uploaded_files:
                st.write(f"- {file.name}")

            if st.button("Build Knowledge Base", use_container_width=True, key="build_api_kb", type="primary"):
                with st.spinner("Processing PDFs and building knowledge base..."):
                    try:
                        build_knowledge_base(uploaded_files)
                    except requests.RequestException:
                        st.error(
                            "Could not reach the backend API. Start FastAPI with "
                            "`uvicorn backend.api:app --reload` and try again."
                        )
                        st.stop()

                st.session_state.kb_ready_api = True
                st.session_state.chat_history_api = []
                st.success("Knowledge base created from multiple PDFs!")

    if st.session_state.kb_ready_api:
        chip_row(["Knowledge Base Ready", "Cross-Document Retrieval Active"])
    else:
        info_card("Workflow", "Upload one or more PDFs, build the knowledge base, then use the chat panel for questions.")

with right_col:
    section_title("Conversation", "Ask concept questions, compare definitions, or request explanations grounded in the uploaded material.")

    chat_container = st.container(border=True, height=420)

    with chat_container:
        for msg in st.session_state.chat_history_api:
            chat_bubble(msg["role"], msg["content"], msg.get("sources"))
            if msg["role"] == "assistant" and msg.get("sources"):
                with st.expander("View source chunks"):
                    for index, source in enumerate(msg["sources"], start=1):
                        st.markdown(
                            f"**Source {index}**  \n"
                            f"`{source['pdf_name']}` • Page {source['page']}"
                        )
                        st.caption(source["snippet"])

    question = st.text_input(
        "Ask a question",
        placeholder="Ask something across all uploaded PDFs",
        disabled=not st.session_state.kb_ready_api,
        key="api_question_input",
    )

    if st.button("Send", use_container_width=True, disabled=not st.session_state.kb_ready_api, key="send_api_question", type="primary"):
        if not question.strip():
            st.warning("Please enter a valid question.")
        else:
            st.session_state.chat_history_api.append(
                {"role": "user", "content": question}
            )

            with st.spinner("Thinking..."):
                try:
                    payload = ask_question(question, st.session_state.chat_history_api)
                except requests.RequestException:
                    st.error(
                        "Could not reach the backend API. Start FastAPI with "
                        "`uvicorn backend.api:app --reload` and try again."
                    )
                    st.stop()

            st.session_state.chat_history_api.append(
                {
                    "role": "assistant",
                    "content": payload["answer"],
                    "sources": payload["sources"],
                }
            )

            st.rerun()
