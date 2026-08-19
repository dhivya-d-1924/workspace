const COLORS = {
  good: '#5fd98a',
  ok: '#f2b84b',
  bad: '#f16565',
};

function colorFor(score) {
  if (score >= 80) return COLORS.good;
  if (score >= 60) return COLORS.ok;
  return COLORS.bad;
}

export default function QualityGauge({ score = 0, size = 96, label = 'Quality', strokeWidth = 8 }) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const filled = Math.max(0, Math.min(100, score)) / 100;
  const dash = `${circumference * filled} ${circumference}`;

  return (
    <div className="flex items-center gap-16">
      <div style={{ position: 'relative', width: size, height: size, flexShrink: 0 }}>
        <svg width={size} height={size} className="gauge-ring">
          <circle cx={size / 2} cy={size / 2} r={radius} className="gauge-track" />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            className="gauge-value"
            stroke={colorFor(score)}
            strokeDasharray={dash}
          />
        </svg>
        <div
          style={{
            position: 'absolute', inset: 0, display: 'flex',
            alignItems: 'center', justifyContent: 'center',
          }}
        >
          <span className="gauge-center-label" style={{ color: colorFor(score) }}>{Math.round(score)}</span>
        </div>
      </div>
      <div>
        <div className="card-title" style={{ marginBottom: 0 }}>{label}</div>
        <div className="text-muted text-sm">out of 100</div>
      </div>
    </div>
  );
}
