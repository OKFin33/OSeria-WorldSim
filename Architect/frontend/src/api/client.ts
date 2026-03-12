import type {
  ApiErrorPayload,
  GenerateResponse,
  InterviewStepResponse,
  StartInterviewResponse,
} from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

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
  const response = await fetch(`${API_BASE_URL}${path}`, {
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
