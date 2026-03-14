interface BubbleFieldProps {
  bubbles: string[];
  mode: "tutorial" | "tags";
  isHidden?: boolean;
  onBubbleClick: (text: string) => void;
}

export function BubbleField({ bubbles, mode, isHidden = false, onBubbleClick }: BubbleFieldProps) {
  return (
    <div
      className={`bubble-field bubble-field--${mode}${isHidden ? " bubble-field--hidden" : ""}`}
      aria-hidden={isHidden}
    >
      {bubbles.map((bubble, index) => (
        <button
          key={`${mode}:${index}:${bubble}`}
          className={`bubble bubble--${mode}`}
          type="button"
          disabled={isHidden}
          onClick={() => onBubbleClick(bubble)}
        >
          <img src="/ink-brush.png" alt="" className="bubble-bg" />
          <span className="bubble-text">{bubble}</span>
        </button>
      ))}
    </div>
  );
}
