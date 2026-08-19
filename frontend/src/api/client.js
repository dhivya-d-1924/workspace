import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

const client = axios.create({ baseURL: API_BASE });

function getTokens() {
  try {
    return JSON.parse(localStorage.getItem('cw_tokens') || 'null');
  } catch {
    return null;
  }
}

function setTokens(tokens) {
  localStorage.setItem('cw_tokens', JSON.stringify(tokens));
}

function clearTokens() {
  localStorage.removeItem('cw_tokens');
  localStorage.removeItem('cw_user');
}

client.interceptors.request.use((config) => {
  const tokens = getTokens();
  if (tokens?.access) {
    config.headers.Authorization = `Bearer ${tokens.access}`;
  }
  return config;
});

let refreshPromise = null;

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      const tokens = getTokens();
      if (!tokens?.refresh) {
        clearTokens();
        window.location.href = '/login';
        return Promise.reject(error);
      }
      try {
        if (!refreshPromise) {
          refreshPromise = axios
            .post(`${API_BASE}/auth/token/refresh/`, { refresh: tokens.refresh })
            .then((res) => {
              setTokens({ ...tokens, access: res.data.access });
              return res.data.access;
            })
            .finally(() => {
              refreshPromise = null;
            });
        }
        const newAccess = await refreshPromise;
        original.headers.Authorization = `Bearer ${newAccess}`;
        return client(original);
      } catch (refreshError) {
        clearTokens();
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }
    return Promise.reject(error);
  }
);

export function extractErrorMessage(error, fallback = 'Something went wrong. Please try again.') {
  const data = error?.response?.data;
  if (!data) return error?.message || fallback;
  if (data.error?.message) {
    const details = data.error.details;
    if (details && typeof details === 'object' && !Array.isArray(details)) {
      const firstKey = Object.keys(details)[0];
      if (firstKey && Array.isArray(details[firstKey])) {
        return `${firstKey}: ${details[firstKey][0]}`;
      }
    }
    return data.error.message;
  }
  if (data.message) return data.message;
  if (typeof data === 'string') return data;
  return fallback;
}

export { client, getTokens, setTokens, clearTokens };
export default client;
