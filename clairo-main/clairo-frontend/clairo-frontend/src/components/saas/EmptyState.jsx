export default function EmptyState({
  icon = "📋",
  title,
  description,
  actionLabel = "Go to Claim Intake",
  onAction,
}) {
  return (
    <div className="empty-state panel">
      <span className="empty-state__icon" aria-hidden="true">
        {icon}
      </span>
      <h2 className="empty-state__title">{title}</h2>
      <p className="empty-state__desc">{description}</p>
      {onAction && (
        <button type="button" className="btn-saas" onClick={onAction}>
          {actionLabel}
        </button>
      )}
    </div>
  );
}
