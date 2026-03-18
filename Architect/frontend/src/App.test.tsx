import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const apiMocks = vi.hoisted(() => ({
  startInterview: vi.fn(),
  sendInterviewMessage: vi.fn(),
  generateWorld: vi.fn(),
  getReplayBundle: vi.fn(),
  createRuntimeSession: vi.fn(),
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
  getReplayBundle: (...args: unknown[]) => apiMocks.getReplayBundle(...args),
  createRuntimeSession: (...args: unknown[]) => apiMocks.createRuntimeSession(...args),
}));

import App from "./App";
import { ApiError } from "./api/client";

function createDeferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

describe("App", () => {
  beforeEach(() => {
    apiMocks.startInterview.mockReset();
    apiMocks.sendInterviewMessage.mockReset();
    apiMocks.generateWorld.mockReset();
    apiMocks.getReplayBundle.mockReset();
    apiMocks.createRuntimeSession.mockReset();
    if (typeof window.localStorage?.removeItem === "function") {
      window.localStorage.removeItem("architect.replay.lab.bundles");
    }
  });

  afterEach(() => {
    cleanup();
  });

  it("boots into q1 and renders the opening scene", async () => {
    apiMocks.startInterview.mockResolvedValue({
      session_id: "session-1",
      phase: "interviewing",
      message: "想象一下。在这个为你准备的世界里。",
      raw_payload: null,
    });

    render(<App />);

    expect(await screen.findByText("想象一下。在这个为你准备的世界里。")).toBeInTheDocument();
    expect(screen.getByText("这是什么？")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "提交" })).toBeDisabled();
  });

  it("renders the follow-up scene echo with refreshed bubble suggestions", async () => {
    const user = userEvent.setup();

    apiMocks.startInterview.mockResolvedValue({
      session_id: "session-1",
      phase: "interviewing",
      message: "想象一下。在这个为你准备的世界里。",
      raw_payload: null,
    });
    apiMocks.sendInterviewMessage.mockResolvedValue({
      phase: "interviewing",
      message: "刚下飞机，纽约，新生活这几个词一出来，空气里就先有了味道。",
      raw_payload: {
        turn: 1,
        question: "这座城市里，第一样真正让你心里一紧的东西是什么？",
        bubble_candidates: [
          { text: "第一次独自面对这座城市的茫然。", kind: "answer" },
          { text: "第一次意识到这里没人认识我的那种自由。", kind: "advance" },
        ],
        routing_snapshot: {
          confirmed: [],
          exploring: ["dim:quest_system"],
          excluded: [],
          untouched: ["dim:social_friction"],
        },
        dossier_update_status: "updated",
        follow_up_signal: "",
      },
    });

    render(<App />);

    await screen.findByText("想象一下。在这个为你准备的世界里。");
    await user.type(screen.getByRole("textbox"), "纽约，新的留学生活。");
    await user.click(screen.getByRole("button", { name: "提交" }));

    expect(await screen.findByText(/刚下飞机，纽约，新生活这几个词一出来/)).toBeInTheDocument();
    expect(await screen.findByText("这座城市里，第一样真正让你心里一紧的东西是什么？")).toBeInTheDocument();
    expect(screen.getByText("第一次独自面对这座城市的茫然。")).toBeInTheDocument();
    expect(screen.getByText("第一次意识到这里没人认识我的那种自由。")).toBeInTheDocument();
  });

  it("shows transient waiting UI during q1 submit and keeps the submitted text visible", async () => {
    const user = userEvent.setup();
    const deferred = createDeferred<{
      phase: "mirror";
      message: string;
      raw_payload: {
        turn: number;
        question: string;
        bubble_candidates: Array<{ text: string; kind: "answer" }>;
        routing_snapshot: {
          confirmed: string[];
          exploring: string[];
          excluded: string[];
          untouched: string[];
        };
        dossier_update_status: "updated";
        follow_up_signal: "";
      };
    }>();

    apiMocks.startInterview.mockResolvedValue({
      session_id: "session-1",
      phase: "interviewing",
      message: "开场问题",
      raw_payload: null,
    });
    apiMocks.sendInterviewMessage.mockReturnValue(deferred.promise);

    render(<App />);

    await screen.findByText("开场问题");
    const textbox = screen.getByRole("textbox");
    await user.type(textbox, "给我一个门阀森严的世界");
    await user.click(screen.getByRole("button", { name: "提交" }));

    expect(screen.getByText("开场问题").closest(".scene-card__content")).toHaveClass("scene-card__content--hidden");
    expect(screen.getByText("这是什么？").closest(".bubble-field")).toHaveClass("bubble-field--hidden");
    expect(screen.getByDisplayValue("给我一个门阀森严的世界")).toBeDisabled();
    expect(screen.getByText("嗯...让我想想")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "提交" })).toBeDisabled();
    expect(document.querySelector(".input-area__submit .loading-spinner")).not.toBeNull();

    deferred.resolve({
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
    });

    expect(await screen.findByText("我看到城墙与风。")).toBeInTheDocument();
  });

  it("imports a replay bundle and hydrates snapshots without live requests", async () => {
    const user = userEvent.setup();

    apiMocks.startInterview.mockResolvedValue({
      session_id: "live-session",
      phase: "interviewing",
      message: "开场问题",
      raw_payload: null,
    });
    apiMocks.getReplayBundle.mockResolvedValue({
      id: "replay:session-1",
      name: "城下之人",
      source_session_id: "session-1",
      captured_at: "2026-03-13T00:00:00+00:00",
      snapshots: [
        {
          key: "q1",
          label: "Q1",
          ui_phase: "q1",
          frontstage: {
            kind: "start",
            response: {
              session_id: "session-1",
              phase: "interviewing",
              message: "想象一下。在这个为你准备的世界里。",
              raw_payload: null,
            },
          },
          backstage: {
            phase: "interviewing",
            turn: 0,
            twin_dossier: {
              routing_snapshot: { confirmed: [], exploring: [], excluded: [], untouched: [] },
              world_dossier: {
                world_premise: "",
                tension_guess: "",
                scene_anchor: "",
                open_threads: [],
                soft_signals: { notable_imagery: [], unstable_hypotheses: [] },
              },
              player_dossier: {
                fantasy_vector: "",
                emotional_seed: "",
                taste_bias: "",
                language_register: "",
                user_no_go_zones: [],
                soft_signals: { notable_phrasing: [], subtext_hypotheses: [], style_notes: "" },
              },
              change_log: { newly_confirmed: [], newly_rejected: [], needs_follow_up: [] },
            },
            compile_output: null,
            frozen_compile_package: null,
            messages: [{ role: "assistant", content: "想象一下。在这个为你准备的世界里。" }],
            debug_event: { event: "start" },
          },
        },
        {
          key: "interview:1",
          label: "访谈 1",
          ui_phase: "interviewing",
          frontstage: {
            kind: "step",
            response: {
              phase: "interviewing",
              message: "飞剑划破云霄，剑光很冷。",
              raw_payload: {
                turn: 1,
                question: "这道规矩最先从哪里压下来？",
                bubble_candidates: [
                  { text: "像空气一样，没人需要解释。", kind: "answer" },
                  { text: "更像所有人都默认该低头。", kind: "advance" },
                ],
                routing_snapshot: {
                  confirmed: [],
                  exploring: ["dim:command_friction"],
                  excluded: [],
                  untouched: ["dim:social_friction"],
                },
                dossier_update_status: "updated",
                follow_up_signal: "",
              },
            },
          },
          backstage: {
            phase: "interviewing",
            turn: 1,
            twin_dossier: {
              routing_snapshot: {
                confirmed: [],
                exploring: ["dim:command_friction"],
                excluded: [],
                untouched: ["dim:social_friction"],
              },
              world_dossier: {
                world_premise: "一个有冷剑光和森严规矩的修仙世界。",
                tension_guess: "规矩压过飞行自由。",
                scene_anchor: "夜里飞剑停在禁区边缘。",
                open_threads: ["谁在执行规矩"],
                soft_signals: {
                  notable_imagery: ["冷剑光"],
                  unstable_hypotheses: ["规矩已经渗进动作"],
                },
              },
              player_dossier: {
                fantasy_vector: "靠近剑修的位置感。",
                emotional_seed: "",
                taste_bias: "冷硬、克制。",
                language_register: "简洁直接。",
                user_no_go_zones: ["纯爽文"],
                soft_signals: {
                  notable_phrasing: ["剑光很冷"],
                  subtext_hypotheses: [],
                  style_notes: "偏克制。",
                },
              },
              change_log: {
                newly_confirmed: [],
                newly_rejected: ["纯爽文"],
                needs_follow_up: ["规矩从哪来"],
              },
            },
            compile_output: null,
            frozen_compile_package: null,
            messages: [
              { role: "assistant", content: "想象一下。在这个为你准备的世界里。" },
              { role: "user", content: "我想要一个有冷剑光的修仙世界。" },
              { role: "assistant", content: "飞剑划破云霄，剑光很冷。\n这道规矩最先从哪里压下来？" },
            ],
            debug_event: { event: "interview_turn" },
          },
        },
        {
          key: "mirror",
          label: "Mirror",
          ui_phase: "mirror",
          frontstage: {
            kind: "step",
            response: {
              phase: "mirror",
              message: "你站在规矩压下来的风里，看见剑光也要低头。",
              raw_payload: null,
            },
          },
          backstage: {
            phase: "mirror",
            turn: 1,
            twin_dossier: {
              routing_snapshot: { confirmed: ["dim:command_friction"], exploring: [], excluded: [], untouched: [] },
              world_dossier: {
                world_premise: "一个有冷剑光和森严规矩的修仙世界。",
                tension_guess: "规矩压过飞行自由。",
                scene_anchor: "夜里飞剑停在禁区边缘。",
                open_threads: [],
                soft_signals: { notable_imagery: ["冷剑光"], unstable_hypotheses: [] },
              },
              player_dossier: {
                fantasy_vector: "靠近剑修的位置感。",
                emotional_seed: "",
                taste_bias: "冷硬、克制。",
                language_register: "简洁直接。",
                user_no_go_zones: ["纯爽文"],
                soft_signals: { notable_phrasing: ["剑光很冷"], subtext_hypotheses: [], style_notes: "偏克制。" },
              },
              change_log: { newly_confirmed: [], newly_rejected: [], needs_follow_up: [] },
            },
            compile_output: null,
            frozen_compile_package: null,
            messages: [],
            debug_event: { event: "interview_to_mirror" },
          },
        },
        {
          key: "landing",
          label: "Landing",
          ui_phase: "landing",
          frontstage: {
            kind: "step",
            response: {
              phase: "landing",
              message: "最后两个问题。你的性别？化身的性别？",
              raw_payload: null,
            },
          },
          backstage: {
            phase: "landing",
            turn: 1,
            twin_dossier: {
              routing_snapshot: { confirmed: ["dim:command_friction"], exploring: [], excluded: [], untouched: [] },
              world_dossier: {
                world_premise: "一个有冷剑光和森严规矩的修仙世界。",
                tension_guess: "规矩压过飞行自由。",
                scene_anchor: "夜里飞剑停在禁区边缘。",
                open_threads: [],
                soft_signals: { notable_imagery: ["冷剑光"], unstable_hypotheses: [] },
              },
              player_dossier: {
                fantasy_vector: "靠近剑修的位置感。",
                emotional_seed: "",
                taste_bias: "冷硬、克制。",
                language_register: "简洁直接。",
                user_no_go_zones: ["纯爽文"],
                soft_signals: { notable_phrasing: ["剑光很冷"], subtext_hypotheses: [], style_notes: "偏克制。" },
              },
              change_log: { newly_confirmed: [], newly_rejected: [], needs_follow_up: [] },
            },
            compile_output: null,
            frozen_compile_package: null,
            messages: [],
            debug_event: { event: "mirror_confirm" },
          },
        },
        {
          key: "complete",
          label: "完成态",
          ui_phase: "complete",
          frontstage: {
            kind: "generate",
            response: {
              blueprint: {
                title: "城下之人",
                world_summary: "世界摘要",
                protagonist_hook: "主角起点",
                core_tension: "核心张力",
                tone_keywords: ["写实"],
                player_profile: "玩家侧写",
                confirmed_dimensions: ["dim:command_friction"],
                emergent_dimensions: ["dim:social_friction"],
                forged_modules: [{ dimension: "dim:command_friction", pack_id: "pack.rules" }],
              },
              system_prompt: "FULL PROMPT",
            },
          },
          backstage: {
            phase: "complete",
            turn: 1,
            twin_dossier: {
              routing_snapshot: { confirmed: ["dim:command_friction"], exploring: [], excluded: [], untouched: [] },
              world_dossier: {
                world_premise: "一个有冷剑光和森严规矩的修仙世界。",
                tension_guess: "规矩压过飞行自由。",
                scene_anchor: "夜里飞剑停在禁区边缘。",
                open_threads: [],
                soft_signals: { notable_imagery: ["冷剑光"], unstable_hypotheses: [] },
              },
              player_dossier: {
                fantasy_vector: "靠近剑修的位置感。",
                emotional_seed: "",
                taste_bias: "冷硬、克制。",
                language_register: "简洁直接。",
                user_no_go_zones: ["纯爽文"],
                soft_signals: { notable_phrasing: ["剑光很冷"], subtext_hypotheses: [], style_notes: "偏克制。" },
              },
              change_log: { newly_confirmed: [], newly_rejected: [], needs_follow_up: [] },
            },
            compile_output: {
              confirmed_dimensions: ["dim:command_friction"],
              emergent_dimensions: ["dim:social_friction"],
              excluded_dimensions: [],
              narrative_briefing: "brief",
              player_profile: "profile",
            },
            frozen_compile_package: {
              compile_output: {
                confirmed_dimensions: ["dim:command_friction"],
                emergent_dimensions: ["dim:social_friction"],
                excluded_dimensions: [],
                narrative_briefing: "brief",
                player_profile: "profile",
              },
              forge_context: { world_premise: "一个有冷剑光和森严规矩的修仙世界。" },
              assembler_context: { player_profile: "profile" },
            },
            messages: [],
            debug_event: { event: "generate_world" },
          },
        },
      ],
    });

    render(<App />);

    expect(await screen.findByText("开场问题")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Replay Lab/i }));
    await user.type(screen.getByPlaceholderText("session_id"), "session-1");
    await user.click(screen.getByRole("button", { name: "导入" }));

    expect((await screen.findAllByText("城下之人")).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "Q1 q1" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "访谈 1 interviewing" })).toBeInTheDocument();
    expect(apiMocks.sendInterviewMessage).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "访谈 1 interviewing" }));
    expect(await screen.findByText("这道规矩最先从哪里压下来？")).toBeInTheDocument();
    expect(screen.getByText("像空气一样，没人需要解释。")).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "Messages" }));
    expect(await screen.findByText("我想要一个有冷剑光的修仙世界。")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Mirror mirror" }));
    expect(await screen.findByText("你站在规矩压下来的风里，看见剑光也要低头。")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Landing landing" }));
    expect(await screen.findByText("最后两个问题。你的性别？化身的性别？")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "完成态 complete" }));
    expect(await screen.findByRole("heading", { name: "城下之人" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "进入 Runtime" })).toBeEnabled();
  });

  it("launches Runtime from a replay complete snapshot using the recorded prompt", async () => {
    const user = userEvent.setup();
    const openSpy = vi.spyOn(window, "open").mockImplementation(() => ({}) as Window);
    apiMocks.startInterview.mockResolvedValue({
      session_id: "live-session",
      phase: "interviewing",
      message: "开场问题",
      raw_payload: null,
    });
    apiMocks.getReplayBundle.mockResolvedValue({
      id: "replay:session-runtime",
      name: "城下之人",
      source_session_id: "session-runtime",
      captured_at: "2026-03-13T00:00:00+00:00",
      snapshots: [
        {
          key: "complete",
          label: "完成态",
          ui_phase: "complete",
          frontstage: {
            kind: "generate",
            response: {
              blueprint: {
                title: "城下之人",
                world_summary: "世界摘要",
                protagonist_hook: "主角起点",
                core_tension: "核心张力",
                tone_keywords: ["冷硬"],
                player_profile: "玩家侧写",
                confirmed_dimensions: ["dim:social_friction"],
                emergent_dimensions: ["dim:power_progression"],
                forged_modules: [{ dimension: "dim:social_friction", pack_id: "pack.urban.friction" }],
              },
              system_prompt: "RECORDED PROMPT",
            },
          },
          backstage: {
            phase: "complete",
            turn: 4,
            twin_dossier: {
              routing_snapshot: { confirmed: [], exploring: [], excluded: [], untouched: [] },
              world_dossier: {
                world_premise: "",
                tension_guess: "",
                scene_anchor: "",
                open_threads: [],
                soft_signals: { notable_imagery: [], unstable_hypotheses: [] },
              },
              player_dossier: {
                fantasy_vector: "",
                emotional_seed: "",
                taste_bias: "",
                language_register: "",
                user_no_go_zones: [],
                soft_signals: { notable_phrasing: [], subtext_hypotheses: [], style_notes: "" },
              },
              change_log: { newly_confirmed: [], newly_rejected: [], needs_follow_up: [] },
            },
            compile_output: {
              confirmed_dimensions: ["dim:social_friction"],
              emergent_dimensions: ["dim:power_progression"],
              excluded_dimensions: [],
              narrative_briefing: "brief",
              player_profile: "profile",
            },
            frozen_compile_package: {
              compile_output: {
                confirmed_dimensions: ["dim:social_friction"],
                emergent_dimensions: ["dim:power_progression"],
                excluded_dimensions: [],
                narrative_briefing: "brief",
                player_profile: "profile",
              },
              forge_context: {},
              assembler_context: {},
            },
            messages: [],
            debug_event: { event: "generate_world" },
          },
        },
      ],
    });
    apiMocks.createRuntimeSession.mockResolvedValue({
      runtime_session_id: "runtime-1",
      turn_count: 0,
      boot_status: "pending",
      intro_message: null,
    });

    render(<App />);

    await screen.findByText("开场问题");
    await user.click(screen.getByRole("button", { name: /Replay Lab/i }));
    await user.type(screen.getByPlaceholderText("session_id"), "session-runtime");
    await user.click(screen.getByRole("button", { name: "导入" }));
    await user.click(screen.getByRole("button", { name: "完成态 complete" }));
    await screen.findByRole("heading", { name: "城下之人" });

    await user.click(screen.getByRole("button", { name: "进入 Runtime" }));

    await waitFor(() => {
      expect(apiMocks.createRuntimeSession).toHaveBeenCalledWith({
        system_prompt: "RECORDED PROMPT",
        title: "城下之人",
        world_summary: "世界摘要",
        tone_keywords: ["冷硬"],
        confirmed_dimensions: ["dim:social_friction"],
        emergent_dimensions: ["dim:power_progression"],
        player_profile: "玩家侧写",
      });
    });
    expect(openSpy).toHaveBeenCalledWith("http://127.0.0.1:5174/?session=runtime-1", "_blank", "noopener");
    openSpy.mockRestore();
  });

  it("shows transient waiting UI for mirror actions", async () => {
    const user = userEvent.setup();
    const deferred = createDeferred<{
      phase: "landing";
      message: string;
      raw_payload: null;
    }>();

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
      .mockReturnValueOnce(deferred.promise);

    render(<App />);

    await screen.findByText("开场问题");
    await user.type(screen.getByRole("textbox"), "给我一个门阀森严的世界");
    await user.click(screen.getByRole("button", { name: "提交" }));
    await screen.findByText("我看到城墙与风。");
    expect(screen.getByText("所以我看到的世界是")).toBeInTheDocument();
    expect(screen.getByText("像就推门，不像就继续修。")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "推门" }));

    expect(screen.queryByText("我看到城墙与风。")).not.toBeInTheDocument();
    expect(screen.getByText("嗯...让我想想")).toBeInTheDocument();
    expect(document.querySelector(".bubble--loading .loading-spinner")).not.toBeNull();

    deferred.resolve({
      phase: "landing",
      message: "最后两个问题。",
      raw_payload: null,
    });

    expect(await screen.findByText("最后两个问题。")).toBeInTheDocument();
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

  it("shows transient waiting UI for landing submit before generation starts", async () => {
    const user = userEvent.setup();
    const deferred = createDeferred<{
      phase: "complete";
      message: null;
      raw_payload: null;
    }>();

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
      .mockReturnValueOnce(deferred.promise);
    apiMocks.generateWorld.mockResolvedValue({
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

    expect(screen.queryByText("最后两个问题。")).not.toBeInTheDocument();
    expect(screen.getByText("嗯...让我想想")).toBeInTheDocument();
    expect(document.querySelector(".action-button--loading .loading-spinner")).not.toBeNull();

    deferred.resolve({
      phase: "complete",
      message: null,
      raw_payload: null,
    });

    await waitFor(() => {
      expect(screen.getByText("城下之人")).toBeInTheDocument();
    });
  });
});
