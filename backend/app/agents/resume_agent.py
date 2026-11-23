"""Source-grounded resume tailoring for one target job at a time.

This agent intentionally uses conservative, deterministic edits: it ranks and
reformats supplied facts, but never generates candidate claims from a job ad.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from app.agents.job_matcher import SKILL_ALIASES, contains_skill


SECTION_TYPES: dict[str, tuple[str, ...]] = {
    "summary": ("summary", "professional summary", "profile", "about me", "career objective", "objective"),
    "skills": ("skills", "technical skills", "technical expertise", "core competencies", "technologies", "tools and technologies"),
    "projects": ("projects", "selected projects", "academic projects", "personal projects", "project experience"),
    "experience": ("experience", "work experience", "professional experience", "employment", "employment history", "internships"),
    "education": ("education", "academic background", "qualifications"),
    "certifications": ("certifications", "certificates", "licenses"),
}

SECTION_PRIORITY = {"summary": 0, "skills": 1, "projects": 2, "experience": 3, "education": 4, "certifications": 5}


def _skill_hits(text: str) -> list[str]:
    return [skill for skill, aliases in SKILL_ALIASES.items() if contains_skill(text, aliases)]


def _ranked_requirements(job_description: str) -> list[str]:
    requirements = _skill_hits(job_description)
    lower = job_description.casefold()
    first_position: dict[str, int] = {}
    for skill in requirements:
        aliases = SKILL_ALIASES.get(skill, [skill])
        positions = [lower.find(alias.casefold()) for alias in aliases if alias.casefold() in lower]
        first_position[skill] = min(positions, default=len(lower))
    return sorted(requirements, key=lambda skill: (lower.count(skill.casefold()), -first_position[skill]), reverse=True)


def _classify_section(line: str) -> str | None:
    candidate = re.sub(r"^\s{0,3}#{1,6}\s*|\*", "", line).strip().rstrip(":").casefold()
    for section, labels in SECTION_TYPES.items():
        if candidate in labels:
            return section
    return None


def _split_resume(resume_text: str) -> tuple[str, list[dict[str, str]]]:
    """Split familiar headings while retaining every original content line."""
    preamble: list[str] = []
    sections: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in resume_text.splitlines():
        kind = _classify_section(line)
        if kind:
            current = {"kind": kind, "heading": line.strip().lstrip("# ").strip(), "body": ""}
            sections.append(current)
        elif current is None:
            preamble.append(line)
        else:
            current["body"] += line + "\n"
    return "\n".join(preamble).strip(), sections


def _required_sentences(job_description: str, patterns: tuple[str, ...], limit: int = 8) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+|\n+", job_description)
    result: list[str] = []
    seen: set[str] = set()
    for sentence in sentences:
        clean = re.sub(r"^\s*(?:[-*•▪]|\d+[.)])\s*", "", sentence).strip()
        normalized = clean.casefold()
        if clean and len(clean) > 16 and any(pattern in normalized for pattern in patterns) and normalized not in seen:
            result.append(clean[:320])
            seen.add(normalized)
        if len(result) == limit:
            break
    return result


def _order_skill_lines(body: str, required: list[str]) -> str:
    """Reorder plain skill-list entries by relevance; preserve all their text."""
    lines = body.splitlines()
    nonempty = [line for line in lines if line.strip()]
    if len(nonempty) == 1 and any(delimiter in nonempty[0] for delimiter in (",", ";", "|")):
        entries = [part.strip() for part in re.split(r"[,;|]", nonempty[0]) if part.strip()]
        if entries and not any("." in entry for entry in entries):
            def score(entry: str) -> int:
                return sum(1 for skill in required if contains_skill(entry, SKILL_ALIASES.get(skill, [skill])))
            return ", ".join(sorted(entries, key=score, reverse=True)) + "\n"
    # For categorized or prose lists, move only existing lines as intact units.
    if len(nonempty) > 1:
        return "\n".join(sorted(nonempty, key=lambda line: sum(1 for skill in required if contains_skill(line, SKILL_ALIASES.get(skill, [skill]))), reverse=True)) + "\n"
    return body


def _order_bullet_runs(body: str, required: list[str]) -> str:
    """Prioritize existing experience bullets without rewriting their claims."""
    lines = body.splitlines()
    output: list[str] = []
    run: list[str] = []

    def flush() -> None:
        if run:
            run.sort(key=lambda line: sum(1 for skill in required if contains_skill(line, SKILL_ALIASES.get(skill, [skill]))), reverse=True)
            output.extend(run)
            run.clear()

    for line in lines:
        if re.match(r"^\s*(?:[-*•▪]|\d+[.)])\s+", line):
            content = re.sub(r"^\s*(?:[-*•▪]|\d+[.)])\s+", "", line).strip()
            # First-person subjects are redundant in resume bullets. Removing
            # them changes style only; the candidate's action and claim remain.
            content = re.sub(r"^(?:I|We)\s+", "", content, flags=re.IGNORECASE)
            run.append("- " + content)
        else:
            flush()
            output.append(line)
    flush()
    return "\n".join(output)


def _project_score(body: str, required: list[str]) -> int:
    return sum(1 for skill in required if contains_skill(body, SKILL_ALIASES.get(skill, [skill])))


def _reorder_projects(body: str, required: list[str]) -> str:
    # Recognize project entries separated by blank lines; do not split a single
    # continuous bullet list, which may be one project's technical details.
    blocks = re.split(r"\n\s*\n", body.strip()) if body.strip() else []
    if len(blocks) < 2:
        return body
    ordered = sorted(enumerate(blocks), key=lambda pair: (_project_score(pair[1], required), -pair[0]), reverse=True)
    return "\n\n".join(block for _, block in ordered) + "\n"


def _verified_skills(resume_text: str, candidate_skills: Iterable[str]) -> list[str]:
    supplied = [str(skill).strip() for skill in candidate_skills if str(skill).strip()]
    detected = _skill_hits(resume_text + "\n" + "\n".join(supplied))
    combined = [*detected, *supplied]
    unique: list[str] = []
    seen: set[str] = set()
    for skill in combined:
        key = skill.casefold()
        if key not in seen:
            unique.append(skill)
            seen.add(key)
    return unique


def _requirement_evidence(requirements: list[str], evidence_text: str, kind: str) -> list[dict[str, Any]]:
    evidence_lines = [line.strip(" \t-*•▪") for line in evidence_text.splitlines() if line.strip(" \t-*•▪")]
    checks: list[dict[str, Any]] = []
    for requirement in requirements:
        related_skills = [skill for skill in _skill_hits(requirement) if skill in _skill_hits(evidence_text)]
        if kind == "qualification":
            degree_aliases = {
                "bachelor": ("bachelor", "bsc", "b.sc"),
                "master": ("master", "msc", "m.sc"),
                "phd": ("phd", "ph.d", "doctorate"),
            }
            required_degrees = [degree for degree, aliases in degree_aliases.items() if any(alias in requirement.casefold() for alias in aliases)]
            present_degrees = [degree for degree, aliases in degree_aliases.items() if any(alias in evidence_text.casefold() for alias in aliases)]
            years_match = re.search(r"(\d+)\+?\s+years?", requirement, re.IGNORECASE)
            years_candidate = [int(value) for value in re.findall(r"(\d+)\+?\s+years?", evidence_text, re.IGNORECASE)]
            if required_degrees:
                supported = bool(set(required_degrees).intersection(present_degrees))
            elif years_match:
                supported = bool(years_candidate and max(years_candidate) >= int(years_match.group(1)))
            else:
                key_terms = [word for word in re.findall(r"[a-zA-Z]{4,}", requirement.casefold()) if word not in {"currently", "enrolled", "related", "field", "degree", "required", "preferred", "qualification", "qualifications", "years", "experience", "with"}]
                supported = bool(key_terms and sum(term in evidence_text.casefold() for term in key_terms) >= max(1, (len(key_terms) + 1) // 2))
            checks.append({"requirement": requirement, "status": "supported_by_profile" if supported else "needs_candidate_verification", "candidate_evidence": []})
            continue

        scored: list[tuple[int, str]] = []
        req_tokens = {token for token in re.findall(r"[a-zA-Z]{3,}", requirement.casefold()) if token not in {"the", "and", "for", "with", "from", "you", "will", "your", "into", "this", "that", "their", "work", "role"}}
        for line in evidence_lines:
            shared_skills = [skill for skill in related_skills if contains_skill(line, SKILL_ALIASES.get(skill, [skill]))]
            line_tokens = set(re.findall(r"[a-zA-Z]{3,}", line.casefold()))
            overlap = len(req_tokens & line_tokens)
            if shared_skills or (req_tokens and overlap / len(req_tokens) >= 0.25):
                scored.append((len(shared_skills) * 10 + overlap, line))
        selected_evidence = [line for _, line in sorted(scored, reverse=True)[:2]]
        checks.append({
            "requirement": requirement,
            "status": "related_candidate_evidence" if selected_evidence else "needs_candidate_verification",
            "candidate_evidence": selected_evidence,
        })
    return checks


def _summary(job_title: str, company: str, source_summary: str, matched: list[str], education: str, experience: str) -> str:
    target = f"Targeting {job_title or 'the selected role'}"
    if company:
        target += f" at {company}"
    clauses = [target + "."]
    if matched:
        clauses.append("Verified role-relevant skills: " + ", ".join(matched[:8]) + ".")
    evidence = source_summary.strip()
    if evidence:
        # Preserve the candidate's own claims and prioritize the most relevant
        # sentences; never add unsupported wording to an existing summary.
        sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", evidence) if part.strip()]
        sentences.sort(key=lambda sentence: sum(1 for skill in matched if contains_skill(sentence, SKILL_ALIASES.get(skill, [skill]))), reverse=True)
        clauses.extend(sentences)
    elif matched:
        clauses.append("Candidate-provided materials confirm skills in " + ", ".join(matched[:8]) + ".")
    if education.strip() and not evidence:
        clauses.append("Candidate-provided education: " + education.strip().rstrip(".") + ".")
    if experience.strip() and not evidence:
        clauses.append("Candidate-provided experience: " + experience.strip().rstrip(".") + ".")
    if len(clauses) == 1:
        clauses.append("See the supplied experience, project, education, and skills sections for verified background.")
    return " ".join(clauses)


def create_resume_package(
    job_description: str,
    resume_text: str = "",
    candidate_skills: list[str] | None = None,
    candidate_education: str = "",
    candidate_experience: str = "",
    candidate_projects: str = "",
    candidate_name: str = "",
    candidate_email: str = "",
    candidate_phone: str = "",
    candidate_certifications: str = "",
    candidate_languages: str = "",
    job_title: str = "",
    company: str = "",
) -> dict[str, Any]:
    """Create a tailored document plus explicit evidence and gap analysis."""
    source = resume_text.strip()
    if not source and not (candidate_skills or candidate_education or candidate_experience or candidate_projects):
        raise ValueError("Resume Agent needs candidate-provided resume text or profile details; no sample profile is substituted.")

    requirements = _ranked_requirements(job_description)
    evidence_text = "\n".join(part for part in (source, " ".join(candidate_skills or []), candidate_education, candidate_experience, candidate_projects) if part)
    verified = _verified_skills(evidence_text, [])
    # Explicit skill fields are evidence supplied by the candidate. Keep their
    # wording, while recognized aliases use the canonical skill label.
    verified.extend(skill for skill in (candidate_skills or []) if skill.strip() and skill.casefold() not in {item.casefold() for item in verified})
    verified_lower = {skill.casefold() for skill in verified}
    matched = [skill for skill in requirements if skill.casefold() in verified_lower]
    missing = [skill for skill in requirements if skill.casefold() not in verified_lower]

    preamble, sections = _split_resume(source)
    summary_section = next((section for section in sections if section["kind"] == "summary"), None)
    source_summary = summary_section["body"].strip() if summary_section else ""
    summary = _summary(job_title, company, source_summary, matched, candidate_education, candidate_experience)

    skill_section = next((section for section in sections if section["kind"] == "skills"), None)
    original_skill_content = skill_section["body"] if skill_section else ""
    if not original_skill_content and verified:
        original_skill_content = ", ".join(verified) + "\n"
    skill_section_text = _order_skill_lines(original_skill_content, requirements).strip()

    # Keep every source section and line; improve only safe ordering and common
    # bullet glyphs. Put job-relevant projects and experience near the top.
    retained: list[tuple[int, int, str]] = []
    for index, section in enumerate(sections):
        if section["kind"] in {"summary", "skills"}:
            continue
        body = section["body"]
        if section["kind"] == "projects":
            body = _reorder_projects(body, requirements)
        elif section["kind"] == "experience":
            body = _order_bullet_runs(body, requirements)
        priority = SECTION_PRIORITY.get(section["kind"], 6)
        # Keep multiple sections of the same type in their original order.
        retained.append((priority, index, f"{section['heading'].upper()}\n{body.strip()}".rstrip()))
    retained.sort(key=lambda part: (part[0], part[1]))

    document: list[str] = []
    contact_lines = [candidate_name.strip(), candidate_email.strip(), candidate_phone.strip()]
    contact_lines = [line for line in contact_lines if line and line.casefold() not in source.casefold()]
    if preamble:
        document.append("\n".join([*contact_lines, preamble]).strip())
    elif contact_lines:
        document.append("\n".join(contact_lines))
    document.extend(("PROFESSIONAL SUMMARY\n" + summary, "TECHNICAL SKILLS\n" + skill_section_text if skill_section_text else "TECHNICAL SKILLS\nNo skills were supplied."))
    document.extend(part[2] for part in retained)
    if candidate_projects.strip():
        project_entries = [line.strip() for line in candidate_projects.splitlines() if line.strip() and line.strip().casefold() not in source.casefold()]
        project_entries.sort(key=lambda line: _project_score(line, requirements), reverse=True)
        if project_entries:
            document.append("ADDITIONAL CANDIDATE-PROVIDED PROJECTS\n" + "\n".join(f"- {line}" for line in project_entries))
    if candidate_education.strip() and candidate_education.casefold() not in source.casefold():
        document.append("EDUCATION\n" + candidate_education.strip())
    if candidate_experience.strip() and candidate_experience.casefold() not in source.casefold():
        document.append("ADDITIONAL CANDIDATE-PROVIDED EXPERIENCE\n" + candidate_experience.strip())
    if candidate_certifications.strip() and candidate_certifications.casefold() not in source.casefold():
        document.append("ADDITIONAL CANDIDATE-PROVIDED CERTIFICATIONS\n" + candidate_certifications.strip())
    if candidate_languages.strip() and candidate_languages.casefold() not in source.casefold():
        document.append("LANGUAGES\n" + candidate_languages.strip())

    qualifications = _required_sentences(job_description, ("required", "qualification", "degree", "bachelor", "master", "phd", "enrolled", "years of", "experience with", "preferred"))
    responsibilities = _required_sentences(job_description, ("responsibilit", "you will", "you'll", "build", "develop", "design", "implement", "analy", "research", "support", "collaborat", "maintain", "evaluate"))
    qualification_analysis = _requirement_evidence(qualifications, evidence_text, "qualification")
    responsibility_analysis = _requirement_evidence(responsibilities, evidence_text, "responsibility")

    verification: list[str] = []
    if not re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", source, re.IGNORECASE):
        verification.append("Confirm whether you want to add an email address.")
    if not re.search(r"(?:\+?\d[\d ()-]{7,}\d)", source):
        verification.append("Confirm whether you want to add a phone number.")
    if any(section["kind"] == "experience" for section in sections) and not re.search(r"\b(?:19|20)\d{2}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}\b", next((s["body"] for s in sections if s["kind"] == "experience"), ""), re.IGNORECASE):
        verification.append("Verify employment dates; none were detected in the supplied experience section.")
    if not any(section["kind"] == "education" for section in sections) and not candidate_education.strip():
        verification.append("Confirm education details and dates if they should appear on this resume.")
    if not any(section["kind"] == "certifications" for section in sections):
        verification.append("Confirm whether you have certifications to include; none were supplied.")
    verification.extend(
        "Verify this job qualification against your actual background: " + item["requirement"]
        for item in qualification_analysis if item["status"] == "needs_candidate_verification"
    )
    verification.extend(
        "Review whether your experience supports this responsibility: " + item["requirement"]
        for item in responsibility_analysis if item["status"] == "needs_candidate_verification"
    )

    changes = [
        "Added a role- and company-specific summary grounded only in the supplied candidate information.",
        "Moved technical skills and project/experience sections ahead of less relevant sections and prioritized job-related content where detectable.",
        "Preserved original resume facts, dates, and metrics; normalized existing bullets to ATS-style hyphens and prioritized job-relevant experience without adding achievements.",
    ]
    if not source_summary:
        changes.append("Created a concise target-specific summary because the source resume had no recognized summary section.")
    return {
        "tailored_resume": "\n\n".join(part for part in document if part.strip()),
        "target_job": {"title": job_title or "Not specified", "company": company or "Not specified"},
        "relevant_skills_matched": matched,
        "missing_skills": missing,
        "requirements_analyzed": {
            "required_skills": requirements,
            "qualifications": qualification_analysis,
            "responsibilities": responsibility_analysis,
        },
        "changes_made": changes,
        "information_needing_candidate_verification": verification,
    }


def tailor_resume(
    job_description: str,
    resume_text: str = "",
    candidate_skills: list[str] | None = None,
    candidate_education: str = "",
    candidate_experience: str = "",
    candidate_projects: str = "",
    candidate_name: str = "",
    candidate_email: str = "",
    candidate_phone: str = "",
    candidate_certifications: str = "",
    candidate_languages: str = "",
    job_title: str = "",
    company: str = "",
) -> str:
    """Backward-compatible text-only interface used by existing callers."""
    return create_resume_package(
        job_description=job_description,
        resume_text=resume_text,
        candidate_skills=candidate_skills,
        candidate_education=candidate_education,
        candidate_experience=candidate_experience,
        candidate_projects=candidate_projects,
        candidate_name=candidate_name,
        candidate_email=candidate_email,
        candidate_phone=candidate_phone,
        candidate_certifications=candidate_certifications,
        candidate_languages=candidate_languages,
        job_title=job_title,
        company=company,
    )["tailored_resume"]
