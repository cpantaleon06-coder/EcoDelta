export function Loading({ label = 'Loading…', minHeight }: { label?: string; minHeight?: number }) {
  return (
    <div className="status" role="status" aria-live="polite" style={{ minHeight }}>
      <span className="spinner" aria-hidden="true" />
      {label}
    </div>
  );
}

export function ErrorBox({ error, minHeight }: { error: Error; minHeight?: number }) {
  return (
    <div className="status status--error" role="alert" style={{ minHeight }}>
      <strong>▼ Something went wrong.</strong> {error.message}
    </div>
  );
}
