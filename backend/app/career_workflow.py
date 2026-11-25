"""Sequential orchestration for the consolidated CareerPilot assistant."""

from __future__ import annotations

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
from typing import Any

from app.agents.career_storage import create_document_pdf
from app.agents.cover_letter_agent import generate_cover_letter
from app.agents.job_hunter import search_jobs
from app.agents.job_matcher import SKILL_ALIASES, contains_skill, match_job
from app.agents.project_intelligence import CANDIDATE_PROFILE as PROJECT_CANDIDATE_PROFILE
from app.agents.remote_job_hunter import search_remote_jobs
from app.agents.resume_agent import create_resume_package


STAGES = [
    (1, "Job Hunter"),
    (2, "Job Matcher"),
    (3, "Resume Agent"),
    (4, "Cover Letter Agent"),
]

EARLY_CAREER_TERMS = (
    "intern", "internship", "working student", "werkstudent", "student",
    "praktikum", "praktikant", "graduate", "trainee", "junior", "entry-level",
)


def _candidate_profile(request: dict[str, Any]) -> dict[str, Any]:
    resume = str(request.get("resume_text", "") or "").strip()
    skills_text = str(request.get("skills", "") or "").strip()
    education = str(request.get("education", "") or "").strip()
    experience = str(request.get("experience", "") or "").strip()
    university = str(request.get("university", "") or "").strip()
    projects_text = str(request.get("projects", "") or "").strip()
    certifications = str(request.get("certifications", "") or "").strip()
    languages = str(request.get("languages", "") or "").strip()
    evidence = "\n".join((resume, skills_text, education, university, experience, projects_text, certifications, languages)).lower()

    skills = [
        skill for skill, aliases in SKILL_ALIASES.items()
        if contains_skill(evidence, aliases)
    ]

    years = 0
    experience_evidence = experience or resume
    match = re.search(r"(\d+)\+?\s+years?", experience_evidence, re.IGNORECASE)
    years = int(match.group(1)) if match else 0

    return {
        "skills": skills,
        "education": "\n".join(part for part in (education, university) if part) or resume,
        "education_provided": "\n".join(part for part in (education, university) if part),
        "experience": experience or resume,
        "experience_provided": experience,
        "experience_years": years,
        "resume_text": resume,
        "projects": [item.strip() for item in re.split(r"[\n;]+", projects_text) if item.strip()] + (
            [project for project in PROJECT_CANDIDATE_PROFILE["projects"] if project.lower() in resume.lower()]
            if resume else []
        ),
        "full_name": str(request.get("full_name", "") or "").strip(),
        "email": str(request.get("email", "") or "").strip(),
        "phone": str(request.get("phone", "") or "").strip(),
        "certifications": certifications,
        "languages": languages,
    }


def _job_text(job: dict[str, Any]) -> str:
    return "\n".join(str(job.get(key, "") or "") for key in ("title", "description", "tags", "job_types", "job_type"))


def _matches_location(job: dict[str, Any], preferred: str) -> bool:
    preferred = (preferred or "Germany").strip().lower()
    if preferred in {"any", "anywhere", "no preference"}:
        return True

    location = str(job.get("location", "") or "").lower()
    text = f"{location} {_job_text(job)}".lower()
    if preferred in {"remote", "remote only"}:
        return bool(job.get("remote")) or "remote" in text
    if preferred in {"germany", "deutschland"}:
        return bool(job.get("remote")) or any(term in text for term in (
            "germany", "deutschland", "berlin", "potsdam", "munich", "münchen",
            "hamburg", "frankfurt", "cologne", "köln", "stuttgart", "düsseldorf",
            "dresden", "leipzig",
        ))
    return preferred in location or bool(job.get("remote"))


def _matches_job_type(job: dict[str, Any], requested_type: str) -> bool:
    requested_type = (requested_type or "internship").strip().lower()
    if requested_type in {"any", "any type", "no preference"}:
        return True
    searchable = _job_text(job).lower()
    aliases = {
        "internship": EARLY_CAREER_TERMS[:7],
        "working student": ("working student", "werkstudent", "student"),
        "junior": ("junior", "entry-level", "graduate", "trainee"),
        "full-time": ("full-time", "full time"),
        "part-time": ("part-time", "part time"),
        "contract": ("contract", "freelance"),
    }.get(requested_type, (requested_type,))
    return any(term in searchable for term in aliases)


def _is_suitable(job: dict[str, Any], match: dict[str, Any], requested_type: str) -> bool:
    # This is the single acceptance rule used throughout the Job Desk.
    return float(match.get("match_score", 0) or 0) >= 80


def _rejection_reasons(job: dict[str, Any], match: dict[str, Any], requested_type: str) -> list[str]:
    reasons: list[str] = []
    score = match.get("match_score", 0)
    if float(score or 0) < 80:
        reasons.append(f"Match score ({score}%) is below the required 80% acceptance threshold.")
    return reasons or ["The listing did not pass the required 80% match threshold."]


def _emit(agent_id: int, status: str, message: str, **extra: Any) -> dict[str, Any]:
    agent_name = dict(STAGES).get(agent_id, "CareerPilot")
    return {
        "type": "progress",
        "agent_id": agent_id,
        "agent": agent_name,
        "status": status,
        "message": message,
        **extra,
    }


def career_workflow_events(request: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """Yield live progress events followed by one consolidated result event."""
    stages: dict[str, dict[str, Any]] = {
        name: {"agent_id": agent_id, "status": "queued", "message": "Waiting"}
        for agent_id, name in STAGES
    }
    errors: list[dict[str, str]] = []
    keywords = str(request.get("keyword", "AI/ML") or "AI/ML").strip()
    preferred_location = str(request.get("preferred_location", "Germany") or "Germany")
    requested_type = str(request.get("job_type", "internship") or "internship")
    limit = max(1, min(int(request.get("limit", 3) or 3), 10))
    candidate = _candidate_profile(request)

    def status(agent_id: int, state: str, message: str, **extra: Any):
        name = dict(STAGES)[agent_id]
        stages[name] = {"agent_id": agent_id, "status": state, "message": message}
        return _emit(agent_id, state, message, **extra)

    # STEP 1: Use listings already returned by the Job Hunter when supplied;
    # otherwise search the configured providers as part of this same run.
    yield status(1, "working", "Passing Job Hunter listings to the team" if request.get("jobs") else "Searching configured job sources")
    provider_results = []
    source_errors: dict[str, str] = {}
    jobs: list[dict[str, Any]] = []
    supplied_jobs = [job for job in request.get("jobs", []) if isinstance(job, dict)]
    if supplied_jobs:
        jobs.extend(supplied_jobs[:limit])
        provider_results.append(("Job Hunter", {"jobs": jobs}))
    else:
        for source_name, provider in (("Arbeitnow", search_jobs), ("Remotive", search_remote_jobs)):
            try:
                result = provider(
                    keyword=keywords,
                    limit=min(limit * 4, 40),
                    **({"preferred_location": preferred_location} if source_name == "Arbeitnow" else {}),
                )
                provider_results.append((source_name, result))
                if result.get("error"):
                    source_errors[source_name] = str(result["error"])
                jobs.extend(result.get("jobs", []) or [])
            except Exception as error:  # keep the independent source alive
                source_errors[source_name] = str(error)

    unique_jobs: list[dict[str, Any]] = []
    seen: set[str] = set()
    for job in jobs:
        if not isinstance(job, dict) or not job.get("title") or not job.get("url"):
            continue
        url = str(job["url"]).strip()
        if url in seen or (not supplied_jobs and (not _matches_location(job, preferred_location) or not _matches_job_type(job, requested_type))):
            continue
        seen.add(url)
        unique_jobs.append(job)

    if not unique_jobs and len(source_errors) == 2:
        yield status(1, "failed", "Job sources could not be reached", source_errors=source_errors)
        errors.append({"agent": "Job Hunter", "message": "Both job sources failed. Check the source errors."})
    else:
        message = f"Found {len(unique_jobs)} listings matching your preferences"
        if source_errors:
            message += "; at least one source was unavailable"
        yield status(1, "completed", message, job_count=len(unique_jobs), source_errors=source_errors)

    # Backwards compatibility: callers of the original workflow may provide one
    # target description. Include it as a supplied listing without inventing a URL.
    supplied_description = str(request.get("job_description", "") or "").strip()
    if supplied_description:
        supplied_job = {
            "title": str(request.get("role", "Target role") or "Target role"),
            "company": str(request.get("company", "Company not specified") or "Company not specified"),
            "location": preferred_location,
            "description": supplied_description,
            "url": str(request.get("job_url", "") or ""),
            "source": "User supplied job description",
        }
        if not any(job.get("url") == supplied_job["url"] and supplied_job["url"] for job in unique_jobs):
            unique_jobs.insert(0, supplied_job)

    # STEP 2: Match every listing against the submitted resume/profile.
    yield status(2, "working", f"Matching {len(unique_jobs)} listings against your profile")
    matched_jobs: list[dict[str, Any]] = []
    for job in unique_jobs:
        try:
            match = match_job(_job_text(job), str(job.get("title", "")), candidate)
            record = {**job, "match": match}
            record["match_score"] = match.get("match_score", 0)
            record["recommendation"] = match.get("recommendation", "")
            matched_jobs.append(record)
        except Exception as error:
            errors.append({"agent": "Job Matcher", "message": f"{job.get('title', 'Listing')}: {error}"})

    matched_jobs.sort(key=lambda item: item.get("match_score", 0), reverse=True)
    for job in matched_jobs:
        job["suitable"] = _is_suitable(job, job["match"], requested_type)
        job["rejection_reasons"] = [] if job["suitable"] else _rejection_reasons(job, job["match"], requested_type)
    suitable_jobs = [job for job in matched_jobs if job["suitable"]]
    yield status(2, "completed", f"Selected {len(suitable_jobs)} suitable listing(s)", selected_count=len(suitable_jobs))

    # The Hunter is the only trigger. The Matcher passes accepted listings to both
    # document agents, which work concurrently from the same verified source CV.
    selected: list[dict[str, Any]] = [
        {"job": job, "match": job["match"]} for job in suitable_jobs
    ]
    if not suitable_jobs:
        for agent_id in (3, 4):
            yield status(agent_id, "skipped", "No job reached the 80% match threshold")

    if suitable_jobs:
        yield status(3, "working", f"Tailoring resumes for {len(suitable_jobs)} selected job(s)")
        yield status(4, "working", f"Writing cover letters for {len(suitable_jobs)} selected job(s)")
        failures = {"resume": 0, "cover_letter": 0}

        def make_resume(item: dict[str, Any]) -> dict[str, Any]:
            job = item["job"]
            return create_resume_package(
                job_description=_job_text(job), resume_text=candidate["resume_text"],
                candidate_skills=candidate["skills"], candidate_education=candidate["education_provided"],
                candidate_experience=candidate["experience_provided"], candidate_projects="\n".join(candidate["projects"]),
                candidate_name=candidate["full_name"], candidate_email=candidate["email"], candidate_phone=candidate["phone"],
                candidate_certifications=candidate["certifications"], candidate_languages=candidate["languages"],
                job_title=str(job.get("title", "")), company=str(job.get("company", "")),
            )

        def make_cover_letter(item: dict[str, Any]) -> str:
            job = item["job"]
            return generate_cover_letter(
                _job_text(job), str(job.get("company", "Company not specified")),
                str(job.get("title", "Role not specified")), candidate["resume_text"],
                candidate_name=candidate["full_name"],
            )

        tasks = {}
        with ThreadPoolExecutor(max_workers=min(8, max(2, len(selected) * 2))) as pool:
            for item in selected:
                tasks[pool.submit(make_resume, item)] = ("resume", item)
                tasks[pool.submit(make_cover_letter, item)] = ("cover_letter", item)
            for future in as_completed(tasks):
                task, item = tasks[future]
                job = item["job"]
                try:
                    output = future.result()
                    if task == "resume":
                        item["resume"] = output["tailored_resume"]
                        item["resume_analysis"] = {key: value for key, value in output.items() if key != "tailored_resume"}
                    else:
                        item["cover_letter"] = output
                except Exception as error:
                    failures[task] += 1
                    agent_name = "Resume Agent" if task == "resume" else "Cover Letter Agent"
                    item.setdefault("errors", []).append(f"{agent_name}: {error}")
                    errors.append({"agent": agent_name, "message": f"{job.get('company')} ? {job.get('title')}: {error}"})

        for agent_id, task, label in ((3, "resume", "Resume Agent"), (4, "cover_letter", "Cover Letter Agent")):
            count = failures[task]
            yield status(agent_id, "failed" if count else "completed",
                         f"{label} failed for {count} job(s)" if count else f"{label} finished",
                         failed_count=count)

    # Save actual, paginated PDFs locally only for accepted jobs with both
    # generated documents. Their opaque IDs are the only download handles sent
    # to the frontend.
    pdf_failures = 0
    for item in selected:
        job = item["job"]
        for key, content, kind in (
            ("resume_document", item.get("resume"), "resume"),
            ("cover_letter_document", item.get("cover_letter"), "cover_letter"),
        ):
            if not content:
                continue
            try:
                item[key] = create_document_pdf(content, str(job.get("title", "Role")), str(job.get("company", "Company")), kind)
            except Exception as error:
                pdf_failures += 1
                item.setdefault("errors", []).append(f"PDF generation: {error}")
                errors.append({"agent": "Document Generator", "message": f"{job.get('company')} ? {job.get('title')}: {error}"})
    if pdf_failures:
        stages["Resume Agent"]["message"] += f"; PDF output failed for {pdf_failures} document(s)"

    result = {
        "agent": "CareerPilot AI Career Assistant",
        "keyword": keywords,
        "preferences": {
            "location": preferred_location,
            "job_type": requested_type,
            "limit": limit,
        },
        "candidate_profile": {
            "skills": candidate["skills"],
            "education": candidate["education"],
            "experience_years": candidate["experience_years"],
        },
        "jobs_found": matched_jobs,
        "selected_jobs": selected,
        "source_summary": {
            name: len(result.get("jobs", []) or [])
            for name, result in provider_results
        },
        "source_errors": source_errors,
        "stages": stages,
        "errors": errors,
        "summary": {
            "jobs_found": len(matched_jobs),
            "jobs_evaluated": len(matched_jobs),
            "selected_jobs": len(selected),
            "suitable_jobs": len(selected),
            "unsuitable_jobs": len([job for job in matched_jobs if not job["suitable"]]),
            "documents_completed": sum(1 for item in selected if item.get("resume") and item.get("cover_letter")),
            "pdfs_generated": sum(int(bool(item.get("resume_document"))) + int(bool(item.get("cover_letter_document"))) for item in selected),
            "failed_tasks": sum(1 for stage in stages.values() if stage["status"] == "failed"),
            "skipped_tasks": sum(1 for stage in stages.values() if stage["status"] == "skipped"),
        },
    }
    yield {"type": "result", "data": result}


def run_career_workflow(request: dict[str, Any]) -> dict[str, Any]:
    """Synchronous compatibility wrapper for existing JSON API clients."""
    final_result: dict[str, Any] | None = None
    for event in career_workflow_events(request):
        if event.get("type") == "result":
            final_result = event["data"]
    return final_result or {"errors": [{"agent": "CareerPilot", "message": "Workflow did not return a result."}]}
