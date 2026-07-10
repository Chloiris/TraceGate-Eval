interface ErrorStateProps {
  title: string;
  message: string;
  onRetry?: () => void;
}

export function LoadingState({ label = "正在读取本地后端状态…" }: { label?: string }) {
  return (
    <div className="request-state" role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      <div>
        <strong>请稍候</strong>
        <p>{label}</p>
      </div>
    </div>
  );
}

export function ErrorState({ title, message, onRetry }: ErrorStateProps) {
  return (
    <div className="request-state request-error" role="alert">
      <span className="request-icon" aria-hidden="true">!</span>
      <div>
        <strong>{title}</strong>
        <p>{message}</p>
        {onRetry ? (
          <button className="button button-secondary button-small" type="button" onClick={onRetry}>
            重试
          </button>
        ) : null}
      </div>
    </div>
  );
}
