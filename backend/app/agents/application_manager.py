import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path


# Store the database inside backend/data/
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASE = DATA_DIR / "careerpilot.db"


VALID_STATUSES = [
    "Discovered",
    "Suitable",
    "Documents Prepared",
    "Ready to Apply",
    "Saved",
    "Applied",
    "Assessment",
    "Interview",
    "Offer",
    "Rejected",
    "Withdrawn"
]


@contextmanager
def get_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def initialize_database():

    with get_connection() as conn:

        conn.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL,
                role TEXT NOT NULL,
                job_url TEXT,
                status TEXT DEFAULT 'Saved',
                application_date TEXT,
                interview_date TEXT,
                notes TEXT,
                location TEXT DEFAULT '',
                source TEXT DEFAULT '',
                match_score REAL,
                resume TEXT DEFAULT '',
                cover_letter TEXT DEFAULT ''
            )
        """)
        existing_columns = {row[1] for row in conn.execute("PRAGMA table_info(applications)").fetchall()}
        for name, definition in (
            ("location", "TEXT DEFAULT ''"),
            ("source", "TEXT DEFAULT ''"),
            ("match_score", "REAL"),
            ("resume", "TEXT DEFAULT ''"),
            ("cover_letter", "TEXT DEFAULT ''"),
        ):
            if name not in existing_columns:
                conn.execute(f"ALTER TABLE applications ADD COLUMN {name} {definition}")


def add_application(company, role, job_url="", status="Saved", location="", source="", match_score=None, resume="", cover_letter=""):

    initialize_database()

    with get_connection() as conn:

        if job_url:
            existing = conn.execute(
                "SELECT id FROM applications WHERE job_url = ? LIMIT 1",
                (job_url,),
            ).fetchone()
        else:
            existing = conn.execute(
                "SELECT id FROM applications WHERE lower(company) = lower(?) AND lower(role) = lower(?) LIMIT 1",
                (company, role),
            ).fetchone()

        if existing:
            return {
                "id": existing["id"],
                "message": "Application is already in your tracker",
                "duplicate": True,
            }

        cursor = conn.execute("""
            INSERT INTO applications
            (company, role, job_url, status, application_date, location, source, match_score, resume, cover_letter)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            company,
            role,
            job_url,
            status,
            datetime.now().strftime("%Y-%m-%d"),
            location,
            source,
            match_score,
            resume,
            cover_letter,
        ))

        return {
            "id": cursor.lastrowid,
            "message": "Opportunity saved to your tracker",
            "duplicate": False,
        }


def get_applications():

    initialize_database()

    with get_connection() as conn:

        rows = conn.execute("""
            SELECT *
            FROM applications
            ORDER BY id DESC
        """).fetchall()

        return [dict(row) for row in rows]


def update_application(
    application_id,
    status=None,
    interview_date=None,
    notes=None
):

    initialize_database()

    if status is not None and status not in VALID_STATUSES:
        return {
            "success": False,
            "message": f"Invalid status. Choose from: {VALID_STATUSES}"
        }

    updates = []
    values = []

    if status is not None:
        updates.append("status = ?")
        values.append(status)

    if interview_date is not None:
        updates.append("interview_date = ?")
        values.append(interview_date)

    if notes is not None:
        updates.append("notes = ?")
        values.append(notes)

    if not updates:
        return {
            "success": False,
            "message": "No fields provided to update"
        }

    values.append(application_id)

    with get_connection() as conn:

        cursor = conn.execute(
            f"""
            UPDATE applications
            SET {", ".join(updates)}
            WHERE id = ?
            """,
            values
        )

        if cursor.rowcount == 0:
            return {
                "success": False,
                "message": "Application not found"
            }

    return {
        "success": True,
        "message": "Application updated successfully",
        "application_id": application_id
    }


def get_application_stats():

    initialize_database()

    with get_connection() as conn:

        total = conn.execute("""
            SELECT COUNT(*) FROM applications
        """).fetchone()[0]

        rows = conn.execute("""
            SELECT status, COUNT(*) AS count
            FROM applications
            GROUP BY status
        """).fetchall()

        status_counts = {
            row["status"]: row["count"]
            for row in rows
        }

        return {
            "total_applications": total,
            "status_counts": status_counts,
            "interviews": status_counts.get("Interview", 0),
            "offers": status_counts.get("Offer", 0),
            "rejections": status_counts.get("Rejected", 0)
        }
