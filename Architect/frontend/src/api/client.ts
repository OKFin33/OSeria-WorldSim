import type {
  ApiErrorPayload,
  ReplayBundle,
  GenerateResponse,
  InterviewStepResponse,
  RuntimeSessionCreateResponse,
  StartInterviewResponse,
} from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
const RUNTIME_API_BASE_URL = import.meta.env.VITE_RUNTIME_API_BASE_URL ?? "http://127.0.0.1:8001";

export class ApiError extends Error {
  payload: ApiErrorPayload;

  constructor(payload: ApiErrorPayload) {
    super(payload.message);
    this.payload = payload;
  }
}

function fallbackError(message = "Unknown error"): ApiErrorPayload {
  return {
    code: "internal",
    message,
    retryable: false,
  };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = path.startsWith("http://") || path.startsWith("https://") ? path : `${API_BASE_URL}${path}`;
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  const text = await response.text();
  const contentType = response.headers.get("content-type") ?? "";
  let data: unknown = null;
  if (text) {
    if (contentType.includes("application/json")) {
      try {
        data = JSON.parse(text);
      } catch {
        data = null;
      }
    } else {
      try {
        data = JSON.parse(text);
      } catch {
        data = null;
      }
    }
  }

  if (!response.ok) {
    const payload =
      typeof data === "object" && data !== null && "error" in data
        ? (data as { error?: ApiErrorPayload }).error ?? fallbackError(text || response.statusText)
        : fallbackError(text || response.statusText || "Unknown error");
    throw new ApiError(payload);
  }

  if (data === null && text) {
    throw new ApiError(fallbackError("Server returned an unreadable response."));
  }
  return data as T;
}

export function startInterview(): Promise<StartInterviewResponse> {
  return request<StartInterviewResponse>("/api/interview/start", { method: "POST" });
}

export function sendInterviewMessage(input: {
  session_id: string;
  message?: string;
  mirror_action?: "confirm" | "reconsider";
}): Promise<InterviewStepResponse> {
  return request<InterviewStepResponse>("/api/interview/message", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function generateWorld(input: { session_id: string }): Promise<GenerateResponse> {
  return request<GenerateResponse>("/api/generate", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function getReplayBundle(sessionId: string): Promise<ReplayBundle> {
  return request<ReplayBundle>(`/api/debug/session/${encodeURIComponent(sessionId)}/replay-bundle`);
}

export function createRuntimeSession(input: {
  system_prompt: string;
  title: string;
  world_summary: string;
  tone_keywords: string[];
  confirmed_dimensions: string[];
  emergent_dimensions: string[];
  player_profile?: string;
}): Promise<RuntimeSessionCreateResponse> {
  return request<RuntimeSessionCreateResponse>(`${RUNTIME_API_BASE_URL}/api/runtime/session`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}
