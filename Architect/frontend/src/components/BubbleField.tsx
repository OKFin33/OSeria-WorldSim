interface BubbleFieldProps {
  bubbles: string[];
  mode: "tutorial" | "tags";
  onBubbleClick: (text: string) => void;
}

export function BubbleField({ bubbles, mode, onBubbleClick }: BubbleFieldProps) {
  return (
    <div className={`bubble-field bubble-field--${mode}`}>
      {bubbles.map((bubble) => (
        <button
          key={bubble}
          className={`bubble bubble--${mode}`}
          type="button"
          onClick={() => onBubbleClick(bubble)}
        >
          {bubble}
        </button>
      ))}
    </div>
  );
}

