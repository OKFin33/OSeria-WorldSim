import type {
  ApiErrorPayload,
  GenerateResponse,
  InterviewArtifacts,
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

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  const text = await response.text();
  const data = text ? JSON.parse(text) : null;
  if (!response.ok) {
    const payload = data?.error ?? {
      code: "internal",
      message: "Unknown error",
      retryable: false,
    };
    throw new ApiError(payload);
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

export function generateWorld(input: {
  session_id: string;
  artifacts: InterviewArtifacts;
}): Promise<GenerateResponse> {
  return request<GenerateResponse>("/api/generate", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

