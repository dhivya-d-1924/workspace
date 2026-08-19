import { useState } from 'react';
import AppLayout from '../components/AppLayout.jsx';
import { useAuth } from '../context/AuthContext.jsx';
import { authApi } from '../api/endpoints';
import { extractErrorMessage } from '../api/client';

export default function Profile() {
  const { user, setUser } = useAuth();
  const [form, setForm] = useState({
    first_name: user?.first_name || '', last_name: user?.last_name || '',
    bio: user?.bio || '', job_title: user?.job_title || '', preferred_language: user?.preferred_language || 'python',
  });
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const [pwForm, setPwForm] = useState({ old_password: '', new_password: '' });
  const [pwError, setPwError] = useState('');
  const [pwSuccess, setPwSuccess] = useState(false);
  const [pwSaving, setPwSaving] = useState(false);

  const submitProfile = async (e) => {
    e.preventDefault();
    setError(''); setSaved(false); setSaving(true);
    try {
      const res = await authApi.updateProfile(form);
      setUser(res.data);
      localStorage.setItem('cw_user', JSON.stringify(res.data));
      setSaved(true);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const submitPassword = async (e) => {
    e.preventDefault();
    setPwError(''); setPwSuccess(false); setPwSaving(true);
    try {
      await authApi.changePassword(pwForm);
      setPwSuccess(true);
      setPwForm({ old_password: '', new_password: '' });
    } catch (err) {
      setPwError(extractErrorMessage(err));
    } finally {
      setPwSaving(false);
    }
  };

  return (
    <AppLayout title="Profile">
      <div className="grid grid-cols-2">
        <div className="card">
          <div className="card-title">Profile details</div>
          <div className="card-subtitle">Update your public information</div>
          {error && <div className="alert alert-error">{error}</div>}
          {saved && <div className="alert alert-success">Profile updated.</div>}
          <form onSubmit={submitProfile}>
            <div className="grid grid-cols-2 gap-12">
              <div className="field">
                <label>First name</label>
                <input className="input" value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} />
              </div>
              <div className="field">
                <label>Last name</label>
                <input className="input" value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} />
              </div>
            </div>
            <div className="field">
              <label>Job title</label>
              <input className="input" value={form.job_title} onChange={(e) => setForm({ ...form, job_title: e.target.value })} />
            </div>
            <div className="field">
              <label>Bio</label>
              <textarea className="textarea" value={form.bio} onChange={(e) => setForm({ ...form, bio: e.target.value })} />
            </div>
            <div className="field">
              <label>Preferred language</label>
              <select className="select" value={form.preferred_language} onChange={(e) => setForm({ ...form, preferred_language: e.target.value })}>
                {['python', 'javascript', 'typescript', 'java', 'go', 'ruby', 'php'].map((l) => <option key={l} value={l}>{l}</option>)}
              </select>
            </div>
            <button className="btn btn-primary" disabled={saving}>{saving ? 'Saving…' : 'Save changes'}</button>
          </form>
        </div>

        <div className="card">
          <div className="card-title">Change password</div>
          <div className="card-subtitle">Keep your account secure</div>
          {pwError && <div className="alert alert-error">{pwError}</div>}
          {pwSuccess && <div className="alert alert-success">Password updated.</div>}
          <form onSubmit={submitPassword}>
            <div className="field">
              <label>Current password</label>
              <input type="password" className="input" required value={pwForm.old_password} onChange={(e) => setPwForm({ ...pwForm, old_password: e.target.value })} />
            </div>
            <div className="field">
              <label>New password</label>
              <input type="password" className="input" required value={pwForm.new_password} onChange={(e) => setPwForm({ ...pwForm, new_password: e.target.value })} />
            </div>
            <button className="btn btn-primary" disabled={pwSaving}>{pwSaving ? 'Updating…' : 'Update password'}</button>
          </form>
        </div>
      </div>
    </AppLayout>
  );
}
