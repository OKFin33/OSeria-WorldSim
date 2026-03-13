import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import userEvent from "@testing-library/user-event";
import { act, render, screen, waitFor } from "@testing-library/react";
import App from "./App";

const BOOT_POLL_INTERVAL_MS = 2000;

function jsonResponse(data: unknown, init: { ok?: boolean; status?: number } = {}) {
  const body = JSON.stringify(data);
  return {
    ok: init.ok ?? true,
    status: init.status ?? 200,
    text: async () => body,
    headers: {
      get: () => "application/json",
    },
  };
}

function makeWorld(runtimeSessionId: string, title: string, updatedAt = "2026-03-14T00:00:00Z") {
  return {
    runtime_session_id: runtimeSessionId,
    title,
    display_title: "",
    world_summary: `${title}摘要`,
    tone_keywords: [],
    turn_count: runtimeSessionId === "world-1" ? 0 : 1,
    updated_at: updatedAt,
    preview: "",
  };
}

function makeSnapshot(
  runtimeSessionId: string,
  bootStatus: "pending" | "booting" | "ready" | "failed",
  overrides: Record<string, unknown> = {},
) {
  return {
    runtime_session_id: runtimeSessionId,
    world_summary_card: {
      title: runtimeSessionId === "world-1" ? "世界一" : "世界二",
      world_summary: runtimeSessionId === "world-1" ? "世界一摘要" : "世界二摘要",
      tone_keywords: [],
      confirmed_dimensions: [],
      emergent_dimensions: [],
      player_profile: "",
    },
    display_title: "",
    boot_status: bootStatus,
    boot_started_at: "",
    boot_completed_at: "",
    boot_error: bootStatus === "failed" ? "boom" : "",
    boot_generation_count: bootStatus === "ready" ? 1 : 0,
    turn_count: bootStatus === "ready" ? 1 : 0,
    messages:
      bootStatus === "ready"
        ? [
            {
              role: "assistant",
              content: runtimeSessionId === "world-1" ? "世界一开场。" : "世界二开场。",
              turn_number: 0,
              created_at: "2026-03-14T00:00:00Z",
              meta: {},
            },
          ]
        : [],
    recent_memories: [],
    lorebook: [],
    world_stats: {
      protagonist_name: "",
      protagonist_gender: "unknown",
      current_timestamp: "",
      current_location: "",
      important_assets: [],
    },
    state_snapshot: {},
    created_at: "2026-03-14T00:00:00Z",
    updated_at: "2026-03-14T00:00:00Z",
    ...overrides,
  };
}

function deferredResponse() {
  let resolve!: (value: ReturnType<typeof jsonResponse>) => void;
  const promise = new Promise<ReturnType<typeof jsonResponse>>((innerResolve) => {
    resolve = innerResolve;
  });
  return { promise, resolve };
}

describe("Runtime App", () => {
  beforeEach(() => {
    window.history.replaceState({}, "", "/");
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("renders the empty-state prompt before a session loads", () => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse([])));
    render(<App />);
    expect(screen.getByText(/从 Architect 进入一个世界/i)).toBeInTheDocument();
  });

  it("opens Architect in a new tab when creating a new world", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse([])));
    const openMock = vi.fn(() => ({ opener: null }) as Window);
    vi.stubGlobal("open", openMock);

    render(<App />);
    await user.click(screen.getByRole("button", { name: "世界列表" }));
    await user.click(screen.getByRole("button", { name: "新建世界" }));

    expect(openMock).toHaveBeenCalledWith("http://localhost:5173", "_blank");
  });

  it("auto bootstraps a pending world exactly once", async () => {
    window.history.replaceState({}, "", "/?session=world-1");
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/api/runtime/worlds")) {
        return jsonResponse([makeWorld("world-1", "世界一")]);
      }
      if (url.endsWith("/api/runtime/session/world-1")) {
        return jsonResponse(makeSnapshot("world-1", "pending"));
      }
      if (url.endsWith("/api/runtime/session/world-1/bootstrap")) {
        return jsonResponse(makeSnapshot("world-1", "ready"));
      }
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    await waitFor(() => expect(screen.getByText("世界一开场。")).toBeInTheDocument());
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8001/api/runtime/session/world-1/bootstrap",
      expect.objectContaining({ method: "POST" }),
    );
    expect(
      fetchMock.mock.calls.filter(([url]) => String(url).endsWith("/api/runtime/session/world-1/bootstrap")),
    ).toHaveLength(1);
  });

  it("polls a booting world without posting bootstrap again", async () => {
    vi.useFakeTimers();
    window.history.replaceState({}, "", "/?session=world-1");
    let sessionReads = 0;
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/runtime/worlds")) {
        return jsonResponse([makeWorld("world-1", "世界一")]);
      }
      if (url.endsWith("/api/runtime/session/world-1")) {
        sessionReads += 1;
        return jsonResponse(makeSnapshot("world-1", sessionReads === 1 ? "booting" : "ready"));
      }
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(screen.getByText(/世界正在苏醒/i)).toBeInTheDocument();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(BOOT_POLL_INTERVAL_MS);
    });

    expect(screen.getByText("世界一开场。")).toBeInTheDocument();
    expect(
      fetchMock.mock.calls.filter(([url]) => String(url).endsWith("/api/runtime/session/world-1/bootstrap")),
    ).toHaveLength(0);
    expect(sessionReads).toBeGreaterThanOrEqual(2);
  });

  it("drops stale bootstrap results after switching worlds", async () => {
    window.history.replaceState({}, "", "/?session=world-1");
    const bootDeferred = deferredResponse();
    const user = userEvent.setup();
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/api/runtime/worlds")) {
        return Promise.resolve(jsonResponse([makeWorld("world-1", "世界一"), makeWorld("world-2", "世界二")]));
      }
      if (url.endsWith("/api/runtime/session/world-1") && init?.method !== "POST") {
        return Promise.resolve(jsonResponse(makeSnapshot("world-1", "pending")));
      }
      if (url.endsWith("/api/runtime/session/world-1/bootstrap")) {
        return bootDeferred.promise;
      }
      if (url.endsWith("/api/runtime/session/world-2")) {
        return Promise.resolve(jsonResponse(makeSnapshot("world-2", "ready")));
      }
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);
    await waitFor(() =>
      expect(
        fetchMock.mock.calls.filter(([url]) => String(url).endsWith("/api/runtime/session/world-1/bootstrap")),
      ).toHaveLength(1),
    );

    await user.click(screen.getByRole("button", { name: "世界列表" }));
    await user.click(screen.getByRole("button", { name: /世界二/ }));
    await waitFor(() => expect(screen.getByText("世界二开场。")).toBeInTheDocument());

    bootDeferred.resolve(jsonResponse(makeSnapshot("world-1", "ready")));
    await act(async () => {
      await Promise.resolve();
    });

    expect(screen.getByText("世界二开场。")).toBeInTheDocument();
    expect(screen.queryByText("世界一开场。")).not.toBeInTheDocument();
  });

  it("does not auto retry a failed world", async () => {
    window.history.replaceState({}, "", "/?session=world-1");
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/api/runtime/worlds")) {
        return jsonResponse([makeWorld("world-1", "世界一")]);
      }
      if (url.endsWith("/api/runtime/session/world-1") && init?.method !== "POST") {
        return jsonResponse(makeSnapshot("world-1", "failed"));
      }
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);
    expect(await screen.findByText("开场没有成功展开。")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "重试开场" })).toBeInTheDocument();
    expect(
      fetchMock.mock.calls.filter(([url]) => String(url).endsWith("/api/runtime/session/world-1/bootstrap")),
    ).toHaveLength(0);
  });
});
