import unittest

from fastapi.testclient import TestClient

from app.agents.resume_agent import create_resume_package, tailor_resume
from app.main import app


class ResumeAgentTests(unittest.TestCase):
    def setUp(self):
        self.resume = """Riya Sharma
riya@example.test | +49 123 4567890

PROFESSIONAL SUMMARY
Frontend developer with experience building React dashboards. MSc student interested in machine learning and language model applications.

TECHNICAL SKILLS
TypeScript, React, Python, RAG, SQL

PROJECTS
React Analytics Dashboard
- Built a React interface for data review.

Python RAG Search
- Implemented retrieval augmented generation with Python and SQL.

EXPERIENCE
Frontend Developer | Example Studio | 2023 - 2025
- Implemented React dashboard components used by the product team.
- Wrote SQL queries to support reporting features.

EDUCATION
MSc Data Science | Example University | Expected 2027
"""
        self.job = """Machine Learning Intern — Example AI
Required skills: Python, RAG, PyTorch, SQL.
Qualifications: Currently enrolled in a Master's degree in Data Science or related field.
Responsibilities: Build retrieval augmented generation prototypes. Evaluate model outputs and collaborate with product engineers.
"""

    def test_tailors_each_section_with_verified_facts_and_structured_gaps(self):
        package = create_resume_package(
            self.job,
            self.resume,
            ["Python", "RAG", "SQL", "React", "TypeScript"],
            job_title="Machine Learning Intern",
            company="Example AI",
        )
        tailored = package["tailored_resume"]

        self.assertIn("Targeting Machine Learning Intern at Example AI", tailored)
        self.assertIn("riya@example.test", tailored)
        self.assertIn("2023 - 2025", tailored)
        self.assertIn("Expected 2027", tailored)
        self.assertIn("Implemented React dashboard components", tailored)
        self.assertIn("Implemented retrieval augmented generation with Python and SQL", tailored)
        self.assertLess(tailored.index("Python RAG Search"), tailored.index("React Analytics Dashboard"))
        self.assertEqual(package["relevant_skills_matched"], ["Machine Learning", "Python", "RAG", "SQL"])
        self.assertEqual(package["missing_skills"], ["PyTorch"])
        self.assertNotIn("PyTorch", tailored)
        self.assertEqual(package["target_job"], {"title": "Machine Learning Intern", "company": "Example AI"})
        self.assertTrue(package["requirements_analyzed"]["qualifications"])
        self.assertTrue(package["requirements_analyzed"]["responsibilities"])
        self.assertTrue(package["changes_made"])
        self.assertNotIn("phone number", " ".join(package["information_needing_candidate_verification"]).lower())

    def test_missing_candidate_information_never_uses_sample_profile(self):
        with self.assertRaisesRegex(ValueError, "no sample profile is substituted"):
            tailor_resume(self.job)

    def test_resume_api_returns_structured_package_and_requires_candidate_source(self):
        client = TestClient(app)
        response = client.post("/api/resume", json={
            "job_description": self.job,
            "resume_text": self.resume,
            "role": "Machine Learning Intern",
            "company": "Example AI",
        })
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertIn("TECHNICAL SKILLS", result["tailored_resume"])
        self.assertEqual(result["target_job"]["company"], "Example AI")
        self.assertEqual(result["missing_skills"], ["PyTorch"])

        missing = client.post("/api/resume", json={"job_description": self.job})
        self.assertEqual(missing.status_code, 422)
        self.assertIn("candidate-provided", missing.json()["detail"])


if __name__ == "__main__":
    unittest.main()
