import { startTransition, useEffect, useState } from "react";
import { ApiError, generateWorld, sendInterviewMessage, startInterview } from "./api/client";
import { BubbleField } from "./components/BubbleField";
import { CompleteView } from "./components/CompleteView";
import { CurrentScene } from "./components/CurrentScene";
import { GenerationView } from "./components/GenerationView";
import { InputArea } from "./components/InputArea";
import { LandingView } from "./components/LandingView";
import { MirrorView } from "./components/MirrorView";
import { TutorialHint } from "./components/TutorialHint";
import type {
  ApiErrorPayload,
  BlueprintSummary,
  InterviewArtifacts,
  InterviewStepResponse,
  StartInterviewResponse,
  UiPhase,
} from "./types";

const TUTORIAL_BUBBLES = ["这是什么？", "你是谁？", "我该说什么？"] as const;

const TUTORIAL_HINTS: Record<(typeof TUTORIAL_BUBBLES)[number], string> = {
  "这是什么？": "这是一次世界构建访谈。你随便描述脑海里的第一幕就行。",
  "你是谁？": "我是造梦者。负责把你的描述编织成一个可运行的世界蓝图。",
  "我该说什么？": "不用完整设定，只说一个画面、一种气味、一个想扮演的人都可以。",
};

function mapToUiPhase(response: InterviewStepResponse | StartInterviewResponse): UiPhase {
  if (response.phase === "interviewing" && response.raw_payload == null) {
    return "q1";
  }
  return response.phase;
}

function toGeneratePayload(artifacts: InterviewArtifacts): InterviewArtifacts {
  return artifacts;
}

function blueprintToClipboard(blueprint: BlueprintSummary): string {
  return [
    `# ${blueprint.title}`,
    "",
    "世界摘要：",
    blueprint.world_summary,
    "",
    "主角起点：",
    blueprint.protagonist_hook,
    "",
    "核心张力：",
    blueprint.core_tension,
    "",
    "核心维度：",
    ...blueprint.confirmed_dimensions.map((item) => `- ${item}`),
    "",
    "留白维度：",
    ...blueprint.emergent_dimensions.map((item) => `- ${item}`),
    "",
    "玩家侧写：",
    blueprint.player_profile,
  ].join("\n");
}

export default function App() {
  const [uiPhase, setUiPhase] = useState<UiPhase>("idle");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [currentMessage, setCurrentMessage] = useState<string>("");
  const [currentBubbles, setCurrentBubbles] = useState<string[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [activeTutorialHint, setActiveTutorialHint] = useState<string | null>(null);
  const [isWaiting, setIsWaiting] = useState(false);
  const [artifacts, setArtifacts] = useState<InterviewArtifacts | null>(null);
  const [blueprint, setBlueprint] = useState<BlueprintSummary | null>(null);
  const [systemPrompt, setSystemPrompt] = useState<string | null>(null);
  const [isPromptInspectorOpen, setIsPromptInspectorOpen] = useState(false);
  const [generateError, setGenerateError] = useState<ApiErrorPayload | null>(null);
  const [copyFeedback, setCopyFeedback] = useState<string | null>(null);

  const placeholder = inputValue.length > 500 ? "够了够了，说重点。" : "或者你有不同的想法？";

  useEffect(() => {
    void boot();
  }, []);

  useEffect(() => {
    if (!copyFeedback) {
      return;
    }
    const timer = window.setTimeout(() => setCopyFeedback(null), 1500);
    return () => window.clearTimeout(timer);
  }, [copyFeedback]);

  useEffect(() => {
    if (!isPromptInspectorOpen) {
      return;
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsPromptInspectorOpen(false);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [isPromptInspectorOpen]);

  async function boot() {
    setIsWaiting(true);
    setGenerateError(null);
    try {
      const response = await startInterview();
      startTransition(() => {
        setSessionId(response.session_id);
        setCurrentMessage(response.message);
        setCurrentBubbles([...TUTORIAL_BUBBLES]);
        setUiPhase(mapToUiPhase(response));
        setArtifacts(null);
        setBlueprint(null);
        setSystemPrompt(null);
        setInputValue("");
        setActiveTutorialHint(null);
        setIsPromptInspectorOpen(false);
      });
    } catch (error) {
      setGenerateError(normalizeError(error));
      setUiPhase("complete");
    } finally {
      setIsWaiting(false);
    }
  }

  async function handleConversationSubmit() {
    if (!sessionId || !inputValue.trim()) {
      return;
    }
    setIsWaiting(true);
    setActiveTutorialHint(null);
    try {
      const response = await sendInterviewMessage({
        session_id: sessionId,
        message: inputValue.trim(),
      });
      setInputValue("");
      applyInterviewResponse(response);
    } catch (error) {
      setGenerateError(normalizeError(error));
      setUiPhase("complete");
    } finally {
      setIsWaiting(false);
    }
  }

  async function handleMirrorAction(action: "confirm" | "reconsider") {
    if (!sessionId) {
      return;
    }
    setIsWaiting(true);
    try {
      const response = await sendInterviewMessage({
        session_id: sessionId,
        mirror_action: action,
      });
      applyInterviewResponse(response);
    } catch (error) {
      setGenerateError(normalizeError(error));
      setUiPhase("complete");
    } finally {
      setIsWaiting(false);
    }
  }

  async function handleLandingSubmit(payload: string) {
    if (!sessionId) {
      return;
    }
    setIsWaiting(true);
    try {
      const response = await sendInterviewMessage({
        session_id: sessionId,
        message: payload,
      });
      applyInterviewResponse(response);
      if (response.artifacts) {
        await runGenerate(response.artifacts);
      }
    } catch (error) {
      setGenerateError(normalizeError(error));
      setUiPhase("complete");
    } finally {
      setIsWaiting(false);
    }
  }

  async function runGenerate(nextArtifacts?: InterviewArtifacts) {
    const targetArtifacts = nextArtifacts ?? artifacts;
    if (!sessionId || !targetArtifacts) {
      return;
    }
    setUiPhase("generating");
    setGenerateError(null);
    try {
      const response = await generateWorld({
        session_id: sessionId,
        artifacts: toGeneratePayload(targetArtifacts),
      });
      startTransition(() => {
        setBlueprint(response.blueprint);
        setSystemPrompt(response.system_prompt);
        setUiPhase("complete");
      });
    } catch (error) {
      setBlueprint(null);
      setSystemPrompt(null);
      setGenerateError(normalizeError(error));
      setUiPhase("complete");
    }
  }

  function applyInterviewResponse(response: InterviewStepResponse) {
    const nextPhase = mapToUiPhase(response);
    if (response.message) {
      setCurrentMessage(response.message);
    }
    if (response.raw_payload?.suggested_tags) {
      setCurrentBubbles(response.raw_payload.suggested_tags);
    } else if (nextPhase !== "q1") {
      setCurrentBubbles([]);
    }
    if (response.artifacts) {
      const normalizedArtifacts: InterviewArtifacts = {
        ...response.artifacts,
      };
      setArtifacts(normalizedArtifacts);
    }
    setUiPhase(nextPhase);
  }

  async function copyText(text: string, label: string) {
    await navigator.clipboard.writeText(text);
    setCopyFeedback(label);
  }

  function handleBubbleClick(text: string) {
    if (uiPhase === "q1") {
      setActiveTutorialHint(TUTORIAL_HINTS[text as keyof typeof TUTORIAL_HINTS] ?? null);
      return;
    }
    setInputValue((current) => (current ? `${current} ${text}` : text));
  }

  const lowerZone =
    uiPhase === "q1" || uiPhase === "interviewing" ? (
      <div className="lower-zone">
        <BubbleField bubbles={currentBubbles} mode={uiPhase === "q1" ? "tutorial" : "tags"} onBubbleClick={handleBubbleClick} />
        <TutorialHint hint={uiPhase === "q1" ? activeTutorialHint : null} />
        <InputArea
          value={inputValue}
          placeholder={placeholder}
          disabled={isWaiting}
          onChange={(value) => {
            setInputValue(value);
            if (value) {
              setActiveTutorialHint(null);
            }
          }}
          onSubmit={handleConversationSubmit}
        />
      </div>
    ) : null;

  return (
    <main className="app-shell">
      <div className="layout">
        {uiPhase === "mirror" ? (
          <MirrorView
            mirrorText={currentMessage}
            disabled={isWaiting}
            onConfirm={() => void handleMirrorAction("confirm")}
            onReconsider={() => void handleMirrorAction("reconsider")}
          />
        ) : uiPhase === "landing" ? (
          <LandingView
            prompt={currentMessage}
            disabled={isWaiting}
            onSubmit={(payload) => void handleLandingSubmit(payload)}
          />
        ) : uiPhase === "generating" ? (
          <GenerationView />
        ) : uiPhase === "complete" ? (
          <CompleteView
            blueprint={blueprint}
            systemPrompt={systemPrompt}
            generateError={generateError}
            isPromptInspectorOpen={isPromptInspectorOpen}
            copyFeedback={copyFeedback}
            onOpenPromptInspector={() => setIsPromptInspectorOpen(true)}
            onClosePromptInspector={() => setIsPromptInspectorOpen(false)}
            onCopyBlueprint={() => blueprint && void copyText(blueprintToClipboard(blueprint), "已复制蓝图摘要")}
            onCopyPrompt={() => systemPrompt && void copyText(systemPrompt, "已复制 Prompt")}
            onRetryGenerate={() => void runGenerate()}
            onRestart={() => void boot()}
          />
        ) : (
          <>
            <section className="upper-zone">
              <CurrentScene message={currentMessage} isWaiting={isWaiting} />
            </section>
            {lowerZone}
          </>
        )}
      </div>
    </main>
  );
}

function normalizeError(error: unknown): ApiErrorPayload {
  if (error instanceof ApiError) {
    return error.payload;
  }
  if (error instanceof Error) {
    return { code: "internal", message: error.message, retryable: false };
  }
  return { code: "internal", message: "Unknown error", retryable: false };
}
