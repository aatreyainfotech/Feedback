import axios from 'axios';

const BACKEND_OVERRIDE_KEY = 'backend_url';
const MOBILE_LAN_FALLBACK = 'https://aatreyainfo-feedback-fefbeqvc3dahrg2.centralindia-01.azurewebsites.net';
const CLOUD_BACKEND_FALLBACK = 'https://aatreyainfo-feedback-fefbeqvc3dahrg2.centralindia-01.azurewebsites.net';
const DEFAULT_TIMEOUT_MS = 15000;
const DEFAULT_GET_CACHE_TTL_MS = 10000;
const STATIC_GET_CACHE_TTL_MS = 60000;

const responseCache = new Map();
const inflightGetRequests = new Map();

const normalizeUrl = (url) => (url || '').trim().replace(/\/$/, '');

const safeClone = (value) => {
  if (value === null || value === undefined) {
    return value;
  }

  if (typeof structuredClone === 'function') {
    try {
      return structuredClone(value);
    } catch {
      // Fall back to JSON clone below for plain API payloads.
    }
  }

  return JSON.parse(JSON.stringify(value));
};

const buildParamsString = (params = {}) => {
  const searchParams = new URLSearchParams();

  Object.entries(params)
    .filter(([, value]) => value !== undefined && value !== null && value !== '')
    .sort(([leftKey], [rightKey]) => leftKey.localeCompare(rightKey))
    .forEach(([key, value]) => {
      if (Array.isArray(value)) {
        value.forEach((item) => searchParams.append(key, String(item)));
      } else {
        searchParams.append(key, String(value));
      }
    });

  return searchParams.toString();
};

const getStoredBackendUrl = () => {
  try {
    return normalizeUrl(localStorage.getItem(BACKEND_OVERRIDE_KEY));
  } catch {
    return '';
  }
};

const getRuntimeBackendUrl = () => {
  const host = window.location.hostname || 'localhost';
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

const BACKEND_URL = isMobileWebView()
  ? (envBackendUrl || MOBILE_LAN_FALLBACK || CLOUD_BACKEND_FALLBACK || storedBackendUrl || runtimeBackendUrl)
  : (storedBackendUrl || envBackendUrl || CLOUD_BACKEND_FALLBACK || runtimeBackendUrl);
export const API = `${BACKEND_URL}/api`;

const getCacheKey = (url, config = {}) => {
  const baseUrl = normalizeUrl(config.baseURL || API);
  const paramsKey = buildParamsString(config.params || {});
  return `${baseUrl}|${url}|${paramsKey}`;
};

const getCacheTtl = (url, explicitTtl) => {
  if (typeof explicitTtl === 'number') {
    return explicitTtl;
  }

  if (/^\/(temples|officers|services)\b/.test(url)) {
    return STATIC_GET_CACHE_TTL_MS;
  }

  if (/^\/(feedback|stats|dashboard\/stats|dashboard\/officer-stats|whatsapp\/logs)\b/.test(url)) {
    return DEFAULT_GET_CACHE_TTL_MS;
  }

  return 0;
};

const sanitizeConfig = (config = {}) => {
  const { cacheTtlMs, forceRefresh, ...axiosConfig } = config || {};
  return axiosConfig;
};

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

  if (isMobileWebView() && !isHttpsUrl(normalized)) {
    return;
  }

  try {
    localStorage.setItem(BACKEND_OVERRIDE_KEY, normalized);
  } catch {
    // Ignore storage failures and continue with runtime resolution.
  }
};

export const invalidateApiCache = (match = '') => {
  const needle = String(match || '');

  Array.from(responseCache.keys()).forEach((key) => {
    if (!needle || key.includes(needle)) {
      responseCache.delete(key);
    }
  });
};

const api = axios.create({
  baseURL: API,
  timeout: DEFAULT_TIMEOUT_MS,
});

const rawGet = api.get.bind(api);

export const apiGet = async (url, config = {}) => {
  const cacheTtlMs = getCacheTtl(url, config.cacheTtlMs);
  const forceRefresh = Boolean(config.forceRefresh);
  const requestConfig = sanitizeConfig(config);

  if (cacheTtlMs <= 0 || forceRefresh) {
    return rawGet(url, requestConfig);
  }

  const cacheKey = getCacheKey(url, config);
  const cachedEntry = responseCache.get(cacheKey);
  if (cachedEntry && cachedEntry.expiresAt > Date.now()) {
    return {
      ...cachedEntry.response,
      data: safeClone(cachedEntry.response.data),
    };
  }

  if (inflightGetRequests.has(cacheKey)) {
    const inFlightResponse = await inflightGetRequests.get(cacheKey);
    return {
      ...inFlightResponse,
      data: safeClone(inFlightResponse.data),
    };
  }

  const requestPromise = rawGet(url, requestConfig)
    .then((response) => {
      const cacheableResponse = {
        ...response,
        data: safeClone(response.data),
      };
      responseCache.set(cacheKey, {
        expiresAt: Date.now() + cacheTtlMs,
        response: cacheableResponse,
      });
      return cacheableResponse;
    })
    .finally(() => {
      inflightGetRequests.delete(cacheKey);
    });

  inflightGetRequests.set(cacheKey, requestPromise);
  const response = await requestPromise;
  return {
    ...response,
    data: safeClone(response.data),
  };
};

api.get = (url, config = {}) => apiGet(url, config);

api.interceptors.request.use((config) => {
  try {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  } catch {
    // Ignore storage lookup failures.
  }
  return config;
});

api.interceptors.response.use(
  (response) => {
    if ((response.config?.method || 'get').toLowerCase() !== 'get') {
      invalidateApiCache();
    }
    return response;
  },
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