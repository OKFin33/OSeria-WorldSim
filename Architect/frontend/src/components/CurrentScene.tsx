interface CurrentSceneProps {
  message: string;
  isWaiting: boolean;
}

export function CurrentScene({ message, isWaiting }: CurrentSceneProps) {
  return (
    <div className={`scene-card${isWaiting ? " scene-card--waiting" : ""}`}>
      <p>{message}</p>
    </div>
  );
}

