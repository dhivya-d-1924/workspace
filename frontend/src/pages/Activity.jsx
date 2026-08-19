import { useEffect, useState } from 'react';
import AppLayout from '../components/AppLayout.jsx';
import { authApi } from '../api/endpoints';
import { EmptyState } from '../components/Widgets.jsx';

export default function Activity() {
  const [activity, setActivity] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    authApi.activity().then((res) => setActivity(res.data.results ?? res.data)).finally(() => setLoading(false));
  }, []);

  return (
    <AppLayout title="Activity history">
      <p className="text-muted mb-16">A full log of your actions across the platform.</p>
      <div className="card">
        {loading ? (
          <div className="spinner" />
        ) : activity.length === 0 ? (
          <EmptyState icon="↻" title="No activity yet" />
        ) : (
          <div className="scroll-x">
            <table className="data-table">
              <thead><tr><th>Action</th><th>Description</th><th>When</th></tr></thead>
              <tbody>
                {activity.map((a) => (
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
    </AppLayout>
  );
}
