import { startTransition, useEffect, useRef, useState } from "react";
import {
  ApiError,
  createRuntimeSession,
  generateWorld,
  getReplayBundle,
  sendInterviewMessage,
  startInterview,
} from "./api/client";
import { BubbleField } from "./components/BubbleField";
import { CompleteView } from "./components/CompleteView";
import { CurrentScene } from "./components/CurrentScene";
import { GenerationView } from "./components/GenerationView";
import { InputArea } from "./components/InputArea";
import { LandingView } from "./components/LandingView";
import { MirrorView } from "./components/MirrorView";
import { ReplayLab, type ReplayInspectorTab } from "./components/ReplayLab";
import { DEV_REPLAY_SEED_BUNDLES } from "./dev/replaySeedBundles";
import type {
  ApiErrorPayload,
  Blueprint,
  BubbleCandidate,
  CompleteViewMode,
  InterviewStepResponse,
  ReplayBundle,
  ReplaySnapshot,
  StartInterviewResponse,
  UiPhase,
} from "./types";

const TUTORIAL_BUBBLES = ["这是什么？", "你是谁？", "我该说什么？"] as const;
const REPLAY_STORAGE_KEY = "architect.replay.lab.bundles";
const REPLAY_SEED_VERSION_KEY = "architect.replay.lab.seed.version";
const REPLAY_SEED_VERSION = "2026-03-13-highwall-harbor-v1";
const SHOULD_REGISTER_REPLAY_SEEDS = import.meta.env.DEV && import.meta.env.MODE !== "test";

const TUTORIAL_HINTS: Record<(typeof TUTORIAL_BUBBLES)[number], string> = {
  "这是什么？": "这是一次构建访谈。描述你脑海里的第一幕即可。",
  "你是谁？": "我是造梦者，将把你的描述编织成可运行的世界蓝图。",
  "我该说什么？": "不必写完整设定，哪怕只说一个画面或气味也可以。",
};

const WAITING_COPY = [
  "嗯...让我想想",
  "别催，想得越久效果越好",
  "你的世界....很有意思",
  "再等一下，线索正在自己对齐。",
  "轮廓已经出来了，我还在往深处看。",
] as const;

type WaitingAction = "conversation" | "mirror-confirm" | "mirror-reconsider" | "landing" | null;

interface LiveViewState {
  uiPhase: UiPhase;
  sessionId: string | null;
  currentMessage: string;
  currentQuestion: string;
  currentBubbles: BubbleCandidate[];
  inputValue: string;
  blueprint: Blueprint | null;
  systemPrompt: string | null;
  isPromptInspectorOpen: boolean;
  completeViewMode: CompleteViewMode;
  completeError: ApiErrorPayload | null;
  copyFeedback: string | null;
}

function mapToUiPhase(response: InterviewStepResponse | StartInterviewResponse): UiPhase {
  if (response.phase === "interviewing" && response.raw_payload == null) {
    return "q1";
  }
  return response.phase;
}

function blueprintToClipboard(blueprint: Blueprint): string {
  return [
    `# ${blueprint.title}`,
    "",
    "世界摘要：",
    blueprint.world_summary,
    "",
    "世界入口：",
    blueprint.protagonist_hook,
    "",
    "核心张力：",
    blueprint.core_tension,
    "",
    "基调关键词：",
    ...blueprint.tone_keywords.map((item) => `- ${item}`),
  ].join("\n");
}

function readReplayBundles(): ReplayBundle[] {
  if (!import.meta.env.DEV) {
    return [];
  }
  const canReadStorage = typeof window.localStorage?.getItem === "function";
  const canPersistSeeds = typeof window.localStorage?.setItem === "function";
  let bundles: ReplayBundle[] = [];

  try {
    if (canReadStorage) {
      const raw = window.localStorage.getItem(REPLAY_STORAGE_KEY);
      const parsed = raw ? JSON.parse(raw) : [];
      bundles = Array.isArray(parsed) ? (parsed as ReplayBundle[]) : [];
    }
  } catch {
    bundles = [];
  }

  if (SHOULD_REGISTER_REPLAY_SEEDS) {
    for (const seedBundle of DEV_REPLAY_SEED_BUNDLES) {
      bundles = replaceReplayBundle(bundles, seedBundle);
    }

    if (canReadStorage && canPersistSeeds) {
      try {
        const registeredVersion = window.localStorage.getItem(REPLAY_SEED_VERSION_KEY);
        if (registeredVersion !== REPLAY_SEED_VERSION) {
          window.localStorage.setItem(REPLAY_STORAGE_KEY, JSON.stringify(bundles));
          window.localStorage.setItem(REPLAY_SEED_VERSION_KEY, REPLAY_SEED_VERSION);
        }
      } catch {
        // Ignore storage failures and keep the in-memory seed bundle available.
      }
    }
  }

  return bundles;
}

function normalizeReplayImportError(error: unknown): string {
  const payload = normalizeError(error);
  const message = payload.message.trim();

  if (message === '{"detail":"Not Found"}' || message === "Not Found") {
    return "当前 127.0.0.1:8000 不是带 replay-bundle 端点的新后端实例。重启当前分支后端，或先使用 Lab 内置样本。";
  }

  if (payload.code === "debug_replay_not_ready") {
    return "这个 session 还没有完成到 /api/generate 成功，暂时不能导入 replay bundle。";
  }

  return message;
}

function writeReplayBundles(bundles: ReplayBundle[]) {
  if (!import.meta.env.DEV) {
    return;
  }
  if (typeof window.localStorage?.setItem !== "function") {
    return;
  }
  window.localStorage.setItem(REPLAY_STORAGE_KEY, JSON.stringify(bundles));
}

function replaceReplayBundle(existing: ReplayBundle[], incoming: ReplayBundle): ReplayBundle[] {
  const filtered = existing.filter((item) => item.id !== incoming.id);
  return [incoming, ...filtered];
}

function bundleFilename(bundle: ReplayBundle): string {
  const safe = bundle.name.replace(/[^\w\u4e00-\u9fff-]+/g, "-").replace(/-+/g, "-").replace(/^-|-$/g, "");
  return `${safe || "architect-replay"}-${bundle.source_session_id.slice(0, 8)}.json`;
}

function resolveReplayHydration(snapshot: ReplaySnapshot, bundle: ReplayBundle) {
  if (snapshot.frontstage.kind === "start") {
    return {
      sessionId: bundle.source_session_id,
      uiPhase: "q1" as UiPhase,
      currentMessage: snapshot.frontstage.response.message,
      currentQuestion: "",
      currentBubbles: TUTORIAL_BUBBLES.map((text) => ({ text, kind: "answer" as const })),
      blueprint: null,
      systemPrompt: null,
      completeViewMode: "success" as CompleteViewMode,
      completeError: null,
    };
  }

  if (snapshot.frontstage.kind === "step") {
    const response = snapshot.frontstage.response;
    if (snapshot.ui_phase === "interviewing") {
      return {
        sessionId: bundle.source_session_id,
        uiPhase: "interviewing" as UiPhase,
        currentMessage: response.message ?? "",
        currentQuestion: response.raw_payload?.question ?? "",
        currentBubbles: response.raw_payload?.bubble_candidates ?? [],
        blueprint: null,
        systemPrompt: null,
        completeViewMode: "success" as CompleteViewMode,
        completeError: null,
      };
    }

    return {
      sessionId: bundle.source_session_id,
      uiPhase: snapshot.ui_phase as UiPhase,
      currentMessage: response.message ?? "",
      currentQuestion: "",
      currentBubbles: [],
      blueprint: null,
      systemPrompt: null,
      completeViewMode: "success" as CompleteViewMode,
      completeError: null,
    };
  }

  return {
    sessionId: bundle.source_session_id,
    uiPhase: "complete" as UiPhase,
    currentMessage: "",
    currentQuestion: "",
    currentBubbles: [],
    blueprint: snapshot.frontstage.response.blueprint,
    systemPrompt: snapshot.frontstage.response.system_prompt,
    completeViewMode: "success" as CompleteViewMode,
    completeError: null,
  };
}

export default function App() {
  const [uiPhase, setUiPhase] = useState<UiPhase>("idle");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [currentMessage, setCurrentMessage] = useState<string>("");
  const [currentQuestion, setCurrentQuestion] = useState<string>("");
  const [currentBubbles, setCurrentBubbles] = useState<BubbleCandidate[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isWaiting, setIsWaiting] = useState(false);
  const [blueprint, setBlueprint] = useState<Blueprint | null>(null);
  const [systemPrompt, setSystemPrompt] = useState<string | null>(null);
  const [isPromptInspectorOpen, setIsPromptInspectorOpen] = useState(false);
  const [completeViewMode, setCompleteViewMode] = useState<CompleteViewMode>("success");
  const [completeError, setCompleteError] = useState<ApiErrorPayload | null>(null);
  const [copyFeedback, setCopyFeedback] = useState<string | null>(null);
  const [isLaunchingRuntime, setIsLaunchingRuntime] = useState(false);
  const [waitingCopyIndex, setWaitingCopyIndex] = useState(0);
  const [activeWaitingAction, setActiveWaitingAction] = useState<WaitingAction>(null);

  const [isReplayLabOpen, setIsReplayLabOpen] = useState(false);
  const [replayBundles, setReplayBundles] = useState<ReplayBundle[]>([]);
  const [selectedReplayBundleId, setSelectedReplayBundleId] = useState<string | null>(null);
  const [activeReplayBundleId, setActiveReplayBundleId] = useState<string | null>(null);
  const [activeReplaySnapshotKey, setActiveReplaySnapshotKey] = useState<string | null>(null);
  const [replayImportSessionId, setReplayImportSessionId] = useState("");
  const [replayImportError, setReplayImportError] = useState<string | null>(null);
  const [isReplayImporting, setIsReplayImporting] = useState(false);
  const [replayInspectorTab, setReplayInspectorTab] = useState<ReplayInspectorTab>("dossier");
  const liveStateRef = useRef<LiveViewState | null>(null);

  const placeholder = inputValue.length > 500 ? "够了够了，说重点。" : "或者你有不同的想法？";
  const showTransientWaiting =
    !activeReplaySnapshotKey &&
    isWaiting &&
    (uiPhase === "q1" || uiPhase === "interviewing" || uiPhase === "mirror" || uiPhase === "landing");
  const waitingPhrase = showTransientWaiting ? WAITING_COPY[waitingCopyIndex] : null;
  const isReplayActive = Boolean(activeReplayBundleId && activeReplaySnapshotKey);
  const selectedReplayBundle =
    replayBundles.find((bundle) => bundle.id === selectedReplayBundleId) ?? null;
  const activeReplaySnapshot =
    replayBundles
      .find((bundle) => bundle.id === activeReplayBundleId)
      ?.snapshots.find((snapshot) => snapshot.key === activeReplaySnapshotKey) ?? null;

  useEffect(() => {
    if (import.meta.env.DEV) {
      const stored = readReplayBundles();
      setReplayBundles(stored);
      if (stored[0]) {
        setSelectedReplayBundleId(stored[0].id);
      }
    }
    void boot();
  }, []);

  useEffect(() => {
    if (!import.meta.env.DEV) {
      return;
    }
    writeReplayBundles(replayBundles);
  }, [replayBundles]);

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

  useEffect(() => {
    if (!showTransientWaiting) {
      setWaitingCopyIndex(0);
      return;
    }

    setWaitingCopyIndex(0);
    const timer = window.setInterval(() => {
      setWaitingCopyIndex((current) => (current + 1) % WAITING_COPY.length);
    }, 6000);

    return () => window.clearInterval(timer);
  }, [showTransientWaiting]);

  async function boot() {
    setIsWaiting(true);
    setCompleteError(null);
    try {
      const response = await startInterview();
      startTransition(() => {
        setSessionId(response.session_id);
        setCurrentMessage(response.message);
        setCurrentQuestion("");
        setCurrentBubbles(TUTORIAL_BUBBLES.map((text) => ({ text, kind: "answer" as const })));
        setUiPhase(mapToUiPhase(response));
        setBlueprint(null);
        setSystemPrompt(null);
        setCompleteViewMode("success");
        setInputValue("");
        setIsPromptInspectorOpen(false);
        setActiveReplayBundleId(null);
        setActiveReplaySnapshotKey(null);
        liveStateRef.current = null;
      });
    } catch (error) {
      setCompleteError(normalizeError(error));
      setCompleteViewMode("fatal_error");
      setUiPhase("complete");
    } finally {
      setIsWaiting(false);
    }
  }

  async function handleConversationSubmit() {
    if (isReplayActive || !sessionId || !inputValue.trim()) {
      return;
    }
    setActiveWaitingAction("conversation");
    setIsWaiting(true);
    try {
      const response = await sendInterviewMessage({
        session_id: sessionId,
        message: inputValue.trim(),
      });
      applyInterviewResponse(response);
    } catch (error) {
      setCompleteError(normalizeError(error));
      setCompleteViewMode("fatal_error");
      setUiPhase("complete");
    } finally {
      setIsWaiting(false);
      setActiveWaitingAction(null);
    }
  }

  async function handleMirrorAction(action: "confirm" | "reconsider") {
    if (isReplayActive || !sessionId) {
      return;
    }
    setActiveWaitingAction(action === "confirm" ? "mirror-confirm" : "mirror-reconsider");
    setIsWaiting(true);
    try {
      const response = await sendInterviewMessage({
        session_id: sessionId,
        mirror_action: action,
      });
      applyInterviewResponse(response);
    } catch (error) {
      setCompleteError(normalizeError(error));
      setCompleteViewMode("fatal_error");
      setUiPhase("complete");
    } finally {
      setIsWaiting(false);
      setActiveWaitingAction(null);
    }
  }

  async function handleLandingSubmit(payload: string) {
    if (isReplayActive || !sessionId) {
      return;
    }
    setActiveWaitingAction("landing");
    setIsWaiting(true);
    try {
      const response = await sendInterviewMessage({
        session_id: sessionId,
        message: payload,
      });
      applyInterviewResponse(response);
      if (response.phase === "complete") {
        await runGenerate();
      }
    } catch (error) {
      setCompleteError(normalizeError(error));
      setCompleteViewMode("fatal_error");
      setUiPhase("complete");
    } finally {
      setIsWaiting(false);
      setActiveWaitingAction(null);
    }
  }

  async function runGenerate() {
    if (isReplayActive || !sessionId) {
      return;
    }
    setUiPhase("generating");
    setCompleteError(null);
    try {
      const response = await generateWorld({
        session_id: sessionId,
      });
      startTransition(() => {
        setBlueprint(response.blueprint);
        setSystemPrompt(response.system_prompt);
        setCompleteViewMode("success");
        setUiPhase("complete");
      });
    } catch (error) {
      setBlueprint(null);
      setSystemPrompt(null);
      setCompleteError(normalizeError(error));
      setCompleteViewMode("generate_failure");
      setUiPhase("complete");
    }
  }

  async function handleLaunchRuntime() {
    if (!blueprint || !systemPrompt || isLaunchingRuntime) {
      return;
    }
    setIsLaunchingRuntime(true);
    setCompleteError(null);
    try {
      const response = await createRuntimeSession({
        system_prompt: systemPrompt,
        title: blueprint.title,
        world_summary: blueprint.world_summary,
        tone_keywords: blueprint.tone_keywords,
        confirmed_dimensions: blueprint.confirmed_dimensions,
        emergent_dimensions: blueprint.emergent_dimensions,
        player_profile: blueprint.player_profile,
      });
      const runtimeAppUrl = import.meta.env.VITE_RUNTIME_APP_URL ?? "http://127.0.0.1:5174";
      const targetUrl = `${runtimeAppUrl}/?session=${encodeURIComponent(response.runtime_session_id)}`;
      const runtimeWindow = window.open(targetUrl, "_blank", "noopener");
      if (!runtimeWindow) {
        window.location.href = targetUrl;
        return;
      }
      setCopyFeedback("Runtime 已启动");
    } catch (error) {
      setCopyFeedback(`Runtime 启动失败：${normalizeError(error).message}`);
    } finally {
      setIsLaunchingRuntime(false);
    }
  }

  function applyInterviewResponse(response: InterviewStepResponse) {
    const nextPhase = mapToUiPhase(response);
    if (response.message) {
      setCurrentMessage(response.message);
    }
    if (nextPhase === "interviewing" && response.raw_payload?.question) {
      setCurrentQuestion(response.raw_payload.question);
    } else {
      setCurrentQuestion("");
    }
    if (response.raw_payload?.bubble_candidates) {
      setCurrentBubbles(response.raw_payload.bubble_candidates);
    } else if (nextPhase !== "q1") {
      setCurrentBubbles([]);
    }
    setInputValue("");
    setUiPhase(nextPhase);
  }

  function captureLiveState(): LiveViewState {
    return {
      uiPhase,
      sessionId,
      currentMessage,
      currentQuestion,
      currentBubbles,
      inputValue,
      blueprint,
      systemPrompt,
      isPromptInspectorOpen,
      completeViewMode,
      completeError,
      copyFeedback,
    };
  }

  function activateReplaySnapshot(bundle: ReplayBundle, snapshot: ReplaySnapshot) {
    if (!liveStateRef.current) {
      liveStateRef.current = captureLiveState();
    }

    const next = resolveReplayHydration(snapshot, bundle);
    startTransition(() => {
      setSessionId(next.sessionId);
      setUiPhase(next.uiPhase);
      setCurrentMessage(next.currentMessage);
      setCurrentQuestion(next.currentQuestion);
      setCurrentBubbles(next.currentBubbles);
      setBlueprint(next.blueprint);
      setSystemPrompt(next.systemPrompt);
      setCompleteViewMode(next.completeViewMode);
      setCompleteError(next.completeError);
      setInputValue("");
      setIsPromptInspectorOpen(false);
      setIsWaiting(false);
      setActiveWaitingAction(null);
      setActiveReplayBundleId(bundle.id);
      setActiveReplaySnapshotKey(snapshot.key);
      setSelectedReplayBundleId(bundle.id);
      setReplayInspectorTab("dossier");
    });
  }

  function handleExitReplay() {
    const liveState = liveStateRef.current;
    setActiveReplayBundleId(null);
    setActiveReplaySnapshotKey(null);
    setIsWaiting(false);
    setActiveWaitingAction(null);
    if (!liveState) {
      void boot();
      return;
    }
    liveStateRef.current = null;
    startTransition(() => {
      setUiPhase(liveState.uiPhase);
      setSessionId(liveState.sessionId);
      setCurrentMessage(liveState.currentMessage);
      setCurrentQuestion(liveState.currentQuestion);
      setCurrentBubbles(liveState.currentBubbles);
      setInputValue(liveState.inputValue);
      setBlueprint(liveState.blueprint);
      setSystemPrompt(liveState.systemPrompt);
      setIsPromptInspectorOpen(liveState.isPromptInspectorOpen);
      setCompleteViewMode(liveState.completeViewMode);
      setCompleteError(liveState.completeError);
      setCopyFeedback(liveState.copyFeedback);
    });
  }

  async function copyText(text: string, label: string) {
    try {
      await navigator.clipboard.writeText(text);
      setCopyFeedback(label);
    } catch {
      setCopyFeedback("当前环境不允许复制");
    }
  }

  function downloadText(text: string, filename: string) {
    const blob = new Blob([text], { type: "application/json;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  async function handleReplayImport() {
    if (!replayImportSessionId.trim()) {
      return;
    }
    setIsReplayImporting(true);
    setReplayImportError(null);
    try {
      const bundle = await getReplayBundle(replayImportSessionId.trim());
      const nextBundles = replaceReplayBundle(replayBundles, bundle);
      setReplayBundles(nextBundles);
      setSelectedReplayBundleId(bundle.id);
      setReplayImportSessionId("");
      if (bundle.snapshots[0]) {
        activateReplaySnapshot(bundle, bundle.snapshots[0]);
      }
      setIsReplayLabOpen(true);
    } catch (error) {
      setReplayImportError(normalizeReplayImportError(error));
    } finally {
      setIsReplayImporting(false);
    }
  }

  function handleSelectReplayBundle(bundleId: string) {
    setSelectedReplayBundleId(bundleId);
    const bundle = replayBundles.find((item) => item.id === bundleId);
    if (!bundle || !bundle.snapshots[0]) {
      return;
    }
    activateReplaySnapshot(bundle, bundle.snapshots[0]);
  }

  function handleSelectReplaySnapshot(snapshotKey: string) {
    const bundle = selectedReplayBundle;
    const snapshot = bundle?.snapshots.find((item) => item.key === snapshotKey);
    if (!bundle || !snapshot) {
      return;
    }
    activateReplaySnapshot(bundle, snapshot);
  }

  function handleDeleteReplayBundle(bundleId: string) {
    const removingActive = activeReplayBundleId === bundleId;
    const nextBundles = replayBundles.filter((bundle) => bundle.id !== bundleId);
    setReplayBundles(nextBundles);
    if (selectedReplayBundleId === bundleId) {
      setSelectedReplayBundleId(nextBundles[0]?.id ?? null);
    }
    if (removingActive) {
      handleExitReplay();
    }
  }

  function handleBubbleClick(text: string) {
    if (isReplayActive) {
      return;
    }
    if (uiPhase === "q1") {
      const hint = TUTORIAL_HINTS[text as keyof typeof TUTORIAL_HINTS];
      if (hint) {
        setCurrentBubbles([]);
        setCurrentMessage(hint);
        setCurrentQuestion("");
      }
      return;
    }
    setInputValue((current) => (current ? `${current} ${text}` : text));
  }

  const lowerZone =
    uiPhase === "q1" || uiPhase === "interviewing" ? (
      <div className="lower-zone">
        <div className="interactive-area">
          {currentBubbles.length > 0 ? (
            <BubbleField
              bubbles={currentBubbles.map((item) => item.text)}
              mode={uiPhase === "q1" ? "tutorial" : "tags"}
              isHidden={showTransientWaiting}
              onBubbleClick={handleBubbleClick}
            />
          ) : null}
        </div>
        <InputArea
          value={inputValue}
          placeholder={isReplayActive ? "Replay 只读模式" : placeholder}
          disabled={isWaiting || isReplayActive}
          isWaiting={activeWaitingAction === "conversation"}
          onChange={(value) => {
            setInputValue(value);
          }}
          onSubmit={handleConversationSubmit}
        />
      </div>
    ) : null;

  return (
    <main className="app-shell">
      {isReplayActive && selectedReplayBundle && activeReplaySnapshot ? (
        <div className="replay-live-badge">
          <span>Replay</span>
          <strong>{selectedReplayBundle.name}</strong>
          <em>{activeReplaySnapshot.label}</em>
        </div>
      ) : null}

      <div className="layout">
        {uiPhase === "mirror" ? (
          <MirrorView
            mirrorText={currentMessage}
            disabled={isWaiting || isReplayActive}
            isWaiting={showTransientWaiting}
            waitingPhrase={waitingPhrase}
            activeAction={
              activeWaitingAction === "mirror-confirm"
                ? "confirm"
                : activeWaitingAction === "mirror-reconsider"
                  ? "reconsider"
                  : null
            }
            onConfirm={() => void handleMirrorAction("confirm")}
            onReconsider={() => void handleMirrorAction("reconsider")}
          />
        ) : uiPhase === "landing" ? (
          <LandingView
            prompt={currentMessage}
            disabled={isWaiting || isReplayActive}
            isWaiting={showTransientWaiting}
            waitingPhrase={waitingPhrase}
            onSubmit={(payload) => void handleLandingSubmit(payload)}
          />
        ) : uiPhase === "generating" ? (
          <GenerationView />
        ) : uiPhase === "complete" ? (
          <CompleteView
            mode={resolveCompleteViewMode(completeViewMode, blueprint, completeError)}
            blueprint={blueprint}
            systemPrompt={systemPrompt}
            error={completeError}
            isPromptInspectorOpen={isPromptInspectorOpen}
            copyFeedback={copyFeedback}
            onOpenPromptInspector={() => setIsPromptInspectorOpen(true)}
            onClosePromptInspector={() => setIsPromptInspectorOpen(false)}
            onCopyBlueprint={() => blueprint && void copyText(blueprintToClipboard(blueprint), "已复制蓝图摘要")}
            onCopyPrompt={() => systemPrompt && void copyText(systemPrompt, "已复制 Prompt")}
            onLaunchRuntime={() => void handleLaunchRuntime()}
            onRetryGenerate={() => void runGenerate()}
            onRestart={() => (isReplayActive ? handleExitReplay() : void boot())}
            isLaunchingRuntime={isLaunchingRuntime}
            isReplay={isReplayActive}
            restartLabel={isReplayActive ? "退出回放" : "再造一个世界"}
          />
        ) : (
          <>
            <section className="upper-zone">
              <CurrentScene
                message={currentMessage}
                question={currentQuestion}
                isWaiting={showTransientWaiting}
                waitingPhrase={waitingPhrase}
              />
            </section>
            {lowerZone}
          </>
        )}
      </div>

      {import.meta.env.DEV ? (
        <ReplayLab
          isOpen={isReplayLabOpen}
          bundles={replayBundles}
          selectedBundle={selectedReplayBundle}
          activeSnapshot={activeReplaySnapshot}
          importSessionId={replayImportSessionId}
          importError={replayImportError}
          isImporting={isReplayImporting}
          inspectorTab={replayInspectorTab}
          isReplayActive={isReplayActive}
          onToggle={() => setIsReplayLabOpen((current) => !current)}
          onImportSessionIdChange={setReplayImportSessionId}
          onImport={() => void handleReplayImport()}
          onSelectBundle={handleSelectReplayBundle}
          onSelectSnapshot={handleSelectReplaySnapshot}
          onDeleteBundle={handleDeleteReplayBundle}
          onCopyBundle={() =>
            selectedReplayBundle &&
            void copyText(JSON.stringify(selectedReplayBundle, null, 2), "已复制 Replay JSON")
          }
          onDownloadBundle={() =>
            selectedReplayBundle &&
            downloadText(JSON.stringify(selectedReplayBundle, null, 2), bundleFilename(selectedReplayBundle))
          }
          onTabChange={setReplayInspectorTab}
          onExitReplay={handleExitReplay}
        />
      ) : null}
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

function resolveCompleteViewMode(
  mode: CompleteViewMode,
  blueprint: Blueprint | null,
  error: ApiErrorPayload | null,
): CompleteViewMode {
  if (error) {
    return mode;
  }
  return blueprint ? "success" : mode;
}
