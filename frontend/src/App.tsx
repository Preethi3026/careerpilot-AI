import { useEffect, useState } from "react";
import "./App.css";
import OfficeScene, { type OfficeAgent } from "./OfficeScene";
import { callAgent as postAgent, checkBackend, createApplication, getApplications, getCandidateProfile, getWorkflowHistory, getWorkflowHistoryItem, saveCandidateProfile, sendAgentChat, streamCareerWorkflow, updateApplication, type CareerWorkflowEvent, type CareerWorkflowPayload, type SavedCandidateProfile } from "./services/api";

type Agent = {
  id: number;
  name: string;
  role: string;
  emoji: string;
  desk: string;
};

type Field = {
  name: string;
  label: string;
  placeholder: string;
  multiline?: boolean;
};

type Application = {
  id: number;
  company: string;
  role: string;
  status: string;
  application_date?: string;
  match_score?: number | null;
  location?: string;
  job_url?: string;
  source?: string;
};

type ChatMessage = { role: "user" | "assistant"; content: string };
type WorkflowJob = {
  job: Record<string, any>;
  match: Record<string, any>;
  resume?: string;
  resume_analysis?: Record<string, any>;
  cover_letter?: string;
  company_research?: string;
  review?: string;
  tracking?: { status: string; applied: boolean; application?: Application | null };
  errors?: string[];
};
type CareerWorkflowResult = {
  jobs_found: Array<Record<string, any>>;
  selected_jobs: WorkflowJob[];
  project_intelligence?: Record<string, any> | null;
  application_tracking?: { statistics?: Record<string, any>; records_changed: boolean };
  errors: Array<{ agent: string; message: string }>;
  summary: Record<string, number>;
};

const agentWorkflowSteps: Record<number, string[]> = {
  1: ["Fetch job listings", "Remove duplicates", "Keep Germany or remote roles", "Check AI, data, and software fit", "Check junior and internship fit", "Score skills and rank results"],
  2: ["Read the job description", "Extract required skills", "Compare verified candidate skills", "Score education and experience", "Check level and role suitability", "Prepare match score and recommendation"],
  3: ["Analyze the complete job description", "Verify resume skills and qualifications", "Prioritize relevant projects and experience", "Tailor the professional summary", "Reorder existing skills and bullets", "Return resume with gaps and verification notes"],
  4: ["Read company, role, and job details", "Select relevant skills and projects", "Draft role-specific fit", "Add experience and motivation", "Assemble the letter and contact fields", "Return the cover letter"],
  5: ["Check resume and cover letter presence", "Find unreplaced placeholders", "Check email and profile links", "Verify project references", "Flag unsupported claims", "Summarize strengths and improvements"],
  6: ["Open the supplied official site", "Collect company information", "Detect industry and technologies", "Identify AI products and signals", "Check the target role context", "Compile the company research"],
  7: ["Load saved application records", "Group records by status", "Calculate application statistics", "Prepare the tracking summary"],
  8: ["Extract job requirements", "Compare against verified skills", "Separate missing and unverified skills", "Choose three distinct projects", "Map projects to skill gaps", "Build a practical roadmap", "Recommend a first project and CV updates"],
};

const agents: Agent[] = [
  { id: 1, name: "Job Hunter", role: "Finding internships", emoji: "🔎", desk: "01" },
  { id: 2, name: "Job Matcher", role: "Matching job skills", emoji: "🎯", desk: "02" },
  { id: 3, name: "Resume Agent", role: "Building resumes", emoji: "📄", desk: "03" },
  { id: 4, name: "Cover Letter", role: "Writing applications", emoji: "✉️", desk: "04" },
  { id: 5, name: "Application Reviewer", role: "Checking quality", emoji: "🔍", desk: "05" },
  { id: 6, name: "Company Researcher", role: "Researching companies", emoji: "🏢", desk: "06" },
  { id: 7, name: "Application Manager", role: "Tracking applications", emoji: "📋", desk: "07" },
  { id: 8, name: "Project Intelligence", role: "Finding skill gaps", emoji: "🧠", desk: "08" },
];

const agentFields: Record<number, Field[]> = {
  1: [
    {
      name: "keyword",
      label: "What job are you looking for?",
      placeholder: "AI/ML Intern",
    },
    {
      name: "limit",
      label: "Number of jobs",
      placeholder: "10",
    },
  ],
  2: [
    {
      name: "job_description",
      label: "Paste the job description",
      placeholder: "Paste the complete job description here...",
      multiline: true,
    },
  ],
  3: [
    {
      name: "resume_text",
      label: "Candidate resume (required)",
      placeholder: "Paste the complete resume or candidate profile...",
      multiline: true,
    },
    {
      name: "skills",
      label: "Additional verified skills (optional)",
      placeholder: "Python, SQL, React",
    },
    {
      name: "education",
      label: "Education (optional)",
      placeholder: "Degree, institution, dates",
    },
    {
      name: "experience",
      label: "Experience details (optional)",
      placeholder: "Candidate-provided roles or responsibilities",
      multiline: true,
    },
    {
      name: "role",
      label: "Target job title (optional)",
      placeholder: "Machine Learning Intern",
    },
    {
      name: "company",
      label: "Target company (optional)",
      placeholder: "Company name",
    },
    {
      name: "job_description",
      label: "Paste the job description",
      placeholder: "Paste the complete job description here...",
      multiline: true,
    },
  ],
  4: [
    {
      name: "company",
      label: "Company name",
      placeholder: "e.g., Mercedes-Benz Tech Innovation",
    },
    {
      name: "role",
      label: "Job role",
      placeholder: "e.g., Data Engineering & AI Intern",
    },
    {
      name: "job_description",
      label: "Job description",
      placeholder: "Paste the job description here...",
      multiline: true,
    },
    {
      name: "resume_text",
      label: "Candidate resume (required)",
      placeholder: "Paste the candidate resume used as the source of truth...",
      multiline: true,
    },
    {
      name: "candidate_name",
      label: "Candidate name (optional)",
      placeholder: "Your name as shown on your resume",
    },
    {
      name: "company_research",
      label: "Company research (optional)",
      placeholder: "Paste sourced company research if available",
      multiline: true,
    },
  ],
  5: [
    {
      name: "job_description",
      label: "Job description",
      placeholder: "Paste the job description here...",
      multiline: true,
    },
    {
      name: "resume_text",
      label: "Your resume text",
      placeholder: "Paste your resume text here...",
      multiline: true,
    },
    {
      name: "cover_letter",
      label: "Cover letter (optional)",
      placeholder: "Paste your cover letter here...",
      multiline: true,
    },
  ],
  6: [
    {
      name: "company",
      label: "Company name",
      placeholder: "Databricks",
    },
    {
      name: "job_role",
      label: "Job role",
      placeholder: "AI/ML Intern",
    },
    {
      name: "company_url",
      label: "Official company website",
      placeholder: "https://www.databricks.com",
    },
  ],
  8: [
    {
      name: "job_description",
      label: "Paste the job description",
      placeholder: "Paste the complete job description here...",
      multiline: true,
    },
  ],
};

const agentEndpoints: Record<number, string> = {
  1: "/api/jobs",
  2: "/api/match",
  3: "/api/resume",
  4: "/api/cover-letter",
  5: "/api/review",
  6: "/api/company-research",
  8: "/api/project-recommendations",
};

const careerWorkflowOrder = [1, 2, 3, 6, 4, 5, 7, 8];

function App() {
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [formValues, setFormValues] = useState<Record<string, string>>({});
  const [result, setResult] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [applications, setApplications] = useState<Application[]>([]);
  const [sceneStatus, setSceneStatus] = useState<Record<number, OfficeAgent["status"]>>({});
  const [sceneStation, setSceneStation] = useState<Record<number, string>>({});
  const [sceneProgress, setSceneProgress] = useState<Record<number, number>>({});
  const [chatMessages, setChatMessages] = useState<Record<number, ChatMessage[]>>({});
  const [agentContextNotes, setAgentContextNotes] = useState<Record<number, string>>({});
  const [chatInput, setChatInput] = useState("");
  const [chatBusy, setChatBusy] = useState(false);
  const [showCrew, setShowCrew] = useState(false);
  const [showActivity, setShowActivity] = useState(false);
  const [stationInfo, setStationInfo] = useState("");
  const [backendConnected, setBackendConnected] = useState(false);
  const [careerAssistantOpen, setCareerAssistantOpen] = useState(false);
  const [careerLoading, setCareerLoading] = useState(false);
  const [careerError, setCareerError] = useState("");
  const [careerProgress, setCareerProgress] = useState<CareerWorkflowEvent[]>([]);
  const [careerResult, setCareerResult] = useState<CareerWorkflowResult | null>(null);
  const [careerForm, setCareerForm] = useState<CareerWorkflowPayload>({
    keyword: "AI / Data Intern",
    resume_text: "",
    skills: "",
    education: "",
    experience: "",
    preferred_location: "Germany",
    job_type: "internship",
    limit: 3,
    company_url: "",
  });
  const [resumeFileName, setResumeFileName] = useState("");
  const [resumeImportError, setResumeImportError] = useState("");
  const [trackerMessages, setTrackerMessages] = useState<Record<string, string>>({});
  const [copiedDocument, setCopiedDocument] = useState("");
  const [profileSaveMessage, setProfileSaveMessage] = useState("");
  const [workflowHistory, setWorkflowHistory] = useState<{ id: number; created_at: string; keyword: string; summary: Record<string, number> }[]>([]);
  const [historyError, setHistoryError] = useState("");

  const [activity, setActivity] = useState<string[]>([
    "Office started successfully",
    "Eight AI employees are ready",
    "Waiting for your instructions",
  ]);

  const [clock, setClock] = useState(new Date());

  // /api/match returns analysis fields under `result`; retain compatibility
  // with a direct analysis object if the response shape changes later.
  const matchResult =
    result && typeof result === "object" && "result" in result
      ? (result as { result: unknown }).result
      : result;

  const sceneAgents: OfficeAgent[] = agents.map((agent) => ({
    id: agent.id,
    name: agent.name,
    status: sceneStatus[agent.id] || "idle",
    station: sceneStation[agent.id],
    phase: agentWorkflowSteps[agent.id][sceneProgress[agent.id] || 0],
    stepIndex: sceneProgress[agent.id] || 0,
    stepCount: agentWorkflowSteps[agent.id].length,
  }));

  useEffect(() => {
    const activeIds = Object.entries(sceneStatus)
      .filter(([, status]) => status === "working")
      .map(([id]) => Number(id));
    if (!activeIds.length) return;

    const startedAt = Date.now();
    const updateProgress = () => {
      const nextStep = Math.floor((Date.now() - startedAt) / 2600);
      setSceneProgress((previous) => {
        let changed = false;
        const next = { ...previous };
        for (const id of activeIds) {
          const step = Math.min(nextStep, agentWorkflowSteps[id].length - 1);
          if (next[id] !== step) { next[id] = step; changed = true; }
        }
        return changed ? next : previous;
      });
    };
    updateProgress();
    const timer = window.setInterval(updateProgress, 700);
    return () => window.clearInterval(timer);
  }, [sceneStatus]);

  useEffect(() => {
    const timer = setInterval(() => {
      setClock(new Date());
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    let cancelled = false;
    void Promise.all([getCandidateProfile(), getWorkflowHistory()]).then(([saved, history]) => {
      if (cancelled) return;
      if (saved.profile) {
        const profile = saved.profile;
        setCareerForm((previous) => ({
          ...previous,
          resume_text: profile.resume_text || previous.resume_text,
          skills: profile.skills || previous.skills,
          education: profile.education || previous.education,
          experience: profile.experience || previous.experience,
          keyword: profile.preferred_job_titles || previous.keyword,
          preferred_location: profile.preferred_location || previous.preferred_location,
          job_type: profile.preferred_job_type || previous.job_type,
          full_name: profile.full_name,
          email: profile.email,
          phone: profile.phone,
          university: profile.university,
          projects: profile.projects,
          certifications: profile.certifications,
          languages: profile.languages,
          career_goals: profile.career_goals,
        }));
      }
      setWorkflowHistory(history.workflows);
    }).catch((loadError) => {
      if (!cancelled) setHistoryError(loadError instanceof Error ? loadError.message : "Could not load saved CareerPilot data.");
    });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    let cancelled = false;
    const refreshBackendStatus = async () => {
      try {
        await checkBackend();
        if (!cancelled) setBackendConnected(true);
      } catch {
        if (!cancelled) setBackendConnected(false);
      }
    };
    void refreshBackendStatus();
    const timer = window.setInterval(refreshBackendStatus, 15000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  function addActivity(message: string) {
    setActivity((previous) => [message, ...previous].slice(0, 5));
  }

  function getProfilePayload(form: CareerWorkflowPayload = careerForm): SavedCandidateProfile {
    return {
      full_name: form.full_name || "", email: form.email || "", phone: form.phone || "",
      resume_text: form.resume_text, skills: form.skills, education: form.education,
      university: form.university || "", experience: form.experience, projects: form.projects || "",
      certifications: form.certifications || "", languages: form.languages || "",
      preferred_job_titles: form.keyword, preferred_location: form.preferred_location,
      preferred_job_type: form.job_type, career_goals: form.career_goals || "",
    };
  }

  async function persistCandidateProfile() {
    try {
      await saveCandidateProfile(getProfilePayload());
      setProfileSaveMessage("PROFILE SAVED");
      addActivity("Candidate profile saved for future analyses");
    } catch (saveError) {
      setProfileSaveMessage(saveError instanceof Error ? `PROFILE NOT SAVED · ${saveError.message}` : "PROFILE NOT SAVED");
    }
  }

  async function reopenWorkflowHistory(id: number) {
    try {
      const saved = await getWorkflowHistoryItem(id);
      const resultData = saved.result as CareerWorkflowResult;
      setCareerResult(resultData);
      setCareerAssistantOpen(true);
      setCareerProgress(Object.values((resultData as any).stages || {}).map((stage: any) => ({ type: "progress", agent_id: stage.agent_id, agent: agents.find((item) => item.id === stage.agent_id)?.name, status: stage.status, message: stage.message })));
      for (const stage of Object.values((resultData as any).stages || {}) as any[]) {
        setSceneStatus((previous) => ({ ...previous, [stage.agent_id]: stage.status }));
      }
      setHistoryError("");
    } catch (loadError) {
      setHistoryError(loadError instanceof Error ? loadError.message : "Could not reopen this analysis.");
    }
  }

  function downloadCareerDocument(filename: string, content: string) {
    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename.replace(/[^a-z0-9-_]+/gi, "_") + ".txt";
    link.click();
    URL.revokeObjectURL(url);
  }

  function printCareerDocument(title: string, content: string) {
    const printWindow = window.open("", "_blank", "width=850,height=700");
    if (!printWindow) {
      setCareerError("The print window was blocked. Allow pop-ups to save this document as PDF.");
      return;
    }
    printWindow.document.title = title;
    const style = printWindow.document.createElement("style");
    style.textContent = "@page{size:A4;margin:18mm}body{font:11pt/1.55 Arial,sans-serif;color:#17251d}h1{font-size:16pt;border-bottom:1px solid #999;padding-bottom:8px}pre{font:10pt/1.55 Arial,sans-serif;white-space:pre-wrap;overflow-wrap:anywhere}";
    const heading = printWindow.document.createElement("h1");
    heading.textContent = title;
    const body = printWindow.document.createElement("pre");
    body.textContent = content;
    printWindow.document.body.append(style, heading, body);
    printWindow.document.close();
    window.setTimeout(() => printWindow.print(), 300);
  }

  function openAgent(agent: Agent) {
    if (careerLoading) return;
    setCareerAssistantOpen(false);
    if (selectedAgent && selectedAgent.id !== agent.id) {
      setSceneStatus((previous) => ({ ...previous, [selectedAgent.id]: "idle" }));
    }
    setSelectedAgent(agent);

    setFormValues(
      agent.id === 1
        ? { keyword: "AI/ML Intern", limit: "10" }
        : {}
    );

    setResult(null);
    setError("");
    setChatInput("");
    setShowCrew(false);
    setShowActivity(false);
    setSceneStatus((previous) => ({ ...previous, [agent.id]: "chatting" }));
    setSceneStation((previous) => ({ ...previous, [agent.id]: "desk" }));
    addActivity(`${agent.name} came to their desk`);
  }

  function openCareerAssistant() {
    if (careerLoading) return;
    setSelectedAgent(null);
    setCareerAssistantOpen(true);
    setShowCrew(false);
    setShowActivity(false);
    setCareerError("");
    setCareerProgress([]);
    setCareerResult(null);
    setTrackerMessages({});
    setResumeFileName("");
    setResumeImportError("");
    for (const id of careerWorkflowOrder) {
      setSceneStatus((previous) => ({ ...previous, [id]: "queued" }));
      setSceneStation((previous) => ({ ...previous, [id]: "notes" }));
      setSceneProgress((previous) => ({ ...previous, [id]: 0 }));
    }
  }

  async function startCareerWorkflow(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (careerLoading) return;
    if (careerForm.resume_text.trim().length < 40) {
      setCareerError("Paste at least a short resume or candidate profile so the team can match jobs accurately.");
      return;
    }
    setCareerLoading(true);
    setCareerError("");
    setCareerProgress([]);
    setCareerResult(null);
    setTrackerMessages({});
    try {
      try {
        await saveCandidateProfile(getProfilePayload());
        setProfileSaveMessage("PROFILE SAVED");
      } catch (saveError) {
        setProfileSaveMessage(saveError instanceof Error ? `PROFILE SAVE FAILED · ${saveError.message}` : "PROFILE SAVE FAILED");
      }
      const result = await streamCareerWorkflow(careerForm, (update) => {
        setCareerProgress((previous) => [...previous, update]);
        if (update.agent_id) {
          const status = update.status === "completed" ? "completed"
            : update.status === "failed" ? "failed"
              : update.status === "skipped" ? "skipped"
                : update.status === "working" ? "working" : "queued";
          setSceneStatus((previous) => ({ ...previous, [update.agent_id!]: status }));
          setSceneStation((previous) => ({ ...previous, [update.agent_id!]: status === "working" ? "web" : "desk" }));
          if (status === "working") setSceneProgress((previous) => ({ ...previous, [update.agent_id!]: 0 }));
        }
        if (update.message) addActivity(`${update.agent}: ${update.message}`);
      });
      setCareerResult(result as CareerWorkflowResult);
      try {
        const savedHistory = await getWorkflowHistory();
        setWorkflowHistory(savedHistory.workflows);
      } catch {
        // Keep the current result visible even if the history refresh fails.
      }
      if (Array.isArray(result.errors)) {
        const failedAgents = new Set(result.errors.map((item: { agent: string }) => item.agent));
        setCareerProgress((previous) => previous.map((item) => item.agent && failedAgents.has(item.agent) && (item.status === "working" || item.status === "completed")
          ? { ...item, status: "failed", message: "One or more tasks for this agent failed" }
          : item));
      }
      addActivity("Career Assistant delivered one consolidated application package");
    } catch (error) {
      setCareerError(error instanceof Error ? error.message : "Career Assistant could not complete the workflow.");
      addActivity("Career Assistant workflow encountered an error");
    } finally {
      setCareerLoading(false);
    }
  }

  async function importResumeFile(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setResumeFileName("");
    setResumeImportError("");
    if (file.size > 15 * 1024 * 1024) {
      setResumeImportError("Choose a resume smaller than 15 MB.");
      return;
    }

    try {
      const extension = file.name.split(".").pop()?.toLowerCase();
      let text = "";
      if (extension === "txt" || extension === "md") {
        text = await file.text();
      } else if (extension === "docx") {
        const mammoth = (await import("mammoth/mammoth.browser")).default;
        const extracted = await mammoth.extractRawText({ arrayBuffer: await file.arrayBuffer() });
        text = extracted.value;
      } else if (extension === "pdf") {
        const [pdfjs, worker] = await Promise.all([
          import("pdfjs-dist"),
          import("pdfjs-dist/build/pdf.worker.min.mjs?url"),
        ]);
        pdfjs.GlobalWorkerOptions.workerSrc = worker.default;
        const document = await pdfjs.getDocument({ data: new Uint8Array(await file.arrayBuffer()) }).promise;
        const pages: string[] = [];
        for (let pageNumber = 1; pageNumber <= document.numPages; pageNumber += 1) {
          const page = await document.getPage(pageNumber);
          const content = await page.getTextContent();
          pages.push(content.items.map((item) => "str" in item ? item.str : "").join(" "));
        }
        text = pages.join("\n");
      } else {
        setResumeImportError("Choose a .pdf, .docx, .txt, or .md resume file.");
        return;
      }

      if (!text.trim()) {
        setResumeImportError("No readable text was found. If this is a scanned PDF, paste its text into the box instead.");
        return;
      }
      setCareerForm((previous) => ({ ...previous, resume_text: text.trim() }));
      setResumeFileName(file.name);
    } catch (importError) {
      setResumeImportError(importError instanceof Error ? `Could not read this file: ${importError.message}` : "Could not read this resume file.");
    }
  }

  async function copyCareerDocument(name: string, value: string) {
    try {
      await navigator.clipboard.writeText(value);
      setCopiedDocument(name);
      window.setTimeout(() => setCopiedDocument(""), 1800);
    } catch {
      setCareerError("Clipboard access was unavailable. Select and copy the document text manually.");
    }
  }

  async function saveWorkflowJob(item: WorkflowJob) {
    const job = item.job;
    const key = String(job.url || `${job.company}-${job.title}`);
    if (trackerMessages[key]) return;
    try {
      const response = await createApplication({
        company: String(job.company || "Company not specified"),
        role: String(job.title || "Role not specified"),
        job_url: String(job.url || ""),
        status: "Documents Prepared",
        location: String(job.location || ""),
        source: String(job.source || ""),
        match_score: Number(item.match.match_score || 0),
        resume: item.resume || "",
        cover_letter: item.cover_letter || "",
      });
      const app = (response as any).application;
      const message = app?.duplicate ? "Already in tracker" : "Saved to tracker";
      setTrackerMessages((previous) => ({ ...previous, [key]: message }));
      addActivity(`${job.company || "Opportunity"} ${message.toLowerCase()}`);
    } catch (error) {
      setTrackerMessages((previous) => ({ ...previous, [key]: error instanceof Error ? error.message : "Could not save" }));
    }
  }

  async function changeApplicationStatus(application: Application, status: string) {
    if (status === "Applied" && !window.confirm("Confirm that you have submitted this application before marking it Applied.")) return;
    try {
      await updateApplication(application.id, { status });
      const response = await getApplications();
      setApplications(response.applications as Application[]);
      addActivity(`${application.company} status updated to ${status}`);
    } catch (statusError) {
      setError(statusError instanceof Error ? statusError.message : "Could not update this application status.");
    }
  }

  function closeAgent() {
    if (loading || chatBusy) return;

    setSelectedAgent(null);
    setResult(null);
    setError("");
    setSceneStatus((previous) => ({ ...previous, [selectedAgent?.id || 0]: "idle" }));
    addActivity(`${selectedAgent?.name || "Agent"} returned to their desk`);
  }

  async function callAgent() {
    if (!selectedAgent) return;

    const requiredInputs: Record<number, string[]> = {
      2: ["job_description"],
      3: ["job_description", "resume_text"],
      4: ["company", "role", "job_description", "resume_text"],
      5: ["job_description", "resume_text"],
      6: ["company", "job_role"],
      8: ["job_description"],
    };
    const fieldLabels: Record<string, string> = {
      company: "company name",
      role: "job role",
      job_role: "job role",
      job_description: "job description",
      resume_text: "resume text",
    };
    const missing = (requiredInputs[selectedAgent.id] || []).filter(
      (name) => !formValues[name]?.trim(),
    );
    if (missing.length > 0) {
      setError(`Please enter ${missing.map((name) => fieldLabels[name] || name).join(", ")} before starting ${selectedAgent.name}.`);
      return;
    }

    setLoading(true);
    setResult(null);
    setError("");
    setSceneStatus((previous) => ({ ...previous, [selectedAgent.id]: "working" }));
    const stationByAgent: Record<number, string> = {
      1: "web", 2: "code", 3: "files", 4: "files", 5: "files", 6: "web", 7: "database", 8: "notes",
    };
    setSceneStation((previous) => ({ ...previous, [selectedAgent.id]: stationByAgent[selectedAgent.id] || "code" }));
    addActivity(`${selectedAgent.name} is heading to a workstation`);

    try {
      let endpoint = agentEndpoints[selectedAgent.id];

      const payload: Record<string, unknown> = { ...formValues };

      // Application Manager
      if (selectedAgent.id === 7) {
        const data = await getApplications();

        setApplications(
          Array.isArray(data.applications) ? (data.applications as Application[]) : [],
        );
        setResult(data);

        addActivity("Application Manager retrieved your applications");

        return;
      }

      // Convert job limit into a number
      if (selectedAgent.id === 1) {
        payload.limit = Number(formValues.limit || "10");
      }

      if (!endpoint) throw new Error("This agent is not available yet.");
      const data = await postAgent(endpoint, payload);

      setResult(data);

      addActivity(`${selectedAgent.name} completed a task successfully`);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Something went wrong.";

      setError(message);

      addActivity(`${selectedAgent.name} encountered an error`);
    } finally {
      setLoading(false);
      setSceneStatus((previous) => ({ ...previous, [selectedAgent.id]: "chatting" }));
      setSceneStation((previous) => ({ ...previous, [selectedAgent.id]: "desk" }));
    }
  }

  async function sendMessage(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const agent = selectedAgent;
    const message = chatInput.trim();
    if (!agent || !message || chatBusy) return;
    const history = chatMessages[agent.id] || [];
    setChatInput("");
    setChatBusy(true);
    setError("");
    setSceneStatus((previous) => ({ ...previous, [agent.id]: "working" }));
    setSceneStation((previous) => ({ ...previous, [agent.id]: "notes" }));
    setChatMessages((previous) => ({ ...previous, [agent.id]: [...(previous[agent.id] || []), { role: "user", content: message }] }));
    try {
      const latestOutput = result == null ? "" : typeof result === "string" ? result : JSON.stringify(result);
      const agentContext = {
        agent_name: agent.name,
        agent_role: agent.role,
        implemented_workflow: agentWorkflowSteps[agent.id],
        current_task_inputs: formValues,
        latest_task_output: latestOutput?.slice(0, 7000) || "",
        user_context_notes: agentContextNotes[agent.id] || "",
      };
      const response = await sendAgentChat(agent.id, message, history, agentContext);
      setChatMessages((previous) => ({ ...previous, [agent.id]: [...(previous[agent.id] || []), { role: "assistant", content: response.ai_response }] }));
      addActivity(`${agent.name} replied in the chat`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "CareerPilot’s team could not reply.");
    } finally {
      setChatBusy(false);
      setSceneStatus((previous) => ({ ...previous, [agent.id]: "chatting" }));
      setSceneStation((previous) => ({ ...previous, [agent.id]: "desk" }));
    }
  }

  async function addApplication() {
    if (!formValues.company?.trim() || !formValues.role?.trim()) {
      setError("Please enter both the company and job role.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);
    setSceneStatus((previous) => ({ ...previous, [7]: "working" }));
    setSceneStation((previous) => ({ ...previous, [7]: "database" }));

    try {
      const data = await createApplication({
        company: formValues.company,
        role: formValues.role,
        job_url: formValues.job_url || "",
      });

      setResult(data);

      addActivity("Application Manager saved a new application");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not save application."
      );
    } finally {
      setLoading(false);
      setSceneStatus((previous) => ({ ...previous, [7]: "chatting" }));
      setSceneStation((previous) => ({ ...previous, [7]: "desk" }));
    }
  }

  const modalStyle: React.CSSProperties = {
    position: "fixed",
    inset: 0,
    background: "rgba(13, 27, 23, 0.56)",
    display: "flex",
    alignItems: "center",
    justifyContent: "flex-end",
    padding: "0",
    zIndex: 1000,
    overflowY: "auto",
  };

  const panelStyle: React.CSSProperties = {
    position: "relative",
    width: "100%",
    maxWidth: "440px",
    height: "100vh",
    maxHeight: "100vh",
    overflowY: "auto",
    background: "#f8f1d8",
    border: "0",
    borderLeft: "4px solid #234537",
    borderRadius: "0",
    padding: "30px",
    boxShadow: "-8px 0 #18362c",
    color: "#23382f",
  };

  const inputStyle: React.CSSProperties = {
    width: "100%",
    padding: "12px",
    border: "2px solid #55765c",
    borderRadius: "0",
    background: "#fffbed",
    color: "#23382f",
    fontFamily: "inherit",
    fontSize: "14px",
    outline: "none",
    marginTop: "7px",
  };

  const actionButtonStyle: React.CSSProperties = {
    width: "100%",
    padding: "15px",
    marginTop: "15px",
    background: "#335f4c",
    color: "white",
    border: "2px solid #18362c",
    borderRadius: "0",
    fontFamily: "inherit",
    fontWeight: 900,
    fontSize: "15px",
    cursor: "pointer",
  };

  function handleStationClick(station: string) {
    if (loading || chatBusy || careerLoading) return;
    const title = station.toUpperCase();
    const detail: Record<string, string> = {
      web: "Web terminal: job search and company research happen here.",
      files: "Files desk: resume, cover letter and application reviews happen here.",
      notes: "Notes shelf: agent conversations and project recommendations happen here.",
      database: "Application database: saved jobs and application tracking happen here.",
      code: "Work desk: matching and analysis happen here.",
    };
    setStationInfo(`${title} · ${detail[station] || "This station is ready for the team."}`);
    const visitor = agents.find((agent) => sceneStatus[agent.id] === "idle") || agents[0];
    setSceneStatus((previous) => ({ ...previous, [visitor.id]: "visiting" }));
    setSceneStation((previous) => ({ ...previous, [visitor.id]: station }));
    addActivity(`${visitor.name} walked over to the ${title.toLowerCase()} station`);
    window.setTimeout(() => {
      setSceneStatus((previous) => previous[visitor.id] === "visiting" ? { ...previous, [visitor.id]: "idle" } : previous);
      setSceneStation((previous) => ({ ...previous, [visitor.id]: "lounge" }));
    }, 7500);
  }

  function toggleTime() {
    addActivity("The office window view changed time of day");
  }

  return (
    <main className="office">
      <header className="office-header">
        <div className="brand">
          <span className="brand-icon">✦</span>

          <div>
            <h1>CareerPilot AI</h1>
            <p>CAREERPILOT · AGENT WORKSPACE</p>
          </div>
        </div>
        <div className="office-clock">
          <span className="system-light" />
          <span>
            {clock.toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>

          <span className="office-open">OLLAMA OFFICE</span>
        </div>
      </header>
      <section className="office-panel" aria-label="CareerPilot agent office">
        <div className="office-panel-head">
          <div><span className="online-dot" />LIVE OFFICE <span className="floor-label">· FLOOR 01</span></div>
          <div className="scene-actions">
            <button type="button" className={showCrew ? "active" : ""} onClick={() => { setShowCrew(!showCrew); setShowActivity(false); }}>CREW <b>08</b></button>
            <button type="button" className={showActivity ? "active" : ""} onClick={() => { setShowActivity(!showActivity); setShowCrew(false); }}>ACTIVITY</button>
          </div>
        </div>
        <div className="scene-wrap">
          <OfficeScene
            agents={sceneAgents}
            selectedId={selectedAgent?.id ?? null}
            onAgentClick={(id) => { if (careerLoading) return; const agent = agents.find((item) => item.id === id); if (agent) openAgent(agent); }}
            onStationClick={handleStationClick}
            onTimeClick={toggleTime}
          />
        </div>
        <div className="office-hint-row">
          <span>CLICK A TEAMMATE TO TALK</span><span>CLICK A LIT TOOL TO VISIT</span><span>CLICK THE WINDOW TO CHANGE THE SKY</span>
        </div>
        {stationInfo && <button type="button" className="station-notice" onClick={() => setStationInfo("")}>{stationInfo}<span>×</span></button>}
        <nav className="office-dock" aria-label="Office navigation">
          <button type="button" className={showCrew ? "active" : ""} onClick={() => { setShowCrew(!showCrew); setShowActivity(false); }}><span>▦</span> CREW</button>
          <button type="button" className={showActivity ? "active" : ""} onClick={() => { setShowActivity(!showActivity); setShowCrew(false); }}><span>≋</span> ACTIVITY</button>
          <button type="button" className={`career-assistant-launch ${careerAssistantOpen ? "active" : ""}`} onClick={openCareerAssistant}><span>✦</span> CAREER ASSISTANT</button>
          <div className="dock-status"><span className="online-dot" /> {loading || chatBusy || careerLoading ? "TEAM IN MOTION" : "ALL AGENTS READY"}</div>
        </nav>
      </section>

      {showCrew && <aside className="office-drawer" aria-label="Crew list">
        <div className="drawer-head"><div><small>THE TEAM</small><h2>CREW <span>08</span></h2></div><button type="button" onClick={() => setShowCrew(false)}>×</button></div>
        <p className="drawer-copy">Select an agent to open their desk. Each workflow lists the concrete steps implemented in the agent code.</p>
        {agents.map((agent, index) => {
          const working = sceneStatus[agent.id] === "working";
          const activeStep = sceneProgress[agent.id] || 0;
          return <section className="crew-workflow-card" key={agent.id}>
            <button className="crew-row" onClick={() => openAgent(agent)}>
              <span className={`crew-swatch swatch-${index + 1}`}><i /></span>
              <span><b>{agent.name}</b><small>{agent.role}</small></span>
              <em>{working ? "WORKING" : sceneStatus[agent.id] === "failed" ? "ERROR" : sceneStatus[agent.id] === "completed" ? "COMPLETE" : sceneStatus[agent.id] === "skipped" ? "SKIPPED" : sceneStatus[agent.id] === "visiting" ? "AT TOOL" : sceneStatus[agent.id] === "chatting" ? "AT DESK" : "AT DESK · READY"}</em>
            </button>
            <ol className="crew-workflow-steps" aria-label={`${agent.name} workflow`}>
              {agentWorkflowSteps[agent.id].map((step, stepIndex) => <li className={working && stepIndex === activeStep ? "current" : ""} key={step}>{step}</li>)}
            </ol>
          </section>;
        })}
      </aside>}

      {showActivity && <aside className="office-drawer activity-drawer" aria-label="Activity log">
        <div className="drawer-head"><div><small>RIGHT NOW</small><h2>ACTIVITY</h2></div><button type="button" onClick={() => setShowActivity(false)}>×</button></div>
        {activity.map((item, index) => <div className="activity-entry" key={`${item}-${index}`}><span className="activity-pip" /><p>{item}<small>{index === 0 ? "JUST NOW" : `${index + 1}M AGO`}</small></p></div>)}
      </aside>}

      {careerAssistantOpen && (
        <div style={modalStyle} onClick={() => !careerLoading && setCareerAssistantOpen(false)}>
          <div
            className="agent-panel career-assistant-panel"
            style={{ ...panelStyle, maxWidth: "1100px" }}
            onClick={(event) => event.stopPropagation()}
          >
            <button type="button" onClick={() => setCareerAssistantOpen(false)} disabled={careerLoading} className="career-close">×</button>
            <header className="career-assistant-header">
              <small>ONE CAREER TEAM · EIGHT AGENTS</small>
              <h2>Career Assistant</h2>
              <p>Share your profile once. The team will search, match and prepare one consolidated application package.</p>
            </header>

            {!careerLoading && !careerResult && (
              <form className="career-intake" onSubmit={startCareerWorkflow}>
                <div className="career-intake-grid">
                  <div className="career-resume-field">
                    <div className="career-resume-head">
                      <label htmlFor="career-resume-text">Your resume or candidate profile <span>Required</span></label>
                      <label className="career-resume-upload">CHOOSE RESUME FILE
                        <input type="file" accept=".pdf,.docx,.txt,.md,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,text/markdown" onChange={importResumeFile} aria-label="Choose a resume file from this device" />
                      </label>
                    </div>
                    <textarea id="career-resume-text" rows={8} value={careerForm.resume_text} onChange={(event) => { setCareerForm((previous) => ({ ...previous, resume_text: event.target.value })); setResumeFileName(""); }} placeholder="Choose a PDF, Word document, or text file, or paste your resume here. The agents use this text as the source of truth." />
                    <div className={`career-resume-note${resumeImportError ? " has-error" : ""}`} role={resumeImportError ? "alert" : "status"}>
                      {resumeImportError || (resumeFileName ? `Loaded ${resumeFileName}. Review the extracted text above before continuing.` : "Choose a local .pdf, .docx, .txt, or .md file, or paste your resume text above.")}
                    </div>
                  </div>
                  <label>Skills (optional)
                    <input value={careerForm.skills} onChange={(event) => setCareerForm((previous) => ({ ...previous, skills: event.target.value }))} placeholder="Python, SQL, Power BI" />
                  </label>
                  <label>Education (optional)
                    <input value={careerForm.education} onChange={(event) => setCareerForm((previous) => ({ ...previous, education: event.target.value }))} placeholder="Degree, subject, university" />
                  </label>
                  <label>Experience (optional)
                    <input value={careerForm.experience} onChange={(event) => setCareerForm((previous) => ({ ...previous, experience: event.target.value }))} placeholder="Years and relevant experience" />
                  </label>
                  <label>Roles or keywords
                    <input value={careerForm.keyword} onChange={(event) => setCareerForm((previous) => ({ ...previous, keyword: event.target.value }))} placeholder="AI / Data Intern" />
                  </label>
                  <label>Preferred location
                    <input value={careerForm.preferred_location} onChange={(event) => setCareerForm((previous) => ({ ...previous, preferred_location: event.target.value }))} placeholder="Germany, Berlin, Remote, or Any" />
                  </label>
                  <label>Job type
                    <select value={careerForm.job_type} onChange={(event) => setCareerForm((previous) => ({ ...previous, job_type: event.target.value }))}>
                      <option value="internship">Internship</option>
                      <option value="working student">Working student</option>
                      <option value="junior">Junior / entry-level</option>
                      <option value="any">Any early-career role</option>
                    </select>
                  </label>
                  <label>Maximum opportunities to prepare
                    <select value={careerForm.limit} onChange={(event) => setCareerForm((previous) => ({ ...previous, limit: Number(event.target.value) }))}>
                      {[1, 2, 3, 5].map((count) => <option key={count} value={count}>{count}</option>)}
                    </select>
                  </label>
                  <label>Official company website (optional; used for one selected job)
                    <input value={careerForm.company_url} onChange={(event) => setCareerForm((previous) => ({ ...previous, company_url: event.target.value }))} placeholder="https://company.example" />
                  </label>
                  <details className="career-section profile-extra-fields">
                    <summary>Candidate details & career goals</summary>
                    <div className="career-intake-grid">
                      <label>Full name<input value={careerForm.full_name || ""} onChange={(event) => setCareerForm((previous) => ({ ...previous, full_name: event.target.value }))} /></label>
                      <label>Email<input type="email" value={careerForm.email || ""} onChange={(event) => setCareerForm((previous) => ({ ...previous, email: event.target.value }))} /></label>
                      <label>Phone<input value={careerForm.phone || ""} onChange={(event) => setCareerForm((previous) => ({ ...previous, phone: event.target.value }))} /></label>
                      <label>University<input value={careerForm.university || ""} onChange={(event) => setCareerForm((previous) => ({ ...previous, university: event.target.value }))} /></label>
                      <label>Projects<textarea rows={3} value={careerForm.projects || ""} onChange={(event) => setCareerForm((previous) => ({ ...previous, projects: event.target.value }))} placeholder="One project per line; include only your actual work" /></label>
                      <label>Certifications<textarea rows={2} value={careerForm.certifications || ""} onChange={(event) => setCareerForm((previous) => ({ ...previous, certifications: event.target.value }))} /></label>
                      <label>Languages<textarea rows={2} value={careerForm.languages || ""} onChange={(event) => setCareerForm((previous) => ({ ...previous, languages: event.target.value }))} /></label>
                      <label>Career goals<textarea rows={2} value={careerForm.career_goals || ""} onChange={(event) => setCareerForm((previous) => ({ ...previous, career_goals: event.target.value }))} /></label>
                    </div>
                  </details>
                </div>
                <div className="career-profile-actions">
                  <button type="button" onClick={() => void persistCandidateProfile()} disabled={!careerForm.resume_text.trim()}>{profileSaveMessage || "SAVE CANDIDATE PROFILE"}</button>
                  <span>Saved locally in your CareerPilot database · loaded automatically next time</span>
                </div>
                <button type="submit" className="career-start-button">✦ START CAREER ANALYSIS</button>
              </form>
            )}

            {!careerLoading && workflowHistory.length > 0 && <details className="career-section career-history-section">
              <summary>Previous Career Analyses <b>{workflowHistory.length}</b></summary>
              {workflowHistory.map((entry) => <div className="career-history-row" key={entry.id}>
                <span><strong>{entry.keyword}</strong><small>{new Date(entry.created_at).toLocaleString()} · {entry.summary.selected_jobs || 0} suitable · {entry.summary.documents_completed || 0} packages</small></span>
                <button type="button" onClick={() => void reopenWorkflowHistory(entry.id)}>OPEN PACKAGE</button>
              </div>)}
            </details>}
            {historyError && <p className="career-inline-error" role="status">{historyError}</p>}

            {careerLoading && (
              <section className="career-progress" aria-live="polite">
                <div className="career-progress-title"><span className="online-dot" /> WORKFLOW IN PROGRESS</div>
                <p>{careerProgress[careerProgress.length - 1]?.message || "Starting the Career Assistant…"}</p>
                <ol>
                  {careerWorkflowOrder.map((id) => {
                    const agent = agents.find((item) => item.id === id)!;
                    const latest = [...careerProgress].reverse().find((item) => item.agent_id === id);
                    const status = latest?.status || "queued";
                    return <li className={`career-stage ${status}`} key={id}><span className="career-stage-mark">{status === "completed" ? "✓" : status === "failed" ? "!" : status === "working" ? "◌" : "·"}</span><b>{agent.name}</b><small>{latest?.message || "Waiting"}</small></li>;
                  })}
                </ol>
              </section>
            )}

            {careerError && <div className="career-error" role="alert">{careerError}</div>}

            {careerResult && (
              <section className="career-results" aria-label="Consolidated career results">
                <div className="career-result-heading"><div><small>CAREERPILOT · FINAL PACKAGE</small><h3>Your Career Analysis</h3></div><button type="button" onClick={() => { setCareerResult(null); setCareerProgress([]); setCareerError(""); }}>EDIT PROFILE / RUN AGAIN</button></div>
                <div className="career-summary-grid">
                  <div><strong>{careerResult.summary.jobs_found || 0}</strong><span>Jobs discovered</span></div>
                  <div><strong>{careerResult.summary.jobs_evaluated ?? careerResult.summary.jobs_found ?? 0}</strong><span>Jobs evaluated</span></div>
                  <div><strong>{careerResult.summary.suitable_jobs ?? careerResult.summary.selected_jobs ?? 0}</strong><span>Suitable jobs</span></div>
                  <div><strong>{careerResult.summary.unsuitable_jobs || 0}</strong><span>Unsuitable jobs</span></div>
                  <div><strong>{careerResult.summary.documents_completed || 0}</strong><span>Packages prepared</span></div>
                  <div><strong>{careerResult.summary.failed_tasks || 0}</strong><span>Failed agents</span></div>
                  <div><strong>{careerResult.summary.skipped_tasks || 0}</strong><span>Skipped agents</span></div>
                </div>

                <details className="career-section">
                  <summary>Job opportunities found <b>{careerResult.jobs_found.length}</b></summary>
                  <div className="career-found-jobs">
                    {careerResult.jobs_found.map((job, index) => <article key={`${job.url || job.title}-${index}`}><div><strong>{job.title}</strong><span>{job.company} · {job.location || "Location not specified"} · {job.suitable ? "Selected as suitable" : "Not selected"}</span>{job.match?.recommendation && <small>{job.match.recommendation}</small>}{!job.suitable && Array.isArray(job.rejection_reasons) && job.rejection_reasons.length > 0 && <small>Why not selected: {job.rejection_reasons.join(" ")}</small>}</div><b>{Number(job.match_score || 0)}%</b>{job.url && <a href={job.url} target="_blank" rel="noreferrer">View listing ↗</a>}</article>)}
                    {careerResult.jobs_found.length === 0 && <p>No matching listings were returned. Check the provider messages below or adjust your preferences.</p>}
                  </div>
                </details>

                <section className="career-section career-selected-section">
                  <h4>Selected opportunities and application packages <span>{careerResult.selected_jobs.length}</span></h4>
                  {careerResult.selected_jobs.map((item, index) => {
                    const job = item.job;
                    const trackingKey = String(job.url || `${job.company}-${job.title}`);
                    return <article className="career-job-package" key={`${trackingKey}-${index}`}>
                      <header><div><small>RECOMMENDED MATCH · {Number(item.match.match_score || 0)}%</small><h5>{job.title}</h5><p>{job.company} · {job.location || "Location not specified"} · {job.source || "Job source not specified"}</p></div><button type="button" onClick={() => void saveWorkflowJob(item)} disabled={Boolean(trackerMessages[trackingKey])}>{trackerMessages[trackingKey] || (item.tracking?.status === "Already tracked" ? "Already tracked" : "SAVE TO TRACKER")}</button></header>
                      <p><strong>Recommendation:</strong> {item.match.recommendation || "Review this opportunity"}</p>
                      <p><strong>Skills match:</strong> {(item.match.matched_skills || []).join(", ") || "No matching skills identified"}</p>
                      <p><strong>Skills to address:</strong> {(item.match.missing_skills || []).join(", ") || "No additional skill gaps identified"}</p>
                      <p><strong>Education:</strong> {item.match.education_match ? "Match identified" : "Review education requirements"} · <strong>Experience:</strong> {item.match.experience_match ? "Relevant experience identified" : "Review experience requirements"}</p>
                      {job.url && <a className="career-listing-link" href={job.url} target="_blank" rel="noreferrer">OPEN ORIGINAL LISTING ↗</a>}
                      {item.resume && <details className="career-document"><summary>Tailored resume</summary><div className="career-document-actions"><button type="button" onClick={() => void copyCareerDocument(`resume-${index}`, item.resume!)}>{copiedDocument === `resume-${index}` ? "COPIED" : "COPY RESUME"}</button><button type="button" onClick={() => downloadCareerDocument(`${job.company}-${job.title}-resume`, item.resume!)}>DOWNLOAD .TXT</button><button type="button" onClick={() => printCareerDocument(`${job.company} - ${job.title} Resume`, item.resume!)}>PRINT / SAVE PDF</button></div><pre>{item.resume}</pre>{item.resume_analysis && <details className="career-document-analysis"><summary>Resume tailoring details</summary><p><strong>Target:</strong> {item.resume_analysis.target_job?.title} · {item.resume_analysis.target_job?.company}</p><p><strong>Matched verified skills:</strong> {(item.resume_analysis.relevant_skills_matched || []).join(", ") || "None detected"}</p><p><strong>Missing skills:</strong> {(item.resume_analysis.missing_skills || []).join(", ") || "None detected"}</p><p><strong>Changes made:</strong></p><ul>{(item.resume_analysis.changes_made || []).map((change: string) => <li key={change}>{change}</li>)}</ul><p><strong>Candidate verification:</strong></p><ul>{(item.resume_analysis.information_needing_candidate_verification || []).map((note: string) => <li key={note}>{note}</li>)}</ul></details>}</details>}
                      {item.cover_letter && <details className="career-document"><summary>Customized cover letter</summary><div className="career-document-actions"><button type="button" onClick={() => void copyCareerDocument(`letter-${index}`, item.cover_letter!)}>{copiedDocument === `letter-${index}` ? "COPIED" : "COPY COVER LETTER"}</button><button type="button" onClick={() => downloadCareerDocument(`${job.company}-${job.title}-cover-letter`, item.cover_letter!)}>DOWNLOAD .TXT</button><button type="button" onClick={() => printCareerDocument(`${job.company} - ${job.title} Cover Letter`, item.cover_letter!)}>PRINT / SAVE PDF</button></div><pre>{item.cover_letter}</pre></details>}
                      {item.company_research && <details className="career-document"><summary>Company research and interview preparation</summary>{job.company_url && <p><a href={job.company_url} target="_blank" rel="noreferrer">Open supplied official website ↗</a></p>}<pre>{item.company_research}</pre></details>}
                      {item.review && <details className="career-document"><summary>Resume and cover letter review</summary><pre>{item.review}</pre></details>}
                      {item.errors?.map((message) => <p className="career-inline-error" key={message}>{message}</p>)}
                    </article>;
                  })}
                  {careerResult.selected_jobs.length === 0 && <p>No jobs passed the suitability threshold, so document generation was skipped.</p>}
                </section>

                <details className="career-section">
                  <summary>Application tracking <b>{careerResult.application_tracking?.statistics?.total_applications ?? 0} existing records</b></summary>
                  <p>Workflow review does not mark opportunities as applied. Use “Save to tracker” on a selected job to add it as Saved. Existing job URLs are deduplicated.</p>
                </details>

                {careerResult.project_intelligence && <details className="career-section"><summary>Project Intelligence · skill and portfolio recommendations</summary><pre>{JSON.stringify(careerResult.project_intelligence, null, 2)}</pre></details>}
                {careerResult.errors.length > 0 && <details className="career-section career-error-section" open><summary>Agent errors and source limitations <b>{careerResult.errors.length}</b></summary>{careerResult.errors.map((item, index) => <p key={`${item.agent}-${index}`}><strong>{item.agent}:</strong> {item.message}</p>)}</details>}
                {(careerResult as any).source_errors && Object.keys((careerResult as any).source_errors).length > 0 && <details className="career-section" open><summary>Job source status</summary><pre>{JSON.stringify((careerResult as any).source_errors, null, 2)}</pre></details>}
              </section>
            )}
          </div>
        </div>
      )}

      {/* AGENT WORKSPACE MODAL */}

      {selectedAgent && (

        <div style={modalStyle} onClick={closeAgent}>

          <div
            className="agent-panel"
            style={panelStyle}
            onClick={(event) => event.stopPropagation()}
          >

            <button
              type="button"
              onClick={closeAgent}
              disabled={loading || chatBusy}
              style={{
                position: "absolute",
                right: "18px",
                top: "15px",
                border: "none",
                borderRadius: "9px",
                background: "#eadcf8",
                padding: "10px 14px",
                fontSize: "20px",
                cursor: "pointer",
                color: "#665080",
              }}
            >
              ×
            </button>

            <div style={{ textAlign: "center" }}>

              <div className={`agent-portrait portrait-${selectedAgent.id}`} aria-hidden="true">
                {selectedAgent.name.split(/\s+/).map((part) => part[0]).join("").slice(0, 2)}
              </div>

              <h2 style={{ margin: "5px 0", color: "#21172b" }}>
                {selectedAgent.name}
              </h2>

              <p style={{ color: "#9681a9", marginTop: "5px" }}>
                {selectedAgent.role}
              </p>

              <span
                style={{
                  display: "inline-block",
                  background: backendConnected ? "#dff4df" : "#ffe5dc",
                  color: backendConnected ? "#398b58" : "#a44330",
                  padding: "10px 20px",
                  borderRadius: "25px",
                  fontSize: "12px",
                  fontWeight: 900,
                  margin: "15px 0",
                }}
              >
                {backendConnected ? "🟢 BACKEND CONNECTED" : "🔴 BACKEND OFFLINE · START THE API"}
              </span>

            </div>

            <div className="agent-conversation-layout">
            <section className="agent-context-window" aria-label={`${selectedAgent.name} context window`}>
              <div className="context-window-head">
                <div><small>CAREERPILOT TEAM · LEAD DESK {selectedAgent.id.toString().padStart(2, "0")}</small><h3>TEAM CONTEXT WINDOW</h3></div>
                <span><i /> {chatBusy ? "TEAM THINKING" : "8 AGENTS READY"}</span>
              </div>
              <div className="context-agent-brief">
                <small>LEAD DESK · {selectedAgent.name.toUpperCase()}</small>
                <p>{selectedAgent.role}. All eight agent specialties inform one consolidated team answer.</p>
              </div>
              <details className="context-workflow">
                <summary>Team specialists <b>8 agents</b></summary>
                <ol>{agents.map((agent) => <li key={agent.id}><strong>{agent.name}:</strong> {agent.role}</li>)}</ol>
              </details>
              <details className="context-workflow">
                <summary>Lead desk workflow <b>{agentWorkflowSteps[selectedAgent.id].length} steps</b></summary>
                <ol>{agentWorkflowSteps[selectedAgent.id].map((step) => <li key={step}>{step}</li>)}</ol>
              </details>
              <div className="context-inputs">
                <small>ACTIVE TASK INPUTS</small>
                {Object.entries(formValues).filter(([, value]) => value.trim()).length ? (
                  <ul>{Object.entries(formValues).filter(([, value]) => value.trim()).map(([key, value]) => <li key={key}><b>{key.replaceAll("_", " ")}</b><span>{value}</span></li>)}</ul>
                ) : <p>No task form inputs supplied yet.</p>}
                <div className="context-output-state"><span className="system-light" /> {result == null ? "No task output attached" : "Latest task output will be shared with this agent"}</div>
                {result != null && <details className="context-latest-output"><summary>Inspect attached result</summary><pre>{(typeof result === "string" ? result : JSON.stringify(result, null, 2)).slice(0, 1800)}</pre></details>}
              </div>
              <label className="context-note-label" htmlFor="agent-context-notes">EXTRA CONTEXT FOR THIS AGENT</label>
              <textarea
                id="agent-context-notes"
                className="agent-context-notes"
                value={agentContextNotes[selectedAgent.id] || ""}
                onChange={(event) => setAgentContextNotes((previous) => ({ ...previous, [selectedAgent.id]: event.target.value }))}
                placeholder="Add preferences, constraints, or details the agent should remember in this conversation…"
                rows={3}
              />
            </section>

            <section className="agent-chat" aria-label={`Chat with ${selectedAgent.name}`}>
              <div className="agent-chat-head"><span>ONE TEAM RESPONSE · 8 AGENTS</span><span>{chatBusy ? "THINKING…" : "CONTEXT LOADED"}</span></div>
              <div className="agent-chat-log" aria-live="polite">
                {(chatMessages[selectedAgent.id] || []).length === 0 ? (
                  <p className="chat-empty">Ask CareerPilot’s full team. You’ll get one combined answer.</p>
                ) : (chatMessages[selectedAgent.id] || []).map((message, index) => (
                  <div className={`chat-line ${message.role}`} key={`${message.role}-${index}`}>
                    <small>{message.role === "user" ? "YOU" : "CAREERPILOT TEAM · 8 AGENTS"}</small>
                    <p>{message.content}</p>
                  </div>
                ))}
                {chatBusy && <div className="chat-thinking">CareerPilot’s team is thinking<span> · · ·</span></div>}
              </div>
              <form className="agent-chat-form" onSubmit={sendMessage}>
                <input value={chatInput} onChange={(event) => setChatInput(event.target.value)} placeholder={`Message ${selectedAgent.name}…`} aria-label="Message the agent" />
                <button type="submit" disabled={chatBusy || !chatInput.trim()} aria-label="Send message">➤</button>
              </form>
            </section>
            </div>

            {/* APPLICATION MANAGER */}

            {selectedAgent.id === 7 ? (

              <div>

                <h3>APPLICATION TRACKER</h3>

                <button
                  type="button"
                  style={actionButtonStyle}
                  onClick={callAgent}
                  disabled={loading}
                >
                  {loading ? "LOADING..." : "VIEW MY APPLICATIONS"}
                </button>

                {applications.length > 0 && (
                  <ul aria-label="Saved applications">
                    {applications.map((application) => (
                      <li key={application.id}>
                        <strong>{application.role}</strong> at {application.company}
                        <span> · Match {application.match_score ?? "—"}% · {application.location || "Location not specified"}</span>
                        <select aria-label={`Status for ${application.role} at ${application.company}`} value={application.status} onChange={(event) => void changeApplicationStatus(application, event.target.value)}>
                          {["Discovered", "Suitable", "Documents Prepared", "Ready to Apply", "Saved", "Applied", "Assessment", "Interview", "Rejected", "Offer", "Withdrawn"].map((status) => <option key={status}>{status}</option>)}
                        </select>
                        {application.application_date && <small>Saved {application.application_date}</small>}
                      </li>
                    ))}
                  </ul>
                )}

                <h3 style={{ marginTop: "25px" }}>ADD APPLICATION</h3>

                <label>
                  Company name

                  <input
                    style={inputStyle}
                    placeholder="Company name"
                    value={formValues.company || ""}
                    onChange={(event) =>
                      setFormValues((previous) => ({
                        ...previous,
                        company: event.target.value,
                      }))
                    }
                  />
                </label>

                <label>
                  Job role

                  <input
                    style={inputStyle}
                    placeholder="AI/ML Intern"
                    value={formValues.role || ""}
                    onChange={(event) =>
                      setFormValues((previous) => ({
                        ...previous,
                        role: event.target.value,
                      }))
                    }
                  />
                </label>

                <label>
                  Job URL (optional)

                  <input
                    style={inputStyle}
                    placeholder="https://..."
                    value={formValues.job_url || ""}
                    onChange={(event) =>
                      setFormValues((previous) => ({
                        ...previous,
                        job_url: event.target.value,
                      }))
                    }
                  />
                </label>

                <button
                  type="button"
                  style={actionButtonStyle}
                  onClick={addApplication}
                  disabled={loading}
                >
                  {loading ? "SAVING..." : "SAVE APPLICATION"}
                </button>

              </div>

            ) : (

              <>

                {agentFields[selectedAgent.id]?.map((field) => (

                  <label
                    key={field.name}
                    style={{
                      display: "block",
                      marginBottom: "15px",
                      fontWeight: 800,
                      fontSize: "13px",
                    }}
                  >

                    {field.label}

                    {field.multiline ? (

                      <textarea
                        style={{
                          ...inputStyle,
                          minHeight: "125px",
                          resize: "vertical",
                        }}
                        placeholder={field.placeholder}
                        value={formValues[field.name] || ""}
                        onChange={(event) =>
                          setFormValues((previous) => ({
                            ...previous,
                            [field.name]: event.target.value,
                          }))
                        }
                      />

                    ) : (

                      <input
                        style={inputStyle}
                        placeholder={field.placeholder}
                        value={formValues[field.name] || ""}
                        onChange={(event) =>
                          setFormValues((previous) => ({
                            ...previous,
                            [field.name]: event.target.value,
                          }))
                        }
                      />

                    )}

                  </label>

                ))}

                <button
                  type="button"
                  style={{
                    ...actionButtonStyle,
                    opacity: loading ? 0.7 : 1,
                  }}
                  onClick={callAgent}
                  disabled={loading}
                >
                  {loading
                    ? "⏳ YOUR AGENT IS WORKING..."
                    : "🚀 START WORKING →"}
                </button>

              </>

            )}

            {/* ERROR MESSAGE */}

            {error && (

              <div
                style={{
                  marginTop: "18px",
                  padding: "13px",
                  background: "#ffe4e4",
                  color: "#a12c2c",
                  borderRadius: "9px",
                  overflowWrap: "anywhere",
                }}
              >
                ⚠️ {error}
              </div>

            )}

            {/* AGENT RESULT */}

            {result !== null && (

              <div style={{ marginTop: "25px" }}>

              <h3 style={{ color: "#563b78", marginBottom: "15px" }}>
                  WORK RESULTS
                </h3>

                {/* JOB HUNTER RESULTS */}

                {selectedAgent.id === 1 &&
                Array.isArray((result as any).jobs) ? (

                  <div>

                    {(result as any).jobs.length === 0 ? (

                      <div>
                        {(result as any).source_errors && Object.keys((result as any).source_errors).length > 0 ? (
                          <div role="status" style={{ background: "#ffe5dc", color: "#842f20", padding: "14px", borderRadius: "8px", marginBottom: "12px" }}>
                            <strong>Job sources could not be reached.</strong>
                            {Object.entries((result as any).source_errors).map(([source, message]) => (
                              <p key={source}><strong>{source}:</strong> {String(message)}</p>
                            ))}
                          </div>
                        ) : (
                          <p>No listings matched this search. Try a broader keyword such as “Python” or “Data Analyst”.</p>
                        )}
                        {(result as any).source_summary && (
                          <small>Listings found by source — Arbeitnow: {(result as any).source_summary.arbeitnow_jobs}, Remotive: {(result as any).source_summary.remotive_jobs}</small>
                        )}
                      </div>

                    ) : (

                      <>

                        {!(result as any).jobs.some(
                          (job: any) => job.internship_suitable === true
                        ) && (

                          <p
                            style={{
                              background: "#fff3cd",
                              padding: "12px",
                              borderRadius: "8px",
                              color: "#795600",
                            }}
                          >
                            No explicitly identified internship roles were
                            found. Review these related job results carefully.
                          </p>

                        )}

                        <div
                          style={{
                            display: "grid",
                            gridTemplateColumns:
                              "repeat(auto-fit, minmax(260px, 1fr))",
                            gap: "15px",
                          }}
                        >

                          {(result as any).jobs.map(
                            (job: any, index: number) => (

                              <div
                                key={index}
                                style={{
                                  background: "#fff",
                                  border: "1px solid #e3d8f0",
                                  borderRadius: "12px",
                                  padding: "18px",
                                  boxShadow:
                                    "0 3px 10px rgba(70, 40, 100, 0.08)",
                                }}
                              >

                                <h3
                                  style={{
                                    color: "#563b78",
                                    marginTop: 0,
                                  }}
                                >
                                  {job.title || "Untitled position"}
                                </h3>

                                <p>
                                  <strong>Company:</strong>{" "}
                                  {job.company || "Not specified"}
                                </p>

                                <p>
                                  <strong>Location:</strong>{" "}
                                  {job.location || "Not specified"}
                                </p>

                                <p>
                                  <strong>Remote:</strong>{" "}
                                  {job.remote ? "Yes" : "Not confirmed"}
                                </p>

                                <div
                                  style={{
                                    background: "#f0e8fa",
                                    padding: "10px",
                                    borderRadius: "8px",
                                    margin: "12px 0",
                                  }}
                                >
                                  <strong>Match Score:</strong>{" "}
                                  {Number(job.match_score ?? 0)}%
                                </div>

                                <p>
                                  <strong>Role level:</strong>{" "}
                                  {job.job_level || "Not specified"}
                                </p>

                                <p>
                                  <strong>Internship suitability:</strong>{" "}
                                  {job.internship_suitable === true
                                    ? "Suitable"
                                    : "Not confirmed"}
                                </p>

                                {Array.isArray(job.matched_skills) &&
                                  job.matched_skills.length > 0 && (

                                    <div>
                                      <strong>Matched Skills:</strong>
                                      <p>{job.matched_skills.join(", ")}</p>
                                    </div>

                                  )}

                                {Array.isArray(job.missing_skills) &&
                                  job.missing_skills.length > 0 && (

                                    <div>
                                      <strong>Skills to Develop:</strong>
                                      <p>{job.missing_skills.join(", ")}</p>
                                    </div>

                                  )}

                                {job.recommendation && (

                                  <p>
                                    <strong>Recommendation:</strong>{" "}
                                    {job.recommendation}
                                  </p>

                                )}

                                {job.url && (

                                  <a
                                    href={job.url}
                                    target="_blank"
                                    rel="noreferrer"
                                    style={{
                                      display: "inline-block",
                                      marginTop: "10px",
                                      background: "#704c99",
                                      color: "#fff",
                                      padding: "10px 16px",
                                      borderRadius: "7px",
                                      textDecoration: "none",
                                      fontWeight: "bold",
                                    }}
                                  >
                                    Apply Now ↗
                                  </a>

                                )}

                              </div>

                            )
                          )}

                        </div>

                      </>

                    )}

                  </div>

                ) : selectedAgent.id === 2 ? (

                  /* JOB MATCHER RESULTS */

                  <div
                    style={{
                      background: "#ffffff",
                      padding: "20px",
                      borderRadius: "14px",
                      border: "1px solid #e3d8f0",
                      boxShadow: "0 3px 10px rgba(70, 40, 100, 0.08)",
                    }}
                  >

                    <h2 style={{ color: "#563b78", marginTop: 0 }}>
                      🎯 Job Match Analysis
                    </h2>

                    <div
                      style={{
                        background: "#f0e8fa",
                        padding: "18px",
                        borderRadius: "12px",
                        textAlign: "center",
                        marginBottom: "18px",
                      }}
                    >

                      <h1
                        style={{
                          color: "#704c99",
                          fontSize: "38px",
                          margin: 0,
                        }}
                      >
                        {Number((matchResult as any)?.match_score ?? 0)}%
                      </h1>

                      <strong>Overall Match Score</strong>

                    </div>

                    <p>
                      <strong>Job Level:</strong>{" "}
                      {(matchResult as any)?.job_level || "Not specified"}
                    </p>

                    <p>
                      <strong>Internship Suitable:</strong>{" "}
                      {(matchResult as any)?.internship_suitable
                        ? "Yes"
                        : "Not confirmed"}
                    </p>

                    <p>
                      <strong>Skill Score:</strong>{" "}
                      {Number((matchResult as any)?.skill_score ?? 0)}%
                    </p>

                    {/* MATCHED SKILLS */}

                    <div style={{ marginTop: "20px" }}>

                      <h3 style={{ color: "#398b58" }}>
                        ✅ Matched Skills
                      </h3>

                      {Array.isArray((matchResult as any)?.matched_skills) &&
                      (matchResult as any).matched_skills.length > 0 ? (

                        <div
                          style={{
                            display: "flex",
                            flexWrap: "wrap",
                            gap: "8px",
                          }}
                        >

                          {(matchResult as any).matched_skills.map(
                            (skill: string, index: number) => (

                              <span
                                key={index}
                                style={{
                                  background: "#dff4df",
                                  color: "#287545",
                                  padding: "7px 12px",
                                  borderRadius: "20px",
                                  fontSize: "13px",
                                }}
                              >
                                {skill}
                              </span>

                            )
                          )}

                        </div>

                      ) : (

                        <p>No matched skills identified.</p>

                      )}

                    </div>

                    {/* MISSING SKILLS */}

                    <div style={{ marginTop: "20px" }}>

                      <h3 style={{ color: "#b45a42" }}>
                        📚 Missing Skills
                      </h3>

                      {Array.isArray((matchResult as any)?.missing_skills) &&
                      (matchResult as any).missing_skills.length > 0 ? (

                        <div
                          style={{
                            display: "flex",
                            flexWrap: "wrap",
                            gap: "8px",
                          }}
                        >

                          {(matchResult as any).missing_skills.map(
                            (skill: string, index: number) => (

                              <span
                                key={index}
                                style={{
                                  background: "#ffe5dc",
                                  color: "#a44330",
                                  padding: "7px 12px",
                                  borderRadius: "20px",
                                  fontSize: "13px",
                                }}
                              >
                                {skill}
                              </span>

                            )
                          )}

                        </div>

                      ) : (

                        <p>No missing skills identified.</p>

                      )}

                    </div>

                    {/* EDUCATION AND EXPERIENCE */}

                    <div
                      style={{
                        marginTop: "20px",
                        background: "#f7f1fc",
                        padding: "15px",
                        borderRadius: "10px",
                      }}
                    >

                      <h3 style={{ color: "#563b78", marginTop: 0 }}>
                        🎓 Education & Experience
                      </h3>

                      <p>
                        <strong>Education Match:</strong>{" "}
                        {(matchResult as any)?.education_match
                          ? "Yes"
                          : "Not identified"}
                      </p>

                      <p>
                        <strong>Experience Match:</strong>{" "}
                        {(matchResult as any)?.experience_match
                          ? "Yes"
                          : "Not identified"}
                      </p>

                      <p>
                        <strong>Seniority Mismatch:</strong>{" "}
                        {(matchResult as any)?.seniority_mismatch
                          ? "Yes"
                          : "No"}
                      </p>

                    </div>

                    {/* RECOMMENDATION */}

                    <div
                      style={{
                        marginTop: "20px",
                        padding: "15px",
                        background: "#eee3f8",
                        borderRadius: "10px",
                      }}
                    >

                      <h3 style={{ color: "#563b78", marginTop: 0 }}>
                        💡 Recommendation
                      </h3>

                      <p>
                        {(matchResult as any)?.recommendation ||
                          "No recommendation available."}
                      </p>

                      {(matchResult as any)?.job_suitability && (

                        <p>
                          <strong>Job Suitability:</strong>{" "}
                          {(matchResult as any).job_suitability}
                        </p>

                      )}

                      {(matchResult as any)?.scoring_note && (

                        <p>
                          <strong>Scoring Note:</strong>{" "}
                          {(matchResult as any).scoring_note}
                        </p>

                      )}

                    </div>

                  </div>

                ) : selectedAgent.id === 3 && (result as any).tailored_resume ? (
                  <div className="career-resume-output">
                    <h4>{(result as any).target_job?.title || "Tailored resume"} · {(result as any).target_job?.company || "Company not specified"}</h4>
                    <pre>{(result as any).tailored_resume}</pre>
                    <h4>Matched verified skills</h4>
                    <p>{((result as any).relevant_skills_matched || []).join(", ") || "None detected"}</p>
                    <h4>Missing skills</h4>
                    <p>{((result as any).missing_skills || []).join(", ") || "None detected"}</p>
                    <h4>Changes made</h4>
                    <ul>{((result as any).changes_made || []).map((change: string) => <li key={change}>{change}</li>)}</ul>
                    <h4>Information to verify</h4>
                    <ul>{((result as any).information_needing_candidate_verification || []).map((note: string) => <li key={note}>{note}</li>)}</ul>
                    <details><summary>Job requirements analyzed</summary><pre>{JSON.stringify((result as any).requirements_analyzed, null, 2)}</pre></details>
                  </div>
                ) : (

                  /* OTHER AGENT RESULTS */

                  <pre
                    style={{
                      background: "#fff",
                      padding: "15px",
                      borderRadius: "10px",
                      overflowX: "auto",
                      whiteSpace: "pre-wrap",
                      wordBreak: "break-word",
                    }}
                  >
                    {JSON.stringify(result, null, 2)}
                  </pre>

                )}

              </div>

            )}

          </div>

        </div>

      )}

    </main>
  );
}

export default App;
