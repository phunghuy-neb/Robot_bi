export default function SectionState({
  state,
  loadingText = 'Đang tải...',
  errorText = 'Không tải được dữ liệu.',
  emptyText = 'Chưa có dữ liệu.',
  emptyIcon = '📭',
  onRetry,
}) {
  if (state === 'loading') {
    return (
      <div className="section-state">
        <div className="spinner" />
        <span className="state-text">{loadingText}</span>
      </div>
    );
  }

  if (state === 'error') {
    return (
      <div className="section-state">
        <span className="state-icon">⚠️</span>
        <span className="state-text">{errorText}</span>
        {onRetry && (
          <button className="retry-btn" onClick={onRetry}>
            Thử lại
          </button>
        )}
      </div>
    );
  }

  if (state === 'empty') {
    return (
      <div className="section-state">
        <span className="state-icon">{emptyIcon}</span>
        <span className="state-text">{emptyText}</span>
      </div>
    );
  }

  return null;
}
