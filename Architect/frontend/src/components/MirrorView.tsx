import { LoadingSpinner } from "./LoadingSpinner";

interface MirrorViewProps {
  mirrorText: string;
  disabled: boolean;
  isWaiting?: boolean;
  waitingPhrase?: string | null;
  activeAction?: "confirm" | "reconsider" | null;
  onConfirm: () => void;
  onReconsider: () => void;
}

export function MirrorView({
  mirrorText,
  disabled,
  isWaiting = false,
  waitingPhrase = null,
  activeAction = null,
  onConfirm,
  onReconsider,
}: MirrorViewProps) {
  const showsInlineLead = /^(所以我看到的世界是[——-]?|我看到的世界是[——-]?)/.test(mirrorText.trim());

  return (
    <section className="full-screen-panel mirror-view">
      {!isWaiting ? (
        <div className="mirror-view__text-wrap">
          {!showsInlineLead ? <p className="mirror-view__lead">所以我看到的世界是</p> : null}
          <div className="mirror-view__text">{mirrorText}</div>
        </div>
      ) : null}
      {isWaiting && waitingPhrase ? (
        <p className="waiting-copy waiting-copy--panel" aria-live="polite" key={waitingPhrase}>
          <span className="waiting-copy__inner">{waitingPhrase}</span>
        </p>
      ) : null}
      <div className={`mirror-view__actions${isWaiting ? " mirror-view__actions--waiting" : ""}`}>
        <button
          className={`bubble bubble--mirror${isWaiting && activeAction === "confirm" ? " bubble--loading" : ""}${isWaiting && activeAction === "reconsider" ? " bubble--muted" : ""}`}
          type="button"
          disabled={disabled}
          onClick={onConfirm}
          aria-label={isWaiting && activeAction === "confirm" ? "正在推门" : "推门"}
        >
          <img src="/ink-brush.png" alt="" className="bubble-bg" />
          <span className="bubble-text">
            {isWaiting && activeAction === "confirm" ? <LoadingSpinner label="正在推门" /> : "推门"}
          </span>
        </button>
        <button
          className={`bubble bubble--mirror${isWaiting && activeAction === "reconsider" ? " bubble--loading" : ""}${isWaiting && activeAction === "confirm" ? " bubble--muted" : ""}`}
          type="button"
          disabled={disabled}
          onClick={onReconsider}
          aria-label={isWaiting && activeAction === "reconsider" ? "正在重新思考" : "得再想想"}
        >
          <img src="/ink-brush.png" alt="" className="bubble-bg" />
          <span className="bubble-text">
            {isWaiting && activeAction === "reconsider" ? <LoadingSpinner label="正在重新思考" /> : "得再想想"}
          </span>
        </button>
        {!isWaiting ? <p className="mirror-view__guide">像就推门，不像就继续修。</p> : null}
      </div>
    </section>
  );
}
