import { useEffect, useState } from 'react';
import AppLayout from '../components/AppLayout.jsx';
import { collaborationApi } from '../api/endpoints';
import { EmptyState } from '../components/Widgets.jsx';
import QualityGauge from '../components/QualityGauge.jsx';

export default function Reviews() {
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    collaborationApi.reviewHistory().then((res) => setReviews(res.data.reviews)).finally(() => setLoading(false));
  }, []);

  return (
    <AppLayout title="Review history">
      <p className="text-muted mb-16">Every AI code review run across your projects, most recent first.</p>
      {loading ? (
        <div className="spinner" />
      ) : reviews.length === 0 ? (
        <EmptyState icon="✓" title="No reviews yet" description="Run 'Full AI review' from any project's workspace to see it here." />
      ) : (
        <div className="grid grid-cols-2">
          {reviews.map((r) => (
            <div key={r.id} className="card">
              <div className="flex items-center justify-between mb-16">
                <div>
                  <div className="card-title" style={{ marginBottom: 2 }}>{r.project}</div>
                  <div className="text-muted text-sm">{r.file || 'Whole project'}</div>
                </div>
                <QualityGauge score={r.quality_score} size={64} strokeWidth={6} label="" />
              </div>
              <p className="text-sm text-muted mb-8">{r.summary}</p>
              <div className="flex gap-16 text-sm text-faint">
                <span>{r.bug_count} bug(s)</span>
                <span>{r.security_issue_count} security issue(s)</span>
                <span>complexity {r.complexity_score}</span>
              </div>
              <div className="text-faint text-sm mt-8">{new Date(r.created_at).toLocaleString()}</div>
            </div>
          ))}
        </div>
      )}
    </AppLayout>
  );
}
