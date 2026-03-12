import { useEffect, useState } from "react";

interface CurrentSceneProps {
  message: string;
  isWaiting: boolean;
}

export function CurrentScene({ message, isWaiting }: CurrentSceneProps) {
  const [displayedText, setDisplayedText] = useState("");
  const [opacity, setOpacity] = useState(1);

  useEffect(() => {
    if (!message) return;

    setOpacity(0);
    const fadeTimer = window.setTimeout(() => {
      setDisplayedText("");
      setOpacity(1);

      let currentIndex = 0;
      const typeInterval = window.setInterval(() => {
        setDisplayedText(message.slice(0, currentIndex + 1));
        currentIndex++;
        if (currentIndex >= message.length) {
          window.clearInterval(typeInterval);
        }
      }, 40);

      return () => window.clearInterval(typeInterval);
    }, 200);

    return () => window.clearTimeout(fadeTimer);
  }, [message]);

  const paragraphs = displayedText.split("\n").filter((p) => p.trim() !== "");
  return (
    <div
      className={`scene-card${isWaiting ? " scene-card--waiting" : ""}`}
      style={{ opacity, transition: "opacity 0.2s ease-in-out" }}
    >
      {paragraphs.map((p, i) => (
        <p key={i}>{p}</p>
      ))}
    </div>
  );
}
