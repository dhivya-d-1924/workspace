import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import AppLayout from '../components/AppLayout.jsx';
import FileTree from '../components/FileTree.jsx';
import CodeEditor from '../components/CodeEditor.jsx';
import AIPanel from '../components/AIPanel.jsx';
import { commentsApi, filesApi, projectsApi } from '../api/endpoints';
import { extractErrorMessage } from '../api/client';

export default function Workspace() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [project, setProject] = useState(null);
  const [files, setFiles] = useState([]);
  const [activeFile, setActiveFile] = useState(null);
  const [content, setContent] = useState('');
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [showShare, setShowShare] = useState(false);
  const [showComments, setShowComments] = useState(false);
  const [showVersions, setShowVersions] = useState(false);

  const loadProject = useCallback(() => {
    projectsApi.get(id).then((res) => {
      setProject(res.data);
      setFiles(res.data.files || []);
    }).catch((err) => setError(extractErrorMessage(err)));
  }, [id]);

  useEffect(() => { loadProject(); }, [loadProject]);

  const selectFile = async (file) => {
    const res = await filesApi.get(id, file.id);
    setActiveFile(res.data);
    setContent(res.data.content);
    setDirty(false);
  };

  const handleCreateFile = async (path) => {
    try {
      const language = guessLanguage(path);
      const res = await filesApi.create(id, { path, content: '', language });
      setFiles((prev) => [...prev, res.data]);
      selectFile(res.data);
    } catch (err) {
      alert(extractErrorMessage(err));
    }
  };

  const handleUpload = async (fileList) => {
    const formData = new FormData();
    Array.from(fileList).forEach((f) => formData.append('files', f));
    try {
      await filesApi.upload(id, formData);
      loadProject();
    } catch (err) {
      alert(extractErrorMessage(err));
    }
  };

  const handleDeleteFile = async (file) => {
    if (!window.confirm(`Delete ${file.path}?`)) return;
    await filesApi.remove(id, file.id);
    setFiles((prev) => prev.filter((f) => f.id !== file.id));
    if (activeFile?.id === file.id) {
      setActiveFile(null);
      setContent('');
    }
  };

  const handleSave = async () => {
    if (!activeFile) return;
    setSaving(true);
    try {
      const res = await filesApi.update(id, activeFile.id, { content });
      setActiveFile(res.data);
      setDirty(false);
      setFiles((prev) => prev.map((f) => (f.id === res.data.id ? { ...f, size_bytes: res.data.size_bytes } : f)));
    } catch (err) {
      alert(extractErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const handleDownloadFile = async () => {
    if (!activeFile) return;
    const res = await filesApi.download(id, activeFile.id);
    const url = window.URL.createObjectURL(new Blob([res.data]));
    const link = document.createElement('a');
    link.href = url;
    link.download = activeFile.path.split('/').pop();
    link.click();
    window.URL.revokeObjectURL(url);
  };

  if (error) {
    return (
      <AppLayout title="Workspace">
        <div className="alert alert-error">{error}</div>
        <button className="btn" onClick={() => navigate('/projects')}>Back to projects</button>
      </AppLayout>
    );
  }

  if (!project) {
    return (
      <AppLayout title="Workspace">
        <div className="spinner" />
      </AppLayout>
    );
  }

  return (
    <AppLayout title={project.name}>
      <div className="card mb-16">
        <div className="flex items-center justify-between" style={{ flexWrap: 'wrap', gap: 12 }}>
          <div>
            <div className="card-title" style={{ marginBottom: 2 }}>{project.name}</div>
            <div className="text-muted text-sm">{project.description || 'No description'}</div>
          </div>
          <div className="flex gap-8">
            {project.role === 'owner' && (
              <button className="btn btn-sm" onClick={() => setShowShare(true)}>Share</button>
            )}
            <button className="btn btn-sm" onClick={() => setShowComments(true)}>Comments</button>
          </div>
        </div>
      </div>

      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div className="workspace-shell">
          <FileTree
            files={files}
            activeFileId={activeFile?.id}
            onSelect={selectFile}
            onCreate={handleCreateFile}
            onUpload={handleUpload}
            onDelete={handleDeleteFile}
          />

          <div className="editor-col">
            <div className="editor-tabbar">
              <div className="flex items-center gap-8">
                {activeFile ? (
                  <>
                    <span className="mono text-sm">{activeFile.path}</span>
                    {dirty && <span className="badge badge-medium">unsaved</span>}
                  </>
                ) : (
                  <span className="text-muted text-sm">No file open</span>
                )}
              </div>
              {activeFile && (
                <div className="flex gap-8">
                  <button className="btn btn-sm" onClick={() => setShowVersions(true)}>History</button>
                  <button className="btn btn-sm" onClick={handleDownloadFile}>Download</button>
                  <button className="btn btn-sm btn-primary" onClick={handleSave} disabled={!dirty || saving}>
                    {saving ? 'Saving…' : 'Save'}
                  </button>
                </div>
              )}
            </div>
            <CodeEditor
              value={content}
              onChange={(v) => { setContent(v); setDirty(true); }}
              readOnly={!activeFile}
            />
          </div>

          <AIPanel
            code={content}
            language={activeFile?.language || project.language}
            projectId={Number(id)}
            fileId={activeFile?.id}
            onApplyFix={(fixedCode) => { setContent(fixedCode); setDirty(true); }}
          />
        </div>
      </div>

      {showShare && <ShareModal projectId={id} onClose={() => setShowShare(false)} />}
      {showComments && <CommentsModal projectId={id} onClose={() => setShowComments(false)} />}
      {showVersions && activeFile && (
        <VersionsModal
          projectId={id}
          file={activeFile}
          onClose={() => setShowVersions(false)}
          onRestore={(newContent) => { setContent(newContent); setDirty(false); setShowVersions(false); }}
        />
      )}
    </AppLayout>
  );
}

function guessLanguage(path) {
  const ext = path.split('.').pop().toLowerCase();
  const map = {
    py: 'python', js: 'javascript', jsx: 'javascript', ts: 'typescript', tsx: 'typescript',
    java: 'java', c: 'c', cpp: 'cpp', cs: 'csharp', go: 'go', rb: 'ruby', php: 'php',
    sql: 'sql', html: 'html', css: 'html',
  };
  return map[ext] || 'other';
}

function ShareModal({ projectId, onClose }) {
  const [username, setUsername] = useState('');
  const [role, setRole] = useState('viewer');
  const [members, setMembers] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    projectsApi.members(projectId).then((res) => setMembers(res.data));
  }, [projectId]);

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await projectsApi.share(projectId, { user: username, role });
      setMembers((prev) => [...prev.filter((m) => m.id !== res.data.id), res.data]);
      setUsername('');
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const removeMember = async (memberId) => {
    await projectsApi.removeMember(projectId, memberId);
    setMembers((prev) => prev.filter((m) => m.id !== memberId));
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <h3>Share project</h3>
        {error && <div className="alert alert-error">{error}</div>}
        <form onSubmit={submit} className="flex gap-8" style={{ alignItems: 'flex-end' }}>
          <div className="field" style={{ flex: 1, marginBottom: 0 }}>
            <label>Username or email</label>
            <input className="input" required value={username} onChange={(e) => setUsername(e.target.value)} />
          </div>
          <div className="field" style={{ marginBottom: 0 }}>
            <label>Role</label>
            <select className="select" value={role} onChange={(e) => setRole(e.target.value)}>
              <option value="viewer">Viewer</option>
              <option value="editor">Editor</option>
              <option value="admin">Admin</option>
            </select>
          </div>
          <button className="btn btn-primary" disabled={loading}>Add</button>
        </form>

        <div className="mt-16">
          {members.length === 0 ? (
            <p className="text-muted text-sm">No collaborators yet.</p>
          ) : (
            members.map((m) => (
              <div key={m.id} className="flex items-center justify-between mb-8">
                <span className="text-sm">{m.username} <span className="text-faint">· {m.role}</span></span>
                <button className="btn btn-sm btn-ghost" onClick={() => removeMember(m.id)}>Remove</button>
              </div>
            ))
          )}
        </div>
        <button className="btn btn-block mt-16" onClick={onClose}>Close</button>
      </div>
    </div>
  );
}

function CommentsModal({ projectId, onClose }) {
  const [comments, setComments] = useState([]);
  const [body, setBody] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    commentsApi.list(projectId).then((res) => setComments(res.data)).finally(() => setLoading(false));
  }, [projectId]);

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    if (!body.trim()) return;
    try {
      const res = await commentsApi.create(projectId, { body });
      setComments((prev) => [...prev, res.data]);
      setBody('');
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" style={{ maxWidth: 480 }} onClick={(e) => e.stopPropagation()}>
        <h3>Comments</h3>
        {error && <div className="alert alert-error">{error}</div>}
        <div style={{ maxHeight: 280, overflowY: 'auto' }} className="mb-16">
          {loading ? (
            <div className="spinner" />
          ) : comments.length === 0 ? (
            <p className="text-muted text-sm">No comments yet — start the discussion.</p>
          ) : (
            comments.map((c) => (
              <div key={c.id} className="mb-16">
                <div className="text-sm" style={{ fontWeight: 600 }}>{c.author_username}</div>
                <div className="text-sm text-muted">{c.body}</div>
                <div className="text-faint text-sm">{new Date(c.created_at).toLocaleString()}</div>
              </div>
            ))
          )}
        </div>
        <form onSubmit={submit} className="flex gap-8">
          <input className="input" placeholder="Add a comment…" value={body} onChange={(e) => setBody(e.target.value)} />
          <button className="btn btn-primary">Post</button>
        </form>
        <button className="btn btn-block mt-16" onClick={onClose}>Close</button>
      </div>
    </div>
  );
}

function VersionsModal({ projectId, file, onClose, onRestore }) {
  const [versions, setVersions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    filesApi.versions(projectId, file.id).then((res) => setVersions(res.data)).finally(() => setLoading(false));
  }, [projectId, file.id]);

  const restore = async (versionNumber) => {
    const res = await filesApi.restore(projectId, file.id, versionNumber);
    onRestore(res.data.content);
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" style={{ maxWidth: 480 }} onClick={(e) => e.stopPropagation()}>
        <h3>Version history — {file.path}</h3>
        {loading ? (
          <div className="spinner" />
        ) : versions.length === 0 ? (
          <p className="text-muted text-sm">No versions recorded yet.</p>
        ) : (
          <div style={{ maxHeight: 320, overflowY: 'auto' }}>
            {versions.map((v) => (
              <div key={v.id} className="flex items-center justify-between mb-8">
                <div>
                  <div className="text-sm" style={{ fontWeight: 600 }}>v{v.version_number} — {v.change_summary}</div>
                  <div className="text-faint text-sm">{v.edited_by_username} · {new Date(v.created_at).toLocaleString()}</div>
                </div>
                <button className="btn btn-sm" onClick={() => restore(v.version_number)}>Restore</button>
              </div>
            ))}
          </div>
        )}
        <button className="btn btn-block mt-16" onClick={onClose}>Close</button>
      </div>
    </div>
  );
}
