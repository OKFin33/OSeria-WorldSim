interface BubbleFieldProps {
  bubbles: string[];
  mode: "tutorial" | "tags";
  onBubbleClick: (text: string) => void;
}

export function BubbleField({ bubbles, mode, onBubbleClick }: BubbleFieldProps) {
  return (
    <div className={`bubble-field bubble-field--${mode}`}>
      {bubbles.map((bubble, index) => (
        <button
          key={`${mode}:${index}:${bubble}`}
          className={`bubble bubble--${mode}`}
          type="button"
          onClick={() => onBubbleClick(bubble)}
        >
          <img src="/ink-brush.png" alt="" className="bubble-bg" />
          <span className="bubble-text">{bubble}</span>
        </button>
      ))}
    </div>
  );
}
