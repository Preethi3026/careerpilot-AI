import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.agents import application_manager
from app.main import app


class CareerStorageTests(unittest.TestCase):
    def test_candidate_profile_survives_api_round_trip(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(application_manager, "DATABASE", Path(folder) / "careerpilot.db"):
            client = TestClient(app)
            profile = {
                "full_name": "Test Candidate", "email": "candidate@example.test", "phone": "",
                "resume_text": "Candidate provided resume content persisted locally.",
                "skills": "Python, SQL", "education": "MSc Data Science", "university": "Example University",
                "experience": "Academic projects", "projects": "Portfolio project A", "certifications": "",
                "languages": "English", "preferred_job_titles": "AI Intern", "preferred_location": "Berlin",
                "preferred_job_type": "internship", "career_goals": "Build responsible ML systems",
            }
            saved = client.put("/api/profile", json=profile)
            loaded = client.get("/api/profile")
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(loaded.json()["profile"], profile)

    def test_workflow_history_reopens_the_saved_package(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(application_manager, "DATABASE", Path(folder) / "careerpilot.db"), patch("app.main.execute_career_workflow", return_value={"keyword": "Data Intern", "summary": {"selected_jobs": 1}, "selected_jobs": [{"resume": "saved draft"}]}):
            client = TestClient(app)
            created = client.post("/api/career-workflow", json={"job_description": "Data internship", "resume_text": "A sufficiently long candidate resume for persistence checks."})
            listing = client.get("/api/workflow-history")
            reopened = client.get(f"/api/workflow-history/{created.json()['history_id']}")
        self.assertEqual(created.status_code, 200)
        self.assertEqual(len(listing.json()["workflows"]), 1)
        self.assertEqual(reopened.json()["result"]["selected_jobs"][0]["resume"], "saved draft")

    def test_tracker_saves_documents_and_allows_user_status_updates(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(application_manager, "DATABASE", Path(folder) / "careerpilot.db"):
            client = TestClient(app)
            created = client.post("/api/applications", json={
                "company": "Example AI", "role": "ML Intern", "job_url": "https://example.test/job",
                "status": "Documents Prepared", "location": "Berlin", "source": "Test Source",
                "match_score": 82, "resume": "Resume draft", "cover_letter": "Letter draft",
            })
            application_id = created.json()["application"]["id"]
            listed = client.get("/api/applications").json()["applications"][0]
            updated = client.put(f"/api/applications/{application_id}", json={"status": "Applied"})
            blocked = client.post("/api/applications", json={"company": "Another", "role": "Role", "status": "Applied"})
        self.assertEqual(listed["status"], "Documents Prepared")
        self.assertEqual(listed["match_score"], 82)
        self.assertEqual(listed["resume"], "Resume draft")
        self.assertTrue(updated.json()["result"]["success"])
        self.assertEqual(blocked.status_code, 400)


if __name__ == "__main__":
    unittest.main()
