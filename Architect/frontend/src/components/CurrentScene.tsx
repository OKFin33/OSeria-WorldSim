interface CurrentSceneProps {
  message: string;
  question: string;
  isWaiting: boolean;
  waitingPhrase?: string | null;
}

export function CurrentScene({ message, question, isWaiting, waitingPhrase = null }: CurrentSceneProps) {
  const paragraphs = message.split("\n").filter((p) => p.trim() !== "");
  const contentKey = `${message}::${question}`;

  return (
    <div className={`scene-card${isWaiting ? " scene-card--waiting" : ""}`}>
      {(message || question) && (
        <div
          key={contentKey}
          className={`scene-card__content${isWaiting ? " scene-card__content--hidden" : ""}`}
          aria-hidden={isWaiting}
        >
          <div className="scene-card__echo">
            {paragraphs.map((p, i) => (
              <p key={i}>{p}</p>
            ))}
          </div>
          {question ? <p className="scene-card__question">{question}</p> : null}
        </div>
      )}
      {isWaiting && waitingPhrase ? (
        <div className="scene-card__waiting" aria-live="polite">
          <p className="scene-card__waiting-copy waiting-copy" key={waitingPhrase}>
            <span className="waiting-copy__inner">{waitingPhrase}</span>
          </p>
        </div>
      ) : null}
    </div>
  );
}
