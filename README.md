# CareerPilot AI

CareerPilot AI is a local-first career assistant presented as a pixel-art office. Its Career Assistant runs eight agents in sequence to find early-career roles, compare them with a candidate profile, prepare application documents, review them, and suggest portfolio work. The workflow does not submit applications; a user can choose to save a selected opportunity to the local tracker.

## Highlights

- Live job discovery through Arbeitnow and Remotive, with source failures shown in results.
- Profile-based match scores, role suitability checks, and visible rejection reasons.
- Separate tailored resume and cover letter for each selected opportunity.
- Company research from a user-supplied official company website.
- Review feedback, application tracker status, and project/skill recommendations in one consolidated results panel.
- Streaming stage updates reflected in the office crew and activity indicators.
- Ollama-powered agent chat and report generation; job matching and suitability checks are deterministic keyword-based analysis, not hiring probabilities.

## The eight agents

The consolidated workflow executes these roles in order:

1. **Job Hunter** searches the configured live providers and removes duplicate listings.
2. **Job Matcher** scores the listings against the submitted resume and profile.
3. **Resume Agent** tailors one resume per suitable listing while preserving supplied facts.
4. **Cover Letter** drafts a role-specific letter from that tailored resume.
5. **Company Researcher** checks an official company URL when one is available and reports source limitations.
6. **Application Reviewer** reviews the resume and letter for consistency and completeness.
7. **Application Manager** reads current tracking records and prepares a “Ready to save” or “Already tracked” status.
8. **Project Intelligence** compares job needs with the candidate’s skills and portfolio.

The tracker is read-only during the workflow. Selecting **Save to Tracker** adds a record as `Saved`; records are deduplicated by job URL (or company and role if no URL is available). No application is submitted automatically.

## Architecture and technologies

- **Frontend:** React, TypeScript, Vite, CSS, HTML Canvas.
- **Backend:** Python, FastAPI, Pydantic, Uvicorn.
- **Local AI:** Ollama through LangChain; default model is `qwen2.5:3b`.
- **Job sources:** Arbeitnow Job Board API and Remotive Remote Jobs API.
- **Storage:** SQLite at `backend/data/careerpilot.db` for the candidate profile, workflow history, and locally saved application tracking.
- **Company research:** retrieves text from a supplied official website and generates a report with explicit source limitations.

## Requirements

- Python 3.11 or newer (the backend has also been exercised with Python 3.14).
- Node.js 20.19+ or 22.12+ for the installed Vite 8 toolchain ([Vite compatibility note](https://vite.dev/guide/)).
- npm.
- Ollama running locally with the configured model pulled. Live job search also requires outbound internet access from the backend machine.

## Install and run on Windows

Open two PowerShell terminals from the project directory.

### 1. Configure and start the backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
ollama pull qwen2.5:3b
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

If Ollama uses a different model or local address, edit `backend/.env`. The example file contains non-secret defaults. The API health check is <http://127.0.0.1:8000/health>; interactive API docs are at <http://127.0.0.1:8000/docs>.

### 2. Configure and start the frontend

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev -- --host 127.0.0.1
```

Open <http://localhost:5173/>. The Vite development server proxies `/api` and `/health` to the local backend. Set `VITE_API_BASE_URL` in `frontend/.env` only when the frontend should call a different backend host directly.

### macOS or Linux

Create the virtual environment with `python3 -m venv .venv`, activate it with `source .venv/bin/activate`, install `backend/requirements.txt`, and run `python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000` from `backend/`. From `frontend/`, run `npm install` and `npm run dev -- --host 127.0.0.1`.

## Run the workflow

1. Open **Career Assistant** in the office. Your candidate profile is saved locally when you use **Save Profile** or start an analysis; you can reopen saved analyses from **Previous Career Analyses**.
2. Choose a local `.pdf`, `.docx`, `.txt`, or `.md` resume file, or paste a candidate profile of at least 40 characters. Text is extracted in the browser and placed in the editable resume box; scanned PDFs need OCR first. Add skills, education, and experience if the resume does not clearly state them.
3. Choose job keywords, preferred location, and job type. Add an official company website when known.
4. Select **Start Career Analysis** and follow the live stage statuses.
5. Review job scores and suitability reasons. Expand the resume and cover letter sections to view, copy, download as text, or print/save as PDF.
6. Choose **Save to Tracker** only for opportunities you want to track. Tracker status starts at `Saved`; update it manually, and confirm before marking it `Applied`.

For a portfolio demo, use a fictional profile rather than personal data. Capture screenshots of (1) the office idle view, (2) the Career Assistant progress panel, and (3) the consolidated results with expanded documents. Do not include private contact details, a real resume, local tracker records, or credentials in public screenshots. There are no committed screenshots at this time.

## API endpoints

The complete endpoint definitions and request schemas are available in FastAPI’s generated docs at `/docs`.

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Backend health status |
| `GET`, `PUT` | `/api/profile` | Read or save the local candidate profile |
| `GET` | `/api/workflow-history` | List saved analysis summaries |
| `GET` | `/api/workflow-history/{workflow_id}` | Reopen a saved consolidated analysis |
| `POST` | `/api/chat` | General AI chat |
| `POST` | `/api/agent-chat` | Context-aware CareerPilot team chat |
| `POST` | `/api/jobs` | Search and score provider listings |
| `POST` | `/api/match` | Match one job description |
| `POST` | `/api/resume` | Generate a tailored resume draft |
| `POST` | `/api/cover-letter` | Generate a cover letter draft |
| `POST` | `/api/review` | Review application documents |
| `POST` | `/api/company-research` | Research a supplied official website |
| `GET`, `POST` | `/api/applications` | List saved records or save an opportunity |
| `PUT` | `/api/applications/{application_id}` | Update an existing tracker record |
| `GET` | `/api/application-stats` | Read tracker totals by status |
| `POST` | `/api/project-recommendations` | Recommend portfolio projects for a job |
| `POST` | `/api/career-workflow` | Run the complete workflow and return JSON |
| `POST` | `/api/career-workflow/stream` | Run the workflow and stream NDJSON progress/results |

## Tests and production build

From `backend/`:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q app tests
```

From `frontend/`:

```powershell
npm run build
```

The workflow tests use clearly labeled fixture listings and stub external providers; they do not insert fixture jobs into live results. A live run can return zero suitable opportunities depending on current listings and the candidate profile.

## Configuration and repository hygiene

- Copy the example environment files to `.env` locally; never commit `.env` files, API keys, passwords, or personal resumes.
- The root `.gitignore` excludes local environments, Python caches, SQLite files, frontend dependencies, and build output while keeping `.env.example` files eligible for version control.
- Application records remain local in SQLite unless the user saves them.

## Current limitations

- Provider data and open roles change; a successful search does not guarantee a suitable opportunity.
- Suitability and match scores are explainable keyword/profile indicators, not predictions of hiring outcomes.
- Company research requires a company URL. Findings are limited to the website content retrieved; interview suggestions are preparation prompts, not verified hiring facts.
- The application is a local portfolio project. It does not submit applications, authenticate to job boards, or verify that a vacancy remains open.
- Generated documents are drafts and should be reviewed before use. The system avoids adding unsupported candidate details when a resume/profile is supplied, but candidate-provided facts still need human verification.
