import json
import threading
import time

import pytest

from app.core.ollama_client import OllamaClient
from app.jobs import profile as profiles


SAMPLE_RESUME = """Alex Example
alex@example.com | +49 123 456 789

PROFESSIONAL SUMMARY
Data engineering student with Python and SQL experience. Built reliable data workflows.

TECHNICAL SKILLS
Programming: Python, SQL
Platforms: AWS

EXPERIENCE
Data Intern, Example Labs | Jun 2024 - Aug 2024
- Built a Python data validation pipeline.
- Reduced manual checks by 25%.

PROJECTS
Forecast Dashboard
- Created a dashboard using Python and React.

EDUCATION
MSc Data Science | Example University | 2023 - 2025

CERTIFICATIONS
- AWS Cloud Practitioner

LANGUAGES
- English: C1
"""


@pytest.fixture
def local_profile_store(tmp_path, monkeypatch):
    monkeypatch.setattr(profiles, "BACKEND_DIR", tmp_path)
    monkeypatch.setattr(profiles, "JOBS_DIR", tmp_path / "data" / "jobs")
    monkeypatch.setattr(profiles, "INPUTS_DIR", tmp_path / "data" / "jobs" / "inputs")
    monkeypatch.setattr(profiles, "ME_DIR", tmp_path / "data" / "jobs" / "me")
    monkeypatch.setattr(profiles, "SCHEMA_PATH", profiles.SCHEMA_PATH)
    return tmp_path


def test_fallback_parser_assigns_stable_fact_and_entry_ids(local_profile_store):
    profile = profiles.profile_from_text(SAMPLE_RESUME)

    assert profile["summary"][0]["id"] == "F001"
    assert profile["skills"][0]["id"] == "S1"
    assert profile["experience"][0]["id"] == "E1"
    assert profile["projects"][0]["id"] == "CP1"
    assert profile["education"][0]["id"] == "ED1"
    fact_ids = [fact["id"] for fact in profiles._fact_records(profile).values()]
    assert len(fact_ids) == len(set(fact_ids))
    assert "alex@example.com" in profile["header"]["contact"][0]


def test_fixes_create_new_profile_versions_and_never_reuse_fact_ids(local_profile_store):
    created = profiles.extract_and_save_profile(SAMPLE_RESUME, "test-resume.txt")
    first_id = created["profile"]["summary"][0]["id"]
    edited = profiles.apply_profile_fixes({
        "set": [{"id": first_id, "text": "Data engineering student with Python, SQL, and documented workflow experience."}],
        "remove": [created["profile"]["experience"][0]["bullets"][1]["id"]],
        "add": [{"to": "summary", "text": "Candidate-provided fact added for review."}],
    })

    assert created["file"].endswith("profile_v1.json")
    assert edited["file"].endswith("profile_v2.json")
    assert edited["profile"]["version"] == 2
    original_fact_ids = [int(identifier[1:]) for identifier in profiles._fact_records(created["profile"])]
    assert int(edited["new_ids"][0][1:]) > max(original_fact_ids)
    assert json.loads((local_profile_store / created["file"]).read_text(encoding="utf-8"))["version"] == 1
    assert (local_profile_store / "data/jobs/me/profile_v2.md").is_file()


def test_profile_fix_rejects_unknown_fact(local_profile_store):
    profiles.extract_and_save_profile(SAMPLE_RESUME)
    with pytest.raises(ValueError, match="No fact or profile entry"):
        profiles.apply_profile_fixes({"remove": ["F999"]})


def test_preferences_defaults_match_search_and_automation_schema(local_profile_store):
    saved = profiles.save_preferences(profiles.PREFERENCES_DEFAULTS)
    preferences = saved["preferences"]

    assert preferences["location"] == "Germany"
    assert preferences["search"]["queries"] == profiles.PREFERENCES_DEFAULTS["search"]["queries"]
    assert preferences["automation"] == {"min_fit": 70, "max_drafts_per_run": 3, "max_matches_per_run": 12, "min_keyword_score": 40}
    assert profiles.get_preferences()["version"] == 1


def test_preferences_reject_invalid_language_level(local_profile_store):
    invalid = {**profiles.PREFERENCES_DEFAULTS, "languages": [{"language": "German", "level": "Fluent"}]}
    with pytest.raises(ValueError, match="level"):
        profiles.save_preferences(invalid)


def test_ollama_payload_supports_schema_thinking_limits_tools_and_keepalive():
    client = OllamaClient(model="qwen3:8b")
    schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}}
    tools = [{"type": "function", "function": {"name": "read_profile", "parameters": {"type": "object"}}}]
    payload = client._payload([{"role": "user", "content": "hello"}], format=schema, think=True, num_predict=400, num_ctx=8192, keep_alive="10m", stream=True, tools=tools)

    assert payload["model"] == "qwen3:8b"
    assert payload["format"] == schema and payload["think"] is True and payload["stream"] is True
    assert payload["options"]["num_predict"] == 400 and payload["options"]["num_ctx"] == 8192
    assert payload["keep_alive"] == "10m" and payload["tools"] == tools


def test_ollama_client_limits_concurrent_calls_to_two():
    client = OllamaClient(max_parallel=2)
    lock = threading.Lock()
    active = 0
    peak = 0

    def run_slot():
        nonlocal active, peak
        with client._slot():
            with lock:
                active += 1
                peak = max(peak, active)
            time.sleep(0.015)
            with lock:
                active -= 1

    threads = [threading.Thread(target=run_slot) for _ in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert peak == 2
