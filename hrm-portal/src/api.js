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
    let message = "API Request failed";

    if (Array.isArray(error.detail)) {
      message = error.detail
        .map(err => typeof err === "string" ? err : err.msg || JSON.stringify(err))
        .filter(Boolean)
        .join("; ");
    } else if (typeof error.detail === "object" && error.detail !== null) {
      message = error.detail.detail || JSON.stringify(error.detail);
    } else if (error.detail) {
      message = error.detail;
    }

    throw new Error(message);
  }

  return response.json();
}
