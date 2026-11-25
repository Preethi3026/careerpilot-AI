import re


CANDIDATE_PROFILE = {
    "education": [
        "Master's in Big Data and Artificial Intelligence",
        "SRH University, Berlin",
        "Expected completion: October 2027"
    ],

    "skills": [
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
    ],

    "experience": [
        "2 years of frontend development experience"
    ],

    "projects": [
        "Production RAG System",
        "Agent with Tools and Observability",
        "AgentEval - AI Model Evaluation Platform",
        "Cross-Cloud Anomaly Detection"
    ]
}


PROJECT_SKILL_EVIDENCE = {
    "Production RAG System": [
        "Python", "RAG", "FAISS", "Embeddings",
        "LLMs", "Ollama"
    ],

    "Agent with Tools and Observability": [
        "Python", "AI Agents", "LangGraph", "FAISS", "SQL"
    ],

    "AgentEval - AI Model Evaluation Platform": [
        "Python", "LLMs", "Model Evaluation"
    ],

    "Cross-Cloud Anomaly Detection": []
}


SKILL_ALIASES = {
    "Python": ["Python"],
    "Machine Learning": ["Machine Learning", "ML"],
    "Deep Learning": ["Deep Learning"],
    "Generative AI": ["Generative AI", "GenAI"],
    "LLMs": ["LLM", "LLMs", "Large Language Models"],
    "RAG": ["RAG", "Retrieval Augmented Generation"],
    "FAISS": ["FAISS"],
    "Ollama": ["Ollama"],
    "LangChain": ["LangChain"],
    "LangGraph": ["LangGraph"],
    "FastAPI": ["FastAPI"],
    "SQL": ["SQL"],
    "React": ["React"],
    "TypeScript": ["TypeScript"],
    "Docker": ["Docker"],
    "Kubernetes": ["Kubernetes"],
    "PyTorch": ["PyTorch"],
    "TensorFlow": ["TensorFlow"],
    "MLOps": ["MLOps"],
    "AWS": ["AWS", "Amazon Web Services"],
    "Azure": ["Azure", "Microsoft Azure"],
    "GCP": ["GCP", "Google Cloud Platform"],
    "Hugging Face": ["Hugging Face"],
    "Model Evaluation": [
        "Model Evaluation",
        "LLM Evaluation",
        "Model Benchmarking",
        "LLM-as-a-judge"
    ],
    "Embeddings": ["Embeddings", "Embedding"],
    "Vector Databases": ["Vector Database", "Vector Databases"],
    "Computer Vision": ["Computer Vision"],
    "NLP": ["NLP", "Natural Language Processing"],
    "Data Engineering": ["Data Engineering"],
    "Airflow": ["Airflow", "Apache Airflow"],
    "Spark": ["Spark", "Apache Spark"],
    "Git": ["Git"],
    "CI/CD": ["CI/CD"]
}


def detect_required_skills(job_description: str):

    required_skills = []

    for skill, aliases in SKILL_ALIASES.items():

        for alias in aliases:

            pattern = (
                r"(?<!\w)"
                + re.escape(alias)
                + r"(?!\w)"
            )

            if re.search(
                pattern,
                job_description,
                re.IGNORECASE
            ):
                required_skills.append(skill)
                break

    return required_skills


def get_verified_candidate_skills():

    verified_skills = set(
        CANDIDATE_PROFILE["skills"]
    )

    for project_skills in PROJECT_SKILL_EVIDENCE.values():
        verified_skills.update(project_skills)

    return verified_skills


def compare_candidate_skills(required_skills, candidate_skills=None):

    candidate_skills = set(candidate_skills) if candidate_skills is not None else get_verified_candidate_skills()

    matched_skills = []
    missing_skills = []

    for skill in required_skills:

        if skill in candidate_skills:
            matched_skills.append(skill)

        else:
            missing_skills.append(skill)

    if required_skills:

        match_percentage = round(
            len(matched_skills)
            / len(required_skills)
            * 100,
            2
        )

    else:
        match_percentage = 0

    return {
        "required_skills": required_skills,
        "matched_skills": matched_skills,
        "missing_or_unverified_skills": missing_skills,
        "skill_coverage_percentage": match_percentage
    }


def generate_project_recommendations(missing_skills):

    recommendations = []

    if "Docker" in missing_skills or "AWS" in missing_skills:

        target_skills = []

        if "Docker" in missing_skills:
            target_skills.append("Docker")

        if "AWS" in missing_skills:
            target_skills.append("AWS")

        recommendations.append({
            "project": "Production RAG System – Cloud Deployment Extension",
            "type": "Extend an existing project",

            "description": (
                "Extend the existing Production RAG System by "
                "containerizing the application and deploying it "
                "to a cloud environment. Add deployment documentation "
                "and basic monitoring."
            ),

            "skills_addressed": target_skills,

            "suggested_tasks": [
                "Create a Dockerfile for the existing RAG application.",
                "Build and run the application inside a Docker container.",
                "Configure environment variables securely.",
                "Deploy the application to AWS if AWS is a target skill.",
                "Document deployment steps and basic monitoring."
            ],

            "important_note": (
                "This is a proposed extension, not a claim that "
                "Docker or AWS has already been used."
            )
        })

    if "Kubernetes" in missing_skills:

        recommendations.append({
            "project": "Container Orchestration Extension",
            "type": "Extend an existing project",

            "description": (
                "After containerizing an existing AI application, "
                "learn Kubernetes by deploying and managing its "
                "containerized services."
            ),

            "skills_addressed": ["Kubernetes"],

            "suggested_tasks": [
                "Create Kubernetes deployment configurations.",
                "Configure services and application health checks.",
                "Practice scaling and updating deployments.",
                "Document the deployment architecture."
            ],

            "important_note": (
                "Kubernetes is a suggested learning objective, "
                "not an existing verified skill."
            )
        })

    if "PyTorch" in missing_skills or "TensorFlow" in missing_skills:

        framework_skills = []

        if "PyTorch" in missing_skills:
            framework_skills.append("PyTorch")

        if "TensorFlow" in missing_skills:
            framework_skills.append("TensorFlow")

        recommendations.append({
            "project": "Machine Learning Model Experiment",
            "type": "New learning project",

            "description": (
                "Build a small machine learning experiment using "
                "a framework required by the target job."
            ),

            "skills_addressed": framework_skills,

            "suggested_tasks": [
                "Choose a beginner-friendly dataset.",
                "Train a baseline machine learning model.",
                "Evaluate the model using suitable metrics.",
                "Compare results and document the experiment."
            ],

            "important_note": "This is a proposed learning project."
        })

    if "MLOps" in missing_skills:

        recommendations.append({
            "project": "ML Experiment Tracking Extension",
            "type": "New learning project",

            "description": (
                "Extend a machine learning experiment with "
                "reproducible runs, experiment tracking and "
                "model version documentation."
            ),

            "skills_addressed": ["MLOps"],

            "suggested_tasks": [
                "Track experiment configurations.",
                "Record model evaluation results.",
                "Version datasets and model artifacts.",
                "Document a reproducible training workflow."
            ],

            "important_note": "This is a proposed learning project."
        })

    if "Model Evaluation" in missing_skills:

        recommendations.append({
            "project": "AgentEval – Evaluation Metrics Extension",
            "type": "Extend an existing project",

            "description": (
                "Improve the existing AgentEval platform with "
                "additional measurable evaluation criteria "
                "and detailed model comparison reports."
            ),

            "skills_addressed": ["Model Evaluation"],

            "suggested_tasks": [
                "Add retrieval precision and recall where applicable.",
                "Measure response latency.",
                "Track token usage and estimated model cost.",
                "Compare model quality across identical test cases.",
                "Create regression reports between model versions."
            ],

            "important_note": (
                "The existing AgentEval project already demonstrates "
                "LLM-as-a-judge and rule-based evaluation. These tasks "
                "are proposed extensions, not claims about existing features."
            )
        })

    if "Deep Learning" in missing_skills:

        recommendations.append({
            "project": "Deep Learning Fundamentals Experiment",
            "type": "New learning project",

            "description": (
                "Build a small neural network experiment to "
                "demonstrate practical deep learning fundamentals."
            ),

            "skills_addressed": ["Deep Learning"],

            "suggested_tasks": [
                "Choose a suitable beginner dataset.",
                "Build and train a neural network.",
                "Evaluate model performance.",
                "Document the architecture and results."
            ],

            "important_note": "This is a proposed learning project."
        })

    if not recommendations:

        recommendations.append({
            "project": "Improve Existing Portfolio Projects",
            "type": "Portfolio improvement",

            "description": (
                "No missing skills were detected from the supplied "
                "job description. Improve the documentation, testing, "
                "demonstrations and technical explanations of existing projects."
            ),

            "skills_addressed": [],

            "suggested_tasks": [
                "Improve project README files.",
                "Add architecture diagrams.",
                "Document testing and evaluation results.",
                "Prepare clear project demonstrations."
            ],

            "important_note": (
                "No new project is necessary based on the detected skill gaps."
            )
        })

    return recommendations


def build_recommendation_report(skill_analysis, recommendations):

    lines = []

    lines.append("PROJECT INTELLIGENCE REPORT")
    lines.append("=" * 45)

    lines.append("\n1. JOB SKILL ANALYSIS")

    lines.append(
        "Required skills: "
        + ", ".join(skill_analysis["required_skills"])
    )

    lines.append("\n2. VERIFIED CANDIDATE SKILLS")

    lines.append(
        "Matched skills: "
        + (
            ", ".join(skill_analysis["matched_skills"])
            or "None detected"
        )
    )

    lines.append(
        "\nSkill coverage: "
        + str(skill_analysis["skill_coverage_percentage"])
        + "%"
    )

    lines.append("\n3. MISSING OR UNVERIFIED SKILLS")

    missing = skill_analysis["missing_or_unverified_skills"]

    lines.append(
        ", ".join(missing)
        if missing
        else "No missing skills detected."
    )

    lines.append("\n4. EXISTING PORTFOLIO PROJECTS")

    for project in CANDIDATE_PROFILE["projects"]:
        lines.append("- " + project)

    lines.append("\n5. RECOMMENDED PROJECT IMPROVEMENTS")

    for index, project in enumerate(recommendations, start=1):

        lines.append(
            f"\n{index}. {project['project']}"
        )

        lines.append(
            "Type: " + project["type"]
        )

        lines.append(
            "Description: " + project["description"]
        )

        lines.append(
            "Skills addressed: "
            + (
                ", ".join(project["skills_addressed"])
                or "General portfolio improvement"
            )
        )

        lines.append("Suggested tasks:")

        for task in project["suggested_tasks"]:
            lines.append("- " + task)

        lines.append(
            "Note: " + project["important_note"]
        )

    lines.append("\n6. IMPORTANT")

    lines.append(
        "Recommendations describe future learning or project extensions. "
        "They must not be presented as completed experience on a CV."
    )

    return "\n".join(lines)


def recommend_projects(
    job_description: str,
    candidate_skills=None,
    candidate_projects=None,
):

    required_skills = detect_required_skills(job_description)

    skill_analysis = compare_candidate_skills(required_skills, candidate_skills)

    recommendations = generate_project_recommendations(
        skill_analysis["missing_or_unverified_skills"]
    )

    report = build_recommendation_report(
        skill_analysis,
        recommendations
    )

    return {
        "agent": "Project Intelligence",
        "skill_analysis": skill_analysis,
        "existing_projects": candidate_projects if candidate_projects is not None else CANDIDATE_PROFILE["projects"],
        "recommendations": report,
        "recommended_projects": recommendations
    }

    required_skills = detect_required_skills(
        job_description
    )

    skill_analysis = compare_candidate_skills(
        required_skills
    )

    prompt = f"""
You are CareerPilot AI's Project Intelligence Agent.

Your responsibility is to help a student develop
the technical skills needed for AI, ML and Data roles.

VERIFIED CANDIDATE PROFILE:

{CANDIDATE_PROFILE}

TARGET JOB DESCRIPTION:

{job_description}

PROGRAMMATIC SKILL ANALYSIS:

{skill_analysis}

EXISTING PROJECTS:

{CANDIDATE_PROFILE["projects"]}

YOUR TASKS:

1. Explain the most important skills in the job description.
2. Explain which skills the candidate already demonstrates.
3. Explain which skills are missing or unverified.
4. Recommend exactly 3 practical portfolio projects.
5. Explain which skill gaps each project addresses.
6. Explain why each project is different from existing projects.
7. Recommend the best project to build first.
8. Create a beginner-friendly implementation roadmap.
9. Suggest relevant technologies for each project.
10. Explain how each project could strengthen the candidate's CV.

STRICT ACCURACY RULES:

- Treat the programmatic skill analysis as authoritative.
- Never add a missing skill to the candidate's verified skills.
- Do not claim the candidate has professional AI/ML experience.
- Do not invent job-market statistics or hiring trends.
- Do not invent project achievements or performance metrics.
- Do not recommend duplicates of existing projects.
- Distinguish between missing and unverified skills.
- Recommend realistic projects that can be completed
  in approximately 1-2 weeks.
- Do not guarantee that a project will lead to employment.

OUTPUT FORMAT:

1. Job Skill Analysis
2. Candidate Skill Coverage
3. Missing and Unverified Skills
4. Three Recommended Portfolio Projects
5. Best Project to Build First
6. Implementation Roadmap
7. CV Improvement Suggestions

Prioritise accuracy, practical learning and career relevance.
"""

    ai_recommendations = get_ai_response(prompt, think=True, timeout=900)

    return {
        "agent": "Project Intelligence",
        "skill_analysis": skill_analysis,
        "existing_projects": CANDIDATE_PROFILE["projects"],
        "recommendations": ai_recommendations
    }
