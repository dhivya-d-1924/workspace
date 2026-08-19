import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import AppLayout from '../components/AppLayout.jsx';
import { projectsApi } from '../api/endpoints';
import { EmptyState, LanguagePill } from '../components/Widgets.jsx';
import { extractErrorMessage } from '../api/client';

const LANGUAGES = ['python', 'javascript', 'typescript', 'java', 'c', 'cpp', 'csharp', 'go', 'ruby', 'php', 'sql', 'html', 'other'];

export default function Projects() {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [error, setError] = useState('');

  const load = () => {
    setLoading(true);
    projectsApi.list({ search }).then((res) => {
      setProjects(res.data.results ?? res.data);
    }).finally(() => setLoading(false));
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, []);

  const handleSearch = (e) => {
    e.preventDefault();
    load();
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this project? This cannot be undone.')) return;
    try {
      await projectsApi.remove(id);
      setProjects((prev) => prev.filter((p) => p.id !== id));
    } catch (err) {
      alert(extractErrorMessage(err));
    }
  };

  const handleDownload = async (id, name) => {
    const res = await projectsApi.download(id);
    const url = window.URL.createObjectURL(new Blob([res.data]));
    const link = document.createElement('a');
    link.href = url;
    link.download = `${name}.zip`;
    link.click();
    window.URL.revokeObjectURL(url);
  };

  return (
    <AppLayout title="Projects">
      <div className="flex items-center justify-between mb-16" style={{ flexWrap: 'wrap', gap: 12 }}>
        <form onSubmit={handleSearch} className="flex gap-8" style={{ flex: 1, minWidth: 220, maxWidth: 360 }}>
          <input
            className="input"
            placeholder="Search projects…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </form>
        <button className="btn btn-primary" onClick={() => { setError(''); setShowModal(true); }}>+ New project</button>
      </div>

      {loading ? (
        <div className="spinner" />
      ) : projects.length === 0 ? (
        <EmptyState
          icon="▤"
          title="No projects found"
          description="Create a project to start writing and analyzing code."
          action={<button className="btn btn-primary mt-16" onClick={() => setShowModal(true)}>+ New project</button>}
        />
      ) : (
        <div className="grid grid-cols-3">
          {projects.map((p) => (
            <div key={p.id} className="card">
              <div className="flex items-center justify-between mb-8">
                <Link to={`/projects/${p.id}`} className="card-title" style={{ marginBottom: 0 }}>{p.name}</Link>
                <LanguagePill language={p.language} />
              </div>
              <p className="text-muted text-sm mb-16">{p.description || 'No description.'}</p>
              <div className="flex items-center justify-between text-sm text-faint mb-16">
                <span>{p.file_count} file(s)</span>
                <span>{p.role === 'owner' ? 'Owner' : `Role: ${p.role || 'viewer'}`}</span>
              </div>
              <div className="flex gap-8">
                <Link to={`/projects/${p.id}`} className="btn btn-sm">Open</Link>
                <button className="btn btn-sm" onClick={() => handleDownload(p.id, p.name)}>Download</button>
                {p.role === 'owner' && (
                  <button className="btn btn-sm btn-danger" onClick={() => handleDelete(p.id)}>Delete</button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {showModal && (
        <NewProjectModal
          onClose={() => setShowModal(false)}
          onCreated={(project) => { setProjects((prev) => [project, ...prev]); setShowModal(false); }}
        />
      )}
    </AppLayout>
  );
}

function NewProjectModal({ onClose, onCreated }) {
  const [form, setForm] = useState({ name: '', description: '', language: 'python', visibility: 'private' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await projectsApi.create(form);
      onCreated(res.data);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <h3>New project</h3>
        {error && <div className="alert alert-error">{error}</div>}
        <form onSubmit={submit}>
          <div className="field">
            <label>Name</label>
            <input className="input" required autoFocus value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </div>
          <div className="field">
            <label>Description</label>
            <textarea className="textarea" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </div>
          <div className="grid grid-cols-2">
            <div className="field">
              <label>Primary language</label>
              <select className="select" value={form.language} onChange={(e) => setForm({ ...form, language: e.target.value })}>
                {LANGUAGES.map((l) => <option key={l} value={l}>{l}</option>)}
              </select>
            </div>
            <div className="field">
              <label>Visibility</label>
              <select className="select" value={form.visibility} onChange={(e) => setForm({ ...form, visibility: e.target.value })}>
                <option value="private">Private</option>
                <option value="shared">Shared</option>
                <option value="public">Public</option>
              </select>
            </div>
          </div>
          <div className="flex gap-8 mt-16">
            <button type="button" className="btn" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={loading}>{loading ? 'Creating…' : 'Create project'}</button>
          </div>
        </form>
      </div>
    </div>
  );
}
