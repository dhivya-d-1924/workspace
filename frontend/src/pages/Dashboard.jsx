import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import AppLayout from '../components/AppLayout.jsx';
import { authApi } from '../api/endpoints';
import { StatCard, EmptyState, LanguagePill } from '../components/Widgets.jsx';
import QualityGauge from '../components/QualityGauge.jsx';
import { useAuth } from '../context/AuthContext.jsx';

export default function Dashboard() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    authApi.dashboard().then((res) => setData(res.data)).finally(() => setLoading(false));
  }, []);

  return (
    <AppLayout title="Dashboard">
      <p className="text-muted mb-16">
        Welcome back, <strong style={{ color: 'var(--text)' }}>{user?.first_name || user?.username}</strong>.
        Here's what's happening across your projects.
      </p>

      {loading ? (
        <div className="spinner" />
      ) : data ? (
        <>
          <div className="grid grid-cols-4 mb-16">
            <StatCard label="Projects" value={data.stats.total_projects} />
            <StatCard label="Files" value={data.stats.total_files} />
            <StatCard label="Code reviews" value={data.stats.total_reviews} />
            <StatCard
              label="AI requests today"
              value={`${data.stats.ai_requests_today} / ${data.stats.ai_daily_quota}`}
            />
          </div>

          <div className="grid grid-cols-2 mb-16" style={{ alignItems: 'stretch' }}>
            <div className="card">
              <div className="card-title">Recent projects</div>
              <div className="card-subtitle">Your most recently updated work</div>
              {data.recent_projects.length === 0 ? (
                <EmptyState
                  icon="▤"
                  title="No projects yet"
                  description="Create your first project to start writing code."
                  action={<Link className="btn btn-primary mt-16" to="/projects">New project</Link>}
                />
              ) : (
                <div>
                  {data.recent_projects.map((p) => (
                    <Link
                      key={p.id}
                      to={`/projects/${p.id}`}
                      className="flex items-center justify-between"
                      style={{ padding: '10px 0', borderBottom: '1px solid var(--border-soft)', color: 'var(--text)' }}
                    >
                      <span>{p.name}</span>
                      <LanguagePill language={p.language} />
                    </Link>
                  ))}
                </div>
              )}
            </div>

            <div className="card">
              <div className="card-title">Recent AI code reviews</div>
              <div className="card-subtitle">Latest quality assessments</div>
              {data.recent_reviews.length === 0 ? (
                <EmptyState icon="✓" title="No reviews yet" description="Run an AI code review from any project's workspace." />
              ) : (
                data.recent_reviews.map((r) => (
                  <div key={r.id} className="flex items-center gap-16 mb-16">
                    <QualityGauge score={r.score} size={56} strokeWidth={5} label="" />
                    <div>
                      <div style={{ fontWeight: 600 }}>{r.project}</div>
                      <div className="text-muted text-sm">{r.summary}</div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="card">
            <div className="card-title">Recent activity</div>
            <div className="card-subtitle">Your latest actions across the platform</div>
            {data.recent_activity.length === 0 ? (
              <EmptyState icon="↻" title="No activity yet" />
            ) : (
              <div className="scroll-x">
                <table className="data-table">
                  <thead>
                    <tr><th>Action</th><th>Description</th><th>When</th></tr>
                  </thead>
                  <tbody>
                    {data.recent_activity.map((a) => (
                      <tr key={a.id}>
                        <td className="mono">{a.action}</td>
                        <td>{a.description}</td>
                        <td>{new Date(a.created_at).toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      ) : null}
    </AppLayout>
  );
}
