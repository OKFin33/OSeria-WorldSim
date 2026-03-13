import type {
  ApiErrorPayload,
  RuntimeSessionDebugSnapshot,
  RuntimeSessionSnapshot,
  RuntimeTurnResponse,
  RuntimeWorldListItem,
} from "../types";

const API_BASE_URL = import.meta.env.VITE_RUNTIME_API_BASE_URL ?? "http://127.0.0.1:8001";

export class ApiError extends Error {
  payload: ApiErrorPayload;

  constructor(payload: ApiErrorPayload) {
    super(payload.message);
    this.payload = payload;
  }
}

function fallbackError(message = "Unknown error"): ApiErrorPayload {
  return { code: "internal", message, retryable: false };
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
        : fallbackError(text || response.statusText);
    throw new ApiError(payload);
  }
  return data as T;
}

export function getRuntimeWorlds(): Promise<RuntimeWorldListItem[]> {
  return request<RuntimeWorldListItem[]>("/api/runtime/worlds");
}

export function getRuntimeSession(runtimeSessionId: string): Promise<RuntimeSessionSnapshot> {
  return request<RuntimeSessionSnapshot>(`/api/runtime/session/${runtimeSessionId}`);
}

export function getRuntimeSessionDebug(runtimeSessionId: string): Promise<RuntimeSessionDebugSnapshot> {
  return request<RuntimeSessionDebugSnapshot>(`/api/runtime/session/${runtimeSessionId}/debug`);
}

export function bootstrapRuntimeSession(runtimeSessionId: string): Promise<RuntimeSessionSnapshot> {
  return request<RuntimeSessionSnapshot>(`/api/runtime/session/${runtimeSessionId}/bootstrap`, {
    method: "POST",
  });
}

export function updateRuntimeDisplayTitle(
  runtimeSessionId: string,
  displayTitle: string,
): Promise<RuntimeSessionSnapshot> {
  return request<RuntimeSessionSnapshot>(`/api/runtime/session/${runtimeSessionId}/display-title`, {
    method: "PATCH",
    body: JSON.stringify({ display_title: displayTitle }),
  });
}

export function runRuntimeTurn(input: {
  runtime_session_id: string;
  user_action: string;
}): Promise<RuntimeTurnResponse> {
  return request<RuntimeTurnResponse>("/api/runtime/turn", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function runRuntimeTurnStream(
  input: {
    runtime_session_id: string;
    user_action: string;
  },
  handlers: {
    onAssistantDelta: (payload: { delta: string; content: string; turn_number: number }) => void;
    onComplete: (response: RuntimeTurnResponse) => void;
  },
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/runtime/turn/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(input),
  });
  if (!response.ok) {
    const text = await response.text();
    let data: unknown = null;
    try {
      data = JSON.parse(text);
    } catch {
      data = null;
    }
    const payload =
      typeof data === "object" && data !== null && "error" in data
        ? (data as { error?: ApiErrorPayload }).error ?? fallbackError(text || response.statusText)
        : fallbackError(text || response.statusText);
    throw new ApiError(payload);
  }
  if (!response.body) {
    throw new ApiError(fallbackError("Streaming response body is unavailable."));
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    let boundary = buffer.indexOf("\n\n");
    while (boundary !== -1) {
      const rawEvent = buffer.slice(0, boundary).trim();
      buffer = buffer.slice(boundary + 2);
      if (rawEvent) {
        const parsed = parseSseEvent(rawEvent);
        if (parsed.event === "assistant_delta") {
          handlers.onAssistantDelta(parsed.data as { delta: string; content: string; turn_number: number });
        } else if (parsed.event === "turn_complete") {
          handlers.onComplete(parsed.data as RuntimeTurnResponse);
        } else if (parsed.event === "error") {
          throw new ApiError(parsed.data as ApiErrorPayload);
        }
      }
      boundary = buffer.indexOf("\n\n");
    }
  }
}

function parseSseEvent(block: string): { event: string; data: unknown } {
  const lines = block.split("\n");
  let event = "message";
  const dataLines: string[] = [];
  for (const line of lines) {
    if (line.startsWith("event:")) {
      event = line.slice("event:".length).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trim());
    }
  }
  const payload = dataLines.join("\n");
  return {
    event,
    data: payload ? JSON.parse(payload) : null,
  };
}
