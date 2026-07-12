import { useI18n } from "../i18n";

interface ErrorStateProps {
  title: string;
  message: string;
  onRetry?: () => void;
}

export function LoadingState({ label }: { label?: string }) {
  const { text } = useI18n();
  return (
    <div className="request-state" role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      <div>
        <strong>{text("请稍候", "Please wait")}</strong>
        <p>{label ?? text("正在读取本地后端状态…", "Reading local backend status…")}</p>
      </div>
    </div>
  );
}

export function ErrorState({ title, message, onRetry }: ErrorStateProps) {
  const { text } = useI18n();
  return (
    <div className="request-state request-error" role="alert">
      <span className="request-icon" aria-hidden="true">!</span>
      <div>
        <strong>{title}</strong>
        <p>{message}</p>
        {onRetry ? (
          <button className="button button-secondary button-small" type="button" onClick={onRetry}>
            {text("重试", "Retry")}
          </button>
        ) : null}
      </div>
    </div>
  );
}
