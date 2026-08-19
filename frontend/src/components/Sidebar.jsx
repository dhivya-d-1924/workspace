import { NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';

const NAV_ITEMS = [
  { to: '/dashboard', label: 'Dashboard', icon: '◧' },
  { to: '/projects', label: 'Projects', icon: '▤' },
  { to: '/reviews', label: 'Review history', icon: '✓' },
  { to: '/activity', label: 'Activity', icon: '↻' },
  { to: '/profile', label: 'Profile', icon: '◍' },
];

export default function Sidebar({ open, onClose }) {
  const { user } = useAuth();

  return (
    <>
      {open && <div className="sidebar-scrim" onClick={onClose} />}
      <aside className={`sidebar ${open ? 'open' : ''}`}>
        <div className="sidebar-brand">
          <div className="sidebar-brand-mark">CI</div>
          <div className="sidebar-brand-name">
            CodeIntel
            <span>Dev Workspace</span>
          </div>
        </div>

        <nav className="sidebar-nav">
          <div className="sidebar-section-label">Workspace</div>
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
              onClick={onClose}
            >
              <span className="icon">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}

          {user?.role === 'admin' && (
            <>
              <div className="sidebar-section-label">Administration</div>
              <NavLink
                to="/admin"
                className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
                onClick={onClose}
              >
                <span className="icon">⚙</span>
                Admin panel
              </NavLink>
            </>
          )}
        </nav>

        <div className="sidebar-footer text-faint text-sm">
          v1.0 · offline AI engine
        </div>
      </aside>
    </>
  );
}
