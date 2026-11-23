from app.core.llm import get_ai_response


# ============================================================
# 1. VERIFIED CANDIDATE PROFILE
# ============================================================

CANDIDATE_PROFILE = """
VERIFIED CANDIDATE PROFILE

Education:
Currently pursuing a Master's in Big Data and Artificial
Intelligence at SRH University, Berlin.
Expected completion: October 2027.

Experience:
2 years of frontend development experience.
This is not professional AI/ML experience.

Verified Technical Skills:
Python, Machine Learning, Generative AI, LLMs, RAG,
FAISS, Ollama, LangChain, LangGraph, FastAPI,
SQL, React, TypeScript, Data Analysis, Embeddings,
Vector Search and AI Agents.

VERIFIED PROJECT EXPERIENCE:

1. Production RAG System:
- BGE embeddings.
- FAISS vector search.
- Ollama with Llama 3.1.
- 244-page Microsoft Azure documentation corpus.
- 33 tests passed.

2. Agent with Tools and Observability:
- LangGraph.
- Langfuse.
- Weather API.
- FAISS knowledge base.
- SQLite customer database.
- Guardrails and retries.

3. AgentEval:
- Streamlit application.
- Ollama models.
- LLM-as-a-judge evaluation.
- Rule-based evaluation.
- Model comparisons.

4. Cross-Cloud Anomaly Detection:
- Project title is known.
- Specific implementation details and technologies
  have not been verified.
"""


# ============================================================
# 2. GLOBAL ACCURACY RULES
# ============================================================

GLOBAL_RULES = """
IMPORTANT ACCURACY RULES:

1. Never invent candidate experience, responsibilities,
   achievements, project features or performance metrics.

2. Never describe the candidate as an experienced
   AI/ML engineer.

3. The candidate has 2 years of frontend development
   experience, not 2 years of AI/ML experience.

4. Use only the verified skills and project details
   provided in the candidate profile.

5. Do not invent project architecture, technologies,
   deployment methods or business results.

6. Do not claim LangGraph was used for model evaluation.

7. Do not associate a technology with a project unless
   that association is verified.

8. Cross-Cloud Anomaly Detection is a known project title,
   but its implementation details are not verified.

9. Do not invent academic grades, certifications,
   employers or internship experience.

10. Keep the preparation suitable for an internship-level
    candidate.
"""


# ============================================================
# 3. GENERAL AI SECTION GENERATOR
# ============================================================

def generate_section(
    section_title,
    instructions,
    job_role,
    job_description
):

    prompt = f"""
You are CareerPilot AI, an accurate interview preparation assistant.

TARGET ROLE:
{job_role}

JOB DESCRIPTION:
{job_description}

VERIFIED CANDIDATE PROFILE:
{CANDIDATE_PROFILE}

{GLOBAL_RULES}

SECTION:
{section_title}

INSTRUCTIONS:
{instructions}

STRICT OUTPUT RULES:

1. Generate questions only unless answers are explicitly requested.
2. Never write answers from the candidate's perspective.
3. Never claim the candidate used a technology in a project
   unless the profile explicitly confirms it.
4. Never mention LangEval. The candidate's evaluation
   project is called AgentEval.
5. Never associate LangGraph with model evaluation.
6. Do not invent metrics, achievements or project details.
7. Do not assume experience with technologies just because
   they appear in the job description.
8. Generate exactly the requested number of questions.
9. Use clear numbering.
10. Do not add unnecessary introductions or conclusions.

Return only the requested content.
"""

    return get_ai_response(prompt).strip()


# ============================================================
# 4. PROJECT INTERVIEW SECTION
# ============================================================

def generate_project_section():

    return """
### Section 3: Project Interview

#### Project 1: Production RAG System

**Q1. Can you explain your Production RAG System?**

Answer:
I built a Retrieval-Augmented Generation application that
answers questions using a Microsoft Azure documentation
dataset. The project uses BGE embeddings, FAISS for
similarity search, and Ollama with Llama 3.1 to generate
answers based on retrieved information.

**Q2. Why did you use FAISS?**

Answer:
FAISS is used for vector similarity search. It helps
retrieve relevant document chunks based on the similarity
between the user's question and the stored embeddings.

**Q3. What is the role of embeddings in your project?**

Answer:
Embeddings convert text into numerical vectors. These
vectors allow the system to compare the meaning of a
question with the meaning of document chunks.

**Q4. How did you test the application?**

Answer:
The project has 33 passing tests. These tests help verify
that the application's components behave as expected.

---

#### Project 2: Agent with Tools and Observability

**Q1. Can you explain your Agent with Tools project?**

Answer:
I developed an AI agent using LangGraph. The project
connects the agent with tools such as a Weather API,
a FAISS knowledge base and a SQLite customer database.
It also includes guardrails, retries and Langfuse
observability.

**Q2. Why did you use LangGraph?**

Answer:
LangGraph helps structure an agent's workflow into
connected steps. It makes it possible to define how
the agent processes requests and interacts with tools.

**Q3. What is observability in an AI application?**

Answer:
Observability helps developers understand what happens
inside an application. It can help inspect execution,
identify errors and understand the behaviour of the system.

**Q4. What is the purpose of guardrails and retries?**

Answer:
Guardrails help enforce rules around an agent's behaviour.
Retries allow certain operations to be attempted again
when they fail.

---

#### Project 3: AgentEval

**Q1. What is AgentEval?**

Answer:
AgentEval is a model evaluation and benchmarking
application I developed using Streamlit and Ollama.
It compares AI models using LLM-as-a-judge evaluation,
rule-based evaluation and model comparisons.

**Q2. Why is model evaluation important?**

Answer:
Model evaluation helps determine whether a model produces
useful and reliable responses. It is especially important
when comparing models or changing the model used by an
AI application.

**Q3. What is LLM-as-a-judge?**

Answer:
LLM-as-a-judge uses another language model to evaluate
a generated response against evaluation criteria.

**Q4. What is rule-based evaluation?**

Answer:
Rule-based evaluation checks responses using predefined
conditions. It can be used to verify specific expected
facts or required behaviour.

---

#### Project 4: Cross-Cloud Anomaly Detection

**Q1. Can you explain the objective of your
Cross-Cloud Anomaly Detection project?**

Answer:
The project is titled Cross-Cloud Anomaly Detection.
I would explain its implementation, technologies and
results using the actual project details rather than
claiming features that have not been verified.
"""


# ============================================================
# 5. HR INTERVIEW SECTION
# ============================================================

def generate_hr_section():

    return """
### Section 4: HR Interview Questions

**Q1. Tell me about yourself.**

Answer:
I am currently pursuing a Master's degree in Big Data
and Artificial Intelligence at SRH University in Berlin.
I also have two years of frontend development experience.
Alongside my studies, I have been developing projects
in areas such as RAG applications, AI agents and model
evaluation. I am looking for an opportunity to apply
my knowledge and gain practical experience in AI and
machine learning.

**Q2. Why are you interested in this internship?**

Answer:
I want to gain practical experience working on real-world
AI and machine learning problems. This internship would
allow me to apply what I am learning during my Master's
degree, improve my technical skills and learn from
experienced engineers.

**Q3. What are your strengths?**

Answer:
I have frontend development experience and enjoy learning
new technologies. I am interested in understanding how
AI applications work and building practical projects.
I am also comfortable learning independently and
improving through hands-on practice.

**Q4. What is one area you are working to improve?**

Answer:
I am continuing to strengthen my practical experience
in machine learning and AI engineering. I am working
on projects to improve my understanding of these areas.

**Q5. When will you complete your Master's degree?**

Answer:
I am currently pursuing my Master's in Big Data and
Artificial Intelligence at SRH University in Berlin.
My expected completion date is October 2027.

**Q6. How many years of professional experience do you have?**

Answer:
I have two years of frontend development experience.
My AI and machine learning experience comes from
my academic learning and personal projects.
"""


# ============================================================
# 6. TECHNICAL REVISION SECTION
# ============================================================

def generate_revision_section():

    return """
### Section 5: Technical Revision

**1. Python — Verified Skill**

Topics:
- Lists, tuples, sets and dictionaries.
- Functions and classes.
- Loops and conditional statements.
- Exception handling.
- List comprehensions.
- Basic coding problems.

**2. Machine Learning — Verified Skill**

Topics:
- Supervised and unsupervised learning.
- Classification and regression.
- Training and testing datasets.
- Overfitting and underfitting.
- Model evaluation metrics.

**3. Generative AI — Verified Skill**

Topics:
- What is Generative AI?
- How generative models work.
- Common use cases.
- Limitations of generative models.

**4. Large Language Models — Verified Skill**

Topics:
- What is an LLM?
- Tokens and context windows.
- Temperature and model parameters.
- Prompt engineering.
- Hallucinations and limitations.

**5. Retrieval-Augmented Generation — Verified Skill**

Topics:
- What is RAG?
- Document loading and text splitting.
- Chunking strategies.
- Embeddings.
- Retrieval and generation.
- RAG versus fine-tuning.

**6. Embeddings and FAISS — Verified Skills**

Topics:
- What are vector embeddings?
- Semantic similarity.
- Vector search.
- Similarity search with FAISS.
- Why vector databases are useful.

**7. LangChain and LangGraph — Verified Skills**

Topics:
- What is LangChain?
- What is LangGraph?
- How AI agents use tools.
- How workflows can be represented as graphs.
- Differences between chains and agent workflows.

Note:
LangGraph is verified in the Agent with Tools project.
Do not assume additional project usage that is not
listed in the candidate profile.

**8. Model Evaluation — Verified Project Experience**

Topics:
- Why evaluate AI models?
- LLM-as-a-judge.
- Rule-based evaluation.
- Comparing model responses.
- Evaluation criteria and test cases.
- Why model comparisons are useful.

Related project:
AgentEval — Streamlit, Ollama, LLM-as-a-judge,
rule-based evaluation and model comparisons.
"""


# ============================================================
# 7. QUESTIONS TO ASK THE INTERVIEWER
# ============================================================

def generate_interviewer_questions(
    job_role,
    job_description
):

    return generate_section(
        section_title="Questions the Candidate Can Ask the Interviewer",

        instructions="""
Generate exactly 4 thoughtful questions that the candidate
can ask the interviewer at the end of the interview.

These must be questions asked BY THE CANDIDATE TO THE
INTERVIEWER.

Suitable topics:
- The team's current AI/ML projects.
- Technologies used by the team.
- Expectations for the internship.
- Mentorship and learning opportunities.

Do not generate questions that an interviewer would ask
the candidate.

Questions only. No explanations or answers.
""",

        job_role=job_role,
        job_description=job_description
    )


# ============================================================
# 8. MOCK INTERVIEW SECTION
# ============================================================

def generate_mock_interview(
    job_role,
    job_description
):

    prompt = f"""
You are conducting a mock interview for an internship.

ROLE:
{job_role}

JOB DESCRIPTION:
{job_description}

CANDIDATE PROFILE:
{CANDIDATE_PROFILE}

Generate EXACTLY 6 interview questions.

Include:

1. One Python question.
2. One Machine Learning question.
3. One Generative AI or LLM question.
4. One RAG or vector search question.
5. One question about a verified candidate project.
6. One HR or internship motivation question.

RULES:

- Questions only.
- Do not generate answers.
- Do not invent candidate experience.
- Do not invent project implementation details.
- Do not assume technologies were used in projects
  unless verified.
- Number questions from 1 to 6.
- Do not generate additional questions.
- Do not add explanations or introductions.

Return only the six questions.
"""

    return get_ai_response(prompt).strip()


# ============================================================
# 9. MAIN INTERVIEW PREPARATION FUNCTION
# ============================================================

def generate_interview_questions(
    job_role,
    job_description
):

    sections = []

    # Section 1: Technical Interview

    sections.append(
        "### Section 1: Technical Interview\n\n"
        + generate_section(
            section_title="Technical Interview Questions",

            instructions="""
Generate exactly 5 technical interview questions
based on the job description.

Focus on the most relevant technologies and concepts.

Questions only. Do not generate answers.
""",

            job_role=job_role,
            job_description=job_description
        )
    )

    # Section 2: Python and Coding

    sections.append(
        "### Section 2: Python and Coding Interview\n\n"
        + generate_section(
            section_title="Python and Coding Questions",

            instructions="""
Generate exactly 3 beginner-to-intermediate Python
coding questions suitable for an AI/ML internship.

For each question, include:
1. The coding problem.
2. A correct Python solution.
3. A short explanation of the solution.

Questions should use Python fundamentals, lists,
strings, loops or dictionaries.

Ensure that the code is logically correct.
If using reduce(), include the required import.
""",

            job_role=job_role,
            job_description=job_description
        )
    )

    # Section 3: Project Interview

    sections.append(
        generate_project_section()
    )

    # Section 4: HR Interview

    sections.append(
        generate_hr_section()
    )

    # Section 5: Technical Revision

    sections.append(
        generate_revision_section()
    )

    # Section 6: Questions for the Interviewer

    sections.append(
        "### Section 6: Questions to Ask the Interviewer\n\n"
        + generate_interviewer_questions(
            job_role,
            job_description
        )
    )

    # Section 7: Mock Interview

    sections.append(
        "### Section 7: Mock Interview\n\n"
        + generate_mock_interview(
            job_role,
            job_description
        )
    )

    return "\n\n".join(sections)