import httpx
import re
import socket
import ipaddress

from html import unescape
from html.parser import HTMLParser
from urllib.parse import urlparse

from app.core.llm import get_ai_response


# ============================================================
# 1. WEBSITE TEXT EXTRACTOR
# ============================================================

class WebsiteTextExtractor(HTMLParser):

    SKIP_TAGS = {
        "script", "style", "nav", "footer",
        "header", "noscript", "svg"
    }

    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP_TAGS:
            self.skip_depth += 1

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS and self.skip_depth > 0:
            self.skip_depth -= 1

    def handle_data(self, data):
        if self.skip_depth == 0:
            text = data.strip()
            if text:
                self.text_parts.append(text)


# ============================================================
# 2. URL VALIDATION
# ============================================================

def validate_company_url(company_url):

    if not company_url.startswith(("https://", "http://")):
        company_url = "https://" + company_url

    parsed = urlparse(company_url)

    if parsed.scheme not in ("https", "http"):
        raise ValueError("Only HTTP and HTTPS URLs are supported.")

    if not parsed.hostname:
        raise ValueError("Invalid company website URL.")

    if parsed.username or parsed.password:
        raise ValueError("URLs containing credentials are not allowed.")

    if parsed.port not in (None, 80, 443):
        raise ValueError("Unsupported website port.")

    addresses = socket.getaddrinfo(
        parsed.hostname,
        None,
        type=socket.SOCK_STREAM
    )

    if not addresses:
        raise ValueError("Website hostname could not be resolved.")

    for address in addresses:

        ip = ipaddress.ip_address(address[4][0])

        if not ip.is_global:
            raise ValueError(
                "Private or local network addresses are not allowed."
            )

    return company_url


# ============================================================
# 3. FETCH COMPANY WEBSITE
# ============================================================

def fetch_company_website(company_url):

    try:

        company_url = validate_company_url(company_url)

        response = httpx.get(
            company_url,
            timeout=15,
            follow_redirects=False,
            headers={
                "User-Agent": "Mozilla/5.0 CareerPilotAI/1.0"
            }
        )

        if response.status_code in (301, 302, 303, 307, 308):

            return {
                "success": False,
                "content": "",
                "message": "Website redirected. Provide the final URL."
            }

        response.raise_for_status()

        content_type = response.headers.get(
            "content-type", ""
        ).lower()

        if "text/html" not in content_type:

            return {
                "success": False,
                "content": "",
                "message": "The URL did not return an HTML page."
            }

        parser = WebsiteTextExtractor()
        parser.feed(response.text)

        clean_parts = []
        seen = set()

        for part in parser.text_parts:

            part = unescape(part)
            part = re.sub(r"\s+", " ", part).strip()

            if len(part) < 25:
                continue

            normalized = part.lower()

            if normalized not in seen:

                seen.add(normalized)
                clean_parts.append(part)

        if not clean_parts:

            return {
                "success": False,
                "content": "",
                "message": "No readable website content found."
            }

        website_text = "\n".join(clean_parts)

        return {
            "success": True,
            "content": website_text[:12000],
            "message": "Website content retrieved successfully."
        }

    except Exception as error:

        return {
            "success": False,
            "content": "",
            "message": str(error)
        }




# TECHNOLOGY DATABASE

TECHNOLOGIES = {

    "Programming Languages": [
        "Python", "Java", "JavaScript",
        "TypeScript", "C++", "Go", "Rust"
    ],

    "AI and Machine Learning": [
        "Artificial Intelligence",
        "Machine Learning",
        "Deep Learning",
        "Generative AI",
        "Neural Networks",
        "Natural Language Processing",
        "Computer Vision",
        "LLM",
        "Large Language Models",
        "Transformers",
        "AI Models",
        "AI Agents"
    ],

    "AI Frameworks": [
        "PyTorch", "TensorFlow", "Keras",
        "Scikit-learn", "Hugging Face",
        "LangChain", "LangGraph"
    ],

    "Cloud and Infrastructure": [
        "AWS", "Amazon Web Services",
        "Microsoft Azure", "Google Cloud",
        "Docker", "Kubernetes"
    ],

    "Databases and Data": [
        "SQL", "PostgreSQL", "MongoDB",
        "BigQuery", "Apache Spark",
        "Redis", "Elasticsearch"
    ],

    "Web Technologies": [
        "React", "Angular", "Vue",
        "Node.js", "FastAPI", "Django"
    ]
}
def detect_technologies(text):

    detected = {}
    text_lower = text.lower()

    for category, technology_list in TECHNOLOGIES.items():

        found = []

        for technology in technology_list:

            pattern = (
                r"(?<![a-z0-9])"
                + re.escape(technology.lower())
                + r"(?![a-z0-9])"
            )

            if re.search(pattern, text_lower):
                found.append(technology)

        if found:
            detected[category] = found

    return detected


# ============================================================
# 5. AI PRODUCT DETECTION
# ============================================================

AI_PRODUCTS = [
    "Gemini",
    "Project Genie",
    "Google AI",
    "Vertex AI",
    "ChatGPT",
    "Copilot",
    "Claude",
    "Amazon Bedrock",
    "Azure AI"
]


def detect_ai_products(text):

    found = []
    text_lower = text.lower()

    for product in AI_PRODUCTS:

        pattern = (
            r"(?<![a-z0-9])"
            + re.escape(product.lower())
            + r"(?![a-z0-9])"
        )

        if re.search(pattern, text_lower):
            found.append(product)

    return found


# ============================================================
# 6. COMPANY INDUSTRY DETECTION
# ============================================================

INDUSTRY_KEYWORDS = {

    "Artificial Intelligence": [
        "artificial intelligence",
        "machine learning",
        "generative ai",
        "large language models",
        "neural networks",
        "deep learning",
        "ai models",
        "ai research",
        "ai-powered",
        "ai agent",
        "ai agents"
    ],

    "Cloud Computing": [
        "cloud computing",
        "cloud infrastructure",
        "cloud services",
        "cloud platform"
    ],

    "Software and Technology": [
        "software",
        "technology",
        "digital products",
        "software platform",
        "developer tools"
    ],

    "E-commerce": [
        "e-commerce",
        "online shopping",
        "marketplace",
        "online store"
    ],

    "Finance and Banking": [
        "financial services",
        "banking",
        "payments",
        "financial technology"
    ],

    "Healthcare": [
        "healthcare",
        "medical technology",
        "health services",
        "digital health"
    ],

    "Automotive": [
        "automotive",
        "electric vehicles",
        "vehicle technology",
        "mobility"
    ],

    "Telecommunications": [
        "telecommunications",
        "wireless networks",
        "mobile network",
        "connectivity"
    ]
}


def detect_company_industry(text):

    detected_industries = []
    text_lower = text.lower()

    for industry, keywords in INDUSTRY_KEYWORDS.items():

        for keyword in keywords:

            if keyword in text_lower:
                detected_industries.append(industry)
                break

    return detected_industries


# ============================================================
# 7. ROLE RELEVANCE ANALYSIS
# ============================================================
def analyze_role_relevance(
    job_role,
    industries,
    website_text
):

    role_lower = job_role.lower()
    website_lower = website_text.lower()

    # AI / ML ROLES

    ai_role_keywords = [
        "ai",
        "artificial intelligence",
        "machine learning",
        "ml",
        "deep learning",
        "data science"
    ]

    ai_website_keywords = [
        "artificial intelligence",
        "machine learning",
        "generative ai",
        "ai models",
        "ai research",
        "deep learning",
        "neural networks",
        "gemini",
        "project genie",
        "large language models"
    ]

    if any(keyword in role_lower for keyword in ai_role_keywords):

        matching_evidence = [
            keyword
            for keyword in ai_website_keywords
            if keyword in website_lower
        ]

        if matching_evidence:

            return (
                "Potential relevance identified for this AI/ML role. "
                "The supplied company website contains AI-related "
                "evidence: "
                + ", ".join(matching_evidence[:5])
                + ". This does not confirm that the hiring team "
                "works on these products or technologies."
            )

    # SOFTWARE ENGINEERING ROLES

    software_role_keywords = [
        "software engineer",
        "software developer",
        "backend developer",
        "frontend developer"
    ]

    software_website_keywords = [
        "software",
        "developer tools",
        "programming",
        "engineering"
    ]

    if any(keyword in role_lower for keyword in software_role_keywords):

        if any(
            keyword in website_lower
            for keyword in software_website_keywords
        ):

            return (
                "Potential relevance identified for a software "
                "engineering role based on website mentions of "
                "software and development activities."
            )

    # DATA SCIENCE ROLES

    data_role_keywords = [
        "data scientist",
        "data science",
        "data analyst"
    ]

    data_website_keywords = [
        "data science",
        "data analytics",
        "data analysis",
        "statistics"
    ]

    if any(keyword in role_lower for keyword in data_role_keywords):

        if any(
            keyword in website_lower
            for keyword in data_website_keywords
        ):

            return (
                "Potential relevance identified for a data-related "
                "role based on website evidence."
            )

    return (
        "Insufficient website evidence to establish a connection "
        "between the company's published activities and this role."
    )


# ============================================================
# 8. GENERIC WEBSITE EVIDENCE EXTRACTION
# ============================================================

def extract_website_evidence(website_text):

    snippets = [
        line.strip()
        for line in website_text.splitlines()
        if line.strip()
    ]

    overview_keywords = [
        "about", "company", "mission",
        "vision", "our story", "who we are"
    ]

    product_keywords = [
        "product", "service", "platform",
        "solution", "software", "application"
    ]

    ai_keywords = [
        "artificial intelligence",
        "machine learning",
        "generative ai",
        " ai ", "llm",
        "deep learning",
        "neural network",
        "gemini",
        "project genie"
    ]

    def select_snippets(keywords, limit=5):

        results = []

        for snippet in snippets:

            text = snippet.lower()

            if any(keyword in text for keyword in keywords):

                if len(snippet) > 350:
                    snippet = snippet[:347] + "..."

                if snippet not in results:
                    results.append(snippet)

            if len(results) >= limit:
                break

        return results

    return {
        "overview": select_snippets(overview_keywords),
        "products": select_snippets(product_keywords),
        "ai": select_snippets(ai_keywords)
    }


# ============================================================
# 9. AI INTERVIEW PREPARATION
# ============================================================

def generate_interview_preparation(job_role):

    prompt = f"""
You are a career interview preparation assistant.

Target role: {job_role}

Generate general interview preparation.

Include:

1. Five technical topics to study.
2. Five likely technical interview questions.
3. Five questions to ask the interviewer.
4. Five practical preparation recommendations.

Do not invent company-specific facts.

Do not claim these are official interview questions
or confirmed hiring requirements.

Keep the response concise and professional.
"""

    try:

        result = get_ai_response(prompt)

        if result and result.strip():
            return result

        return "AI interview preparation was unavailable."

    except Exception:

        return "AI interview preparation was unavailable."


# ============================================================
# 10. GENERATE COMPANY RESEARCH REPORT
# ============================================================
def generate_research_report(
    company,
    job_role,
    website_text,
    technologies
):

    evidence = extract_website_evidence(website_text)

    ai_products = detect_ai_products(website_text)

    industries = detect_company_industry(website_text)

    role_relevance = analyze_role_relevance(
        job_role,
        industries,
        website_text
    )

    interview_preparation = generate_interview_preparation(
        job_role
    )

    report = []

    # COMPANY OVERVIEW

    report.append("\n1. COMPANY OVERVIEW")

    if evidence["overview"]:
        for item in evidence["overview"]:
            report.append(f"- {item}")
    else:
        report.append("No relevant overview information identified.")

    # PRODUCTS AND SERVICES

    report.append("\n2. PRODUCTS AND SERVICES")

    if evidence["products"]:
        for item in evidence["products"]:
            report.append(f"- {item}")
    else:
        report.append("No relevant products or services identified.")

    # INDUSTRY

    report.append("\n3. COMPANY INDUSTRY")

    if industries:
        for industry in industries:
            report.append(f"- {industry}")
    else:
        report.append(
            "No industry keywords identified in the website content."
        )

    report.append(
        "Note: Industry classification is keyword-based "
        "and requires independent verification."
    )

    # TECHNOLOGIES

    report.append("\n4. TECHNOLOGIES")

    if technologies:
        for category, technology_list in technologies.items():
            report.append(f"\n{category}:")
            for technology in technology_list:
                report.append(f"- {technology}")
    else:
        report.append(
            "No technologies from the predefined detection list "
            "were found in the extracted website text."
        )

    # AI PRODUCTS

    report.append("\n5. IDENTIFIED AI PRODUCTS")

    if ai_products:
        for product in ai_products:
            report.append(f"- {product}")
    else:
        report.append("No recognized AI products detected.")

    # AI EVIDENCE

    report.append("\n6. AI-RELATED WEBSITE INFORMATION")

    if evidence["ai"]:
        for item in evidence["ai"]:
            report.append(f"- {item}")
    else:
        report.append("No specific AI-related snippets identified.")

    report.append(
        "\nNote: Website mentions do not prove that a technology "
        "is used by the hiring team."
    )

    # ROLE RELEVANCE

    report.append("\n7. ROLE RELEVANCE")
    report.append(f"Target position: {job_role}")
    report.append(role_relevance)

    report.append(
        "Actual internship responsibilities must be checked "
        "against the official job description."
    )

    # INTERVIEW PREPARATION

    report.append("\n8. AI-GENERATED INTERVIEW PREPARATION")

    report.append(
        "These are general AI-generated suggestions, not verified "
        "company-specific hiring requirements."
    )

    report.append(interview_preparation)

    # SOURCES AND LIMITATIONS

    report.append("\n9. SOURCES AND LIMITATIONS")

    report.append("Primary source: Supplied company website.")
    report.append("Website retrieval: Successful.")

    report.append(
        "Company facts are limited to the extracted website text."
    )

    report.append(
        "No independent external sources were consulted."
    )

    return "\n".join(report)


# ============================================================
# 11. MAIN COMPANY RESEARCH FUNCTION
# ============================================================

def research_company(
    company: str,
    job_role: str,
    company_url: str = ""
):

    company = company.strip() or "Company not specified"

    job_role = job_role.strip() or "Role not specified"

    company_url = company_url.strip()

    # CHECK URL

    if not company_url:

        return f"""
COMPANY RESEARCH REPORT
=============================================

Company: {company}
Target Role: {job_role}

Research not started.

Please provide the official company website URL.
"""

    # FETCH WEBSITE

    website_result = fetch_company_website(company_url)

    if not website_result["success"]:

        return f"""
COMPANY RESEARCH REPORT
=============================================

Company: {company}
Target Role: {job_role}

Website retrieval failed.

Reason:
{website_result["message"]}
"""

    website_text = website_result["content"]

    # DETECT TECHNOLOGIES

    technologies = detect_technologies(website_text)

    detected_products = detect_ai_products(website_text)

    detected_industries = detect_company_industry(website_text)

    # GENERATE REPORT

    try:

        report = generate_research_report(
            company=company,
            job_role=job_role,
            website_text=website_text,
            technologies=technologies
        )

        total_technologies = sum(
            len(items)
            for items in technologies.values()
        )

        return f"""
CAREERPILOT AI
COMPANY RESEARCH REPORT
=============================================

Company: {company}
Target Role: {job_role}

SOURCE INFORMATION
---------------------------------------------

Official Website:
{company_url}

Website Retrieval: Successful

Total Technologies Detected:
{total_technologies}

AI Products Detected:
{", ".join(detected_products) if detected_products else "None detected"}

Industries Detected:
{", ".join(detected_industries) if detected_industries else "None detected"}

=============================================

{report}

=============================================

RESEARCH LIMITATIONS

This report uses extracted text from the supplied
company website.

Company-specific information is limited to the
retrieved website content.

AI-generated interview suggestions are general
preparation recommendations, not verified company facts.

The report does not independently verify the current
job vacancy, hiring team, or internal technology stack.
"""

    except Exception as error:

        return f"""
COMPANY RESEARCH REPORT
=============================================

Company: {company}
Target Role: {job_role}

Website Retrieval: Successful

Research Generation: Failed

Reason:
{str(error)}
"""