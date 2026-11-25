"""Persistence for the local candidate profile and consolidated workflow history."""

from __future__ import annotations

import json
import hashlib
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.agents.application_manager import get_connection, initialize_database

BACKEND_DIR = Path(__file__).resolve().parents[2]
GENERATED_DIR = BACKEND_DIR / "generated_documents"


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
        connection.execute("""
            CREATE TABLE IF NOT EXISTS generated_documents (
                id TEXT PRIMARY KEY,
                workflow_id INTEGER,
                job_key TEXT NOT NULL,
                kind TEXT NOT NULL,
                content_hash TEXT NOT NULL DEFAULT '',
                filename TEXT NOT NULL,
                path TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        document_columns = {row[1] for row in connection.execute("PRAGMA table_info(generated_documents)").fetchall()}
        if "content_hash" not in document_columns:
            connection.execute("ALTER TABLE generated_documents ADD COLUMN content_hash TEXT NOT NULL DEFAULT ''")
        # Keep all documents created by an earlier schema while assigning each
        # one a distinct legacy key before installing the de-duplication index.
        connection.execute("UPDATE generated_documents SET content_hash = 'legacy:' || id WHERE content_hash = ''")
        connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS generated_documents_dedupe ON generated_documents(job_key, kind, content_hash)")
        connection.execute("""
            CREATE TABLE IF NOT EXISTS workflow_runs (
                idempotency_key TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                result_json TEXT,
                updated_at TEXT NOT NULL
            )
        """)


def claim_workflow_run(idempotency_key: str) -> tuple[str, dict[str, Any] | None]:
    """Atomically claim an execution key or return its persisted state."""
    initialize_career_storage()
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as connection:
        row = connection.execute("SELECT status, result_json FROM workflow_runs WHERE idempotency_key = ?", (idempotency_key,)).fetchone()
        if row and row["status"] == "completed":
            return "completed", json.loads(row["result_json"] or "{}")
        if row and row["status"] == "running":
            return "running", None
        connection.execute(
            "INSERT INTO workflow_runs (idempotency_key, status, updated_at) VALUES (?, 'running', ?) "
            "ON CONFLICT(idempotency_key) DO UPDATE SET status='running', result_json=NULL, updated_at=excluded.updated_at",
            (idempotency_key, now),
        )
    return "claimed", None


def complete_workflow_run(idempotency_key: str, result: dict[str, Any]) -> None:
    initialize_career_storage()
    with get_connection() as connection:
        connection.execute(
            "UPDATE workflow_runs SET status='completed', result_json=?, updated_at=? WHERE idempotency_key=?",
            (json.dumps(result, ensure_ascii=False, default=str), datetime.now(timezone.utc).isoformat(), idempotency_key),
        )


def fail_workflow_run(idempotency_key: str) -> None:
    initialize_career_storage()
    with get_connection() as connection:
        connection.execute(
            "UPDATE workflow_runs SET status='failed', updated_at=? WHERE idempotency_key=?",
            (datetime.now(timezone.utc).isoformat(), idempotency_key),
        )


def get_workflow_run(idempotency_key: str) -> dict[str, Any] | None:
    initialize_career_storage()
    with get_connection() as connection:
        row = connection.execute(
            "SELECT status, result_json, updated_at FROM workflow_runs WHERE idempotency_key = ?",
            (idempotency_key,),
        ).fetchone()
    if not row:
        return None
    return {
        "status": row["status"],
        "result": json.loads(row["result_json"]) if row["result_json"] else None,
        "updated_at": row["updated_at"],
    }


def fail_interrupted_workflow_runs() -> None:
    """Mark prior-process runs as failed so startup recovery can retry them."""
    initialize_career_storage()
    with get_connection() as connection:
        connection.execute(
            "UPDATE workflow_runs SET status='failed', updated_at=? WHERE status='running'",
            (datetime.now(timezone.utc).isoformat(),),
        )


def create_document_pdf(text: str, job_title: str, company: str, kind: str) -> dict[str, str]:
    """Create a paginated local PDF and register an opaque download identifier."""
    try:
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer
    except ImportError as error:
        raise RuntimeError("PDF generation needs the reportlab dependency. Install backend/requirements.txt.") from error

    safe = lambda value: re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_")[:60] or "CareerPilot"
    job_key = f"{company}|{job_title}"
    filename = f"{safe(company)}_{safe(job_title)}.pdf"
    folder = GENERATED_DIR / ("resumes" if kind == "resume" else "cover_letters")
    content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    initialize_career_storage()
    with get_connection() as connection:
        existing = connection.execute(
            "SELECT id, filename, path FROM generated_documents WHERE job_key = ? AND kind = ? AND content_hash = ?",
            (job_key, kind, content_hash),
        ).fetchone()
    if existing and existing["filename"] == filename and Path(existing["path"]).is_file():
        return {"id": existing["id"], "filename": existing["filename"], "download_url": f"/api/documents/{existing['id']}"}
    document_id = uuid.uuid4().hex
    kind_label = "Resume" if kind == "resume" else "Cover Letter"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / filename
    styles = getSampleStyleSheet()
    navy = colors.HexColor("#17365D")
    body = ParagraphStyle("CareerBody", parent=styles["BodyText"], fontName="Helvetica", fontSize=9, leading=11.3, spaceAfter=2.4)
    name_style = ParagraphStyle("CareerName", parent=body, alignment=TA_CENTER, fontName="Helvetica-Bold", fontSize=17, leading=20, spaceAfter=3)
    contact_style = ParagraphStyle("CareerContact", parent=body, alignment=TA_CENTER, fontSize=8.5, leading=10, spaceAfter=7)
    section_style = ParagraphStyle("CareerSection", parent=body, fontName="Helvetica-Bold", textColor=navy, fontSize=10, leading=12, spaceBefore=5, spaceAfter=2)
    story = []
    lines = text.splitlines()
    section_names = {"PROFILE", "PROFESSIONAL SUMMARY", "EDUCATION", "EXPERIENCE", "WORK EXPERIENCE", "PROJECTS", "TECHNICAL SKILLS", "SKILLS", "CERTIFICATIONS & PUBLICATION", "CERTIFICATIONS", "LANGUAGES", "ADDITIONAL CANDIDATE-PROVIDED PROJECTS", "ADDITIONAL CANDIDATE-PROVIDED EXPERIENCE", "ADDITIONAL CANDIDATE-PROVIDED CERTIFICATIONS"}
    first_section = next((i for i, line in enumerate(lines) if line.strip().upper() in section_names), len(lines))
    header_lines = [line.strip() for line in lines[:first_section] if line.strip()]
    if kind == "resume" and header_lines:
        story.append(Paragraph(header_lines[0], name_style))
        if len(header_lines) > 1:
            story.append(Paragraph(" &nbsp;|&nbsp; ".join(header_lines[1:]), contact_style))
    elif kind == "cover_letter":
        story.append(Paragraph(f"{safe(job_title)} · {safe(company)}", name_style))
        story.append(Paragraph(kind_label, contact_style))
    active_lines = lines[first_section:] if kind == "resume" else lines
    for line in active_lines:
        clean = line.strip()
        if not clean:
            story.append(Spacer(1, 1.5 * mm))
            continue
        escaped = clean.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if clean.upper() in section_names:
            story.extend([Paragraph(clean.upper(), section_style), HRFlowable(width="100%", thickness=0.65, color=navy, spaceAfter=3)])
        elif clean.startswith(("- ", "• ", "* ")):
            story.append(Paragraph("• &nbsp;" + escaped[2:], body))
        else:
            story.append(Paragraph(escaped, body))
    SimpleDocTemplate(str(path), pagesize=A4, rightMargin=17 * mm, leftMargin=17 * mm, topMargin=14 * mm, bottomMargin=14 * mm, title=f"{job_title} - {kind_label}").build(story)
    initialize_career_storage()
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO generated_documents (id, job_key, kind, content_hash, filename, path, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (document_id, job_key, kind, content_hash, filename, str(path.resolve()), datetime.now(timezone.utc).isoformat()),
        )
    return {"id": document_id, "filename": filename, "download_url": f"/api/documents/{document_id}"}


def get_generated_document(document_id: str) -> dict[str, str] | None:
    initialize_career_storage()
    with get_connection() as connection:
        row = connection.execute("SELECT filename, path FROM generated_documents WHERE id = ?", (document_id,)).fetchone()
    if not row:
        return None
    path = Path(row["path"]).resolve()
    if not path.is_relative_to(GENERATED_DIR.resolve()) or not path.is_file():
        return None
    return {"filename": row["filename"], "path": str(path)}


def attach_workflow_documents(workflow_id: int, result: dict[str, Any]) -> None:
    """Persist the workflow relationship for each document in its result."""
    initialize_career_storage()
    identifiers = [
        item[kind]["id"]
        for item in result.get("selected_jobs", [])
        for kind in ("resume_document", "cover_letter_document")
        if isinstance(item.get(kind), dict) and item[kind].get("id")
    ]
    if not identifiers:
        return
    with get_connection() as connection:
        connection.executemany(
            "UPDATE generated_documents SET workflow_id = ? WHERE id = ?",
            [(workflow_id, identifier) for identifier in identifiers],
        )


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
