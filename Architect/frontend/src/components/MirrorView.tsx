interface MirrorViewProps {
  mirrorText: string;
  disabled: boolean;
  onConfirm: () => void;
  onReconsider: () => void;
}

export function MirrorView({
  mirrorText,
  disabled,
  onConfirm,
  onReconsider,
}: MirrorViewProps) {
  return (
    <section className="full-screen-panel mirror-view">
      <div className="mirror-view__text">{mirrorText}</div>
      <div className="mirror-view__actions">
        <button className="bubble bubble--mirror" type="button" disabled={disabled} onClick={onConfirm}>
          推门
        </button>
        <button className="bubble bubble--mirror" type="button" disabled={disabled} onClick={onReconsider}>
          我得再想想
        </button>
      </div>
    </section>
  );
}
