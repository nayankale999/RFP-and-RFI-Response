const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type RequestOptions = {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
};

function getAuthHeader(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, headers = {} } = options;

  const config: RequestInit = {
    method,
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeader(),
      ...headers,
    },
  };

  if (body) {
    config.body = JSON.stringify(body);
  }

  const response = await fetch(`${API_BASE}${endpoint}`, config);

  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      if (typeof window !== "undefined") {
        localStorage.removeItem("token");
        window.location.href = "/login";
      }
    }
    const error = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(error.detail || error.error || `HTTP ${response.status}`);
  }

  if (response.status === 204) return {} as T;
  return response.json();
}

async function uploadFiles(endpoint: string, files: File[]): Promise<unknown> {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));

  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: "POST",
    headers: getAuthHeader(),
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Upload failed" }));
    throw new Error(error.detail || error.error || `HTTP ${response.status}`);
  }

  return response.json();
}

async function downloadFile(endpoint: string): Promise<Blob> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeader(),
    },
  });

  if (!response.ok) {
    throw new Error(`Download failed: HTTP ${response.status}`);
  }

  return response.blob();
}

// Auth
export const auth = {
  login: (email: string, password: string) =>
    request("/api/auth/login", { method: "POST", body: { email, password } }),
  register: (email: string, name: string, password: string, role: string = "proposal_lead") =>
    request("/api/auth/register", { method: "POST", body: { email, name, password, role } }),
  me: () => request("/api/auth/me"),
};

// Projects
export const projects = {
  list: (skip = 0, limit = 50) => request(`/api/projects?skip=${skip}&limit=${limit}`),
  get: (id: string) => request(`/api/projects/${id}`),
  create: (data: { name: string; description?: string; client_name?: string; industry?: string; deadline?: string }) =>
    request("/api/projects", { method: "POST", body: data }),
  update: (id: string, data: Record<string, unknown>) =>
    request(`/api/projects/${id}`, { method: "PUT", body: data }),
  delete: (id: string) => request(`/api/projects/${id}`, { method: "DELETE" }),
};

// Documents
export const documents = {
  upload: (projectId: string, files: File[]) =>
    uploadFiles(`/api/projects/${projectId}/documents`, files),
  list: (projectId: string) => request(`/api/projects/${projectId}/documents`),
  parse: (documentId: string) =>
    request(`/api/documents/${documentId}/parse`, { method: "POST" }),
  status: (documentId: string) => request(`/api/documents/${documentId}/status`),
};

// Requirements
export const requirements = {
  list: (projectId: string, type?: string) =>
    request(`/api/projects/${projectId}/requirements${type ? `?req_type=${type}` : ""}`),
  update: (id: string, data: Record<string, unknown>) =>
    request(`/api/requirements/${id}`, { method: "PUT", body: data }),
  extract: (projectId: string) =>
    request(`/api/projects/${projectId}/extract`, { method: "POST" }),
};

// Responses
export const responses = {
  list: (projectId: string) => request(`/api/projects/${projectId}/responses`),
  update: (id: string, data: Record<string, unknown>) =>
    request(`/api/responses/${id}`, { method: "PUT", body: data }),
  generate: (projectId: string) =>
    request(`/api/projects/${projectId}/generate`, { method: "POST" }),
  regenerate: (id: string) =>
    request(`/api/responses/${id}/regenerate`, { method: "POST" }),
};

// Schedule & Pricing
export const schedule = {
  list: (projectId: string) => request(`/api/projects/${projectId}/schedule`),
  extract: (projectId: string) =>
    request(`/api/projects/${projectId}/schedule/extract`, { method: "POST" }),
};

export const pricing = {
  list: (projectId: string) => request(`/api/projects/${projectId}/pricing`),
  add: (projectId: string, data: Record<string, unknown>) =>
    request(`/api/projects/${projectId}/pricing`, { method: "POST", body: data }),
  update: (id: string, data: Record<string, unknown>) =>
    request(`/api/pricing/${id}`, { method: "PUT", body: data }),
};

// Export
export const exportApi = {
  word: (projectId: string) => downloadFile(`/api/projects/${projectId}/export/word`),
};

// Response Plan
export const plan = {
  generate: (projectId: string) =>
    request(`/api/projects/${projectId}/plan/generate`, { method: "POST" }),
};
