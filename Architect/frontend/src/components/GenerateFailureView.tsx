import type { ApiErrorPayload } from "../types";

interface GenerateFailureViewProps {
  error: ApiErrorPayload;
  onRetryGenerate: () => void;
  onRestart: () => void;
}

export function GenerateFailureView({
  error,
  onRetryGenerate,
  onRestart,
}: GenerateFailureViewProps) {
  return (
    <>
      <div className="complete-view__hero">
        <p className="complete-view__eyebrow">生成失败</p>
        <h1>法则还没有编织完成。</h1>
      </div>
      <div className="blueprint-card blueprint-card--error">
        <p>访谈成果已经保留，不需要重走一遍。</p>
        <p className="support-copy">
          {error.retryable ? "这次生成没有接稳，再试一次就行。" : "这次生成无法继续，只能换一个新世界。"}
        </p>
        <p className="support-copy support-copy--detail">{error.message}</p>
      </div>
      <div className="result-actions">
        <button className="text-button" type="button" disabled={!error.retryable} onClick={onRetryGenerate}>
          重新生成
        </button>
        <button className="text-button" type="button" onClick={onRestart}>
          再造一个世界
        </button>
      </div>
    </>
  );
}
