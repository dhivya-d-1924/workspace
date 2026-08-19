import { useRef, useState } from 'react';

export default function FileTree({ files, activeFileId, onSelect, onCreate, onUpload, onDelete }) {
  const [creating, setCreating] = useState(false);
  const [newPath, setNewPath] = useState('');
  const fileInputRef = useRef(null);

  const submitCreate = (e) => {
    e.preventDefault();
    if (!newPath.trim()) return;
    onCreate(newPath.trim());
    setNewPath('');
    setCreating(false);
  };

  return (
    <div className="file-tree-col">
      <div className="file-tree-header">
        <span className="text-sm" style={{ fontWeight: 700 }}>Files</span>
        <div className="flex gap-8">
          <button className="btn btn-ghost btn-sm" title="New file" onClick={() => setCreating((v) => !v)}>+</button>
          <button className="btn btn-ghost btn-sm" title="Upload files" onClick={() => fileInputRef.current?.click()}>↑</button>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            style={{ display: 'none' }}
            onChange={(e) => {
              if (e.target.files?.length) onUpload(e.target.files);
              e.target.value = '';
            }}
          />
        </div>
      </div>

      {creating && (
        <form onSubmit={submitCreate} style={{ padding: '8px 16px' }}>
          <input
            className="input"
            style={{ fontSize: 12 }}
            autoFocus
            placeholder="path/to/file.py"
            value={newPath}
            onChange={(e) => setNewPath(e.target.value)}
            onBlur={() => !newPath && setCreating(false)}
          />
        </form>
      )}

      {files.length === 0 ? (
        <div className="text-muted text-sm" style={{ padding: '16px' }}>No files yet.</div>
      ) : (
        files.map((f) => (
          <div
            key={f.id}
            className={`file-row ${f.id === activeFileId ? 'active' : ''}`}
            onClick={() => onSelect(f)}
          >
            <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis' }}>{f.path}</span>
            <span
              className="text-faint"
              style={{ fontSize: 14 }}
              onClick={(e) => { e.stopPropagation(); onDelete(f); }}
              title="Delete file"
            >
              ×
            </span>
          </div>
        ))
      )}
    </div>
  );
}
