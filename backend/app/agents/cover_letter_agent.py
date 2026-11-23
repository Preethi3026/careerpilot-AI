import re


# ============================================================
# 2. VERIFIED PROJECT INFORMATION
# ============================================================

PROJECTS = [
    {
        "name": "Production RAG System",
        "keywords": [
            "Python", "RAG", "FAISS", "Ollama",
            "Embeddings", "LLMs", "Vector Search"
        ],
        "description": (
            "In my Production RAG System project, I built a "
            "Retrieval-Augmented Generation application using "
            "Microsoft Azure documentation as its knowledge source. "
            "The project uses BGE embeddings, FAISS for similarity "
            "search and Ollama with Llama 3.1 for answer generation. "
            "The system processes a 244-page documentation corpus "
            "and has 33 passing tests."
        )
    },
    {
        "name": "Agent with Tools and Observability",
        "keywords": [
            "Python", "AI Agents", "LangGraph",
            "FAISS", "SQL", "LLMs"
        ],
        "description": (
            "I also built an Agent with Tools and Observability "
            "using LangGraph. It integrates a Weather API, a FAISS "
            "knowledge base and an SQLite customer database, with "
            "guardrails, retries and Langfuse observability."
        )
    },
    {
        "name": "AgentEval - AI Model Evaluation Platform",
        "keywords": [
            "Python", "Machine Learning", "Generative AI",
            "LLMs", "Ollama", "Model Evaluation"
        ],
        "description": (
            "My AgentEval project is an AI model evaluation "
            "and benchmarking application built with Streamlit "
            "and Ollama. It includes LLM-as-a-judge and "
            "rule-based evaluation to compare AI models."
        )
    }
]


# ============================================================
# 3. SKILL DETECTION
# ============================================================

SKILL_ALIASES = {
    "Python": ["python"],
    "Machine Learning": ["machine learning"],
    "Generative AI": ["generative ai", "gen ai"],
    "LLMs": ["llm", "llms", "large language models"],
    "RAG": ["rag", "retrieval augmented generation"],
    "FAISS": ["faiss"],
    "Ollama": ["ollama"],
    "LangChain": ["langchain"],
    "LangGraph": ["langgraph"],
    "FastAPI": ["fastapi"],
    "SQL": ["sql", "sqlite"],
    "React": ["react"],
    "TypeScript": ["typescript"],
    "Data Analysis": ["data analysis", "data analytics"],
    "Embeddings": ["embedding", "embeddings"],
    "Vector Search": ["vector search", "similarity search"],
    "AI Agents": ["ai agents", "ai agent"]
}


def detect_relevant_skills(job_description):

    text = job_description.lower()

    matched = []

    for skill, aliases in SKILL_ALIASES.items():

        for alias in aliases:

            pattern = (
                r"(?<![a-z0-9])"
                + re.escape(alias)
                + r"(?![a-z0-9])"
            )

            if re.search(pattern, text):
                matched.append(skill)
                break

    return matched


# ============================================================
# 4. SELECT RELEVANT PROJECTS
# ============================================================

def select_relevant_projects(job_description):

    required_skills = set(
        detect_relevant_skills(job_description)
    )

    scored_projects = []

    for project in PROJECTS:

        overlap = required_skills.intersection(
            project["keywords"]
        )

        if overlap:

            scored_projects.append({
                "project": project,
                "score": len(overlap)
            })

    scored_projects.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    return [
        item["project"]
        for item in scored_projects[:2]
    ]


# ============================================================
# 5. GENERATE COVER LETTER
# ============================================================

def generate_cover_letter(
    job_description: str,
    company: str,
    role: str,
    resume_text: str = "",
    company_research: str = "",
    candidate_name: str = "",
):

    company = company.strip() or "the organisation"
    role = role.strip() or "the advertised position"
    if not resume_text.strip():
        raise ValueError("Cover Letter Agent requires candidate-provided resume text; no sample profile is substituted.")

    relevant_skills = detect_relevant_skills(
        job_description
    )

    relevant_projects = select_relevant_projects(
        job_description
    )
    if resume_text.strip():
        resume_lower = resume_text.lower()
        relevant_skills = [
            skill for skill in relevant_skills
            if skill.lower() in resume_lower
        ]
        relevant_projects = [
            project for project in relevant_projects
            if project["name"].lower() in resume_lower
        ]

    if not candidate_name.strip() and resume_text.strip():
        for line in resume_text.splitlines()[:8]:
            candidate_line = line.strip()
            if candidate_line and not re.search(r"@|https?://|\+?\d[\d ()-]{6,}", candidate_line, re.IGNORECASE):
                if len(candidate_line.split()) <= 5 and not any(mark in candidate_line for mark in "|,:;•"):
                    candidate_name = candidate_line
                    break

    # --------------------------------------------------------
    # Opening
    # --------------------------------------------------------

    paragraphs = []

    paragraphs.append(
        f"Dear Hiring Team at {company},"
    )

    paragraphs.append(
        f"I am writing to apply for the {role} position at {company}. "
        "My application is based on the education, skills, and experience "
        "documented in my resume. I am interested in contributing "
        "to the work described in the position."
    )

    # --------------------------------------------------------
    # Relevant skills
    # --------------------------------------------------------

    if relevant_skills:

        skill_text = ", ".join(relevant_skills)

        paragraphs.append(
            f"My technical skills relevant to this position "
            f"include {skill_text}. These verified skills align "
            f"with the requirements described for this position."
        )

    else:
        paragraphs.append("I would welcome the opportunity to discuss how the background documented in my resume could support this role.")

    # --------------------------------------------------------
    # Relevant projects
    # --------------------------------------------------------

    if relevant_projects:

        project_text = " ".join(
            project["description"]
            for project in relevant_projects
        )

        paragraphs.append(project_text)

    # Carry the Company Researcher's result into the letter. Only quote a
    # concise factual excerpt from a successfully retrieved report.
    if company_research and "Website retrieval: Successful" in company_research:
        research_match = re.search(
            r"(?:2\. PRODUCTS AND SERVICES|PRODUCTS AND SERVICES)(.*?)(?=\n\s*\d+\.|\n\s*[A-Z][A-Z ]{5,}\n|$)",
            company_research,
            re.IGNORECASE | re.DOTALL,
        )
        if research_match:
            excerpt = re.sub(r"\s+", " ", research_match.group(1)).strip(" \n:-")[:220]
            if excerpt:
                paragraphs.append(f"The company research highlighted the following company information as relevant to this application: {excerpt}")

    # --------------------------------------------------------
    # Experience
    # --------------------------------------------------------

    paragraphs.append(
        "I would be glad to explain how the relevant work in my resume "
        "connects with the responsibilities of this position."
    )

    # --------------------------------------------------------
    # Motivation and closing
    # --------------------------------------------------------

    paragraphs.append(
        f"I would welcome the opportunity to discuss how my documented "
        f"background could contribute to the {role} position. "
        f"Thank you for considering my application."
    )

    paragraphs.append(
        "Kind regards,\n" +
        (candidate_name.strip() or "Candidate")
    )

    return "\n\n".join(paragraphs)
