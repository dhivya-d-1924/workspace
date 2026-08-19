import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import { extractErrorMessage } from '../api/client';

const initialForm = {
  username: '', email: '', first_name: '', last_name: '', password: '', password_confirm: '',
};

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState(initialForm);
  const [errors, setErrors] = useState({});
  const [serverError, setServerError] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const update = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  const validate = () => {
    const next = {};
    if (form.username.trim().length < 3) next.username = 'At least 3 characters.';
    if (!/^\S+@\S+\.\S+$/.test(form.email)) next.email = 'Enter a valid email address.';
    if (form.password.length < 8) next.password = 'At least 8 characters.';
    if (form.password !== form.password_confirm) next.password_confirm = 'Passwords do not match.';
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setServerError('');
    if (!validate()) return;
    setLoading(true);
    try {
      await register(form);
      setSuccess(true);
      setTimeout(() => navigate('/login'), 1200);
    } catch (err) {
      setServerError(extractErrorMessage(err, 'Registration failed. Please check your details.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-shell">
      <div className="auth-visual">
        <h1 style={{ fontSize: 34, maxWidth: 480 }}>One workspace for every step of writing code.</h1>
        <p className="text-muted" style={{ maxWidth: 460, marginBottom: 28 }}>
          Projects, files, version history, and fourteen AI-assisted code
          features — all in one place.
        </p>
        <pre>
{`class Workspace:
    features = [
`}<span className="accent-tok">        "explain_code", "find_bugs", "fix_bugs",
</span>{`        "optimize_code", "generate_code",
`}<span className="accent2-tok">        "generate_tests", "code_review",
</span>{`    ]
`}<span className="muted-tok"># ...and 7 more</span>
        </pre>
      </div>
      <div className="auth-form-side">
        <div className="auth-card">
          <h2>Create your account</h2>
          <p className="text-muted mb-16">Start writing and reviewing code with AI assistance.</p>

          {serverError && <div className="alert alert-error">{serverError}</div>}
          {success && <div className="alert alert-success">Account created! Redirecting to login…</div>}

          <form onSubmit={handleSubmit}>
            <div className="grid grid-cols-2 gap-12">
              <div className="field">
                <label htmlFor="first_name">First name</label>
                <input id="first_name" className="input" value={form.first_name} onChange={update('first_name')} />
              </div>
              <div className="field">
                <label htmlFor="last_name">Last name</label>
                <input id="last_name" className="input" value={form.last_name} onChange={update('last_name')} />
              </div>
            </div>
            <div className="field">
              <label htmlFor="username">Username</label>
              <input id="username" className="input" required value={form.username} onChange={update('username')} />
              {errors.username && <div className="field-error">{errors.username}</div>}
            </div>
            <div className="field">
              <label htmlFor="email">Email</label>
              <input id="email" type="email" className="input" required value={form.email} onChange={update('email')} />
              {errors.email && <div className="field-error">{errors.email}</div>}
            </div>
            <div className="field">
              <label htmlFor="password">Password</label>
              <input id="password" type="password" className="input" required value={form.password} onChange={update('password')} />
              {errors.password && <div className="field-error">{errors.password}</div>}
              <div className="field-hint">At least 8 characters, not too common, not all-numeric.</div>
            </div>
            <div className="field">
              <label htmlFor="password_confirm">Confirm password</label>
              <input id="password_confirm" type="password" className="input" required value={form.password_confirm} onChange={update('password_confirm')} />
              {errors.password_confirm && <div className="field-error">{errors.password_confirm}</div>}
            </div>
            <button className="btn btn-primary btn-block" type="submit" disabled={loading}>
              {loading ? 'Creating account…' : 'Create account'}
            </button>
          </form>

          <p className="text-muted text-sm mt-16">
            Already have an account? <Link to="/login">Log in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
