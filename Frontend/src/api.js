
const API_URL = (
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000"
).replace(/\/+$/, "");

const TOKEN_KEY = "quizwise_access_token";
const USER_KEY = "quizwise_user";

export function saveLogin(data) {
  localStorage.setItem(TOKEN_KEY, data.access_token);
  localStorage.setItem(USER_KEY, JSON.stringify(data.user));
}

export function clearLogin() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function getSavedToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function getSavedUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY) || "null");
  } catch {
    return null;
  }
}

async function request(path, options = {}) {
  const token = getSavedToken();
  let response;

  try {
    response = await fetch(`${API_URL}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(options.headers || {}),
      },
    });
  } catch {
    throw new Error(
      "Can't connect to the backend. Check that FastAPI is running on port 8000."
    );
  }

  const payload = await response.json().catch(() => ({}));

  if (!response.ok) {
    if (response.status === 401 && token) {
      clearLogin();
      window.dispatchEvent(new Event("quizwise:logout"));
    }

    const detail = payload.detail;
    throw new Error(
      typeof detail === "string"
        ? detail
        : `Request failed with status ${response.status}. Please try again.`
    );
  }

  return payload;
}

export const api = {
  health: () => request("/api/health"),

  signup: (data) =>
    request("/api/auth/signup", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  login: (data) =>
    request("/api/auth/login", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  me: () => request("/api/auth/me"),

  generateQuiz: (data) =>
    request("/api/quiz/generate", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  submitQuiz: (data) =>
    request("/api/quiz/submit", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  history: () => request("/api/history"),

  historyItem: (id) => request(`/api/history/${id}`),

  weakConcepts: () => request("/api/weak-concepts"),

  generateWeeklyQuiz: () =>
    request("/api/weekly-quiz/generate", {
      method: "POST",
    }),
};
