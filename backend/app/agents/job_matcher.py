import re


# ============================================================
# 1. CANDIDATE PROFILE
# ============================================================

CANDIDATE_PROFILE = {
    "education": [
        "Big Data",
        "Artificial Intelligence",
        "Machine Learning"
    ],

    "skills": [
        "Python",
        "Machine Learning",
        "Artificial Intelligence",
        "Generative AI",
        "LLM",
        "RAG",
        "FAISS",
        "Ollama",
        "LangChain",
        "LangGraph",
        "FastAPI",
        "SQL",
        "React",
        "TypeScript",
        "Data Analysis",
        "Embeddings",
        "Vector Search",
        "AI Agents"
    ],

    "experience_years": 2,

    "experience_area": [
        "Frontend Development",
        "React",
        "TypeScript"
    ]
}


# ============================================================
# 2. SKILL ALIASES
# ============================================================

SKILL_ALIASES = {
    "Python": ["python"],
    "Machine Learning": ["machine learning", "machine-learning"],
    "Generative AI": ["generative ai", "genai"],
    "LLM": [
        "llm", "llms",
        "large language model",
        "large language models"
    ],
    "RAG": [
        "rag",
        "retrieval augmented generation",
        "retrieval-augmented generation"
    ],
    "FAISS": ["faiss"],
    "Ollama": ["ollama"],
    "LangChain": ["langchain"],
    "LangGraph": ["langgraph"],
    "FastAPI": ["fastapi", "fast api"],
    "SQL": ["sql", "structured query language"],
    "React": ["react.js", "reactjs", "react"],
    "TypeScript": ["typescript", "type script"],
    "Data Analysis": [
        "data analysis",
        "data analytics",
        "data analyst"
    ],
    "Embeddings": [
        "embedding",
        "embeddings",
        "vector embeddings"
    ],
    "Vector Search": [
        "vector search",
        "vector database",
        "vector databases",
        "similarity search"
    ],
    "PyTorch": ["pytorch"],
    "TensorFlow": ["tensorflow"],
    "Docker": ["docker", "containerization"],
    "Kubernetes": ["kubernetes", "k8s"],
    "Deep Learning": ["deep learning"],
    "Model Evaluation": [
        "model evaluation",
        "llm evaluation",
        "model performance evaluation"
    ],
    "AI Agents": [
        "ai agents",
        "agentic ai",
        "autonomous agents",
        "intelligent agents"
    ],
    "Java": ["java"],
    "JavaScript": ["javascript"],
    "Node.js": ["node.js", "nodejs"],
    "C++": ["c++"],
    "AWS": ["aws", "amazon web services"],
    "Azure": ["microsoft azure", "azure"],
    "GCP": ["google cloud platform", "gcp"],
    "PostgreSQL": ["postgresql", "postgres"],
    "MongoDB": ["mongodb"],
    "Git": ["git"],
    "REST API": ["rest api", "restful api"],
    "Linux": ["linux"],
    "Spark": ["apache spark", "pyspark", "spark"],
    "Hugging Face": ["hugging face", "huggingface"],
    "Scikit-learn": ["scikit-learn", "sklearn"]
}


# ============================================================
# 3. SKILL WEIGHTS
# ============================================================

SKILL_WEIGHTS = {
    "Python": 5,
    "Machine Learning": 5,
    "Generative AI": 5,
    "LLM": 5,
    "RAG": 5,
    "LangChain": 4,
    "LangGraph": 4,
    "FAISS": 3,
    "Ollama": 2,
    "FastAPI": 3,
    "SQL": 3,
    "Data Analysis": 3,
    "Embeddings": 3,
    "Vector Search": 3,
    "PyTorch": 4,
    "TensorFlow": 4,
    "Deep Learning": 5,
    "AI Agents": 4,
    "Docker": 2,
    "Kubernetes": 2,
    "React": 2,
    "TypeScript": 2,
    "Java": 2,
    "JavaScript": 2,
    "Node.js": 2,
    "C++": 2,
    "AWS": 2,
    "Azure": 2,
    "GCP": 2,
    "PostgreSQL": 2,
    "MongoDB": 2,
    "Git": 1,
    "REST API": 2,
    "Linux": 1,
    "Spark": 3,
    "Hugging Face": 3,
    "Scikit-learn": 3
}


# ============================================================
# 4. TEXT MATCHING
# ============================================================

def contains_skill(text, aliases):

    text = text.lower()

    for alias in aliases:

        pattern = (
            r"(?<!\w)"
            + re.escape(alias.lower())
            + r"(?!\w)"
        )

        if re.search(pattern, text):
            return True

    return False


# ============================================================
# 5. EDUCATION MATCHING
# ============================================================

def check_education_match(description):

    description = description.lower()

    education_keywords = [
        "computer science",
        "data science",
        "artificial intelligence",
        "machine learning",
        "big data",
        "informatics",
        "related field",
        "engineering"
    ]

    return any(
        keyword in description
        for keyword in education_keywords
    )


# ============================================================
# 6. EXPERIENCE MATCHING
# ============================================================

def check_experience_match(description):

    description = description.lower()

    experience_keywords = [
        "frontend",
        "front-end",
        "react",
        "typescript",
        "web development",
        "software development",
        "software engineering"
    ]

    return any(
        keyword in description
        for keyword in experience_keywords
    )


# ============================================================
# 7. JOB LEVEL DETECTION
# ============================================================

def detect_job_level(description, job_title=""):

    title = job_title.lower().strip()
    description = description.lower()

    # --------------------------------------------------------
    # PRIORITY 1: INTERNSHIP / STUDENT TITLES
    # --------------------------------------------------------

    entry_level_patterns = [
        r"\bintern\b",
        r"\binternship\b",
        r"\bworking student\b",
        r"\bwerkstudent\b",
        r"\bstudent position\b",
        r"\bstudent job\b",
        r"\bgraduate\b",
        r"\btrainee\b"
    ]

    if any(
        re.search(pattern, title)
        for pattern in entry_level_patterns
    ):
        return "Entry Level"

    # --------------------------------------------------------
    # PRIORITY 2: JUNIOR TITLES
    # --------------------------------------------------------

    junior_patterns = [
        r"\bjunior\b",
        r"\bentry[\s-]?level\b"
    ]

    if any(
        re.search(pattern, title)
        for pattern in junior_patterns
    ):
        return "Junior"

    # --------------------------------------------------------
    # PRIORITY 3: SENIOR TITLES
    # --------------------------------------------------------

    senior_patterns = [
        r"\bsenior\b",
        r"\blead\b",
        r"\bprincipal\b",
        r"\bstaff engineer\b",
        r"\bdirector\b",
        r"\bhead of\b",
        r"\bmanager\b"
    ]

    if any(
        re.search(pattern, title)
        for pattern in senior_patterns
    ):
        return "Senior"

    # --------------------------------------------------------
    # PRIORITY 4: DESCRIPTION FALLBACK
    # Only explicit senior-level requirements are considered.
    # Generic mentions of senior colleagues are ignored.
    # --------------------------------------------------------

    explicit_senior_patterns = [
        r"\bsenior[\s-]level position\b",
        r"\bsenior[\s-]level role\b",
        r"\bfor senior candidates\b",
        r"\bexperienced senior professional\b",
        r"\bminimum of 5 years of experience\b",
        r"\bat least 5 years of experience\b",
        r"\b5\+ years of experience\b",
        r"\bminimum of 7 years of experience\b",
        r"\bat least 7 years of experience\b",
        r"\b7\+ years of experience\b",
        r"\bminimum of 8 years of experience\b",
        r"\bat least 8 years of experience\b",
        r"\b8\+ years of experience\b"
    ]

    if any(
        re.search(pattern, description)
        for pattern in explicit_senior_patterns
    ):
        return "Senior"

    return "Not Specified"


# ============================================================
# 8. SKILL MATCHING
# ============================================================

def analyze_skills(description, candidate_skills=None):

    required_skills = []
    matched_skills = []
    missing_skills = []

    candidate_skills = set(
        candidate_skills
        if candidate_skills is not None
        else CANDIDATE_PROFILE["skills"]
    )

    for skill, aliases in SKILL_ALIASES.items():

        if contains_skill(description, aliases):

            required_skills.append(skill)

            if skill in candidate_skills:

                matched_skills.append(skill)

            else:

                missing_skills.append(skill)

    return (
        required_skills,
        matched_skills,
        missing_skills
    )


# ============================================================
# 9. WEIGHTED SKILL SCORE
# ============================================================

def calculate_skill_score(
    required_skills,
    matched_skills
):

    if not required_skills:
        return 0

    total_weight = sum(
        SKILL_WEIGHTS.get(skill, 1)
        for skill in required_skills
    )

    matched_weight = sum(
        SKILL_WEIGHTS.get(skill, 1)
        for skill in matched_skills
    )

    if total_weight == 0:
        return 0

    return round(
        (matched_weight / total_weight) * 100
    )


# ============================================================
# 10. JOB SUITABILITY
# ============================================================

def analyze_job_suitability(description, job_title=""):

    job_level = detect_job_level(
        description,
        job_title
    )

    internship_suitable = (
        job_level == "Entry Level"
    )

    seniority_mismatch = (
        job_level == "Senior"
    )

    if seniority_mismatch:

        suitability = "Low - Senior role"

    elif internship_suitable:

        suitability = (
            "Good - Student/Entry-level opportunity"
        )

    elif job_level == "Junior":

        suitability = "Good - Junior opportunity"

    else:

        suitability = (
            "Not specified - Review requirements"
        )

    return {
        "job_level": job_level,
        "internship_suitable": internship_suitable,
        "seniority_mismatch": seniority_mismatch,
        "job_suitability": suitability
    }


# ============================================================
# 11. MAIN JOB MATCHING FUNCTION
# ============================================================

def match_job(
    job_description: str,
    job_title: str = "",
    candidate_profile: dict | None = None,
):

    if not isinstance(job_description, str):
        job_description = ""

    if not isinstance(job_title, str):
        job_title = ""

    description = job_description.lower()

    # --------------------------------------------------------
    # TECHNICAL SKILL ANALYSIS
    # --------------------------------------------------------

    (
        required_skills,
        matched_skills,
        missing_skills
    ) = analyze_skills(
        description,
        candidate_profile.get("skills") if candidate_profile else None,
    )

    # --------------------------------------------------------
    # TECHNICAL SCORE
    # --------------------------------------------------------

    skill_score = calculate_skill_score(
        required_skills,
        matched_skills
    )

    # --------------------------------------------------------
    # EDUCATION COMPATIBILITY
    # --------------------------------------------------------

    education_match = check_education_match(description)
    if candidate_profile:
        education = candidate_profile.get("education", "")
        education_text = " ".join(education) if isinstance(education, list) else str(education)
        education_domains = [
            "computer science", "informatics", "data science", "data analytics",
            "big data", "artificial intelligence", "machine learning",
            "engineering", "mathematics",
        ]
        job_domains = [domain for domain in education_domains if domain in description]
        candidate_domains = [domain for domain in education_domains if domain in education_text.lower()]
        has_education_requirement = any(
            word in description for word in ("degree", "student", "bachelor", "master", "enrolled", "university")
        )
        education_match = bool(
            has_education_requirement
            and candidate_domains
            and (not job_domains or set(job_domains).intersection(candidate_domains)
                 or "related field" in description)
        )

    # --------------------------------------------------------
    # EXPERIENCE COMPATIBILITY
    # --------------------------------------------------------

    experience_match = check_experience_match(description)
    if candidate_profile:
        experience_text = str(candidate_profile.get("experience", ""))
        experience_years = candidate_profile.get("experience_years", 0)
        if not experience_years:
            year_match = re.search(r"(\d+)\+?\s+years?", experience_text, re.IGNORECASE)
            experience_years = int(year_match.group(1)) if year_match else 0
        required_years = [
            int(value)
            for value in re.findall(r"(?:at least|minimum of)?\s*(\d+)\+?\s+years?", description)
        ]
        experience_match = (
            experience_years >= max(required_years)
            if required_years
            else bool(experience_text.strip() or experience_years)
        )

    # --------------------------------------------------------
    # JOB SUITABILITY
    # --------------------------------------------------------

    suitability = analyze_job_suitability(
        description,
        job_title
    )

    # --------------------------------------------------------
    # FINAL SCORE
    # --------------------------------------------------------

    final_score = skill_score

    # Limited evidence adjustment

    if len(required_skills) < 5:

        final_score = min(final_score, 50)

    elif len(required_skills) < 8:

        final_score = min(final_score, 70)

    # Education contribution

    if education_match:
        final_score += 5

    # Experience contribution

    if experience_match:
        final_score += 5

    # Seniority penalty

    if suitability["seniority_mismatch"]:
        final_score -= 25

    # Keep score within 0-100

    final_score = max(
        0,
        min(100, final_score)
    )

    final_score = round(final_score)

    # --------------------------------------------------------
    # RECOMMENDATION
    # --------------------------------------------------------

    if suitability["seniority_mismatch"]:

        recommendation = (
            "Not Recommended - Seniority Mismatch"
        )

    elif final_score >= 80:

        recommendation = "Strong Match - Apply!"

    elif final_score >= 60:

        recommendation = (
            "Good Match - Consider Applying"
        )

    elif final_score >= 40:

        recommendation = (
            "Moderate Match - Review Requirements"
        )

    else:

        recommendation = (
            "Low Match - Develop Missing Skills"
        )

    # --------------------------------------------------------
    # RETURN RESULT
    # --------------------------------------------------------

    return {

        "match_score": final_score,

        "skill_score": skill_score,

        "matched_skills": matched_skills,

        "missing_skills": missing_skills,

        "required_skills": required_skills,

        "total_required_skills": len(
            required_skills
        ),

        "total_matched_skills": len(
            matched_skills
        ),

        "education_match": education_match,

        "experience_match": experience_match,

        "job_level": suitability["job_level"],

        "internship_suitable": suitability[
            "internship_suitable"
        ],

        "seniority_mismatch": suitability[
            "seniority_mismatch"
        ],

        "job_suitability": suitability[
            "job_suitability"
        ],

        "recommendation": recommendation,

        "scoring_note": (
            "CareerPilot Job Matcher V3 uses weighted "
            "technical skill matching, education and "
            "experience indicators, and title-first "
            "job-level detection. Scores are approximate "
            "indicators, not hiring probabilities or "
            "guarantees of suitability."
        )
    }
