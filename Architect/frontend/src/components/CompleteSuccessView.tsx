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
  onRestart: () => void;
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
  onRestart,
}: CompleteSuccessViewProps) {
  return (
    <>
      <div className="complete-view__hero">
        <p className="complete-view__eyebrow">结果</p>
        <h1>{blueprint.title}</h1>
      </div>

      <div className="blueprint-stack">
        <article className="blueprint-card">
          <h2>世界摘要</h2>
          <p>{blueprint.world_summary}</p>
        </article>
        <article className="blueprint-grid">
          <div className="blueprint-card">
            <h3>主角起点</h3>
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
        <article className="blueprint-grid">
          <div className="blueprint-card">
            <h3>核心维度</h3>
            <div className="chip-row">
              {blueprint.confirmed_dimensions.map((item) => (
                <span className="chip" key={item}>
                  {item}
                </span>
              ))}
            </div>
          </div>
          <div className="blueprint-card">
            <h3>留白维度</h3>
            <div className="chip-row">
              {blueprint.emergent_dimensions.map((item) => (
                <span className="chip chip--muted" key={item}>
                  {item}
                </span>
              ))}
            </div>
          </div>
        </article>
        <article className="blueprint-card">
          <h3>玩家侧写</h3>
          <p>{blueprint.player_profile}</p>
        </article>
      </div>

      <div className="result-actions">
        <button className="text-button" type="button" disabled={!systemPrompt} onClick={onOpenPromptInspector}>
          查看完整 Prompt
        </button>
        <button className="text-button" type="button" onClick={onCopyBlueprint}>
          复制蓝图摘要
        </button>
        <button className="text-button" type="button" onClick={onRestart}>
          再造一个世界
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
