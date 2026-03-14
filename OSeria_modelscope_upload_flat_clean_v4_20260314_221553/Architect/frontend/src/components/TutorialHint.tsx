interface TutorialHintProps {
  hint: string | null;
}

export function TutorialHint({ hint }: TutorialHintProps) {
  if (!hint) {
    return <div className="tutorial-hint tutorial-hint--empty" />;
  }

  return <div className="tutorial-hint">{hint}</div>;
}

