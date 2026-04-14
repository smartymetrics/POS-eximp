// HRM Portal API Wrapper
export const API_BASE = "/api";

export async function apiFetch(endpoint, options = {}) {
  const token = localStorage.getItem("ec_token");
  const headers = {
    "Content-Type": "application/json",
    ...(token && { Authorization: `Bearer ${token}` }),
    ...options.headers,
  };

  const response = await fetch(`${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    localStorage.removeItem("ec_token");
    window.location.reload();
    return;
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || "API Request failed");
  }

  return response.json();
}
