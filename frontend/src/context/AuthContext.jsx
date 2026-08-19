import { createContext, useContext, useEffect, useState } from 'react';
import { authApi } from '../api/endpoints';
import { clearTokens, getTokens, setTokens } from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('cw_user') || 'null');
    } catch {
      return null;
    }
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const tokens = getTokens();
    if (!tokens?.access) {
      setLoading(false);
      return;
    }
    authApi
      .profile()
      .then((res) => {
        setUser(res.data);
        localStorage.setItem('cw_user', JSON.stringify(res.data));
      })
      .catch(() => {
        clearTokens();
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const login = async (username, password) => {
    const res = await authApi.login({ username, password });
    setTokens({ access: res.data.access, refresh: res.data.refresh });
    setUser(res.data.user);
    localStorage.setItem('cw_user', JSON.stringify(res.data.user));
    return res.data.user;
  };

  const register = async (payload) => {
    const res = await authApi.register(payload);
    return res.data;
  };

  const logout = async () => {
    const tokens = getTokens();
    try {
      if (tokens?.refresh) await authApi.logout(tokens.refresh);
    } catch {
      /* ignore network errors on logout */
    }
    clearTokens();
    setUser(null);
  };

  const refreshProfile = async () => {
    const res = await authApi.profile();
    setUser(res.data);
    localStorage.setItem('cw_user', JSON.stringify(res.data));
    return res.data;
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refreshProfile, setUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
