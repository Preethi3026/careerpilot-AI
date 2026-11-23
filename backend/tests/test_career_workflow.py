import unittest
import tempfile
from unittest.mock import patch
from fastapi.testclient import TestClient

from app import career_workflow as workflow
from app.agents import application_manager
from app.main import app


class CareerWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.request = {
            "keyword": "AI/ML Intern",
            "resume_text": "Candidate profile: Master's student in Data Science. Built machine learning projects in Python with pandas, scikit-learn, TensorFlow, and PyTorch. Developed a FastAPI model inference service.",
            "skills": "Python, Machine Learning, pandas, scikit-learn, TensorFlow, PyTorch, FastAPI",
            "education": "Master's student in Data Science",
            "experience": "Academic machine learning projects",
            "preferred_location": "Any",
            "job_type": "internship",
            "limit": 2,
        }
        self.job = {
            "title": "AI/ML Intern",
            "company": "Fixture AI Labs",
            "location": "Berlin, Germany",
            "description": "AI/ML internship for students enrolled in Data Science or Computer Science. Work on machine learning models using Python, pandas, scikit-learn, TensorFlow and PyTorch. Prior internship not required.",
            "url": "https://fixture.invalid/ai-ml-intern",
            "source": "TEST FIXTURE (not a live listing)",
        }

    def test_ai_ml_fixture_completes_all_agents_and_handoffs(self):
        second_job = {
            **self.job,
            "title": "AI Model Evaluation Intern",
            "company": "Fixture Evaluation Lab",
            "description": "Student internship in Data Science working on AI/ML model evaluation with Python and scikit-learn. Enrolled Master's students welcome.",
            "url": "https://fixture.invalid/model-evaluation-intern",
        }
        selected_job = {**self.job, "company_url": "https://fixture.invalid/company"}
        second_job["company_url"] = "https://fixture.invalid/company"
        with (
            patch.object(workflow, "search_jobs", return_value={"jobs": [selected_job, second_job]}) as hunter,
            patch.object(workflow, "search_remote_jobs", return_value={"jobs": []}),
            patch.object(workflow, "match_job", wraps=workflow.match_job) as matcher,
            patch.object(workflow, "create_resume_package", wraps=workflow.create_resume_package) as resume_agent,
            patch.object(workflow, "generate_cover_letter", wraps=workflow.generate_cover_letter) as cover_agent,
            patch("app.agents.company_researcher.fetch_company_website", return_value={
                "success": True,
                "content": "Fixture AI Labs develops artificial intelligence and machine learning software with Python, TensorFlow, and FastAPI.",
                "message": "Fixture website content loaded.",
            }),
            patch("app.agents.company_researcher.generate_research_report", return_value="Fixture verified report"),
            patch.object(workflow, "research_company", wraps=workflow.research_company) as researcher,
            patch.object(workflow, "review_application", wraps=workflow.review_application) as reviewer,
            patch.object(workflow, "get_applications", return_value=[]) as tracker,
            patch.object(workflow, "get_application_stats", return_value={"total_applications": 0}),
            patch.object(workflow, "recommend_projects", wraps=workflow.recommend_projects) as projects,
        ):
            events = list(workflow.career_workflow_events(self.request))
        result = events[-1]["data"]

        hunter.assert_called_once()
        self.assertEqual(matcher.call_count, 2)
        self.assertEqual({call.args[1] for call in matcher.call_args_list}, {self.job["title"], second_job["title"]})
        self.assertTrue(all("Python" in call.args[2]["skills"] for call in matcher.call_args_list))
        self.assertEqual(resume_agent.call_count, 2)
        self.assertTrue(all(call.kwargs["resume_text"] == self.request["resume_text"] for call in resume_agent.call_args_list))
        self.assertEqual(
            {(call.kwargs["job_title"], call.kwargs["company"]) for call in resume_agent.call_args_list},
            {(self.job["title"], self.job["company"]), (second_job["title"], second_job["company"])},
        )
        self.assertTrue(all("resume_analysis" in item for item in result["selected_jobs"]))
        self.assertEqual(cover_agent.call_count, 2)
        self.assertEqual(
            {tuple(item.args) for item in researcher.call_args_list},
            {(self.job["company"], self.job["title"], "https://fixture.invalid/company"), (second_job["company"], second_job["title"], "https://fixture.invalid/company")},
        )
        self.assertEqual(reviewer.call_count, 2)
        tracker.assert_called_once()
        projects.assert_called_once()

        self.assertEqual(events[-1]["type"], "result")
        self.assertEqual(result["summary"]["selected_jobs"], 2)
        self.assertEqual(result["summary"]["documents_completed"], 2)
        self.assertTrue(all(item["match"]["match_score"] >= 50 for item in result["selected_jobs"]))
        for item in result["selected_jobs"]:
            self.assertIn(self.request["resume_text"], item["resume"])
            self.assertTrue(item["cover_letter"])
            self.assertTrue(item["company_research"])
            self.assertIn("Fixture verified report", item["company_research"])
            self.assertTrue(item["review"])
            self.assertEqual(item["tracking"]["status"], "Ready to save")
        for call, item in zip(cover_agent.call_args_list, result["selected_jobs"]):
            self.assertEqual(call.args[3], item["resume"])
        for call, item in zip(reviewer.call_args_list, result["selected_jobs"]):
            self.assertEqual(call.args[1], item["resume"])
            self.assertEqual(call.args[2], item["cover_letter"])
            self.assertEqual(call.args[3], item["company_research"])
        self.assertFalse(result["application_tracking"]["records_changed"])
        self.assertTrue(result["project_intelligence"])
        self.assertTrue(all(stage["status"] == "completed" for stage in result["stages"].values()))

        working_order = [event["agent_id"] for event in events if event.get("type") == "progress" and event.get("status") == "working"]
        self.assertEqual(working_order, [1, 2, 3, 6, 4, 5, 7, 8])
        self.assertIn("Fixture verified report", cover_agent.call_args_list[0].args[4])

    def test_senior_fixture_is_rejected_and_document_agents_are_skipped(self):
        unsuitable_job = {
            **self.job,
            "title": "Senior AI/ML Engineer",
            "description": "Senior engineering role requiring 8 years of professional machine learning experience, production model ownership, and independent technical leadership.",
        }
        request = {**self.request, "job_type": "any"}
        with (
            patch.object(workflow, "search_jobs", return_value={"jobs": [unsuitable_job]}),
            patch.object(workflow, "search_remote_jobs", return_value={"jobs": []}),
            patch.object(workflow, "create_resume_package") as resume,
            patch.object(workflow, "generate_cover_letter") as cover,
            patch.object(workflow, "get_applications", return_value=[]),
            patch.object(workflow, "get_application_stats", return_value={}),
            patch.object(workflow, "recommend_projects", return_value={}),
        ):
            result = workflow.run_career_workflow(request)
        self.assertEqual(result["selected_jobs"], [])
        resume.assert_not_called()
        cover.assert_not_called()
        self.assertEqual(result["stages"]["Resume Agent"]["status"], "skipped")
        rejected_match = result["jobs_found"][0]
        self.assertTrue(rejected_match["match"]["seniority_mismatch"])
        self.assertIn("Senior", rejected_match["match"]["job_level"])
        self.assertFalse(rejected_match["suitable"])
        self.assertTrue(any("seniority" in reason for reason in rejected_match["rejection_reasons"]))
        self.assertEqual(result["summary"]["documents_completed"], 0)

    def test_zero_jobs_and_invalid_job_description_are_reported_without_crashing(self):
        with (
            patch.object(workflow, "search_jobs", return_value={"jobs": []}),
            patch.object(workflow, "search_remote_jobs", return_value={"jobs": []}),
            patch.object(workflow, "get_applications", return_value=[]),
            patch.object(workflow, "get_application_stats", return_value={}),
            patch.object(workflow, "recommend_projects", return_value={"recommended_projects": []}),
        ):
            empty = workflow.run_career_workflow(self.request)
        self.assertEqual(empty["summary"]["jobs_found"], 0)
        self.assertEqual(empty["summary"]["selected_jobs"], 0)
        self.assertEqual(empty["stages"]["Resume Agent"]["status"], "skipped")
        self.assertEqual(empty["stages"]["Project Intelligence"]["status"], "completed")

        malformed_job = {**self.job, "description": None}
        with (
            patch.object(workflow, "search_jobs", return_value={"jobs": [malformed_job]}),
            patch.object(workflow, "search_remote_jobs", return_value={"jobs": []}),
            patch.object(workflow, "get_applications", return_value=[]),
            patch.object(workflow, "get_application_stats", return_value={}),
            patch.object(workflow, "recommend_projects", return_value={}),
        ):
            malformed = workflow.run_career_workflow(self.request)
        self.assertEqual(malformed["summary"]["selected_jobs"], 0)
        self.assertTrue(malformed["jobs_found"])
        self.assertFalse(malformed["jobs_found"][0]["suitable"])
        self.assertTrue(malformed["jobs_found"][0]["rejection_reasons"])

    def test_missing_resume_is_rejected_with_readable_validation_message(self):
        response = TestClient(app).post(
            "/api/career-workflow/stream",
            json={"keyword": "AI/ML Intern", "skills": "Python"},
        )
        self.assertEqual(response.status_code, 422)
        messages = " ".join(item["msg"] for item in response.json()["detail"])
        self.assertIn("Paste at least 40 characters", messages)

    def test_company_website_failure_is_reported_without_crashing(self):
        with patch("app.agents.company_researcher.fetch_company_website", return_value={
            "success": False,
            "content": "",
            "message": "Connection timed out",
        }):
            report = workflow.research_company(
                "Fixture AI Labs", "AI/ML Intern", "https://fixture.invalid"
            )
        self.assertIn("Website retrieval failed", report)
        self.assertIn("Connection timed out", report)

    def test_interrupted_stream_does_not_start_downstream_agents_or_save_records(self):
        with (
            patch.object(workflow, "search_jobs", return_value={"jobs": [self.job]}) as hunter,
            patch.object(workflow, "search_remote_jobs", return_value={"jobs": []}),
            patch.object(workflow, "match_job", wraps=workflow.match_job),
            patch.object(workflow, "create_resume_package") as resume,
            patch.object(workflow, "get_applications", return_value=[]) as tracker,
            patch.object(workflow, "get_application_stats", return_value={}),
        ):
            stream = workflow.career_workflow_events(self.request)
            self.assertEqual(next(stream)["agent"], "Job Hunter")
            self.assertEqual(next(stream)["status"], "completed")
            self.assertEqual(next(stream)["agent"], "Job Matcher")
            stream.close()

        hunter.assert_called_once()
        resume.assert_not_called()
        tracker.assert_not_called()

    @patch.object(workflow, "recommend_projects", return_value={})
    @patch.object(workflow, "get_application_stats", return_value={})
    @patch.object(workflow, "get_applications", return_value=[])
    @patch.object(workflow, "review_application", return_value="Review continued")
    @patch.object(workflow, "research_company", return_value="Research continued")
    @patch.object(workflow, "generate_cover_letter")
    @patch.object(workflow, "create_resume_package", side_effect=RuntimeError("resume agent unavailable"))
    @patch.object(workflow, "search_remote_jobs", return_value={"jobs": []})
    @patch.object(workflow, "search_jobs")
    def test_agent_failure_is_reported_and_later_stages_continue(self, search_jobs, *_mocks):
        search_jobs.return_value = {"jobs": [self.job]}
        result = workflow.run_career_workflow(self.request)
        self.assertEqual(result["selected_jobs"][0]["errors"], ["Resume Agent: resume agent unavailable"])
        self.assertTrue(any(error["agent"] == "Resume Agent" for error in result["errors"]))
        self.assertEqual(result["stages"]["Resume Agent"]["status"], "failed")
        self.assertEqual(result["stages"]["Cover Letter"]["status"], "skipped")
        self.assertEqual(result["stages"]["Application Reviewer"]["status"], "skipped")
        self.assertEqual(result["stages"]["Project Intelligence"]["status"], "completed")

    def test_stream_endpoint_returns_progress_then_one_result(self):
        events = [
            {"type": "progress", "agent_id": 1, "agent": "Job Hunter", "status": "working", "message": "Searching"},
            {"type": "result", "data": {"selected_jobs": [], "errors": []}},
        ]
        payload = {"keyword": "Data Intern", "resume_text": "A candidate profile with Python and SQL."}
        with patch("app.main.career_workflow_events", return_value=iter(events)):
            response = TestClient(app).post("/api/career-workflow/stream", json=payload)
        self.assertEqual(response.status_code, 200)
        decoded = [__import__("json").loads(line) for line in response.text.splitlines()]
        self.assertEqual([event["type"] for event in decoded], ["progress", "result"])
        self.assertIn("selected_jobs", decoded[-1]["data"])

    def test_stream_endpoint_completes_ai_ml_fixture_pipeline(self):
        with (
            patch.object(workflow, "search_jobs", return_value={"jobs": [{**self.job, "company_url": "https://fixture.invalid/company"}]}),
            patch.object(workflow, "search_remote_jobs", return_value={"jobs": []}),
            patch("app.agents.company_researcher.fetch_company_website", return_value={
                "success": True,
                "content": "Fixture AI Labs develops artificial intelligence and machine learning software with Python, TensorFlow, and FastAPI.",
                "message": "Fixture website content loaded.",
            }),
            patch("app.agents.company_researcher.generate_research_report", return_value="Fixture verified report"),
            patch.object(workflow, "get_applications", return_value=[]),
            patch.object(workflow, "get_application_stats", return_value={"total_applications": 0}),
        ):
            response = TestClient(app).post("/api/career-workflow/stream", json=self.request)

        self.assertEqual(response.status_code, 200)
        decoded = [__import__("json").loads(line) for line in response.text.splitlines()]
        result = decoded[-1]["data"]
        self.assertEqual(decoded[-1]["type"], "result")
        self.assertEqual(result["summary"]["selected_jobs"], 1)
        self.assertTrue(result["selected_jobs"][0]["resume"])
        self.assertTrue(result["selected_jobs"][0]["cover_letter"])
        self.assertEqual(
            [event["agent_id"] for event in decoded if event.get("status") == "working"],
            [1, 2, 3, 6, 4, 5, 7, 8],
        )

    def test_legacy_json_workflow_route_remains_available(self):
        expected = {"agent": "CareerPilot AI Career Assistant", "selected_jobs": []}
        payload = {"company": "Example", "role": "Intern", "job_description": "Python internship"}
        with patch("app.main.execute_career_workflow", return_value=expected):
            response = TestClient(app).post("/api/career-workflow", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

    def test_tracker_saves_as_saved_and_deduplicates_job_urls(self):
        with tempfile.TemporaryDirectory() as directory:
            database = f"{directory}\\applications.db"
            with patch.object(application_manager, "DATABASE", database):
                first = application_manager.add_application(
                    "Example Data", "Data Engineering Intern", "https://jobs.example.test/data-intern"
                )
                duplicate = application_manager.add_application(
                    "Different label", "Duplicate title", "https://jobs.example.test/data-intern"
                )
                applications = application_manager.get_applications()

        self.assertFalse(first["duplicate"])
        self.assertTrue(duplicate["duplicate"])
        self.assertEqual(first["id"], duplicate["id"])
        self.assertEqual(len(applications), 1)
        self.assertEqual(applications[0]["status"], "Saved")


if __name__ == "__main__":
    unittest.main()
