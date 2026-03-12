import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
const apiMocks = vi.hoisted(() => ({
  startInterview: vi.fn(),
  sendInterviewMessage: vi.fn(),
  generateWorld: vi.fn(),
}));

vi.mock("./api/client", () => ({
  ApiError: class MockApiError extends Error {
    payload: { code: string; message: string; retryable: boolean };

    constructor(payload: { code: string; message: string; retryable: boolean }) {
      super(payload.message);
      this.payload = payload;
    }
  },
  startInterview: (...args: unknown[]) => apiMocks.startInterview(...args),
  sendInterviewMessage: (...args: unknown[]) => apiMocks.sendInterviewMessage(...args),
  generateWorld: (...args: unknown[]) => apiMocks.generateWorld(...args),
}));

import App from "./App";
import { ApiError } from "./api/client";

describe("App", () => {
  beforeEach(() => {
    apiMocks.startInterview.mockReset();
    apiMocks.sendInterviewMessage.mockReset();
    apiMocks.generateWorld.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it("boots into q1 and renders the opening scene", async () => {
    apiMocks.startInterview.mockResolvedValue({
      session_id: "session-1",
      phase: "interviewing",
      message: "闭上眼。在这个为你准备的世界里。",
      raw_payload: null,
    });

    render(<App />);

    expect(await screen.findByText("闭上眼。在这个为你准备的世界里。")).toBeInTheDocument();
    expect(screen.getByText("这是什么？")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "提交" })).toBeDisabled();
  });

  it("routes mirror confirm into landing", async () => {
    const user = userEvent.setup();
    apiMocks.startInterview.mockResolvedValue({
      session_id: "session-1",
      phase: "interviewing",
      message: "开场问题",
      raw_payload: null,
    });
    apiMocks.sendInterviewMessage
      .mockResolvedValueOnce({
        phase: "mirror",
        message: "我看到城墙与风。",
        raw_payload: {
          turn: 1,
          question: "继续",
          bubble_candidates: [{ text: "tag-a", kind: "answer" }],
          routing_snapshot: {
            confirmed: ["dim:social_friction"],
            exploring: [],
            excluded: [],
            untouched: ["dim:quest_system"],
          },
          dossier_update_status: "updated",
          follow_up_signal: "",
        },
      })
      .mockResolvedValueOnce({
        phase: "landing",
        message: "最后两个问题。",
        raw_payload: null,
      });

    render(<App />);

    await screen.findByText("开场问题");
    await user.type(screen.getByRole("textbox"), "给我一个门阀森严的世界");
    await user.click(screen.getByRole("button", { name: "提交" }));
    expect(await screen.findByText("我看到城墙与风。")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "推门" }));
    expect(await screen.findByText("最后两个问题。")).toBeInTheDocument();
  });

  it("shows generate failure view and allows retry without redoing the interview", async () => {
    const user = userEvent.setup();
    apiMocks.startInterview.mockResolvedValue({
      session_id: "session-1",
      phase: "interviewing",
      message: "开场问题",
      raw_payload: null,
    });
    apiMocks.sendInterviewMessage
      .mockResolvedValueOnce({
        phase: "mirror",
        message: "一扇门。",
        raw_payload: {
          turn: 1,
          question: "继续",
          bubble_candidates: [{ text: "tag-a", kind: "answer" }],
          routing_snapshot: {
            confirmed: ["dim:social_friction"],
            exploring: [],
            excluded: [],
            untouched: ["dim:quest_system"],
          },
          dossier_update_status: "updated",
          follow_up_signal: "",
        },
      })
      .mockResolvedValueOnce({
        phase: "landing",
        message: "最后两个问题。",
        raw_payload: null,
      })
      .mockResolvedValueOnce({
        phase: "complete",
        message: null,
        raw_payload: null,
      });
    apiMocks.generateWorld
      .mockRejectedValueOnce(
        new ApiError({
          code: "generate_failed",
          message: "upstream timeout",
          retryable: true,
        }),
      )
      .mockResolvedValueOnce({
        blueprint: {
          title: "城下之人",
          world_summary: "世界摘要",
          protagonist_hook: "主角起点",
          core_tension: "核心张力",
          tone_keywords: ["写实"],
          player_profile: "玩家侧写",
          confirmed_dimensions: ["dim:social_friction"],
          emergent_dimensions: ["dim:quest_system"],
          forged_modules: [{ dimension: "dim:social_friction", pack_id: "pack.urban.friction" }],
        },
        system_prompt: "FINAL PROMPT",
      });

    render(<App />);

    await screen.findByText("开场问题");
    await user.type(screen.getByRole("textbox"), "我要一个阶层压抑的世界");
    await user.click(screen.getByRole("button", { name: "提交" }));
    await screen.findByText("一扇门。");
    await user.click(screen.getByRole("button", { name: "推门" }));
    await screen.findByText("最后两个问题。");
    await user.click(screen.getByRole("button", { name: "开始" }));

    expect(await screen.findByText("法则还没有编织完成。")).toBeInTheDocument();
    expect(screen.getByText("访谈成果已经保留，不需要重走一遍。")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "重新生成" }));

    await waitFor(() => {
      expect(screen.getByText("城下之人")).toBeInTheDocument();
    });
    expect(screen.getByRole("heading", { name: "世界摘要" })).toBeInTheDocument();
  });
});
