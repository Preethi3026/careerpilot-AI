"""Sequential orchestration for the consolidated CareerPilot assistant."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from app.agents.application_manager import get_applications, get_application_stats
from app.agents.application_reviewer import review_application
from app.agents.company_researcher import research_company
from app.agents.cover_letter_agent import generate_cover_letter
from app.agents.job_hunter import search_jobs
from app.agents.job_matcher import SKILL_ALIASES, contains_skill, match_job
from app.agents.project_intelligence import CANDIDATE_PROFILE as PROJECT_CANDIDATE_PROFILE, recommend_projects
from app.agents.remote_job_hunter import search_remote_jobs
from app.agents.resume_agent import create_resume_package


STAGES = [
    (1, "Job Hunter"),
    (2, "Job Matcher"),
    (3, "Resume Agent"),
    (6, "Company Researcher"),
    (4, "Cover Letter"),
    (5, "Application Reviewer"),
    (7, "Application Manager"),
    (8, "Project Intelligence"),
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
    if experience:
        import re
        match = re.search(r"(\d+)\+?\s+years?", experience, re.IGNORECASE)
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
    if match.get("seniority_mismatch") or match.get("match_score", 0) < 50:
        return False
    level = str(match.get("job_level", "")).lower()
    early_career = bool(match.get("internship_suitable")) or level == "junior"
    explicit_early_career = any(term in _job_text(job).lower() for term in EARLY_CAREER_TERMS)
    type_is_early_career = requested_type.lower() in {"internship", "working student", "junior"}
    return early_career or explicit_early_career or not type_is_early_career


def _rejection_reasons(job: dict[str, Any], match: dict[str, Any], requested_type: str) -> list[str]:
    reasons: list[str] = []
    score = match.get("match_score", 0)
    if match.get("seniority_mismatch"):
        reasons.append(f"{match.get('job_level', 'Senior')} seniority does not fit the requested early-career target.")
    if score < 50:
        reasons.append(f"Match score ({score}%) is below the 50% selection threshold.")
    level = str(match.get("job_level", "")).lower()
    early_career = bool(match.get("internship_suitable")) or level == "junior"
    explicit_early_career = any(term in _job_text(job).lower() for term in EARLY_CAREER_TERMS)
    if (requested_type or "internship").strip().lower() in {"internship", "working student", "junior"} and not (early_career or explicit_early_career):
        reasons.append("The listing does not identify itself as an internship, student, junior, or entry-level role.")
    return reasons or ["The listing did not pass the configured suitability checks."]


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

    # STEP 1: Fetch listings once from each configured provider.
    yield status(1, "working", "Searching configured job sources")
    provider_results = []
    source_errors: dict[str, str] = {}
    jobs: list[dict[str, Any]] = []
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
        if url in seen or not _matches_location(job, preferred_location) or not _matches_job_type(job, requested_type):
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
    suitable_jobs = [job for job in matched_jobs if job["suitable"]][:limit]
    yield status(2, "completed", f"Selected {len(suitable_jobs)} suitable listing(s)", selected_count=len(suitable_jobs))

    # Every later agent receives the selected listing, and the document agents
    # receive the actual user's resume plus the output from the previous stage.
    selected: list[dict[str, Any]] = [
        {"job": job, "match": job["match"]} for job in suitable_jobs
    ]
    if not suitable_jobs:
        for agent_id in (3, 6, 4, 5):
            yield status(agent_id, "skipped", "No suitable job was selected")
            stages[dict(STAGES)[agent_id]]["status"] = "skipped"

    # STEP 3: Tailor a separate resume for each selected job.
    if suitable_jobs:
        yield status(3, "working", f"Tailoring resumes for {len(suitable_jobs)} selected job(s)")
        resume_failures = 0
        for item in selected:
            job = item["job"]
            try:
                package = create_resume_package(
                    job_description=_job_text(job),
                    resume_text=candidate["resume_text"],
                    candidate_skills=candidate["skills"],
                    candidate_education=candidate["education_provided"],
                    candidate_experience=candidate["experience_provided"],
                    candidate_projects="\n".join(candidate["projects"]),
                    candidate_name=candidate["full_name"],
                    candidate_email=candidate["email"],
                    candidate_phone=candidate["phone"],
                    candidate_certifications=candidate["certifications"],
                    candidate_languages=candidate["languages"],
                    job_title=str(job.get("title", "")),
                    company=str(job.get("company", "")),
                )
                item["resume"] = package["tailored_resume"]
                item["resume_analysis"] = {
                    key: value for key, value in package.items() if key != "tailored_resume"
                }
            except Exception as error:
                resume_failures += 1
                item["errors"] = [f"Resume Agent: {error}"]
                errors.append({"agent": "Resume Agent", "message": f"{job.get('company')} · {job.get('title')}: {error}"})
        yield status(3, "failed" if resume_failures else "completed",
                     f"Resume tailoring failed for {resume_failures} job(s)" if resume_failures else "Resume tailoring finished",
                     failed_count=resume_failures)

        # STEP 4: Research first so grounded company context is available to
        # the Cover Letter Agent. Never guess a company URL.
        yield status(6, "working", "Collecting verifiable company information")
        research_failures = 0
        for item in selected:
            job = item["job"]
            company_url = str(job.get("company_url", "") or "")
            if not company_url and len(selected) == 1:
                company_url = str(request.get("company_url", "") or "")
            try:
                item["company_research"] = research_company(
                    str(job.get("company", "Company not specified")),
                    str(job.get("title", "Role not specified")),
                    company_url,
                )
            except Exception as error:
                research_failures += 1
                item.setdefault("errors", []).append(f"Company Researcher: {error}")
                errors.append({"agent": "Company Researcher", "message": f"{job.get('company')}: {error}"})
        yield status(6, "failed" if research_failures else "completed",
                     f"Company research failed for {research_failures} job(s)" if research_failures else "Company research finished with source limitations noted",
                     failed_count=research_failures)

        # STEP 5: Cover letters receive the tailored resume and company report.
        cover_letter_jobs = [item for item in selected if item.get("resume")]
        if not cover_letter_jobs:
            yield status(4, "skipped", "No tailored resume was available")
        else:
            yield status(4, "working", "Writing job-specific cover letters using resume and company context")
            cover_letter_failures = 0
            for item in cover_letter_jobs:
                job = item["job"]
                try:
                    item["cover_letter"] = generate_cover_letter(
                        _job_text(job),
                        str(job.get("company", "Company not specified")),
                        str(job.get("title", "Role not specified")),
                        item["resume"],
                        item.get("company_research", ""),
                        candidate["full_name"],
                    )
                except Exception as error:
                    cover_letter_failures += 1
                    item.setdefault("errors", []).append(f"Cover Letter: {error}")
                    errors.append({"agent": "Cover Letter", "message": f"{job.get('company')} · {job.get('title')}: {error}"})
            yield status(4, "failed" if cover_letter_failures else "completed",
                         f"Cover letter generation failed for {cover_letter_failures} job(s)" if cover_letter_failures else "Cover letter generation finished",
                         failed_count=cover_letter_failures)

        # STEP 6: Review the exact tailored documents before delivery.
        review_jobs = [item for item in selected if item.get("resume") and item.get("cover_letter")]
        if not review_jobs:
            yield status(5, "skipped", "No complete resume and cover letter pair was available")
        else:
            yield status(5, "working", "Reviewing tailored documents for fit and consistency")
            review_failures = 0
            for item in review_jobs:
                job = item["job"]
                try:
                    item["review"] = review_application(
                        _job_text(job), item["resume"], item["cover_letter"], item.get("company_research", "")
                    )
                except Exception as error:
                    review_failures += 1
                    item.setdefault("errors", []).append(f"Application Reviewer: {error}")
                    errors.append({"agent": "Application Reviewer", "message": f"{job.get('company')} · {job.get('title')}: {error}"})
            yield status(5, "failed" if review_failures else "completed",
                         f"Document review failed for {review_failures} job(s)" if review_failures else "Document review finished",
                         failed_count=review_failures)

    # STEP 7: Match existing tracking records. Do not mark jobs as applied or
    # write new records until the user explicitly saves an opportunity.
    yield status(7, "working", "Checking the application tracker without changing records")
    try:
        applications = get_applications()
        statistics = get_application_stats()
        for item in selected:
            job = item["job"]
            job_url = str(job.get("url", "") or "")
            existing = next((
                app for app in applications
                if (job_url and app.get("job_url") == job_url)
                or (str(app.get("company", "")).casefold() == str(job.get("company", "")).casefold()
                    and str(app.get("role", "")).casefold() == str(job.get("title", "")).casefold())
            ), None)
            item["tracking"] = {
                "status": "Already tracked" if existing else "Ready to save",
                "application": existing,
                "applied": bool(existing and existing.get("status") not in {"Saved", "Interested"}),
            }
        yield status(7, "completed", "Tracker checked; no records were changed")
    except Exception as error:
        applications = []
        statistics = {}
        errors.append({"agent": "Application Manager", "message": str(error)})
        yield status(7, "failed", "Could not read the application tracker", error=str(error))

    # STEP 8: Recommend portfolio improvements from selected jobs, or from the
    # user's target query when no suitable opportunity was found.
    yield status(8, "working", "Mapping portfolio work to skill gaps")
    project_text = "\n\n".join(_job_text(item["job"]) for item in selected) or keywords
    try:
        project_analysis = recommend_projects(
            project_text,
            candidate_skills=candidate["skills"],
            candidate_projects=candidate["projects"],
        )
        yield status(8, "completed", "Project and skill recommendations are ready")
    except Exception as error:
        project_analysis = None
        errors.append({"agent": "Project Intelligence", "message": str(error)})
        yield status(8, "failed", "Project recommendations could not be generated", error=str(error))

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
        "application_tracking": {
            "statistics": statistics,
            "records": applications,
            "records_changed": False,
        },
        "project_intelligence": project_analysis,
        "stages": stages,
        "errors": errors,
        "summary": {
            "jobs_found": len(matched_jobs),
            "jobs_evaluated": len(matched_jobs),
            "selected_jobs": len(selected),
            "suitable_jobs": len(selected),
            "unsuitable_jobs": len([job for job in matched_jobs if not job["suitable"]]),
            "documents_completed": sum(1 for item in selected if item.get("resume") and item.get("cover_letter")),
            "failed_tasks": sum(1 for stage in stages.values() if stage["status"] == "failed"),
            "skipped_tasks": sum(1 for stage in stages.values() if stage["status"] == "skipped"),
            "applications_saved": 0,
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
