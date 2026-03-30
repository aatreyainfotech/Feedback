import axios from 'axios';

const BACKEND_OVERRIDE_KEY = 'backend_url';
const MOBILE_LAN_FALLBACK = 'https://aatreyainfo-feedback-fefbeqcve3dahrg2.centralindia-01.azurewebsites.net';

const normalizeUrl = (url) => (url || '').trim().replace(/\/$/, '');

const getStoredBackendUrl = () => {
  try {
    return normalizeUrl(localStorage.getItem(BACKEND_OVERRIDE_KEY));
  } catch {
    return '';
  }
};

const getRuntimeBackendUrl = () => {
  const host = window.location.hostname || 'localhost';
  // In WebView / mobile localhost refers to the phone itself; prefer LAN fallback.
  if (host === 'localhost' || host === '127.0.0.1') {
    return MOBILE_LAN_FALLBACK;
  }
  return `http://${host}:8000`;
};

const envBackendUrl = normalizeUrl(process.env.REACT_APP_BACKEND_URL);
const storedBackendUrl = getStoredBackendUrl();
const runtimeBackendUrl = getRuntimeBackendUrl();
const isMobileWebView = () => {
  const host = window.location.hostname || 'localhost';
  return host === 'localhost' || host === '127.0.0.1';
};

const isHttpsUrl = (url) => (url || '').startsWith('https://');

// Prefer env URL in production/mobile to avoid stale localStorage overrides.
const BACKEND_URL = isMobileWebView()
  ? (envBackendUrl || MOBILE_LAN_FALLBACK || storedBackendUrl || runtimeBackendUrl)
  : (storedBackendUrl || envBackendUrl || runtimeBackendUrl);
export const API = `${BACKEND_URL}/api`;

export const getApiCandidates = () => {
  const candidates = [
    `${storedBackendUrl}/api`,
    `${envBackendUrl}/api`,
    `${runtimeBackendUrl}/api`,
    `${MOBILE_LAN_FALLBACK}/api`,
    'http://127.0.0.1:8000/api',
    'http://localhost:8000/api',
  ];

  return [...new Set(candidates.map(normalizeUrl).filter(Boolean))];
};

export const setBackendUrlOverride = (backendUrl) => {
  const normalized = normalizeUrl(backendUrl);
  if (!normalized) {
    return;
  }

  // Ignore insecure overrides on mobile when we have cloud HTTPS backend.
  if (isMobileWebView() && !isHttpsUrl(normalized)) {
    return;
  }

  try {
    localStorage.setItem(BACKEND_OVERRIDE_KEY, normalized);
  } catch {
    // Ignore storage failures and continue with runtime resolution.
  }
};

const api = axios.create({
  baseURL: API,
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;