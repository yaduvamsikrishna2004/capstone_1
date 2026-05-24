import { wait } from "./utils.js";

const DEFAULT_BASE_URL = "http://localhost:8000";
const API_CONFIG_KEY = "docassist_api_config";

export function getApiBaseUrl() {
  const saved = localStorage.getItem(API_CONFIG_KEY);
  if (!saved) return DEFAULT_BASE_URL;
  try {
    const parsed = JSON.parse(saved);
    if (typeof parsed.baseUrl === "string" && parsed.baseUrl.trim()) {
      return parsed.baseUrl.trim().replace(/\/$/, "");
    }
  } catch {
    return DEFAULT_BASE_URL;
  }
  return DEFAULT_BASE_URL;
}

export function setApiBaseUrl(value) {
  const next = value.trim().replace(/\/$/, "");
  localStorage.setItem(API_CONFIG_KEY, JSON.stringify({ baseUrl: next || DEFAULT_BASE_URL }));
}

async function request(endpoint, options = {}) {
  const {
    method = "GET",
    body,
    headers = {},
    timeout = 20000,
    retries = 1,
    isForm = false,
  } = options;
  const url = `${getApiBaseUrl()}${endpoint}`;

  for (let attempt = 0; attempt <= retries; attempt += 1) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
      const response = await fetch(url, {
        method,
        headers: isForm ? headers : { "Content-Type": "application/json", ...headers },
        body: isForm ? body : body ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      const contentType = response.headers.get("content-type") || "";
      const payload = contentType.includes("application/json")
        ? await response.json()
        : await response.text();

      if (!response.ok) {
        const detail = payload?.detail || payload?.message || `Request failed (${response.status})`;
        throw new Error(detail);
      }

      return payload;
    } catch (error) {
      clearTimeout(timeoutId);
      const isLast = attempt === retries;
      if (isLast) {
        throw error;
      }
      await wait((attempt + 1) * 550);
    }
  }

  throw new Error("Unexpected request failure.");
}

export async function uploadFiles(files, onProgress = () => {}) {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));

  let progress = 0;
  onProgress(2);
  const timer = setInterval(() => {
    progress = Math.min(progress + Math.ceil(Math.random() * 13), 93);
    onProgress(progress);
  }, 170);

  try {
    const response = await request("/upload", {
      method: "POST",
      body: formData,
      isForm: true,
      timeout: 180000,
      retries: 1,
    });
    onProgress(100);
    return response;
  } finally {
    clearInterval(timer);
  }
}

export async function sendMessage(question, userId = "web_user") {
  return request("/ask", {
    method: "POST",
    body: {
      question,
      user_id: userId,
    },
    timeout: 120000,
    retries: 1,
  });
}

export async function getChatHistory(limit = 20) {
  return request(`/history?limit=${encodeURIComponent(limit)}`, {
    method: "GET",
    timeout: 30000,
    retries: 1,
  });
}

export async function sendEmail(payload) {
  return request("/send-email", {
    method: "POST",
    body: payload,
    timeout: 45000,
    retries: 1,
  });
}

export async function sendWhatsapp(payload) {
  return request("/send-whatsapp", {
    method: "POST",
    body: payload,
    timeout: 45000,
    retries: 1,
  });
}

export async function sendSMS(payload) {
  return request("/send-sms", {
    method: "POST",
    body: payload,
    timeout: 45000,
    retries: 1,
  });
}

export async function checkHealth() {
  return request("/health", { method: "GET", timeout: 8000, retries: 0 });
}

export async function checkNotificationHealth() {
  return request("/notification-health", { method: "GET", timeout: 10000, retries: 0 });
}
