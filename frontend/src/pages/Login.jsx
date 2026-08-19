import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import { extractErrorMessage } from '../api/client';

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ username: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(form.username, form.password);
      navigate('/dashboard');
    } catch (err) {
      setError(extractErrorMessage(err, 'Invalid username or password.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-shell">
      <div className="auth-visual">
        <h1 style={{ fontSize: 34, maxWidth: 480 }}>Write, review and ship code — with an AI pair sitting in the margin.</h1>
        <p className="text-muted" style={{ maxWidth: 460, marginBottom: 28 }}>
          Explain, debug, optimize, document and test your code, and get a real
          quality score on every review.
        </p>
        <pre>
{`$ curl -X POST /api/ai/find-bugs/ \\
    -d '{"code": "...", "language": "python"}'

`}<span className="accent-tok">{`{`}</span>{`
  "bugs": [
    { "line": 3, "type": "`}<span className="accent2-tok">mutable_default_arg</span>{`",
      "severity": "high" }
  ],
  "total": 1
`}<span className="accent-tok">{`}`}</span>
        </pre>
      </div>
      <div className="auth-form-side">
        <div className="auth-card">
          <h2>Welcome back</h2>
          <p className="text-muted mb-16">Log in to your developer workspace.</p>

          {error && <div className="alert alert-error">{error}</div>}

          <form onSubmit={handleSubmit}>
            <div className="field">
              <label htmlFor="username">Username</label>
              <input
                id="username"
                className="input"
                required
                autoFocus
                value={form.username}
                onChange={(e) => setForm({ ...form, username: e.target.value })}
              />
            </div>
            <div className="field">
              <label htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                className="input"
                required
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
              />
            </div>
            <button className="btn btn-primary btn-block" type="submit" disabled={loading}>
              {loading ? <Spinner /> : 'Log in'}
            </button>
          </form>

          <p className="text-muted text-sm mt-16">
            Don't have an account? <Link to="/register">Create one</Link>
          </p>
        </div>
      </div>
    </div>
  );
}

function Spinner() {
  return <span className="spinner" style={{ borderTopColor: '#06211e' }} />;
}
