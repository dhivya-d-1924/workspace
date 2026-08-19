import { useEffect, useState } from 'react';
import AppLayout from '../components/AppLayout.jsx';
import { adminApi } from '../api/endpoints';
import { StatCard } from '../components/Widgets.jsx';
import { extractErrorMessage } from '../api/client';

const TABS = ['overview', 'users', 'projects', 'ai-usage', 'reviews', 'settings'];

export default function AdminPanel() {
  const [tab, setTab] = useState('overview');

  return (
    <AppLayout title="Admin panel">
      <div className="flex gap-8 mb-16" style={{ flexWrap: 'wrap' }}>
        {TABS.map((t) => (
          <button key={t} className={`btn btn-sm ${tab === t ? 'btn-primary' : ''}`} onClick={() => setTab(t)}>
            {t.replace('-', ' ')}
          </button>
        ))}
      </div>

      {tab === 'overview' && <OverviewTab />}
      {tab === 'users' && <UsersTab />}
      {tab === 'projects' && <ProjectsTab />}
      {tab === 'ai-usage' && <AIUsageTab />}
      {tab === 'reviews' && <ReviewStatsTab />}
      {tab === 'settings' && <SettingsTab />}
    </AppLayout>
  );
}

function OverviewTab() {
  const [data, setData] = useState(null);
  useEffect(() => { adminApi.overview().then((res) => setData(res.data)); }, []);
  if (!data) return <div className="spinner" />;
  return (
    <div className="grid grid-cols-4">
      <StatCard label="Total users" value={data.total_users} delta={`${data.active_users_7d} active in last 7d`} />
      <StatCard label="Total projects" value={data.total_projects} />
      <StatCard label="Total files" value={data.total_files} />
      <StatCard label="Total AI requests" value={data.total_ai_requests} delta={`${data.requests_today} today`} />
      <StatCard label="Total reviews" value={data.total_reviews} />
    </div>
  );
}

function UsersTab() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = () => {
    setLoading(true);
    adminApi.users().then((res) => setUsers(res.data.results ?? res.data)).finally(() => setLoading(false));
  };
  useEffect(load, []);

  const toggleActive = async (u) => {
    try {
      const res = await adminApi.updateUser(u.id, { is_active: !u.is_active });
      setUsers((prev) => prev.map((x) => (x.id === u.id ? { ...x, is_active: res.data.is_active } : x)));
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  };

  const changeRole = async (u, role) => {
    try {
      const res = await adminApi.updateUser(u.id, { role });
      setUsers((prev) => prev.map((x) => (x.id === u.id ? { ...x, role: res.data.role } : x)));
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  };

  if (loading) return <div className="spinner" />;

  return (
    <div className="card">
      {error && <div className="alert alert-error">{error}</div>}
      <div className="scroll-x">
        <table className="data-table">
          <thead><tr><th>Username</th><th>Email</th><th>Role</th><th>Projects</th><th>Status</th><th>Actions</th></tr></thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td>{u.username}</td>
                <td>{u.email}</td>
                <td>
                  <select className="select" style={{ padding: 4 }} value={u.role} onChange={(e) => changeRole(u, e.target.value)}>
                    <option value="developer">developer</option>
                    <option value="admin">admin</option>
                  </select>
                </td>
                <td>{u.project_count}</td>
                <td>{u.is_active ? <span className="badge badge-success">active</span> : <span className="badge badge-critical">disabled</span>}</td>
                <td><button className="btn btn-sm" onClick={() => toggleActive(u)}>{u.is_active ? 'Deactivate' : 'Activate'}</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ProjectsTab() {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    adminApi.projects().then((res) => setProjects(res.data.results ?? res.data)).finally(() => setLoading(false));
  };
  useEffect(load, []);

  const doAction = async (id, action) => {
    await adminApi.projectAction(id, action);
    load();
  };

  if (loading) return <div className="spinner" />;

  return (
    <div className="card">
      <div className="scroll-x">
        <table className="data-table">
          <thead><tr><th>Name</th><th>Owner</th><th>Language</th><th>Files</th><th>Members</th><th>Status</th><th>Actions</th></tr></thead>
          <tbody>
            {projects.map((p) => (
              <tr key={p.id}>
                <td>{p.name}</td>
                <td>{p.owner}</td>
                <td className="mono">{p.language}</td>
                <td>{p.file_count}</td>
                <td>{p.member_count}</td>
                <td>{p.is_archived ? <span className="badge badge-medium">archived</span> : <span className="badge badge-success">active</span>}</td>
                <td className="flex gap-8">
                  <button className="btn btn-sm" onClick={() => doAction(p.id, p.is_archived ? 'unarchive' : 'archive')}>
                    {p.is_archived ? 'Unarchive' : 'Archive'}
                  </button>
                  <button className="btn btn-sm btn-danger" onClick={() => { if (window.confirm('Delete project?')) doAction(p.id, 'delete'); }}>Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function AIUsageTab() {
  const [data, setData] = useState(null);
  useEffect(() => { adminApi.aiUsageStats(30).then((res) => setData(res.data)); }, []);
  if (!data) return <div className="spinner" />;

  return (
    <div>
      <div className="grid grid-cols-3 mb-16">
        <StatCard label="Total requests (30d)" value={data.total_requests} />
        <StatCard label="Avg. duration" value={`${data.average_duration_ms} ms`} />
        <StatCard label="Distinct features used" value={data.by_feature.length} />
      </div>
      <div className="grid grid-cols-2">
        <div className="card">
          <div className="card-title">Requests by feature</div>
          {data.by_feature.map((f) => (
            <div key={f.feature} className="flex items-center justify-between mb-8 text-sm">
              <span className="mono">{f.feature}</span><strong>{f.count}</strong>
            </div>
          ))}
        </div>
        <div className="card">
          <div className="card-title">Top users</div>
          {data.top_users.map((u) => (
            <div key={u.user__username} className="flex items-center justify-between mb-8 text-sm">
              <span>{u.user__username}</span><strong>{u.count}</strong>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function ReviewStatsTab() {
  const [data, setData] = useState(null);
  useEffect(() => { adminApi.reviewStats().then((res) => setData(res.data)); }, []);
  if (!data) return <div className="spinner" />;

  return (
    <div>
      <div className="grid grid-cols-3 mb-16">
        <StatCard label="Total reviews" value={data.total_reviews} />
        <StatCard label="Avg. quality score" value={data.average_quality_score} />
        <StatCard label="Avg. complexity" value={data.average_complexity} />
      </div>
      <div className="card">
        <div className="card-title">Grade distribution</div>
        <div className="grid grid-cols-4">
          {Object.entries(data.grade_distribution).map(([grade, count]) => (
            <div key={grade} className="stat-card">
              <div className="stat-label">Grade {grade}</div>
              <div className="stat-value">{count}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function SettingsTab() {
  const [settings, setSettings] = useState([]);
  const [form, setForm] = useState({ key: '', value: '', description: '' });
  const [error, setError] = useState('');

  const load = () => { adminApi.settings().then((res) => setSettings(res.data.settings)); };
  useEffect(load, []);

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      let parsedValue;
      try { parsedValue = JSON.parse(form.value); } catch { parsedValue = form.value; }
      await adminApi.setSetting({ key: form.key, value: parsedValue, description: form.description });
      setForm({ key: '', value: '', description: '' });
      load();
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  };

  return (
    <div className="grid grid-cols-2">
      <div className="card">
        <div className="card-title">System settings</div>
        {settings.length === 0 ? <p className="text-muted text-sm">No settings configured yet.</p> : (
          settings.map((s) => (
            <div key={s.id} className="mb-16">
              <div className="mono text-sm" style={{ fontWeight: 600 }}>{s.key}</div>
              <pre style={{ margin: '4px 0' }}>{JSON.stringify(s.value)}</pre>
              <div className="text-faint text-sm">{s.description}</div>
            </div>
          ))
        )}
      </div>
      <div className="card">
        <div className="card-title">Add / update setting</div>
        {error && <div className="alert alert-error">{error}</div>}
        <form onSubmit={submit}>
          <div className="field">
            <label>Key</label>
            <input className="input" required value={form.key} onChange={(e) => setForm({ ...form, key: e.target.value })} />
          </div>
          <div className="field">
            <label>Value (JSON or plain text)</label>
            <input className="input" required value={form.value} onChange={(e) => setForm({ ...form, value: e.target.value })} />
          </div>
          <div className="field">
            <label>Description</label>
            <input className="input" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </div>
          <button className="btn btn-primary">Save setting</button>
        </form>
      </div>
    </div>
  );
}
