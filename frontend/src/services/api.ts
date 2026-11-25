const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

export function getDocumentUrl(path: string) {
  return `${API_BASE_URL}${path}`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, init);
  } catch {
    throw new Error(`Could not reach the CareerPilot backend at ${API_BASE_URL}. Start the backend and retry.`);
  }
  const contentType = response.headers.get("content-type") || "";
  const data: unknown = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const detail =
      typeof data === "object" && data !== null && "detail" in data
        ? (data as { detail: unknown }).detail
        : undefined;
    const message = typeof detail === "string"
      ? detail
      : Array.isArray(detail)
        ? detail.map((issue) => {
          if (typeof issue !== "object" || issue === null) return String(issue);
          const item = issue as { loc?: unknown[]; msg?: unknown };
          const field = Array.isArray(item.loc) ? item.loc.slice(1).join(" ") : "input";
          return `${field}: ${String(item.msg || "is invalid")}`;
        }).join("; ")
        : JSON.stringify(detail ?? data);
    throw new Error(message || `Server error: ${response.status}`);
  }

  return data as T;
}

export function callAgent<T = Record<string, unknown>>(path: string, payload: Record<string, unknown>) {
  return request<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function checkBackend() {
  return request<{ status: string }>("/health");
}

export function searchJobs(keyword: string, limit = 10) {
  return callAgent("/api/jobs", { keyword, limit });
}

export function matchJob(job_description: string) {
  return callAgent("/api/match", { job_description });
}

export function getApplications() {
  return request<{ applications: unknown[] }>("/api/applications");
}

export function updateApplication(applicationId: number, payload: { status?: string; interview_date?: string; notes?: string }) {
  return request(`/api/applications/${applicationId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function createApplication(payload: { company: string; role: string; job_url: string; status?: string; location?: string; source?: string; match_score?: number; resume?: string; cover_letter?: string }) {
  return callAgent("/api/applications", payload);
}

export type SavedCandidateProfile = {
  full_name: string;
  email: string;
  phone: string;
  resume_text: string;
  skills: string;
  education: string;
  university: string;
  experience: string;
  projects: string;
  certifications: string;
  languages: string;
  preferred_job_titles: string;
  preferred_location: string;
  preferred_job_type: string;
  career_goals: string;
  github_username: string;
};

export function getCandidateProfile() {
  return request<{ profile: SavedCandidateProfile | null; updated_at: string | null }>("/api/profile");
}

export function saveCandidateProfile(profile: SavedCandidateProfile) {
  return request<{ profile: SavedCandidateProfile; updated_at: string }>("/api/profile", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(profile),
  });
}

export function getProfileFacts() {
  return request<{ profile: Record<string, any> | null }>("/api/profile/facts");
}

export function createProfileFacts(resume_text: string, source = "saved-profile") {
  return callAgent<{ profile: Record<string, any>; file: string; facts_file: string }>("/api/profile/facts", { resume_text, source });
}

export function fixProfileFacts(changes: Record<string, unknown>) {
  return request<{ profile: Record<string, any>; file: string; facts_file: string; changed: string[]; new_ids: string[] }>("/api/profile/facts", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(changes),
  });
}

export function uploadMasterCV(file: File) {
  const form = new FormData();
  form.append("file", file);
  return request<{ profile: Record<string, any>; resume_text: string; file: string; facts_file: string }>("/api/profile/master-cv", {
    method: "POST",
    body: form,
  });
}

export function getProfilePreferences() {
  return request<{ preferences: Record<string, any> }>("/api/profile/preferences");
}

export function saveProfilePreferences(preferences: Record<string, any>) {
  return request<{ preferences: Record<string, any>; file: string }>("/api/profile/preferences", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(preferences),
  });
}

export function getGitHubProjects() {
  return request<{ catalogue: Record<string, any> | null }>("/api/profile/github");
}

export function fetchGitHubProjects(username: string) {
  return callAgent<{ username: string; repos: number; projects: Record<string, any>[]; file: string }>("/api/profile/github", { username });
}

export function getWorkflowHistory() {
  return request<{ workflows: { id: number; created_at: string; keyword: string; summary: Record<string, number> }[] }>("/api/workflow-history");
}

export function getWorkflowHistoryItem(id: number) {
  return request<{ id: number; created_at: string; result: Record<string, any> }>(`/api/workflow-history/${id}`);
}

export function getWorkflowRunStatus(idempotencyKey: string) {
  return request<{ status: string; result: Record<string, any> | null; updated_at: string }>(`/api/workflow-runs/${encodeURIComponent(idempotencyKey)}`);
}

export function sendAgentChat(
  agentId: number,
  message: string,
  history: { role: "user" | "assistant"; content: string }[],
  context: Record<string, unknown>,
) {
  return callAgent<{ ai_response: string; agent_name: string; team_size: number; context_used: boolean }>("/api/agent-chat", {
    agent_id: agentId,
    message,
    history: history.slice(-12),
    context,
  });
}

export function getApplicationStats() {
  return request<{ statistics: Record<string, unknown> }>("/api/application-stats");
}

export type CareerWorkflowPayload = {
  keyword: string;
  resume_text: string;
  skills: string;
  education: string;
  experience: string;
  preferred_location: string;
  job_type: string;
  limit: number;
  company_url: string;
  full_name?: string;
  email?: string;
  phone?: string;
  university?: string;
  projects?: string;
  certifications?: string;
  languages?: string;
  career_goals?: string;
  github_username?: string;
  jobs?: Record<string, any>[];
};

export type CareerWorkflowEvent = {
  type: "progress" | "result";
  agent_id?: number;
  agent?: string;
  status?: string;
  message?: string;
  data?: Record<string, any>;
  [key: string]: unknown;
};

export async function streamCareerWorkflow(
  payload: CareerWorkflowPayload,
  onProgress: (event: CareerWorkflowEvent) => void,
  idempotencyKey?: string,
) {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/career-workflow/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/x-ndjson", ...(idempotencyKey ? { "Idempotency-Key": idempotencyKey } : {}) },
      body: JSON.stringify(payload),
    });
  } catch {
    throw new Error(`Could not reach the CareerPilot backend at ${API_BASE_URL}. Start the backend and retry.`);
  }
  if (!response.ok || !response.body) {
    const body = await response.text();
    let detail = body;
    try {
      const data = JSON.parse(body) as { detail?: unknown };
      if (typeof data.detail === "string") detail = data.detail;
      else if (Array.isArray(data.detail)) {
        detail = data.detail.map((issue) => {
          if (typeof issue !== "object" || issue === null) return String(issue);
          const item = issue as { loc?: unknown[]; msg?: unknown };
          const field = Array.isArray(item.loc) ? item.loc.slice(1).join(" ") : "input";
          return `${field}: ${String(item.msg || "is invalid").replace(/^Value error,\s*/i, "")}`;
        }).join("; ");
      }
    } catch {
      // Keep the server's plain-text detail as-is.
    }
    throw new Error(detail || `Career workflow failed: ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finalResult: Record<string, any> | undefined;
  const consume = (line: string) => {
    if (!line.trim()) return;
    const event = JSON.parse(line) as CareerWorkflowEvent;
    if (event.type === "result") finalResult = event.data;
    else onProgress(event);
  };

  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";
    lines.forEach(consume);
    if (done) break;
  }
  consume(buffer);
  if (!finalResult) throw new Error("Career workflow ended before returning its consolidated result.");
  return finalResult;
}
