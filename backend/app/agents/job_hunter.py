import re
import html
import requests

from typing import Any


API_URL = "https://www.arbeitnow.com/api/job-board-api"

MAX_PAGES = 10

AI_KEYWORDS = [
    "artificial intelligence",
    "machine learning",
    "deep learning",
    "generative ai",
    "genai",
    "llm",
    "large language model",
    "rag",
    "nlp",
    "computer vision",
    "ai engineer",
    "ml engineer",
    "ai research",
    "machine learning engineer",
]

DATA_KEYWORDS = [
    "data science",
    "data scientist",
    "data engineer",
    "data analyst",
    "business intelligence",
    "data analytics",
    "analytics engineer",
    "big data",
]

AUTOMATION_KEYWORDS = [
    "automation engineer",
    "data automation",
    "process automation",
]

STUDENT_KEYWORDS = [
    "intern",
    "internship",
    "working student",
    "werkstudent",
    "praktikum",
    "praktikant",
    "student",
    "trainee",
    "graduate",
    "junior",
]

SENIOR_KEYWORDS = [
    "senior",
    "lead",
    "principal",
    "director",
    "head of",
    "manager",
]

IRRELEVANT_KEYWORDS = [
    "mechanical engineer",
    "microbiology",
    "biologist",
    "nurse",
    "physician",
    "doctor",
    "sales representative",
    "account executive",
    "customer service",
    "recruiter",
    "marketing manager",
    "graphic designer",
    "civil engineer",
    "electrical engineer",
    "warehouse",
    "construction",
    "finance manager",
]


def clean_html(text: str) -> str:
    """Convert HTML descriptions into readable plain text."""

    if not text:
        return ""

    text = re.sub(
        r"<(script|style).*?>.*?</\1>",
        " ",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def contains_keyword(text: str, keywords: list[str]) -> bool:
    text = text.lower()
    return any(keyword in text for keyword in keywords)

def get_relevance_score(job: dict[str, Any], keyword: str) -> tuple[int, list[str]]:
    """Score jobs based on their actual role and technical relevance."""

    title = job.get("title", "").lower()
    description = clean_html(job.get("description", "")).lower()
    tags = " ".join(job.get("tags", [])).lower()
    job_types = " ".join(job.get("job_types", [])).lower()

    # Exclude unrelated job categories based on their titles.
    excluded_titles = [
        "marketing",
        "sales",
        "customer success",
        "customer service",
        "marketplaces",
        "e-commerce",
        "ecommerce",
        "purchasing",
        "einkauf",
        "operations",
        "kundenbetreuung",
        "content",
        "social media",
        "influencer",
        "mechanical",
        "electronics engineering",
        "uav",
        "business development",
        "recruitment",
        "human resources",
        "finance",
        "accounting",
        "consultant",
        "consulting",
    ]

    if any(word in title for word in excluded_titles):
        return 0, []

    # Relevant technical roles.
    ai_roles = [
        "ai engineer",
        "artificial intelligence",
        "machine learning",
        "ml engineer",
        "ai research",
        "llm",
        "generative ai",
        "genai",
        "deep learning",
        "nlp",
        "computer vision",
    ]

    data_roles = [
        "data scientist",
        "data science",
        "data engineer",
        "data analyst",
        "data analytics",
        "business intelligence",
        "analytics engineer",
    ]

    software_roles = [
        "software engineer",
        "software developer",
        "python developer",
        "backend developer",
        "backend engineer",
    ]

    student_roles = [
        "intern",
        "internship",
        "working student",
        "werkstudent",
        "praktikum",
        "praktikant",
        "junior",
        "graduate",
        "trainee",
    ]

    reasons = []
    score = 0

    is_ai_role = any(word in title for word in ai_roles)
    is_data_role = any(word in title for word in data_roles)
    is_software_role = any(word in title for word in software_roles)

    is_student_role = (
        any(word in title for word in student_roles)
        or any(word in job_types for word in student_roles)
    )

    # Must be an AI, ML, data or software-related position.
    if not (is_ai_role or is_data_role or is_software_role):
        return 0, []

    # Must be suitable for students or early-career applicants.
    if not is_student_role:
        return 0, []

    score += 30
    reasons.append("Student or junior opportunity")

    if is_ai_role:
        score += 50
        reasons.append("AI/ML role")

    if is_data_role:
        score += 40
        reasons.append("Data-related role")

    if is_software_role:
        score += 25
        reasons.append("Software development role")

    # Check whether technical skills appear in the description.
    technical_skills = [
        "python",
        "machine learning",
        "deep learning",
        "tensorflow",
        "pytorch",
        "llm",
        "rag",
        "sql",
        "data science",
        "neural networks",
    ]

    if any(skill in description for skill in technical_skills):
        score += 10
        reasons.append("Relevant technical skills")

    return score, reasons


def is_germany_or_remote(job: dict[str, Any], preferred_location: str = "Germany") -> bool:
    """Keep jobs matching the requested location or explicitly remote."""

    location = job.get("location", "").lower()
    description = clean_html(job.get("description", "")).lower()
    tags = " ".join(job.get("tags", [])).lower()

    germany_locations = [
        "germany",
        "deutschland",
        "berlin",
        "potsdam",
        "munich",
        "münchen",
        "hamburg",
        "frankfurt",
        "cologne",
        "köln",
        "stuttgart",
        "düsseldorf",
        "dresden",
        "leipzig",
    ]

    preferred_location = (preferred_location or "Germany").strip().lower()
    if preferred_location in {"any", "anywhere", "no preference"}:
        return True

    if preferred_location not in {"germany", "deutschland"} and preferred_location in location:
        return True

    if any(place in location for place in germany_locations):
        return preferred_location in {"germany", "deutschland"}

    remote_indicators = [
        "remote in germany",
        "remote germany",
        "remote deutschland",
        "germany remote",
    ]

    combined_text = f"{location} {tags} {description[:1500]}"

    return any(term in combined_text for term in remote_indicators)


def search_jobs(
    keyword: str = "AI/ML Intern",
    limit: int = 10,
    preferred_location: str = "Germany",
):
    """
    Search for relevant AI, ML, and data student jobs in Germany.
    """

    try:
        limit = max(1, min(int(limit), 50))

        all_jobs = []
        next_url = API_URL

        # Fetch multiple pages from Arbeitnow.
        for page_number in range(MAX_PAGES):

            response = requests.get(
                next_url,
                timeout=20,
                headers={"User-Agent": "CareerPilotAI/1.0"},
            )

            response.raise_for_status()
            data = response.json()

            jobs = data.get("data", [])
            all_jobs.extend(jobs)

            next_page = data.get("links", {}).get("next")

            if not next_page:
                break

            next_url = next_page

        results = []
        seen_urls = set()

        for job in all_jobs:

            title = job.get("title", "")
            company = job.get("company_name", "")

            url = job.get("url", "")

            if not title or not url:
                continue

            if url in seen_urls:
                continue

            seen_urls.add(url)

            # Keep Germany-based and Germany-remote jobs.
            if not is_germany_or_remote(job, preferred_location):
                continue

            score, reasons = get_relevance_score(job, keyword)

            # Ignore jobs with insufficient relevance.
            if score < 30:
                continue

            description = clean_html(job.get("description", ""))

            results.append({
                "title": title,
                "company": company,
                "company_url": job.get("company_url") or job.get("company_website") or "",
                "location": job.get("location", ""),
                "url": url,
                "tags": job.get("tags", []),
                "job_types": job.get("job_types", []),
                "remote": job.get("remote", False),
                "description": description[:1500],
                "posted_at": job.get("created_at", ""),
                "source": "Arbeitnow",
                "relevance_score": score,
                "match_reasons": reasons,
            })

        # Highest relevance first.
        results.sort(
            key=lambda item: item["relevance_score"],
            reverse=True,
        )

        return {
            "keyword": keyword,
            "total_jobs": min(len(results), limit),
            "jobs": results[:limit],
        }

    except requests.RequestException as error:
        return {
            "error": f"Job API request failed: {str(error)}"
        }

    except Exception as error:
        return {
            "error": str(error)
        }
