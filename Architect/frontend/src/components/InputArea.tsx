import { useState } from "react";

interface InputAreaProps {
  value: string;
  placeholder: string;
  disabled: boolean;
  onChange: (value: string) => void;
  onSubmit: () => void;
}

export function InputArea({
  value,
  placeholder,
  disabled,
  onChange,
  onSubmit,
}: InputAreaProps) {
  const [isComposing, setIsComposing] = useState(false);

  return (
    <div className="input-area">
      <textarea
        className="input-area__textarea"
        rows={3}
        value={value}
        disabled={disabled}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
        onCompositionStart={() => setIsComposing(true)}
        onCompositionEnd={() => setIsComposing(false)}
        onKeyDown={(event) => {
          if (event.key !== "Enter") {
            return;
          }
          if (event.shiftKey || isComposing) {
            return;
          }
          event.preventDefault();
          onSubmit();
        }}
      />
      <button
        className="input-area__submit"
        type="button"
        disabled={disabled || !value.trim()}
        onClick={onSubmit}
      >
        提交
      </button>
    </div>
  );
}

