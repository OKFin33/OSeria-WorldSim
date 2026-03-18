interface PromptInspectorProps {
  isOpen: boolean;
  systemPrompt: string;
  onClose: () => void;
  onCopyPrompt: () => void;
}

export function PromptInspector({
  isOpen,
  systemPrompt,
  onClose,
  onCopyPrompt,
}: PromptInspectorProps) {
  if (!isOpen) {
    return null;
  }

  return (
    <div className="prompt-inspector-backdrop" role="presentation" onClick={onClose}>
      <aside
        className="prompt-inspector"
        role="dialog"
        aria-modal="true"
        aria-label="完整 Prompt"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="prompt-inspector__header">
          <h2>完整 Prompt</h2>
          <div className="prompt-inspector__actions">
            <button className="text-button" type="button" onClick={onCopyPrompt}>
              复制 Prompt
            </button>
            <button className="text-button" type="button" onClick={onClose}>
              关闭
            </button>
          </div>
        </div>
        <pre className="prompt-content">{systemPrompt}</pre>
      </aside>
    </div>
  );
}

