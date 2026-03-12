import type { ApiErrorPayload, Blueprint } from "../types";
import { CompleteSuccessView } from "./CompleteSuccessView";
import { FatalErrorView } from "./FatalErrorView";
import { GenerateFailureView } from "./GenerateFailureView";

type CompleteViewMode = "success" | "generate_failure" | "fatal_error";

interface CompleteViewProps {
  mode: CompleteViewMode;
  blueprint: Blueprint | null;
  systemPrompt: string | null;
  error: ApiErrorPayload | null;
  isPromptInspectorOpen: boolean;
  copyFeedback: string | null;
  onOpenPromptInspector: () => void;
  onClosePromptInspector: () => void;
  onCopyBlueprint: () => void;
  onCopyPrompt: () => void;
  onRetryGenerate: () => void;
  onRestart: () => void;
}

export function CompleteView({
  mode,
  blueprint,
  systemPrompt,
  error,
  isPromptInspectorOpen,
  copyFeedback,
  onOpenPromptInspector,
  onClosePromptInspector,
  onCopyBlueprint,
  onCopyPrompt,
  onRetryGenerate,
  onRestart,
}: CompleteViewProps) {
  return (
    <section className="full-screen-panel complete-view">
      {mode === "success" && blueprint ? (
        <CompleteSuccessView
          blueprint={blueprint}
          systemPrompt={systemPrompt}
          isPromptInspectorOpen={isPromptInspectorOpen}
          copyFeedback={copyFeedback}
          onOpenPromptInspector={onOpenPromptInspector}
          onClosePromptInspector={onClosePromptInspector}
          onCopyBlueprint={onCopyBlueprint}
          onCopyPrompt={onCopyPrompt}
          onRestart={onRestart}
        />
      ) : null}

      {mode === "generate_failure" && error ? (
        <GenerateFailureView error={error} onRetryGenerate={onRetryGenerate} onRestart={onRestart} />
      ) : null}

      {mode === "fatal_error" && error ? (
        <FatalErrorView error={error} onRestart={onRestart} />
      ) : null}
    </section>
  );
}
