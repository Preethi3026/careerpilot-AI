"""Local, versioned candidate facts, preferences and public GitHub projects."""

from __future__ import annotations

import hashlib
import json
import re
import time
import unicodedata
from datetime import date
from pathlib import Path
from typing import Any

import httpx

BACKEND_DIR = Path(__file__).resolve().parents[2]
JOBS_DIR = BACKEND_DIR / "data" / "jobs"
INPUTS_DIR = JOBS_DIR / "inputs"
ME_DIR = JOBS_DIR / "me"
SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "preferences.schema.json"
PREFERENCES_DEFAULTS: dict[str, Any] = {
    "location": "Germany",
    "target_roles": [
        "Machine Learning Intern", "AI Intern", "Data Engineering Intern",
        "Praktikum Machine Learning", "Praktikum Künstliche Intelligenz", "Praktikum Data Engineering",
    ],
    "seniority": ["internship"],
    "languages": [],
    "availability": "",
    "mandatory_internship": False,
    "search": {
        "queries": [
            "Machine Learning Intern", "AI Intern", "Data Engineering Intern",
            "Praktikum Machine Learning", "Praktikum Künstliche Intelligenz", "Praktikum Data Engineering",
        ],
        "location": "Germany",
        "job_types": ["internship"],
    },
    "automation": {"min_fit": 70, "max_drafts_per_run": 3, "max_matches_per_run": 12, "min_keyword_score": 40},
}

SECTION_TITLES = {
    "summary": {"summary", "professional summary", "profile", "about me", "career objective", "objective"},
    "skills": {"skills", "technical skills", "technical expertise", "core competencies", "technologies", "tools and technologies"},
    "projects": {"projects", "selected projects", "academic projects", "personal projects", "project experience"},
    "experience": {"experience", "work experience", "professional experience", "employment", "employment history", "internships"},
    "education": {"education", "academic background", "qualifications"},
    "certifications": {"certifications", "certificates", "licenses"},
    "languages": {"languages", "language skills"},
}
EDITABLE_FIELDS = {"title", "org", "location", "dates", "name", "headline", "tagline", "link", "degree", "school", "note", "label", "items"}
README_NAMES = ("README.md", "readme.md", "Readme.md", "README.rst", "README.txt", "README")
DEPENDENCY_FILES = ("requirements.txt", "pyproject.toml", "package.json", "Package.swift")
TECHNOLOGY_NAMES = {
    "fastapi": "FastAPI", "flask": "Flask", "django": "Django", "pandas": "Pandas", "numpy": "NumPy",
    "torch": "PyTorch", "pytorch": "PyTorch", "tensorflow": "TensorFlow", "scikit-learn": "scikit-learn",
    "sklearn": "scikit-learn", "langgraph": "LangGraph", "langchain": "LangChain", "ollama": "Ollama",
    "openai": "OpenAI API", "pytest": "pytest", "streamlit": "Streamlit", "pyspark": "Spark", "kafka": "Kafka",
    "airflow": "Airflow", "docker": "Docker", "sqlalchemy": "SQLAlchemy", "postgres": "PostgreSQL",
    "sqlite": "SQLite", "react.js": "React", "reactjs": "React", "next.js": "Next.js", "nextjs": "Next.js",
    "typescript": "TypeScript", "playwright": "Playwright", "selenium": "Selenium", "beautifulsoup4": "BeautifulSoup",
    "httpx": "httpx", "faiss": "FAISS", "chromadb": "ChromaDB", "spacy": "spaCy", "transformers": "Hugging Face Transformers",
    "opencv": "OpenCV", "matplotlib": "Matplotlib", "plotly": "Plotly", "dbt": "dbt", "aws": "AWS",
}


def _next_version(folder: Path, stem: str, suffix: str = ".json") -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    version = 1
    while (folder / f"{stem}_v{version}{suffix}").exists() or (suffix == ".json" and (folder / f"{stem}_v{version}.md").exists()):
        version += 1
    return folder / f"{stem}_v{version}{suffix}"


def _write_new(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(content)


def _latest(folder: Path, stem: str) -> Path | None:
    matches = []
    for path in folder.glob(f"{stem}_v*.json"):
        match = re.fullmatch(rf"{re.escape(stem)}_v(\d+)\.json", path.name)
        if match:
            matches.append((int(match.group(1)), path))
    return max(matches, default=(0, None))[1]


def _fact_id(number: int) -> str:
    return f"F{number:03d}"


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", text) if part.strip()]


def _clean_line(text: str) -> str:
    return re.sub(r"^\s*(?:[-*•▪]|\d+[.)])\s*", "", text).strip()


def _section_name(line: str) -> str | None:
    candidate = re.sub(r"^\s{0,3}#{1,6}\s*|\*", "", line).strip().rstrip(":").casefold()
    return next((kind for kind, names in SECTION_TITLES.items() if candidate in names), None)


def _group_entries(body: str, kind: str, next_fact: list[int]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for raw in body.splitlines():
        line = raw.strip()
        if not line:
            continue
        bullet = bool(re.match(r"^(?:[-*•▪]|\d+[.)])\s+", line))
        text = _clean_line(line)
        if bullet:
            if current is None:
                current = {"heading": "Candidate-provided " + ("experience" if kind == "experience" else "project"), "bullets": []}
                entries.append(current)
            current["bullets"].append({"id": _fact_id(next_fact[0]), "text": text})
            next_fact[0] += 1
        else:
            current = {"heading": text, "bullets": []}
            entries.append(current)
    if not entries and body.strip():
        entries = [{"heading": "Candidate-provided " + kind, "bullets": [{"id": _fact_id(next_fact[0]), "text": body.strip()}]}]
        next_fact[0] += 1

    result: list[dict[str, Any]] = []
    for index, entry in enumerate(entries, start=1):
        heading = entry["heading"]
        dates_match = re.search(r"(?:19|20)\d{2}.*?(?:19|20)\d{2}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}.*?(?:Present|Current|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4})", heading, re.I)
        dates = dates_match.group(0) if dates_match else ""
        head = heading.replace(dates, "").strip(" ,-–|·") if dates else heading
        parts = [part.strip() for part in re.split(r"\s+[|·]\s+|,\s+", head, maxsplit=1) if part.strip()]
        if kind == "experience":
            result.append({"id": f"E{index}", "title": parts[0] if parts else head, "org": parts[1] if len(parts) > 1 else "", "location": "", "dates": dates, "bullets": entry["bullets"]})
        elif kind == "projects":
            result.append({"id": f"CP{index}", "name": parts[0] if parts else head, "tagline": parts[1] if len(parts) > 1 else "", "stack": [], "link": "", "bullets": entry["bullets"]})
    return result


def profile_from_text(text: str, source: str = "saved-profile") -> dict[str, Any]:
    """Fallback extraction using CareerPilot's established resume section parser."""
    from app.agents.resume_agent import _split_resume

    preamble, sections = _split_resume(text)
    header_lines = [line.strip() for line in preamble.splitlines() if line.strip()]
    contact: list[str] = []
    name = ""
    headline = ""
    for line in header_lines:
        if re.search(r"@|https?://|(?:\+?\d[\d ()-]{6,}\d)", line):
            contact.append(line)
        elif not name and len(line.split()) <= 6:
            name = line
        elif not headline:
            headline = line

    profile: dict[str, Any] = {
        "version": 1, "source": source, "extracted": date.today().isoformat(),
        "header": {"name": name, "headline": headline, "contact": contact},
        "summary": [], "skills": [], "experience": [], "projects": [], "education": [],
        "certifications": [], "languages": [],
    }
    next_fact = [1]
    for section in sections:
        kind = section["kind"]
        body = section["body"].strip()
        if not body:
            continue
        if kind == "summary":
            profile["summary"] = [{"id": _fact_id(next_fact[0] + i), "text": sentence} for i, sentence in enumerate(_sentences(re.sub(r"\s+", " ", body)))]
            next_fact[0] += len(profile["summary"])
        elif kind == "skills":
            groups: list[dict[str, str]] = []
            for line in (line.strip() for line in body.splitlines() if line.strip()):
                if ":" in line:
                    label, items = line.split(":", 1)
                    groups.append({"label": label.strip(), "items": items.strip()})
                elif groups:
                    groups[-1]["items"] = (groups[-1]["items"] + ", " + line).strip(", ")
                else:
                    groups.append({"label": "Technical Skills", "items": line})
            profile["skills"].extend({"id": f"S{len(profile['skills']) + i + 1}", **group} for i, group in enumerate(groups))
        elif kind in {"experience", "projects"}:
            profile[kind].extend(_group_entries(body, kind, next_fact))
        elif kind == "education":
            for line in (line.strip() for line in body.splitlines() if line.strip()):
                parts = [part.strip() for part in re.split(r"\s+[|·]\s+", line, maxsplit=2)]
                profile["education"].append({"id": f"ED{len(profile['education']) + 1}", "degree": parts[0], "school": parts[1] if len(parts) > 1 else "", "note": parts[2] if len(parts) > 2 else "", "dates": ""})
        elif kind in {"certifications", "languages"}:
            profile[kind] = [{"id": _fact_id(next_fact[0] + i), "text": _clean_line(line)} for i, line in enumerate(body.splitlines()) if _clean_line(line)]
            next_fact[0] += len(profile[kind])
    return profile


def _pdf_layout_profile(pdf_path: Path, source: str) -> tuple[dict[str, Any] | None, str]:
    """Recognise the reference CV layout: navy bold headings and aligned grey dates."""
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    page = reader.pages[0]
    all_text = "\n".join((item.extract_text() or "") for item in reader.pages).strip()
    height = float(page.mediabox.height)
    state = {"color": "#000000"}
    runs: list[dict[str, Any]] = []

    def color(operands: Any) -> str:
        try:
            return "#%02x%02x%02x" % tuple(round(float(value) * 255) for value in operands[:3])
        except (TypeError, ValueError):
            return "#000000"

    def before(op: bytes, operands: Any, _cm: Any, _tm: Any) -> None:
        if op == b"rg":
            state["color"] = color(operands)

    def visit(raw: str, cm: Any, tm: Any, fontdict: Any, size: float) -> None:
        if not raw.strip() or raw.strip() == "•":
            return
        font = str((fontdict or {}).get("/BaseFont", ""))
        runs.append({
            "y": round(height - (tm[4] * cm[1] + tm[5] * cm[3] + cm[5]), 1),
            "x": round(tm[4] * cm[0] + tm[5] * cm[2] + cm[4], 1),
            "size": round(size * abs(cm[3] or 1) * abs(tm[3] or 1), 1),
            "bold": "bold" in font.casefold(), "color": state["color"],
            "text": unicodedata.normalize("NFKC", raw),
        })

    try:
        extracted_text = page.extract_text(visitor_operand_before=before, visitor_text=visit) or ""
    except Exception:
        extracted_text = page.extract_text() or ""
    if len(runs) < 5 or len(reader.pages) > 1:
        return None, all_text or extracted_text
    rows: list[list[dict[str, Any]]] = []
    for run in sorted(runs, key=lambda item: (item["y"], item["x"])):
        if rows and abs(rows[-1][0]["y"] - run["y"]) <= 1.5:
            rows[-1].append(run)
        else:
            rows.append([run])
    lines = [{"y": row[0]["y"], "x": min(item["x"] for item in row), "runs": sorted(row, key=lambda item: item["x"]), "size": max(item["size"] for item in row)} for row in rows]
    body_size = max(set(item["size"] for item in runs), key=[item["size"] for item in runs].count)
    left = min(item["x"] for item in runs)
    name_line = max(lines, key=lambda line: line["size"])
    header = {"name": " ".join(item["text"].strip() for item in name_line["runs"]).title(), "headline": "", "contact": []}

    def marked(row_runs: list[dict[str, Any]]) -> str:
        mixed = any(item["bold"] for item in row_runs) and not all(item["bold"] for item in row_runs)
        out = ""
        for item in row_runs:
            value = item["text"].replace("\n", " ")
            if mixed and item["bold"] and value.strip():
                out += f"{value[:len(value) - len(value.lstrip())]}**{value.strip()}**{value[len(value.rstrip()):]}"
            else:
                out += value
        return re.sub(r"\s+", " ", out).strip()

    sections: list[tuple[str, list[dict[str, Any]]]] = []
    for line in lines[lines.index(name_line) + 1:]:
        line_text = "".join(item["text"] for item in line["runs"]).strip()
        accent = line["runs"][0]["color"]
        try:
            red, _green, blue = (int(accent[index:index + 2], 16) / 255 for index in (1, 3, 5))
        except ValueError:
            red, blue = 0, 0
        is_heading = all(item["bold"] for item in line["runs"]) and blue - red > 0.15 and blue > 0.3 and line["size"] > body_size + 0.8 and line_text.upper() == line_text
        if is_heading:
            sections.append((line_text.upper(), []))
        elif sections:
            sections[-1][1].append(line)
        elif not header["headline"]:
            header["headline"] = marked(line["runs"])
        else:
            header["contact"] = [part.strip() for part in line_text.split("|") if part.strip()]

    if not sections:
        return None, all_text or extracted_text or page.extract_text() or ""
    profile: dict[str, Any] = {"version": 1, "source": source, "extracted": date.today().isoformat(), "header": header, "summary": [], "skills": [], "experience": [], "projects": [], "education": [], "certifications": [], "languages": []}
    fact_counter = [1]

    def new_facts(values: list[str]) -> list[dict[str, str]]:
        output = [{"id": _fact_id(fact_counter[0] + index), "text": value} for index, value in enumerate(values) if value]
        fact_counter[0] += len(output)
        return output

    for title, rows_in_section in sections:
        text = " ".join(marked(row["runs"]) for row in rows_in_section)
        if "SUMMARY" in title or "PROFILE" in title:
            profile["summary"] = new_facts(_sentences(re.sub(r"\s+", " ", text)))
        elif "SKILL" in title:
            groups: list[dict[str, str]] = []
            for row in rows_in_section:
                row_runs = row["runs"]
                first = row_runs[0]
                if first["bold"] and first["text"].strip().endswith(":"):
                    groups.append({"label": first["text"].strip().rstrip(":"), "items": marked(row_runs[1:])})
                elif groups:
                    groups[-1]["items"] += ", " + marked(row_runs)
            profile["skills"].extend({"id": f"S{len(profile['skills']) + index + 1}", **group} for index, group in enumerate(groups))
        elif any(word in title for word in ("EXPERIENCE", "PROJECT", "EDUCATION")):
            entries: list[dict[str, Any]] = []
            for row in rows_in_section:
                at_left = abs(row["x"] - left) < 3
                if at_left and row["runs"][0]["bold"]:
                    entries.append({"head": row, "extra": [], "rows": []})
                elif at_left and entries and not entries[-1]["rows"]:
                    entries[-1]["extra"].append(row)
                elif entries:
                    entries[-1]["rows"].append(row)
            for entry in entries:
                head_runs = entry["head"]["runs"]
                all_runs = head_runs + [run for row in entry["extra"] for run in row["runs"]]
                bold_text = " ".join(run["text"].strip() for run in head_runs if run["bold"])
                meta = " ".join(run["text"].strip() for run in all_runs if not run["bold"] and run["x"] > 300 and run["color"] == "#555555")
                rest = " ".join(run["text"].strip() for run in all_runs if not run["bold"] and not (run["x"] > 300 and run["color"] == "#555555"))
                bullet_groups: list[str] = []
                previous_y = None
                for row in entry["rows"]:
                    text_line = marked(row["runs"])
                    if previous_y is None or row["y"] - previous_y > body_size * 1.24:
                        bullet_groups.append(text_line)
                    elif bullet_groups:
                        bullet_groups[-1] += " " + text_line
                    previous_y = row["y"]
                bullets = new_facts(bullet_groups)
                if "EXPERIENCE" in title:
                    role, _, org = bold_text.rpartition(", ")
                    location, _, dates = meta.partition(" | ")
                    profile["experience"].append({"id": f"E{len(profile['experience']) + 1}", "title": role or bold_text, "org": org, "location": location.strip(), "dates": dates.strip(), "bullets": bullets})
                elif "PROJECT" in title:
                    name, _, tagline = bold_text.partition(": ")
                    parts = [part.strip() for part in re.split(r"\s*·\s*", rest) if part.strip()]
                    link = next((part for part in parts if re.match(r"(?:github\.com|gitlab\.com|https?://)", part)), "")
                    profile["projects"].append({"id": f"CP{len(profile['projects']) + 1}", "name": name.strip(), "tagline": tagline.strip(), "stack": [part for part in parts if part != link], "link": link, "bullets": bullets})
                else:
                    extras = " ".join(run["text"].strip() for row in entry["extra"] for run in row["runs"])
                    school, _, note = extras.partition(" · ")
                    profile["education"].append({"id": f"ED{len(profile['education']) + 1}", "degree": bold_text, "school": school or rest.lstrip("· ").strip(), "note": note, "dates": meta.strip()})
    fallback = profile_from_text(all_text, source)

    def quality(value: dict[str, Any]) -> int:
        return sum(len(value.get(key, [])) for key in ("summary", "skills", "experience", "projects", "education", "certifications", "languages")) + sum(
            len(entry.get("bullets", [])) for key in ("experience", "projects") for entry in value.get(key, [])
        )

    if quality(fallback) > quality(profile) + 2:
        return fallback, all_text or extracted_text
    return profile, all_text or extracted_text or page.extract_text() or ""


def read_master_cv_text() -> str:
    path = INPUTS_DIR / "master_cv.pdf"
    if not path.is_file():
        return ""
    from pypdf import PdfReader
    return "\n".join((page.extract_text() or "") for page in PdfReader(str(path)).pages).strip()


def profile_markdown(profile: dict[str, Any]) -> str:
    header = profile.get("header", {})
    lines = ["# Candidate facts (cite IDs; do not add claims)", "", f"Name: {header.get('name', '')}. Headline: {header.get('headline', '')}", "", "## Summary sentences"]
    lines.extend(f"- {fact['id']}: {fact['text']}" for fact in profile.get("summary", []))
    lines.extend(["", "## Skills"])
    lines.extend(f"- {skill['id']} {skill.get('label', 'Skills')}: {skill.get('items', '')}" for skill in profile.get("skills", []))
    lines.extend(["", "## Experience"])
    for entry in profile.get("experience", []):
        lines.append(f"{entry['id']} {entry.get('title', '')}, {entry.get('org', '')}, {entry.get('location', '')}, {entry.get('dates', '')}")
        lines.extend(f"- {fact['id']}: {fact['text']}" for fact in entry.get("bullets", []))
    lines.extend(["", "## Projects"])
    for project in profile.get("projects", []):
        lines.append(f"{project['id']} {project.get('name', '')}: {project.get('tagline', '')} ({', '.join(project.get('stack', []))})")
        lines.extend(f"- {fact['id']}: {fact['text']}" for fact in project.get("bullets", []))
    lines.extend(["", "## Education"])
    lines.extend(f"- {entry['id']}: {entry.get('degree', '')}, {entry.get('school', '')}, {entry.get('dates', '')}" for entry in profile.get("education", []))
    for section in ("certifications", "languages"):
        if profile.get(section):
            lines.extend(["", f"## {section.title()}"])
            lines.extend(f"- {item['id']}: {item['text']}" for item in profile[section])
    return "\n".join(lines) + "\n"


def save_profile_version(profile: dict[str, Any]) -> dict[str, Any]:
    folder = ME_DIR
    path = _next_version(folder, "profile")
    version = int(re.search(r"_v(\d+)", path.name).group(1))
    profile["version"] = version
    json_path = path
    markdown_path = path.with_suffix(".md")
    _write_new(json_path, json.dumps(profile, ensure_ascii=False, indent=2) + "\n")
    _write_new(markdown_path, profile_markdown(profile))
    return {"file": str(json_path.relative_to(BACKEND_DIR)).replace("\\", "/"), "facts_file": str(markdown_path.relative_to(BACKEND_DIR)).replace("\\", "/"), "profile": profile}


def save_candidate_profile_file(profile: dict[str, Any], updated_at: str | None = None) -> dict[str, Any]:
    """Persist the editable candidate form as a new local version, not in SQLite."""
    from datetime import datetime, timezone

    path = _next_version(ME_DIR, "candidate")
    updated_at = updated_at or datetime.now(timezone.utc).isoformat()
    stored = {**profile, "saved_at": updated_at}
    _write_new(path, json.dumps(stored, ensure_ascii=False, indent=2) + "\n")
    return {"profile": profile, "updated_at": updated_at, "file": str(path.relative_to(BACKEND_DIR)).replace("\\", "/")}


def load_candidate_profile_file() -> dict[str, Any] | None:
    path = _latest(ME_DIR, "candidate")
    if not path:
        return None
    stored = json.loads(path.read_text(encoding="utf-8"))
    return {"profile": {key: value for key, value in stored.items() if key != "saved_at"}, "updated_at": stored.get("saved_at")}


def load_profile() -> dict[str, Any] | None:
    path = _latest(ME_DIR, "profile")
    return json.loads(path.read_text(encoding="utf-8")) if path else None


def extract_and_save_profile(text: str, source: str = "saved-profile") -> dict[str, Any]:
    profile = profile_from_text(text, source)
    return save_profile_version(profile)


def upload_master_cv(filename: str, content: bytes) -> dict[str, Any]:
    if not filename.casefold().endswith(".pdf") or not content.startswith(b"%PDF-"):
        raise ValueError("Upload a readable PDF master CV.")
    if not content or len(content) > 15 * 1024 * 1024:
        raise ValueError("The master CV must be under 15 MB.")
    INPUTS_DIR.mkdir(parents=True, exist_ok=True)
    target = INPUTS_DIR / "master_cv.pdf"
    temporary = target.with_suffix(".pdf.part")
    temporary.write_bytes(content)
    temporary.replace(target)
    profile, extracted_text = _pdf_layout_profile(target, "inputs/master_cv.pdf")
    if profile is None:
        if len(extracted_text.strip()) < 40:
            raise ValueError("This PDF has no readable text. Paste its text into the resume field, or use a text-based PDF.")
        profile = profile_from_text(extracted_text, "inputs/master_cv.pdf")
    return {**save_profile_version(profile), "resume_text": extracted_text}


def _fact_records(profile: dict[str, Any]) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for item in profile.get("summary", []) + profile.get("certifications", []) + profile.get("languages", []):
        records[item["id"]] = item
    for group in ("experience", "projects"):
        for entry in profile.get(group, []):
            for item in entry.get("bullets", []):
                records[item["id"]] = item
    return records


def apply_profile_fixes(changes: dict[str, Any]) -> dict[str, Any]:
    profile = load_profile()
    if not profile:
        raise ValueError("Upload a master CV or save resume text before editing profile facts.")
    facts = _fact_records(profile)
    entries = {entry["id"]: entry for key in ("skills", "experience", "projects", "education") for entry in profile.get(key, [])}
    changed: list[str] = []
    new_ids: list[str] = []
    for change in changes.get("set", []):
        identifier = str(change.get("id", ""))
        if identifier in facts and "text" in change:
            facts[identifier]["text"] = str(change["text"]).strip()
        elif identifier == "header" and change.get("field") in {"name", "headline", "contact"}:
            value = change.get("value", "")
            profile["header"][change["field"]] = [part.strip() for part in value.split("|") if part.strip()] if change.get("field") == "contact" and isinstance(value, str) else value
        elif identifier in entries and change.get("field") in EDITABLE_FIELDS:
            entries[identifier][change["field"]] = change.get("value", "")
        else:
            raise ValueError(f"Cannot update {identifier}: use a fact text, header field, or editable entry field.")
        changed.append(identifier)
    for identifier in changes.get("remove", []):
        identifier = str(identifier)
        found = identifier in facts
        for key in ("summary", "certifications", "languages"):
            before = len(profile.get(key, []))
            profile[key] = [item for item in profile.get(key, []) if item.get("id") != identifier]
            found = found or before != len(profile[key])
        for key in ("experience", "projects"):
            for entry in profile.get(key, []):
                before = len(entry.get("bullets", []))
                entry["bullets"] = [item for item in entry.get("bullets", []) if item.get("id") != identifier]
                found = found or before != len(entry["bullets"])
        for key in ("skills", "experience", "projects", "education"):
            before = len(profile.get(key, []))
            profile[key] = [item for item in profile.get(key, []) if item.get("id") != identifier]
            found = found or before != len(profile[key])
        if not found:
            raise ValueError(f"No fact or profile entry with ID {identifier}.")
        changed.append(identifier)
    current_ids = [int(identifier[1:]) for identifier in facts if re.fullmatch(r"F\d+", identifier)]
    next_id = max(current_ids, default=0) + 1
    for addition in changes.get("add", []):
        target, text = str(addition.get("to", "")), str(addition.get("text", "")).strip()
        if not text:
            raise ValueError("Each added fact needs text.")
        fact = {"id": _fact_id(next_id), "text": text}
        next_id += 1
        if target == "summary":
            profile.setdefault("summary", []).append(fact)
        elif target in entries and "bullets" in entries[target] and any(entry.get("id") == target for group in ("experience", "projects") for entry in profile.get(group, [])):
            entries[target].setdefault("bullets", []).append(fact)
        else:
            raise ValueError("Add a fact to 'summary' or an existing experience/project ID such as E1 or CP1.")
        new_ids.append(fact["id"])
    if not changed and not new_ids:
        raise ValueError("Give at least one set, remove, or add change.")
    profile["edited"] = date.today().isoformat()
    return {**save_profile_version(profile), "changed": changed, "new_ids": new_ids}


def _preference_path() -> Path | None:
    return _latest(ME_DIR, "preferences")


def get_preferences() -> dict[str, Any]:
    path = _preference_path()
    return json.loads(path.read_text(encoding="utf-8")) if path else {"version": 0, **PREFERENCES_DEFAULTS}


def save_preferences(preferences: dict[str, Any]) -> dict[str, Any]:
    import jsonschema

    previous_path = _preference_path()
    previous = json.loads(previous_path.read_text(encoding="utf-8")) if previous_path else {}
    previous.pop("version", None)
    previous.pop("saved", None)
    merged = {**previous, **{key: value for key, value in PREFERENCES_DEFAULTS.items() if key not in previous}, **preferences}
    for key in ("search", "automation"):
        if isinstance(preferences.get(key), dict):
            merged[key] = {**previous.get(key, PREFERENCES_DEFAULTS.get(key, {})), **preferences[key]}
        else:
            merged[key] = {**PREFERENCES_DEFAULTS.get(key, {}), **previous.get(key, {})}
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = sorted(jsonschema.Draft202012Validator(schema).iter_errors(merged), key=lambda error: list(error.path))
    if errors:
        raise ValueError("Preferences are invalid: " + "; ".join(f"{'/'.join(map(str, issue.path)) or '$'}: {issue.message}" for issue in errors[:8]))
    path = _next_version(ME_DIR, "preferences")
    version = int(re.search(r"_v(\d+)", path.name).group(1))
    saved = {"version": version, "saved": date.today().isoformat(), **merged}
    _write_new(path, json.dumps(saved, ensure_ascii=False, indent=2) + "\n")
    return {"file": str(path.relative_to(BACKEND_DIR)).replace("\\", "/"), "preferences": saved}


def _github_get(client: httpx.Client, url: str, delay: float, attempts: int = 4) -> httpx.Response | None:
    wait = max(0.0, delay)
    for _ in range(attempts):
        if wait:
            time.sleep(wait)
        response = client.get(url)
        if response.status_code in (403, 429) and response.headers.get("x-ratelimit-remaining") == "0":
            reset = int(response.headers.get("x-ratelimit-reset", "0")) - int(time.time())
            if reset > 120:
                raise ValueError(f"GitHub API limit reached; retry in about {reset // 60} minutes.")
            wait = max(reset, 5)
            continue
        if response.status_code in (429, 500, 502, 503, 504):
            wait = min(wait * 2 + 1, 30)
            continue
        return response
    return None


def _clean_readme(text: str) -> str:
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"^\s{0,3}#+\s*", "", text, flags=re.M)
    return re.sub(r"[*_`>|]", " ", text)


def fetch_public_github_projects(username: str, max_repos: int = 40, delay_s: float = 1.0) -> dict[str, Any]:
    user = username.strip().removeprefix("https://github.com/").strip("/")
    if not re.fullmatch(r"[A-Za-z0-9-]{1,39}", user):
        raise ValueError("Enter a valid public GitHub username.")
    headers = {"User-Agent": "CareerPilot-local-job-search", "Accept": "application/vnd.github+json"}
    with httpx.Client(headers=headers, timeout=25, follow_redirects=True) as client:
        response = _github_get(client, f"https://api.github.com/users/{user}/repos?per_page=100&type=owner&sort=pushed", 0)
        if response is None or response.status_code != 200:
            raise ValueError(f"Could not list public repositories for {user} (GitHub returned {getattr(response, 'status_code', 'no response')}).")
        repositories = [repo for repo in response.json() if not repo.get("fork")][:max(1, min(max_repos, 40))]
        projects = []
        for repo in repositories:
            name, branch = repo.get("name", ""), repo.get("default_branch") or "main"
            readme = ""
            for readme_name in README_NAMES:
                result = _github_get(client, f"https://raw.githubusercontent.com/{user}/{name}/{branch}/{readme_name}", delay_s)
                if result is not None and result.status_code == 200 and result.text.strip():
                    readme = result.text[:3000]
                    break
            dependencies = ""
            for filename in DEPENDENCY_FILES:
                result = _github_get(client, f"https://raw.githubusercontent.com/{user}/{name}/{branch}/{filename}", delay_s / 2)
                if result is not None and result.status_code == 200:
                    dependencies += result.text[:3000] + "\n"
            clean = _clean_readme(readme)
            paragraphs = [re.sub(r"\s+", " ", part).strip() for part in re.split(r"\n\s*\n", clean)]
            paragraphs = [part for part in paragraphs if len(part) > 40 and not part.lower().startswith(("license", "installation", "install", "usage"))]
            stack: list[str] = []
            for value in [repo.get("language"), *(repo.get("topics") or [])]:
                if value and value not in stack:
                    stack.append(value)
            haystack = f"{readme}\n{dependencies}".casefold()
            for key, technology in TECHNOLOGY_NAMES.items():
                if re.search(rf"(?<![a-z0-9]){re.escape(key)}(?![a-z0-9])", haystack) and technology not in stack:
                    stack.append(technology)
            slug = re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-")[:30] or "project"
            outcomes = []
            for sentence in re.split(r"(?<=[.!?])\s+|\n", re.sub(r"[ \t]+", " ", clean)):
                sentence = sentence.strip(" -•")
                if 20 < len(sentence) < 220 and re.search(r"\d[\d,.]*\s*(?:%|x\b|ms\b|seconds?|minutes?|hours?|tests?\b|users|runs|repos|files|requests|models|agents|documents|accuracy|f1)", sentence, re.I):
                    outcomes.append(sentence)
                if len(outcomes) == 6:
                    break
            projects.append({
                "id": f"PRJ-{slug}", "name": name, "summary": (repo.get("description") or (paragraphs[0] if paragraphs else ""))[:300],
                "stack": stack[:14], "what_was_built": " ".join(paragraphs[:2])[:700], "outcomes": outcomes,
                "link": f"github.com/{user}/{name}", "tags": [tag for tag in [repo.get("language"), *(repo.get("topics") or [])] if tag],
                "updated": (repo.get("pushed_at") or "")[:10], "stars": repo.get("stargazers_count", 0), "has_readme": bool(readme),
            })
    path = _next_version(ME_DIR, "projects")
    _write_new(path, json.dumps({"version": int(re.search(r"_v(\d+)", path.name).group(1)), "user": user, "fetched": date.today().isoformat(), "projects": projects}, ensure_ascii=False, indent=2) + "\n")
    return {"file": str(path.relative_to(BACKEND_DIR)).replace("\\", "/"), "username": user, "repos": len(projects), "projects": projects}


def load_github_projects() -> dict[str, Any] | None:
    path = _latest(ME_DIR, "projects")
    return json.loads(path.read_text(encoding="utf-8")) if path else None
