const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchAPI(endpoint: string, options: RequestInit = {}) {
  const token =
    typeof window !== "undefined" ? localStorage.getItem("token") : null;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const res = await fetch(`${API_URL}${endpoint}`, { ...options, headers });
  if (res.status === 401) {
    if (typeof window !== "undefined") {
      localStorage.removeItem("token");
      window.location.href = "/login";
    }
    throw new Error("Unauthorized");
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || res.statusText);
  }
  return res.json();
}

export const api = {
  // Auth
  register: (data: { username: string; email: string; password: string }) =>
    fetchAPI("/api/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  login: (username: string, password: string) => {
    const formData = new URLSearchParams();
    formData.append("username", username);
    formData.append("password", password);
    return fetch(`${API_URL}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: formData.toString(),
    }).then((r) => {
      if (!r.ok) throw new Error("Login failed");
      return r.json();
    });
  },
  me: () => fetchAPI("/api/auth/me"),

  // Boxes
  getBoxes: () => fetchAPI("/api/boxes"),
  getBox: (slug: string) => fetchAPI(`/api/boxes/${slug}`),

  // Instances
  createInstance: (boxSlug: string) =>
    fetchAPI("/api/instances", {
      method: "POST",
      body: JSON.stringify({ box_slug: boxSlug }),
    }),
  getInstances: () => fetchAPI("/api/instances"),
  getInstance: (id: number) => fetchAPI(`/api/instances/${id}`),
  deleteInstance: (id: number) =>
    fetchAPI(`/api/instances/${id}`, { method: "DELETE" }),
  resetInstance: (id: number) =>
    fetchAPI(`/api/instances/${id}/reset`, { method: "POST" }),
  getVpnConfig: (id: number) => fetchAPI(`/api/instances/${id}/vpn`),

  // Submissions
  submitFlag: (challengeId: number, flag: string) =>
    fetchAPI("/api/submissions", {
      method: "POST",
      body: JSON.stringify({ challenge_id: challengeId, flag }),
    }),
  getSubmissions: () => fetchAPI("/api/submissions"),
  getScoreboard: () => fetchAPI("/api/submissions/scoreboard"),
};
