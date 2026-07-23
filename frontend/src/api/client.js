// Central API client. All fetches go through here so the base URL and
// error handling live in one place.
// Strip any trailing slash(es) so a VITE_API_URL like "https://api.example.com/"
// doesn't produce a broken "https://api.example.com//api/login".
const BASE = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/+$/, "");

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export const api = {
  // Auth
  login: (username, password) =>
    request("/api/login", { method: "POST", body: JSON.stringify({ username, password }) }),

  // Meta (topics + designation hierarchy)
  getMeta: () => request("/api/meta"),

  // Workshops
  getWorkshops: (topic) => request(`/api/workshops${topic ? `?topic=${encodeURIComponent(topic)}` : ""}`),
  getWorkshopTitles: () => request("/api/workshop-titles"),
  createWorkshop: (data) =>
    request("/api/workshops", { method: "POST", body: JSON.stringify(data) }),

  // Allotment (admin)
  previewAllotment: (programId) => request(`/api/allot/${programId}`),
  commitAllotment: (programId) =>
    request(`/api/allot/${programId}/commit`, { method: "POST" }),
  getAdminAllotments: (programId) => request(`/api/admin/allotments/${programId}`),
  acceptAllotment: (allotmentId) =>
    request(`/api/admin/allotments/${allotmentId}/accept`, { method: "POST" }),
  rejectAllotment: (allotmentId) =>
    request(`/api/admin/allotments/${allotmentId}/reject`, { method: "POST" }),
  getPersonnelDirectory: () => request("/api/personnel"),

  // Advanced AI
  getMetrics: () => request("/api/admin/metrics"),
  retrain: () => request("/api/ai/retrain", { method: "POST" }),
  getOracle: () => request("/api/ai/oracle"),

  // Manual override
  searchPersonnel: (q) => request(`/api/personnel/search?q=${encodeURIComponent(q)}`),
  manualAllot: (programId, personnelId) =>
    request("/api/admin/allotments/manual", {
      method: "POST",
      body: JSON.stringify({ program_id: programId, personnel_id: personnelId }),
    }),

  // Personnel analytics
  getMyAnalytics: (id) => request(`/api/me/${id}/analytics`),

  // Chatbot
  chat: (personnelId, message) =>
    request("/api/chat", {
      method: "POST",
      body: JSON.stringify({ personnel_id: personnelId, message }),
    }),

  // Personnel self-service
  getProfile: (id) => request(`/api/me/${id}`),
  getMyAllotments: (id) => request(`/api/me/${id}/allotments`),
  updateAllotmentStatus: (allotmentId, status) =>
    request(`/api/allotments/${allotmentId}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),
};
