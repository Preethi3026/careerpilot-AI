"""Persistence for the local candidate profile and consolidated workflow history."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.agents.application_manager import get_connection, initialize_database


def initialize_career_storage() -> None:
    initialize_database()
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS candidate_profile (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                profile_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS workflow_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                keyword TEXT NOT NULL,
                summary_json TEXT NOT NULL,
                result_json TEXT NOT NULL
            )
        """)


def save_candidate_profile(profile: dict[str, Any]) -> dict[str, Any]:
    initialize_career_storage()
    updated_at = datetime.now(timezone.utc).isoformat()
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO candidate_profile (id, profile_json, updated_at) VALUES (1, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET profile_json=excluded.profile_json, updated_at=excluded.updated_at",
            (json.dumps(profile, ensure_ascii=False), updated_at),
        )
    return {"profile": profile, "updated_at": updated_at}


def get_candidate_profile() -> dict[str, Any] | None:
    initialize_career_storage()
    with get_connection() as connection:
        row = connection.execute("SELECT profile_json, updated_at FROM candidate_profile WHERE id = 1").fetchone()
    if not row:
        return None
    return {"profile": json.loads(row["profile_json"]), "updated_at": row["updated_at"]}


def save_workflow_result(result: dict[str, Any]) -> int:
    initialize_career_storage()
    created_at = datetime.now(timezone.utc).isoformat()
    summary = result.get("summary", {})
    keyword = str(result.get("keyword", "Career analysis"))
    with get_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO workflow_history (created_at, keyword, summary_json, result_json) VALUES (?, ?, ?, ?)",
            (created_at, keyword, json.dumps(summary, ensure_ascii=False), json.dumps(result, ensure_ascii=False, default=str)),
        )
        return int(cursor.lastrowid)


def list_workflow_history(limit: int = 25) -> list[dict[str, Any]]:
    initialize_career_storage()
    safe_limit = max(1, min(limit, 100))
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT id, created_at, keyword, summary_json FROM workflow_history ORDER BY id DESC LIMIT ?",
            (safe_limit,),
        ).fetchall()
    return [{"id": row["id"], "created_at": row["created_at"], "keyword": row["keyword"], "summary": json.loads(row["summary_json"])} for row in rows]


def get_workflow_history(workflow_id: int) -> dict[str, Any] | None:
    initialize_career_storage()
    with get_connection() as connection:
        row = connection.execute(
            "SELECT id, created_at, result_json FROM workflow_history WHERE id = ?",
            (workflow_id,),
        ).fetchone()
    if not row:
        return None
    return {"id": row["id"], "created_at": row["created_at"], "result": json.loads(row["result_json"])}
