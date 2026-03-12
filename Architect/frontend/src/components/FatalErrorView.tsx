import type { ApiErrorPayload } from "../types";

interface FatalErrorViewProps {
  error: ApiErrorPayload;
  onRestart: () => void;
}

function resolveFatalHeadline(error: ApiErrorPayload): string {
  if (error.code === "session_expired") {
    return "这扇门已经关上了。";
  }
  if (error.code === "validation_error") {
    return "这一步没接上。";
  }
  return "这个世界暂时接不回来了。";
}

export function FatalErrorView({ error, onRestart }: FatalErrorViewProps) {
  return (
    <>
      <div className="complete-view__hero">
        <p className="complete-view__eyebrow">故障</p>
        <h1>{resolveFatalHeadline(error)}</h1>
      </div>
      <div className="blueprint-card blueprint-card--error">
        <p>这不是生成阶段的卡顿，当前上下文已经不可恢复。</p>
        <p className="support-copy">最稳妥的处理方式是重新开始。</p>
        <p className="support-copy support-copy--detail">{error.message}</p>
      </div>
      <div className="result-actions">
        <button className="text-button" type="button" onClick={onRestart}>
          再造一个世界
        </button>
      </div>
    </>
  );
}
