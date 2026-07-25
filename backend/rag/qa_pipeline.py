from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
import os

from backend.rag.vector_store import get_vector_store


# -------------------------------
# Rewrite follow-up question
# -------------------------------
def rewrite_question(chat_history, question):
    """
    Converts a follow-up question into a standalone question.
    """

    history_text = "\n".join(
        [f"{m['role']}: {m['content']}" for m in chat_history[-4:]]
    )

    prompt = PromptTemplate.from_template(
        """
You are a helpful assistant.

Given the conversation history and a follow-up question,
rewrite the follow-up question into a standalone question.

Conversation history:
{history}

Follow-up question:
{question}

Standalone question:
"""
    )

    llm = ChatGroq(
        model="llama-3.1-8b-instant",
        groq_api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.0
    )

    chain = prompt | llm

    rewritten = chain.invoke(
        {
            "history": history_text,
            "question": question
        }
    )

    return rewritten.content.strip()


def _format_source(doc):
    pdf_name = doc.metadata.get("pdf_name", "Unknown PDF")
    page_number = doc.metadata.get("page_number", doc.metadata.get("page_label", doc.metadata.get("page", "?")))
    snippet = doc.page_content.strip().replace("\n", " ")
    return {
        "pdf_name": pdf_name,
        "page": str(page_number),
        "chunk_id": doc.metadata.get("chunk_id", ""),
        "snippet": snippet[:320],
    }


# -------------------------------
# Main QA function (chat-aware)
# -------------------------------
def get_answer(question, chat_history=None, top_k=7):
    """
    Chat-aware RAG:
    - Rewrites follow-up questions
    - Retrieves from vector DB
    - Answers with citations
    """

    if chat_history:
        question = rewrite_question(chat_history, question)

    vectorstore = get_vector_store()
    docs = vectorstore.max_marginal_relevance_search(question, k=top_k, fetch_k=max(top_k * 3, 12))

    if not docs:
        return "The uploaded documents do not contain information about this question.", []

    context = "\n\n".join(
        [
            (
                f"[Source {index}] PDF: {d.metadata.get('pdf_name', 'Unknown PDF')} | "
                f"Page: {d.metadata.get('page_number', d.metadata.get('page_label', d.metadata.get('page', '?')))}\n"
                f"{d.page_content}"
            )
            for index, d in enumerate(docs, start=1)
        ]
    )

    prompt = PromptTemplate.from_template(
        """
You are Study Genie, an academic assistant.

Use only the retrieved context to answer the question.

Rules:
- Give a direct, helpful answer first.
- If the context supports multiple points, organize them briefly with bullets.
- Do not invent facts outside the retrieved context.
- If the answer is incomplete in the context, say what is available and what is missing.
- End with a short `Sources used:` line citing the most relevant source numbers like `[Source 1]`.
- If the answer is not present, say exactly:
"The uploaded documents do not contain information about this question."

Retrieved context:
{context}

Question:
{question}

Answer:
"""
    )

    llm = ChatGroq(
        model="llama-3.1-8b-instant",
        groq_api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.1
    )

    chain = prompt | llm

    response = chain.invoke(
        {
            "context": context,
            "question": question
        }
    )

    sources = [_format_source(doc) for doc in docs]

    return response.content, sources
