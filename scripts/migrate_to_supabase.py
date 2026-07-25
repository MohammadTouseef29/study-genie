"""One-time setup script: creates the Postgres schema on your Supabase project
and seeds it with the existing synthetic classroom dataset (student_activity,
quiz_performance, doubt_interactions, assignment_submissions) so the ML risk
model, study plan, and doubt-frequency tracking work immediately.

Safe to re-run: schema creation is idempotent (IF NOT EXISTS everywhere), and
each seed table is only populated if it's currently empty.

Usage:
    python scripts/migrate_to_supabase.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

from backend.db import get_engine  # noqa: E402

ANALYTICS_DIR = PROJECT_ROOT / "data" / "analytics"
SCHEMA_FILE = PROJECT_ROOT / "supabase" / "schema.sql"

SEED_TABLES = {
    "student_activity": {
        "csv": "student_activity.csv",
        "parse_dates": ["date"],
    },
    "quiz_performance": {
        "csv": "quiz_performance.csv",
        "parse_dates": ["date"],
    },
    "doubt_interactions": {
        "csv": "doubt_interactions.csv",
        "parse_dates": ["date"],
    },
    "assignment_submissions": {
        "csv": "assignment_submissions.csv",
        "parse_dates": ["due_date", "submitted_at"],
    },
}


def apply_schema(engine) -> None:
    print(f"Applying schema from {SCHEMA_FILE} ...")
    sql = SCHEMA_FILE.read_text(encoding="utf-8")
    with engine.begin() as conn:
        conn.exec_driver_sql(sql)
    print("Schema applied.")


def seed_table(engine, table_name: str, csv_name: str, parse_dates: list[str]) -> None:
    csv_path = ANALYTICS_DIR / csv_name
    if not csv_path.exists():
        print(f"  Skipping {table_name}: {csv_path} not found.")
        return

    with engine.connect() as conn:
        existing_rows = conn.execute(text(f"SELECT count(*) FROM {table_name}")).scalar_one()

    if existing_rows:
        print(f"  Skipping {table_name}: already has {existing_rows} rows.")
        return

    df = pd.read_csv(csv_path, parse_dates=parse_dates)
    with engine.begin() as conn:
        df.to_sql(table_name, conn, if_exists="append", index=False)
    print(f"  Seeded {table_name} with {len(df)} rows from {csv_name}.")


def main() -> None:
    engine = get_engine()

    apply_schema(engine)

    print("\nSeeding synthetic classroom dataset ...")
    for table_name, config in SEED_TABLES.items():
        seed_table(engine, table_name, config["csv"], config["parse_dates"])

    print("\nDone. Your Supabase project is ready.")


if __name__ == "__main__":
    main()
