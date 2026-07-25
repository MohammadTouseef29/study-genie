---
title: Study Genie API
emoji: 🎓
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# Study Genie API

FastAPI backend for [Study Genie](https://github.com/MohammadTouseef29/study-genie) — an AI-driven classroom
intelligence platform (doubt solving, lecture transcription, adaptive quizzes, face-recognition attendance,
personalized study plans). This Space runs the backend only; the Streamlit frontend is deployed separately
(e.g. Streamlit Community Cloud) and points at this Space's URL via `STUDY_GENIE_API_URL`.

Interactive API docs: `/docs` on this Space's URL.

## Required secrets

Set these under this Space's **Settings → Variables and secrets**:

- `GROQ_API_KEY`
- `DATABASE_URL` — Supabase Postgres connection pooler URI
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

This is not the source-of-truth repo — see the main GitHub repository linked above for source, docs, and issues.
