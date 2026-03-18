import type { Blueprint } from "../types";
import { PromptInspector } from "./PromptInspector";

interface CompleteSuccessViewProps {
  blueprint: Blueprint;
  systemPrompt: string | null;
  isPromptInspectorOpen: boolean;
  copyFeedback: string | null;
  onOpenPromptInspector: () => void;
  onClosePromptInspector: () => void;
  onCopyBlueprint: () => void;
  onCopyPrompt: () => void;
  onLaunchRuntime: () => void;
  onRestart: () => void;
  isLaunchingRuntime: boolean;
  isReplay?: boolean;
  restartLabel?: string;
}

export function CompleteSuccessView({
  blueprint,
  systemPrompt,
  isPromptInspectorOpen,
  copyFeedback,
  onOpenPromptInspector,
  onClosePromptInspector,
  onCopyBlueprint,
  onCopyPrompt,
  onLaunchRuntime,
  onRestart,
  isLaunchingRuntime,
  isReplay = false,
  restartLabel = "再造一个世界",
}: CompleteSuccessViewProps) {
  return (
    <>
      <div className="complete-view__hero">
        <p className="complete-view__eyebrow">新世界</p>
        <h1>{blueprint.title}</h1>
      </div>

      <div className="blueprint-stack">
        <article className="blueprint-card">
          <h2>世界摘要</h2>
          <p>{blueprint.world_summary}</p>
        </article>
        <article className="blueprint-grid">
          <div className="blueprint-card">
            <h3>世界入口</h3>
            <p>{blueprint.protagonist_hook}</p>
          </div>
          <div className="blueprint-card">
            <h3>核心张力</h3>
            <p>{blueprint.core_tension}</p>
          </div>
        </article>
        <article className="blueprint-card">
          <h3>基调关键词</h3>
          <div className="chip-row">
            {blueprint.tone_keywords.map((keyword) => (
              <span className="chip" key={keyword}>
                {keyword}
              </span>
            ))}
          </div>
        </article>
      </div>

      <div className="result-actions">
        <button className="text-button" type="button" disabled={!systemPrompt || isLaunchingRuntime} onClick={onLaunchRuntime}>
          {isLaunchingRuntime ? "启动 Runtime 中..." : "进入 Runtime"}
        </button>
        <button className="text-button" type="button" disabled={!systemPrompt} onClick={onOpenPromptInspector}>
          查看完整 Prompt
        </button>
        <button className="text-button" type="button" onClick={onCopyBlueprint}>
          复制蓝图摘要
        </button>
        <button className="text-button" type="button" onClick={onRestart}>
          {restartLabel}
        </button>
      </div>

      {copyFeedback ? <div className="copy-feedback">{copyFeedback}</div> : null}

      <PromptInspector
        isOpen={isPromptInspectorOpen}
        systemPrompt={systemPrompt ?? ""}
        onClose={onClosePromptInspector}
        onCopyPrompt={onCopyPrompt}
      />
    </>
  );
}
