import re
import requests
from html.parser import HTMLParser


API_URL = "https://remotive.com/api/remote-jobs"

MAX_RESULTS = 200

STUDENT_KEYWORDS = [
    "intern",
    "internship",
    "working student",
    "working-student",
    "student",
    "graduate",
    "trainee",
    "junior",
    "entry level",
    "entry-level",
    "early career",
]

TECH_KEYWORDS = [
    "artificial intelligence",
    "machine learning",
    "deep learning",
    "generative ai",
    "llm",
    "large language model",
    "data science",
    "data analyst",
    "data engineer",
    "python",
    "software engineer",
    "software developer",
    "automation",
    "nlp",
    "computer vision",
]

EXCLUDED_KEYWORDS = [
    "senior",
    "lead",
    "principal",
    "director",
    "manager",
    "head of",
    "staff engineer",
    "sales",
    "marketing",
    "customer success",
    "patient care",
    "customer service",
    "customer support",
]


class HTMLTextExtractor(HTMLParser):

    def __init__(self):
        super().__init__()
        self.text_parts = []

    def handle_data(self, data):
        self.text_parts.append(data)

    def get_text(self):
        return " ".join(self.text_parts)


def clean_html(html):

    if not html:
        return ""

    parser = HTMLTextExtractor()

    try:
        parser.feed(html)
        text = parser.get_text()
        return re.sub(r"\s+", " ", text).strip()

    except Exception:
        return html


def calculate_relevance(job, keyword):

    title = (job.get("title") or "").lower()

    description = clean_html(
        job.get("description", "")
    ).lower()

    category = (job.get("category") or "").lower()

    tags = job.get("tags", [])

    tags_text = " ".join(
        str(tag) for tag in tags
    ).lower()

    combined_text = (
        f"{title} {description} {category} {tags_text}"
    )

    # Exclude senior and unrelated positions
    if any(word in title for word in EXCLUDED_KEYWORDS):
        return 0

    # Check technical relevance
    matched_keywords = [
        word
        for word in TECH_KEYWORDS
        if word in combined_text
    ]

    if not matched_keywords:
        return 0

    score = 40

    # Technical role in title
    if any(word in title for word in TECH_KEYWORDS):
        score += 30

    # Student and early-career bonus
    if any(word in title for word in STUDENT_KEYWORDS):
        score += 20

    # Technical skills bonus
    score += min(len(matched_keywords) * 2, 10)

    return min(score, 100)


def search_remote_jobs(keyword="AI/ML Intern", limit=10):

    try:

        response = requests.get(
            API_URL,
            params={"limit": MAX_RESULTS},
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        raw_jobs = data.get("jobs", [])

        results = []

        for job in raw_jobs:

            score = calculate_relevance(job, keyword)

            title = (
                job.get("title") or ""
            ).lower()

            # Exclude unrelated job categories
            excluded_titles = [
                "patient care",
                "customer service",
                "customer support",
                "tech lead",
                "team lead",
                "manager",
                "director",
                "principal",
                "senior"
            ]

            if any(
                word in title
                for word in excluded_titles
            ):
                continue

            if score == 0:
                continue

            description = clean_html(
                job.get("description", "")
            )

            results.append({

                "title": job.get(
                    "title",
                    "Not specified"
                ),

                "company": job.get(
                    "company_name",
                    "Not specified"
                ),

                "company_url": job.get("company_url") or job.get("company_website") or "",

                "location": job.get(
                    "candidate_required_location",
                    "Remote"
                ),

                "url": job.get("url", ""),

                "tags": job.get("tags", []),

                "job_type": job.get(
                    "job_type",
                    "Not specified"
                ),

                "remote": True,

                "description": description[:1500],

                "posted_at": job.get(
                    "publication_date",
                    ""
                ),

                "source": "Remotive",

                "relevance_score": score,

                "match_reasons": [
                    word
                    for word in TECH_KEYWORDS
                    if word in description.lower()
                ][:5]

            })

        # Sort by relevance score
        results.sort(
            key=lambda item: item["relevance_score"],
            reverse=True
        )

        return {

            "source": "Remotive",

            "keyword": keyword,

            "total_jobs": len(results[:limit]),

            "jobs": results[:limit]

        }

    except requests.exceptions.RequestException as error:

        return {

            "source": "Remotive",

            "error": (
                f"Could not connect to Remotive API: {str(error)}"
            ),

            "total_jobs": 0,

            "jobs": []

        }

    except Exception as error:

        return {

            "source": "Remotive",

            "error": str(error),

            "total_jobs": 0,

            "jobs": []

        }
