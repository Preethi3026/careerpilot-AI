import re


# ============================================================
# 1. VERIFIED CANDIDATE PROFILE
# ============================================================

VERIFIED_SKILLS = [
    "Python",
    "Machine Learning",
    "Generative AI",
    "LLMs",
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
]


VERIFIED_PROJECTS = [
    "Production RAG System",
    "Agent with Tools and Observability",
    "AgentEval",
    "Cross-Cloud Anomaly Detection"
]


# ============================================================
# 2. SKILL KEYWORD DETECTION
# ============================================================

SKILL_ALIASES = {

    "Python": ["python"],

    "Machine Learning": [
        "machine learning"
    ],

    "Generative AI": [
        "generative ai",
        "gen ai"
    ],

    "LLMs": [
        "llm",
        "llms",
        "large language models"
    ],

    "RAG": [
        "rag",
        "retrieval augmented generation"
    ],

    "FAISS": ["faiss"],

    "Ollama": ["ollama"],

    "LangChain": ["langchain"],

    "LangGraph": ["langgraph"],

    "FastAPI": ["fastapi"],

    "SQL": ["sql", "sqlite"],

    "React": ["react"],

    "TypeScript": ["typescript"],

    "Data Analysis": [
        "data analysis",
        "data analytics"
    ],

    "Embeddings": [
        "embedding",
        "embeddings"
    ],

    "Vector Search": [
        "vector search",
        "similarity search"
    ],

    "AI Agents": [
        "ai agent",
        "ai agents"
    ],

    "Docker": ["docker"],

    "PyTorch": ["pytorch"],

    "Kubernetes": ["kubernetes"],

    "AWS": [
        "aws",
        "amazon web services"
    ],

    "Azure": ["azure"],

    "MLOps": ["mlops"]
}


def contains_keyword(text, keyword):

    pattern = (
        r"(?<![a-z0-9])"
        + re.escape(keyword.lower())
        + r"(?![a-z0-9])"
    )

    return bool(re.search(pattern, text.lower()))


def detect_keywords(text):

    found = []

    for skill, aliases in SKILL_ALIASES.items():

        for alias in aliases:

            if contains_keyword(text, alias):

                found.append(skill)
                break

    return found


# ============================================================
# 3. CHECK EDUCATION ACCURACY
# ============================================================

def check_education(text):

    issues = []

    incorrect_phrases = [
        "master's degree completed",
        "master's graduate",
        "graduated with a master's",
        "holds a master's degree",
        "completed my master's"
    ]

    for phrase in incorrect_phrases:

        if phrase in text.lower():

            issues.append(
                f"Potentially inaccurate education claim: "
                f"'{phrase}'. The Master's degree is still in progress."
            )

    if "October 2027" not in text:

        issues.append(
            "Expected Master's completion date (October 2027) "
            "is not mentioned."
        )

    return issues


# ============================================================
# 4. CHECK EXPERIENCE ACCURACY
# ============================================================

def check_experience(text):

    issues = []

    incorrect_phrases = [
        "2 years of ai/ml experience",
        "2 years of machine learning experience",
        "2 years of artificial intelligence experience",
        "2 years of professional ai experience"
    ]

    for phrase in incorrect_phrases:

        if phrase in text.lower():

            issues.append(
                "The candidate's 2 years of experience are "
                "in frontend development, not professional AI/ML."
            )

    return issues


# ============================================================
# 5. CHECK UNSUPPORTED TECHNOLOGIES
# ============================================================

def check_unsupported_skills(text):

    issues = []

    unsupported_skills = [
        "Docker",
        "PyTorch",
        "Kubernetes",
        "AWS",
        "MLOps"
    ]

    for skill in unsupported_skills:

        if contains_keyword(text, skill):

            # Mentioning a skill as something to learn or develop
            # is not the same as claiming experience with it.

            learning_context = re.search(
                rf"(skills to develop|learning|want to learn|"
                rf"interested in learning|to be developed|"
                rf"not yet experienced|not verified)"
                rf".{{0,100}}\b{re.escape(skill)}\b",
                text,
                re.IGNORECASE
            )

            if not learning_context:

                issues.append(
                    f"{skill} is not currently verified "
                    "in the candidate profile. Check that it "
                    "is not presented as an existing skill."
                )

    return issues


# ============================================================
# 6. CHECK PLACEHOLDERS AND MISSING INFORMATION
# ============================================================

def check_missing_information(resume, cover_letter):

    issues = []

    combined = resume + "\n" + cover_letter

    placeholders = [
        "[Your Name]",
        "[Your Email]",
        "[Phone Number]",
        "[Company Address]",
        "[Date]"
    ]

    for placeholder in placeholders:

        if placeholder.lower() in combined.lower():

            issues.append(
                f"Replace placeholder: {placeholder}"
            )

    if not re.search(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        combined
    ):

        issues.append(
            "Email address is missing."
        )

    if "linkedin.com" not in combined.lower():

        issues.append(
            "LinkedIn profile URL is missing."
        )

    if "github.com" not in combined.lower():

        issues.append(
            "GitHub profile URL is missing."
        )

    return issues


# ============================================================
# 7. CHECK PROJECT REFERENCES
# ============================================================

def check_projects(text):

    found = []

    for project in VERIFIED_PROJECTS:

        if project.lower() in text.lower():

            found.append(project)

    return found


# ============================================================
# 8. MAIN APPLICATION REVIEWER
# ============================================================

def review_application(
    job_description: str,
    resume_text: str,
    cover_letter: str = "",
    company_research: str = "",
):

    resume = resume_text.strip()
    cover_letter = cover_letter.strip()

    combined = resume + "\n" + cover_letter

    strengths = []
    issues = []
    unsupported_claims = []
    improvements = []

    # --------------------------------------------------------
    # A. DOCUMENT PRESENCE
    # --------------------------------------------------------

    if not resume:

        issues.append("Resume is missing.")

    else:

        strengths.append("Resume has been provided.")

    if not cover_letter:

        issues.append("Cover letter is missing.")

    else:

        strengths.append("Cover letter has been provided.")

    if company_research:
        if "Website retrieval: Successful" in company_research:
            strengths.append("Company research report was available as context for company-specific statements.")
        elif "Website retrieval failed" in company_research:
            issues.append("Company-specific claims could not be checked against the supplied website because retrieval failed.")
        else:
            issues.append("Company research was unavailable or did not confirm a website source.")
    else:
        issues.append("No company research was supplied to validate company-specific cover-letter statements.")

    # --------------------------------------------------------
    # B. ATS KEYWORD ANALYSIS
    # --------------------------------------------------------

    required_skills = detect_keywords(job_description)

    candidate_skills = detect_keywords(resume)

    matched_skills = [
        skill for skill in required_skills
        if skill in candidate_skills
        and skill in VERIFIED_SKILLS
    ]

    missing_skills = [
        skill for skill in required_skills
        if skill not in VERIFIED_SKILLS
    ]

    if required_skills:

        ats_percentage = round(
            len(matched_skills) / len(required_skills) * 100,
            2
        )

    else:

        ats_percentage = 0

    # --------------------------------------------------------
    # C. EDUCATION CHECK
    # --------------------------------------------------------

    education_issues = check_education(combined)

    unsupported_claims.extend(education_issues)

    # --------------------------------------------------------
    # D. EXPERIENCE CHECK
    # --------------------------------------------------------

    experience_issues = check_experience(combined)

    unsupported_claims.extend(experience_issues)

    # --------------------------------------------------------
    # E. TECHNOLOGY CHECK
    # --------------------------------------------------------

    technology_issues = check_unsupported_skills(combined)

    unsupported_claims.extend(technology_issues)

    # --------------------------------------------------------
    # F. PROJECT CHECK
    # --------------------------------------------------------

    found_projects = check_projects(combined)

    if found_projects:

        strengths.append(
            "Verified projects mentioned: "
            + ", ".join(found_projects)
        )

    else:

        issues.append(
            "No verified project names were detected."
        )

    # --------------------------------------------------------
    # G. MISSING INFORMATION
    # --------------------------------------------------------

    missing_information = check_missing_information(
        resume,
        cover_letter
    )

    # --------------------------------------------------------
    # H. SCORE CALCULATION
    # --------------------------------------------------------

    score = 100

    if not resume:
        score -= 40

    if not cover_letter:
        score -= 15

    if unsupported_claims:
        score -= min(
            30,
            len(unsupported_claims) * 10
        )

    if missing_information:
        score -= min(
            15,
            len(missing_information) * 3
        )

    if not found_projects:
        score -= 10

    score = max(0, min(100, score))

    # --------------------------------------------------------
    # I. RECOMMENDATIONS
    # --------------------------------------------------------

    if missing_skills:

        improvements.append(
            "The following job requirements are not verified "
            "in the candidate profile: "
            + ", ".join(missing_skills)
        )

    if missing_information:

        improvements.append(
            "Complete missing personal and professional "
            "information before submitting the application."
        )

    if unsupported_claims:

        improvements.append(
            "Correct or remove potentially unsupported claims."
        )

    if not cover_letter:

        improvements.append(
            "Prepare a tailored cover letter."
        )

    improvements.append(
        "Check grammar, spelling and formatting manually "
        "before submitting."
    )

    # --------------------------------------------------------
    # J. FINAL RECOMMENDATION
    # --------------------------------------------------------

    if not resume:

        recommendation = (
            "NOT READY - A resume is required."
        )

    elif unsupported_claims:

        recommendation = (
            "NEEDS REVISION - Potentially unsupported claims "
            "must be checked before submission."
        )

    elif score >= 85:

        recommendation = (
            "GOOD - The application passed the automated "
            "accuracy checks. Complete a final human review."
        )

    elif score >= 65:

        recommendation = (
            "NEEDS IMPROVEMENT - Address the missing information "
            "and review the application before submission."
        )

    else:

        recommendation = (
            "NOT READY - Significant application improvements "
            "are recommended."
        )

    # --------------------------------------------------------
    # K. RETURN REVIEW
    # --------------------------------------------------------

    result = f"""
APPLICATION REVIEW REPORT
========================================

Overall Application Score: {score}/100

ATS Compatibility: {ats_percentage}%

Matched Verified Skills:
{', '.join(matched_skills) if matched_skills else 'None detected'}

Job Requirements Not Verified:
{', '.join(missing_skills) if missing_skills else 'None detected'}

Company Research Context:
{'Website-derived company report supplied; review its source limitations before relying on company claims.' if company_research and 'Website retrieval: Successful' in company_research else 'Company-specific statements require manual verification.'}

STRENGTHS:
{chr(10).join('- ' + item for item in strengths) if strengths else '- None detected'}

ISSUES FOUND:
{chr(10).join('- ' + item for item in issues) if issues else '- No document presence issues detected.'}

POTENTIALLY UNSUPPORTED CLAIMS:
{chr(10).join('- ' + item for item in unsupported_claims) if unsupported_claims else '- No predefined accuracy conflicts detected.'}

MISSING INFORMATION:
{chr(10).join('- ' + item for item in missing_information) if missing_information else '- No predefined missing information detected.'}

RECOMMENDED IMPROVEMENTS:
{chr(10).join('- ' + item for item in improvements)}

FINAL RECOMMENDATION:
{recommendation}

NOTE:
This score measures automated document completeness and
predefined factual consistency. It is not an ATS vendor score,
a hiring probability or a complete grammar assessment.
"""

    return result
