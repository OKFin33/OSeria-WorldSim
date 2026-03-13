interface LoadingSpinnerProps {
  label: string;
}

export function LoadingSpinner({ label }: LoadingSpinnerProps) {
  return (
    <>
      <span className="sr-only">{label}</span>
      <span className="loading-spinner" aria-hidden="true" />
    </>
  );
}
