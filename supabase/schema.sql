-- Study Genie — Supabase/Postgres schema
-- Run this once in the Supabase SQL editor (or via psql) against a fresh project.
-- Safe to re-run: every statement is guarded with IF NOT EXISTS.

create extension if not exists vector;

-- ============================================================
-- Accounts
-- ============================================================
create table if not exists users (
    user_id text primary key,
    email text unique not null,
    name text not null,
    password_hash text not null,
    demo_student_id text not null,
    created_at timestamptz not null default now()
);

-- ============================================================
-- Attendance (face recognition)
-- ============================================================
create table if not exists attendance_roster (
    student_id text primary key,
    name text not null,
    encoding double precision[] not null,
    photo_path text,
    faces_detected_at_enrollment int,
    enrolled_at timestamptz not null default now()
);

create table if not exists attendance_log (
    id bigserial primary key,
    session_id text not null,
    course_id text not null,
    course_name text,
    session_label text,
    session_date date not null,
    student_id text not null,
    student_name text,
    status text not null check (status in ('present', 'absent')),
    confidence double precision,
    marked_at timestamptz not null default now()
);
create index if not exists idx_attendance_log_session on attendance_log(session_id);
create index if not exists idx_attendance_log_student on attendance_log(student_id);

-- ============================================================
-- Study materials (flashcards + quizzes)
-- ============================================================
create table if not exists study_materials (
    material_id text primary key,
    generated_at timestamptz not null,
    source_type text not null,
    source_name text,
    topic_tags jsonb not null default '[]',
    flashcards jsonb not null default '[]',
    quiz jsonb not null default '[]',
    difficulty_bias text,
    difficulty_reason text,
    student_id text,
    course_id text,
    course_name text,
    saved_at timestamptz
);
create index if not exists idx_study_materials_student on study_materials(student_id);

create table if not exists quiz_attempts (
    id bigserial primary key,
    material_id text not null references study_materials(material_id) on delete cascade,
    attempted_at timestamptz not null default now(),
    student_id text not null,
    course_id text,
    score int not null,
    total_questions int not null,
    percentage double precision not null
);
create index if not exists idx_quiz_attempts_student on quiz_attempts(student_id);
create index if not exists idx_quiz_attempts_material on quiz_attempts(material_id);

create table if not exists study_material_topic_mapping (
    id bigserial primary key,
    material_id text not null,
    generated_at timestamptz not null,
    source_type text,
    source_name text,
    topic text not null,
    flashcard_count int not null default 0,
    quiz_count int not null default 0
);

-- ============================================================
-- Synthetic classroom dataset (seeds the ML risk model,
-- doubt-frequency tracking, and study plan generation)
-- ============================================================
create table if not exists student_activity (
    student_id text not null,
    date date not null,
    lecture_id int,
    attendance int not null,
    engagement_score double precision not null
);
create index if not exists idx_student_activity_student on student_activity(student_id);

create table if not exists quiz_performance (
    student_id text not null,
    quiz_id text,
    topic text not null,
    score double precision not null,
    max_score double precision,
    date date not null
);
create index if not exists idx_quiz_performance_student on quiz_performance(student_id);
create index if not exists idx_quiz_performance_topic on quiz_performance(topic);

create table if not exists doubt_interactions (
    student_id text not null,
    topic text not null,
    question_count int not null,
    date date not null
);
create index if not exists idx_doubt_interactions_student on doubt_interactions(student_id);
create index if not exists idx_doubt_interactions_topic on doubt_interactions(topic);

create table if not exists assignment_submissions (
    student_id text not null,
    assignment_id text,
    topic text,
    due_date date,
    submitted_at date,
    delay_days double precision,
    status text,
    is_late integer,
    is_missed integer,
    was_submitted integer
);
create index if not exists idx_assignment_submissions_student on assignment_submissions(student_id);

-- ============================================================
-- Note: RAG document embeddings are NOT defined here.
-- langchain_postgres.PGVector manages its own tables
-- (langchain_pg_collection / langchain_pg_embedding) automatically
-- the first time the backend runs, using the same pgvector extension
-- enabled above.
-- ============================================================
