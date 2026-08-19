import { useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { useAuth } from '../context/AuthContext.jsx';

export default function Topbar({ title, onMenuClick }) {
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const navigate = useNavigate();

  const initials = (user?.username || '?').slice(0, 2).toUpperCase();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <header className="topbar">
      <div className="flex items-center gap-12">
        <button className="btn btn-ghost sidebar-toggle" onClick={onMenuClick} aria-label="Open menu">
          ☰
        </button>
        <h1 className="topbar-title">{title}</h1>
      </div>

      <div style={{ position: 'relative' }}>
        <div className="user-chip" onClick={() => setMenuOpen((v) => !v)}>
          <div className="user-avatar">{initials}</div>
          <span>{user?.username}</span>
        </div>
        {menuOpen && (
          <div
            className="card"
            style={{ position: 'absolute', right: 0, top: '44px', minWidth: 180, padding: 8, zIndex: 30 }}
            onMouseLeave={() => setMenuOpen(false)}
          >
            <button className="btn btn-ghost btn-block" style={{ justifyContent: 'flex-start' }} onClick={() => { setMenuOpen(false); navigate('/profile'); }}>
              Profile settings
            </button>
            <button className="btn btn-ghost btn-block" style={{ justifyContent: 'flex-start', color: 'var(--danger)' }} onClick={handleLogout}>
              Log out
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
