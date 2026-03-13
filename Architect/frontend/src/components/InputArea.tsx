import { useState } from "react";
import { LoadingSpinner } from "./LoadingSpinner";

interface InputAreaProps {
  value: string;
  placeholder: string;
  disabled: boolean;
  isWaiting?: boolean;
  onChange: (value: string) => void;
  onSubmit: () => void;
}

export function InputArea({
  value,
  placeholder,
  disabled,
  isWaiting = false,
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
        aria-label="提交"
      >
        {isWaiting ? (
          <LoadingSpinner label="正在提交" />
        ) : (
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M3 12L21 12M21 12L14 5M21 12L14 19" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        )}
      </button>
    </div>
  );
}
