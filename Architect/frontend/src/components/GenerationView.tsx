import { useEffect, useState } from "react";

const COPY = [
  "让我为你完成这个世界。",
  "正在为你编织法则……",
  "你的每一句话，都在变成世界的一条规则。",
  "快好了。",
];

export function GenerationView() {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setIndex((current) => (current + 1) % COPY.length);
    }, 4000);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <section className="full-screen-panel generation-view">
      <p key={index} className="generation-view__copy">
        {COPY[index]}
      </p>
    </section>
  );
}

