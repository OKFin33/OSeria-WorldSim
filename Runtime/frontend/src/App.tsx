import { useEffect, useMemo, useRef, useState } from "react";
import {
  ApiError,
  bootstrapRuntimeSession,
  getRuntimeSessionDebug,
  getRuntimeSession,
  getRuntimeWorlds,
  runRuntimeTurnStream,
  updateRuntimeDisplayTitle,
} from "./api/client";
import type {
  ApiErrorPayload,
  LorebookEntry,
  RuntimeMessage,
  RuntimeSessionDebugSnapshot,
  RuntimeSessionSnapshot,
  RuntimeTurnResponse,
  RuntimeWorldListItem,
  TurnSummaryMemory,
} from "./types";

const ARCHITECT_APP_URL = import.meta.env.VITE_ARCHITECT_APP_URL ?? "http://localhost:5173";
const LOREBOOK_CONFIRM_KEY_PREFIX = "runtime:lorebook-confirmed:";
const THEME_STORAGE_KEY = "runtime:theme";
const BOOT_POLL_INTERVAL_MS = 2000;

type ActivePanel = "memory" | "lorebook" | null;
type ContextMenuState = { sessionId: string; x: number; y: number } | null;
type RenameState = { sessionId: string; value: string } | null;
type ThemeMode = "light" | "dark";

function currentSessionIdFromUrl(): string {
  return new URLSearchParams(window.location.search).get("session") ?? "";
}

function debugModeFromUrl(): boolean {
  return new URLSearchParams(window.location.search).get("debug") === "1";
}

function safeStorageGet(key: string): string | null {
  const storage = window.localStorage;
  return typeof storage?.getItem === "function" ? storage.getItem(key) : null;
}

function safeStorageSet(key: string, value: string): void {
  const storage = window.localStorage;
  if (typeof storage?.setItem === "function") {
    storage.setItem(key, value);
  }
}

function lorebookConfirmKey(sessionId: string): string {
  return `${LOREBOOK_CONFIRM_KEY_PREFIX}${sessionId}`;
}

function isDesktopPointer(): boolean {
  return window.matchMedia?.("(pointer: fine)").matches ?? true;
}

export default function App() {
  const [worlds, setWorlds] = useState<RuntimeWorldListItem[]>([]);
  const [session, setSession] = useState<RuntimeSessionSnapshot | null>(null);
  const [sessionId, setSessionId] = useState<string>(currentSessionIdFromUrl());
  const [isLoading, setIsLoading] = useState(false);
  const [isBootstrapping, setIsBootstrapping] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [input, setInput] = useState("");
  const [error, setError] = useState<ApiErrorPayload | null>(null);
  const [leftOpen, setLeftOpen] = useState(false);
  const [rightOpen, setRightOpen] = useState(false);
  const [activePanel, setActivePanel] = useState<ActivePanel>(null);
  const [contextMenu, setContextMenu] = useState<ContextMenuState>(null);
  const [renameState, setRenameState] = useState<RenameState>(null);
  const [lorebookUnlocked, setLorebookUnlocked] = useState(false);
  const [rememberLorebookChoice, setRememberLorebookChoice] = useState(false);
  const [debugSnapshot, setDebugSnapshot] = useState<RuntimeSessionDebugSnapshot | null>(null);
  const [theme, setTheme] = useState<ThemeMode>(() => {
    const stored = safeStorageGet(THEME_STORAGE_KEY);
    return stored === "dark" ? "dark" : "light";
  });
  const debugMode = useMemo(() => debugModeFromUrl(), []);
  const selectedSessionRef = useRef(sessionId);
  const selectionNonceRef = useRef(0);
  const bootstrapNonceRef = useRef(0);
  const pollTimerRef = useRef<number | null>(null);

  useEffect(() => {
    void refreshWorlds();
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    safeStorageSet(THEME_STORAGE_KEY, theme);
  }, [theme]);

  useEffect(() => {
    selectedSessionRef.current = sessionId;
    if (!sessionId) {
      stopPolling();
      setSession(null);
      setIsBootstrapping(false);
      setDebugSnapshot(null);
      return;
    }
    const selectionNonce = ++selectionNonceRef.current;
    void loadSession(sessionId, selectionNonce);
  }, [sessionId]);

  useEffect(() => () => stopPolling(), []);

  useEffect(() => {
    if (!sessionId) {
      setLorebookUnlocked(false);
      setRememberLorebookChoice(false);
      return;
    }
    const persisted = safeStorageGet(lorebookConfirmKey(sessionId)) === "1";
    setLorebookUnlocked(persisted);
    setRememberLorebookChoice(persisted);
  }, [sessionId]);

  useEffect(() => {
    if (!contextMenu) {
      return;
    }
    function handlePointerDown() {
      setContextMenu(null);
    }
    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setContextMenu(null);
      }
    }
    window.addEventListener("pointerdown", handlePointerDown);
    window.addEventListener("keydown", handleEscape);
    return () => {
      window.removeEventListener("pointerdown", handlePointerDown);
      window.removeEventListener("keydown", handleEscape);
    };
  }, [contextMenu]);

  async function refreshWorlds() {
    try {
      const response = await getRuntimeWorlds();
      setWorlds(response);
    } catch (err) {
      setError(toUserError(err, "世界列表暂时无法载入。"));
    }
  }

  async function refreshDebugSnapshot(runtimeSessionId: string) {
    if (!debugMode) {
      return;
    }
    try {
      const snapshot = await getRuntimeSessionDebug(runtimeSessionId);
      if (selectedSessionRef.current === runtimeSessionId) {
        setDebugSnapshot(snapshot);
      }
    } catch {
      // Dev diagnostics are best-effort only.
    }
  }

  function stopPolling() {
    if (pollTimerRef.current !== null) {
      window.clearTimeout(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }

  function isCurrentSelection(runtimeSessionId: string, selectionNonce: number): boolean {
    return selectedSessionRef.current === runtimeSessionId && selectionNonceRef.current === selectionNonce;
  }

  function isCurrentBootstrap(runtimeSessionId: string, selectionNonce: number, bootstrapNonce: number): boolean {
    return isCurrentSelection(runtimeSessionId, selectionNonce) && bootstrapNonceRef.current === bootstrapNonce;
  }

  function syncSessionSnapshot(snapshot: RuntimeSessionSnapshot) {
    setSession(snapshot);
    setIsBootstrapping(snapshot.boot_status === "booting");
    const url = new URL(window.location.href);
    url.searchParams.set("session", snapshot.runtime_session_id);
    window.history.replaceState({}, "", url.toString());
  }

  async function startBootPolling(runtimeSessionId: string, selectionNonce: number) {
    stopPolling();
    pollTimerRef.current = window.setTimeout(async () => {
      try {
        const snapshot = await getRuntimeSession(runtimeSessionId);
        if (!isCurrentSelection(runtimeSessionId, selectionNonce)) {
          return;
        }
        syncSessionSnapshot(snapshot);
        if (snapshot.boot_status === "booting") {
          await startBootPolling(runtimeSessionId, selectionNonce);
          return;
        }
        stopPolling();
        setIsBootstrapping(false);
        await refreshWorlds();
      } catch (err) {
        if (!isCurrentSelection(runtimeSessionId, selectionNonce)) {
          return;
        }
        stopPolling();
        setIsBootstrapping(false);
        setError(toUserError(err, "无法进入该世界，请重试。"));
      }
    }, BOOT_POLL_INTERVAL_MS);
  }

  async function loadSession(runtimeSessionId: string, selectionNonce: number) {
    stopPolling();
    setIsLoading(true);
    setError(null);
    try {
      const snapshot = await getRuntimeSession(runtimeSessionId);
      if (!isCurrentSelection(runtimeSessionId, selectionNonce)) {
        return;
      }
      syncSessionSnapshot(snapshot);
      if (snapshot.boot_status === "pending") {
        await hydrateOpening(runtimeSessionId, selectionNonce);
      } else if (snapshot.boot_status === "booting") {
        await startBootPolling(runtimeSessionId, selectionNonce);
      } else {
        setIsBootstrapping(false);
      }
      await refreshDebugSnapshot(runtimeSessionId);
    } catch (err) {
      if (isCurrentSelection(runtimeSessionId, selectionNonce)) {
        setError(toUserError(err, "无法进入该世界，请重试。"));
        await refreshDebugSnapshot(runtimeSessionId);
      }
    } finally {
      if (isCurrentSelection(runtimeSessionId, selectionNonce)) {
        setIsLoading(false);
      }
    }
  }

  async function hydrateOpening(runtimeSessionId: string, selectionNonce = selectionNonceRef.current) {
    const bootstrapNonce = ++bootstrapNonceRef.current;
    setIsBootstrapping(true);
    setError(null);
    try {
      const snapshot = await bootstrapRuntimeSession(runtimeSessionId);
      if (!isCurrentBootstrap(runtimeSessionId, selectionNonce, bootstrapNonce)) {
        return;
      }
      syncSessionSnapshot(snapshot);
      if (snapshot.boot_status === "booting") {
        await startBootPolling(runtimeSessionId, selectionNonce);
        return;
      }
      setIsBootstrapping(false);
      await refreshWorlds();
      await refreshDebugSnapshot(runtimeSessionId);
    } catch (err) {
      if (!isCurrentSelection(runtimeSessionId, selectionNonce)) {
        return;
      }
      try {
        const failedSnapshot = await getRuntimeSession(runtimeSessionId);
        if (isCurrentSelection(runtimeSessionId, selectionNonce)) {
          syncSessionSnapshot(failedSnapshot);
          if (failedSnapshot.boot_status === "booting") {
            await startBootPolling(runtimeSessionId, selectionNonce);
            return;
          }
        }
      } catch {
        // Ignore refresh failure and surface the original bootstrap error.
      }
      setError(toUserError(err, "开场没有成功展开，请重试。"));
      await refreshDebugSnapshot(runtimeSessionId);
    } finally {
      if (isCurrentBootstrap(runtimeSessionId, selectionNonce, bootstrapNonce)) {
        setIsBootstrapping(false);
      }
    }
  }

  async function handleSend() {
    if (!session || session.boot_status !== "ready" || !input.trim() || isSending || isBootstrapping) {
      return;
    }
    const userAction = input.trim();
    const optimisticTurnNumber = session.turn_count + 1;
    const optimisticUserMessage: RuntimeMessage = {
      role: "user",
      content: userAction,
      turn_number: optimisticTurnNumber,
      created_at: new Date().toISOString(),
      meta: {},
    };
    const streamingAssistantMessage: RuntimeMessage = {
      role: "assistant",
      content: "",
      turn_number: optimisticTurnNumber,
      created_at: new Date().toISOString(),
      meta: { streaming: true },
    };
    setInput("");
    setSession((current) =>
      current
        ? {
            ...current,
            messages: [...current.messages, optimisticUserMessage, streamingAssistantMessage],
          }
        : current,
    );

    setIsSending(true);
    setError(null);
    let completed = false;
    try {
      await runRuntimeTurnStream(
        {
          runtime_session_id: session.runtime_session_id,
          user_action: userAction,
        },
        {
          onAssistantDelta: (payload) => {
            setSession((current) =>
              current ? applyStreamingAssistantDelta(current, payload.turn_number, payload.content) : current,
            );
          },
          onComplete: (response) => {
            completed = true;
            setSession((current) => mergeTurnResponse(current, response));
            setIsSending(false);
          },
        },
      );
      await refreshWorlds();
      await refreshDebugSnapshot(session.runtime_session_id);
    } catch (err) {
      setError(toUserError(err, "这一轮没有成功展开，请重试。"));
      setSession((current) =>
        current
            ? {
                ...current,
                messages: current.messages.filter((message) => {
                  if (message.role === "assistant" && message.meta?.streaming) {
                    return false;
                  }
                  return !(message.role === "user" && message.turn_number === optimisticTurnNumber && message.content === userAction);
                }),
              }
            : current,
      );
      await refreshDebugSnapshot(session.runtime_session_id);
    } finally {
      if (!completed) {
        setIsSending(false);
      }
    }
  }

  async function handleRenameSubmit() {
    if (!renameState) {
      return;
    }
    try {
      const snapshot = await updateRuntimeDisplayTitle(renameState.sessionId, renameState.value);
      if (snapshot.runtime_session_id === sessionId) {
        setSession(snapshot);
      }
      setRenameState(null);
      await refreshWorlds();
    } catch (err) {
      setError(toUserError(err, "这个名字没有保存成功，请重试。"));
    }
  }

  function handleOpenLorebook() {
    setActivePanel("lorebook");
  }

  function handleConfirmLorebook() {
    if (!sessionId) {
      return;
    }
    if (rememberLorebookChoice) {
      safeStorageSet(lorebookConfirmKey(sessionId), "1");
    }
    setLorebookUnlocked(true);
  }

  function openArchitect() {
    const architectWindow = window.open(ARCHITECT_APP_URL, "_blank");
    if (!architectWindow) {
      window.location.assign(ARCHITECT_APP_URL);
      return;
    }
    architectWindow.opener = null;
  }

  const visibleLorebook = useMemo(() => session?.lorebook ?? [], [session?.lorebook]);
  const visibleMemories = useMemo(
    () => [...(session?.recent_memories ?? [])].reverse(),
    [session?.recent_memories],
  );
  const title = session ? displayWorldTitle(session.display_title, session.world_summary_card.title) : "OSeria Runtime";
  const isRuntimeReady = Boolean(session && session.boot_status === "ready");
  const protagonistName = session?.world_stats.protagonist_name?.trim() ?? "";
  const protagonistGender = genderBadge(session?.world_stats.protagonist_gender ?? "unknown");
  const currentTimestamp = session?.world_stats.current_timestamp?.trim() ?? "";
  const currentLocation = session?.world_stats.current_location?.trim() ?? "";

  return (
    <main className="runtime-shell">
      <button className="drawer-toggle drawer-toggle--left" onClick={() => setLeftOpen((open) => !open)} type="button">
        世界列表
      </button>
      <button
        className="drawer-toggle drawer-toggle--right"
        onClick={() => setRightOpen((open) => !open)}
        type="button"
      >
        当前状态
      </button>

      <aside className={`drawer drawer--left ${leftOpen ? "drawer--open" : ""}`}>
        <div className="drawer__body drawer__body--stack drawer__body--left">
          <div className="world-list">
            {worlds.length === 0 ? <p className="drawer__empty">还没有可进入的世界。</p> : null}
            {worlds.map((world) => (
              <button
                className={`world-card ${world.runtime_session_id === sessionId ? "world-card--active" : ""}`}
                key={world.runtime_session_id}
                onClick={() => {
                  setLeftOpen(false);
                  setSessionId(world.runtime_session_id);
                }}
                onContextMenu={(event) => {
                  if (!isDesktopPointer()) {
                    return;
                  }
                  event.preventDefault();
                  setContextMenu({
                    sessionId: world.runtime_session_id,
                    x: event.clientX,
                    y: event.clientY,
                  });
                }}
                type="button"
              >
                <strong>{displayWorldTitle(world.display_title, world.title)}</strong>
                <small>{formatRelativeTime(world.updated_at)}</small>
              </button>
            ))}
          </div>
          <button className="world-card world-card--new" onClick={openArchitect} type="button">
            <strong>新建世界</strong>
          </button>
        </div>
      </aside>

      <aside className={`drawer drawer--right ${rightOpen ? "drawer--open" : ""}`}>
        <div className="drawer__body drawer__body--right">
          {session ? (
            <>
              <section className="detail-card detail-card--status">
                {protagonistName ? (
                  <div className="status-row">
                    <span className="status-label">主角</span>
                    <strong className="status-value">
                      {protagonistName}
                      <span className="gender-badge">{protagonistGender}</span>
                    </strong>
                  </div>
                ) : null}
                {currentTimestamp ? (
                  <div className="status-row">
                    <span className="status-label">时间</span>
                    <strong className="status-value">{currentTimestamp}</strong>
                  </div>
                ) : null}
                {currentLocation ? (
                  <div className="status-row">
                    <span className="status-label">地点</span>
                    <strong className="status-value">{currentLocation}</strong>
                  </div>
                ) : null}
              </section>

              <div className="panel-switcher">
                <button
                  className={`panel-switcher__button ${activePanel === "memory" ? "is-active" : ""}`}
                  onClick={() => setActivePanel((current) => (current === "memory" ? null : "memory"))}
                  type="button"
                >
                  短期记忆
                </button>
                <button
                  className={`panel-switcher__button ${activePanel === "lorebook" ? "is-active" : ""}`}
                  onClick={handleOpenLorebook}
                  type="button"
                >
                  Lorebook
                </button>
              </div>

              {activePanel === "memory" ? (
                <section className="detail-card">
                  <div className="memory-list">
                    {visibleMemories.map((memory: TurnSummaryMemory) => (
                      <article className="memory-entry" key={`memory-${memory.turn_number}`}>
                        <small>第 {memory.turn_number} 轮</small>
                        <p>{memory.summary}</p>
                      </article>
                    ))}
                    {visibleMemories.length === 0 ? <p className="drawer__empty">这一段故事还很新。</p> : null}
                  </div>
                </section>
              ) : null}

              {activePanel === "lorebook" ? (
                lorebookUnlocked ? (
                  <section className="detail-card">
                    <div className="lorebook-list">
                      {visibleLorebook.map((entry: LorebookEntry) => (
                        <article key={entry.id} className="lorebook-entry">
                          <header>
                            <strong>{entry.name}</strong>
                            <span>{entry.type}</span>
                          </header>
                          <p>{entry.description}</p>
                        </article>
                      ))}
                      {visibleLorebook.length === 0 ? <p className="drawer__empty">还没有形成可查阅的条目。</p> : null}
                    </div>
                  </section>
                ) : (
                  <section className="detail-card">
                    <div className="spoiler-guard">
                      <p>Lorebook 可能包含当前叙事中你尚未亲眼得知的信息。</p>
                      <label className="spoiler-guard__remember">
                        <input
                          checked={rememberLorebookChoice}
                          onChange={(event) => setRememberLorebookChoice(event.target.checked)}
                          type="checkbox"
                        />
                        本世界不再提示
                      </label>
                      <div className="spoiler-guard__actions">
                        <button onClick={handleConfirmLorebook} type="button">
                          仍然查看
                        </button>
                      </div>
                    </div>
                  </section>
                )
              ) : null}

              {debugMode && debugSnapshot ? (
                <section className="detail-card detail-card--debug">
                  <strong>Dev Diagnostics</strong>
                  <p>boot={debugSnapshot.boot_status} · turn={debugSnapshot.turn_count}</p>
                  <p>
                    lorebook={debugSnapshot.last_lorebook_job_status}
                    {debugSnapshot.last_lorebook_job_turn
                      ? ` · lorebook_turn=${debugSnapshot.last_lorebook_job_turn}`
                      : ""}
                  </p>
                  {debugSnapshot.last_turn_error ? (
                    <pre className="debug-block">
                      {formatDebugError("turn", debugSnapshot.last_turn_error)}
                    </pre>
                  ) : null}
                  {debugSnapshot.last_bootstrap_error ? (
                    <pre className="debug-block">
                      {formatDebugError("bootstrap", debugSnapshot.last_bootstrap_error)}
                    </pre>
                  ) : null}
                  {debugSnapshot.last_lorebook_error ? (
                    <pre className="debug-block">
                      {formatDebugError("lorebook", debugSnapshot.last_lorebook_error)}
                    </pre>
                  ) : null}
                  {!debugSnapshot.last_turn_error &&
                  !debugSnapshot.last_bootstrap_error &&
                  !debugSnapshot.last_lorebook_error ? (
                    <p className="drawer__empty">No recorded runtime errors.</p>
                  ) : null}
                </section>
              ) : null}

              <button
                aria-label={theme === "light" ? "切换到夜间模式" : "切换到日间模式"}
                className="theme-toggle"
                onClick={() => setTheme((current) => (current === "light" ? "dark" : "light"))}
                title={theme === "light" ? "切换到夜间模式" : "切换到日间模式"}
                type="button"
              >
                {theme === "light" ? <MoonIcon /> : <SunIcon />}
              </button>
            </>
          ) : (
            <p className="drawer__empty">先进入一个世界，这里才会出现它此刻的状态。</p>
          )}
        </div>
      </aside>

      {contextMenu ? (
        <div
          className="context-menu"
          onPointerDown={(event) => event.stopPropagation()}
          style={{ left: contextMenu.x, top: contextMenu.y }}
        >
          <button
            onClick={() => {
              const world = worlds.find((item) => item.runtime_session_id === contextMenu.sessionId);
              setRenameState({
                sessionId: contextMenu.sessionId,
                value: world?.display_title || world?.title || "",
              });
              setContextMenu(null);
            }}
            type="button"
          >
            重命名
          </button>
        </div>
      ) : null}

      {renameState ? (
        <div className="modal-shell" onClick={() => setRenameState(null)} role="presentation">
          <div
            className="modal-card"
            onClick={(event) => event.stopPropagation()}
            onPointerDown={(event) => event.stopPropagation()}
            role="dialog"
            aria-modal="true"
          >
            <h3>世界备注名</h3>
            <input
              autoFocus
              onChange={(event) => setRenameState((current) => (current ? { ...current, value: event.target.value } : current))}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  void handleRenameSubmit();
                }
              }}
              placeholder="输入新的前台名称"
              value={renameState.value}
            />
            <div className="modal-card__actions">
              <button className="button-ghost" onClick={() => setRenameState(null)} type="button">
                取消
              </button>
              <button onClick={() => void handleRenameSubmit()} type="button">
                保存
              </button>
            </div>
          </div>
        </div>
      ) : null}

      <section className="chat-stage">
        <header className="chat-stage__header">
          <p className="chat-stage__eyebrow">OSeria Runtime</p>
          <h1>{title}</h1>
        </header>

        <div className="chat-stream" aria-live="polite">
          {!session && !isLoading ? (
            <div className="empty-state">
              <p>从 Architect 进入一个世界，这里的故事才会继续往前走。</p>
            </div>
          ) : null}
          {session && !isRuntimeReady ? (
            <div className="system-note">
              {isBootstrapping ? "世界正在苏醒，开场还在生成..." : "这个世界还没有成功展开开场。"}
            </div>
          ) : null}
          {session && session.boot_status === "failed" && !isBootstrapping ? (
            <div className="system-note system-note--error">
              开场没有成功展开。
              <button
                className="inline-action"
                onClick={() => void hydrateOpening(session.runtime_session_id, selectionNonceRef.current)}
                type="button"
              >
                重试开场
              </button>
            </div>
          ) : null}
          {session?.messages.map((message, index) => (
            <article
              className={`message message--${message.role}`}
              key={`${message.turn_number}-${message.role}-${index}`}
            >
              <div className="message__body">{message.content}</div>
            </article>
          ))}
          {isLoading ? <div className="system-note">正在载入世界...</div> : null}
          {isSending ? <div className="system-note">世界正在回应...</div> : null}
          {error ? <div className="system-note system-note--error">{error.message}</div> : null}
        </div>

        <footer className="composer">
          <div className="composer__input-shell">
            <textarea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  void handleSend();
                }
              }}
              placeholder="你准备怎么做？"
              disabled={!isRuntimeReady || isSending || isBootstrapping}
            />
            <button
              aria-label="发送"
              className="composer__submit"
              onClick={() => void handleSend()}
              type="button"
              disabled={!isRuntimeReady || isSending || isBootstrapping || !input.trim()}
            >
              <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M3 12L21 12M21 12L14 5M21 12L14 19" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
          </div>
        </footer>
      </section>
    </main>
  );
}

function mergeTurnResponse(
  current: RuntimeSessionSnapshot | null,
  response: RuntimeTurnResponse,
): RuntimeSessionSnapshot | null {
  if (!current) {
    return current;
  }
  return {
    ...current,
    turn_count: response.turn_count,
    messages: [...current.messages.filter((message) => !(message.role === "assistant" && message.meta?.streaming)), response.assistant_message],
    world_stats: response.world_stats,
    state_snapshot: response.state_snapshot,
    recent_memories: response.recent_memories,
    lorebook: response.lorebook,
    updated_at: response.updated_at,
  };
}

function applyStreamingAssistantDelta(
  current: RuntimeSessionSnapshot,
  turnNumber: number,
  content: string,
): RuntimeSessionSnapshot {
  return {
    ...current,
    messages: current.messages.map((message) =>
      message.role === "assistant" && message.meta?.streaming && message.turn_number === turnNumber
        ? { ...message, content }
        : message,
    ),
  };
}

function displayWorldTitle(displayTitle: string, title: string): string {
  return displayTitle.trim() || title.trim() || "未命名世界";
}

function formatRelativeTime(updatedAt: string): string {
  const diffMs = Date.now() - new Date(updatedAt).getTime();
  if (!Number.isFinite(diffMs) || diffMs <= 0) {
    return "1分";
  }
  const diffMinutes = Math.max(1, Math.floor(diffMs / 60000));
  if (diffMinutes < 60) {
    return `${diffMinutes}分`;
  }
  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) {
    return `${diffHours}小时`;
  }
  return `${Math.floor(diffHours / 24)}天`;
}

function genderBadge(value: "male" | "female" | "unknown"): string {
  if (value === "male") {
    return "男";
  }
  if (value === "female") {
    return "女";
  }
  return "？";
}

function toUserError(error: unknown, fallback: string): ApiErrorPayload {
  if (error instanceof ApiError) {
    return { ...error.payload, message: fallback };
  }
  return { code: "internal", message: fallback, retryable: false };
}

function formatDebugError(
  label: string,
  error: {
    code: string;
    message: string;
    status_code: number;
    retryable: boolean;
    created_at: string;
    turn_number: number;
    user_action: string;
  },
): string {
  return [
    `[${label}] ${error.code} (${error.status_code})`,
    error.message,
    error.turn_number ? `turn=${error.turn_number}` : "",
    error.user_action ? `user_action=${error.user_action}` : "",
    `retryable=${error.retryable}`,
    `at=${error.created_at}`,
  ]
    .filter(Boolean)
    .join("\n");
}

function MoonIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <path
        d="M18 15.2A7.7 7.7 0 0 1 8.8 6a7.9 7.9 0 1 0 9.2 9.2Z"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function SunIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <circle cx="12" cy="12" r="4" stroke="currentColor" strokeWidth="1.8" />
      <path
        d="M12 2.5V5.2M12 18.8V21.5M21.5 12H18.8M5.2 12H2.5M18.7 5.3L16.8 7.2M7.2 16.8L5.3 18.7M18.7 18.7L16.8 16.8M7.2 7.2L5.3 5.3"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  );
}
