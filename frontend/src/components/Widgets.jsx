export function SeverityBadge({ severity }) {
  const level = (severity || 'low').toLowerCase();
  return <span className={`badge badge-${level}`}>{level}</span>;
}

export function EmptyState({ icon = '◌', title, description, action }) {
  return (
    <div className="empty-state">
      <div className="icon">{icon}</div>
      <h3>{title}</h3>
      {description && <p className="text-muted">{description}</p>}
      {action}
    </div>
  );
}

export function StatCard({ label, value, delta }) {
  return (
    <div className="stat-card">
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {delta && <div className="stat-delta">{delta}</div>}
    </div>
  );
}

export function LanguagePill({ language }) {
  return <span className="lang-pill">{language}</span>;
}

export function Spinner() {
  return <div className="spinner" />;
}
