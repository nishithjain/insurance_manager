import axios from 'axios';

/**
 * Resolve FastAPI origin. Preview hosts (e.g. *.emergentagent.com) often serve **no** Python API.
 * When the UI runs on localhost, prefer local FastAPI unless REACT_APP_ALLOW_PREVIEW_API=true.
 */
function resolveBackendOrigin() {
  const raw = process.env.REACT_APP_BACKEND_URL;
  let base =
    raw != null && String(raw).trim() !== '' ? String(raw).replace(/\/$/, '') : '';

  if (typeof window === 'undefined') {
    return base;
  }

  const localUi =
    window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';

  if (!localUi || process.env.REACT_APP_ALLOW_PREVIEW_API === 'true') {
    return base;
  }

  const pointsAtPreview =
    base.includes('emergentagent.com') ||
    base.includes('emergent.sh') ||
    /preview\./i.test(base);

  if (pointsAtPreview || !base) {
    return 'http://127.0.0.1:8000';
  }

  return base;
}

const BACKEND_URL = resolveBackendOrigin();
const API = BACKEND_URL ? `${BACKEND_URL}/api` : '/api';

const AUTH_TOKEN_STORAGE_KEY = 'insurance.auth.token';

const api = axios.create({
  baseURL: API,
  withCredentials: false,
});

/**
 * Session token plumbing.
 * Storing the JWT in localStorage keeps the pattern simple and survives refreshes.
 * The interceptor attaches it to every request; a 401 listener centralizes the
 * "kick user back to login" behavior so no page has to handle it ad hoc.
 */
let _onUnauthorized = null;

export const authTokenStore = {
  get: () => {
    try {
      return localStorage.getItem(AUTH_TOKEN_STORAGE_KEY) || null;
    } catch {
      return null;
    }
  },
  set: (token) => {
    try {
      if (token) localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token);
      else localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
    } catch {
      /* Storage may be unavailable (private mode, etc.) — auth then lasts
         only for the page session via the axios default header below. */
    }
  },
  clear: () => authTokenStore.set(null),
};

export function registerUnauthorizedHandler(handler) {
  _onUnauthorized = typeof handler === 'function' ? handler : null;
}

api.interceptors.request.use((config) => {
  const token = authTokenStore.get();
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (error) => {
    const status = error?.response?.status;
    if (status === 401 || status === 403) {
      authTokenStore.clear();
      if (_onUnauthorized) _onUnauthorized(status);
    }
    return Promise.reject(error);
  },
);

// Customer APIs
export const customerAPI = {
  getAll: () => api.get('/customers'),
  getOne: (id) => api.get(`/customers/${id}`),
  create: (data) => api.post('/customers', data),
  update: (id, data) => api.put(`/customers/${id}`, data),
  delete: (id) => api.delete(`/customers/${id}`),
};

// Policy APIs
export const policyAPI = {
  getAll: () => api.get('/policies'),
  getOne: (id) => api.get(`/policies/${id}`),
  create: (data) => api.post('/policies', data),
  update: (id, data) => api.put(`/policies/${id}`, data),
  /** Partial update: last_contacted_at, contact_status, follow_up_date */
  patchContact: (id, data) => api.patch(`/policies/${id}/contact`, data),
  /** Expired renewal workflow: renewal_status, renewal_resolution_note */
  patchRenewalResolution: (id, data) => api.patch(`/policies/${id}/renewal-resolution`, data),
  /** Clear PENDING payment → CUSTOMER ONLINE / CHEQUE / etc. */
  patchPayment: (id, data) => api.patch(`/policies/${id}/payment`, data),
  delete: (id) => api.delete(`/policies/${id}`),
};

// Sync APIs (local sync_info history only; no cloud upload)
export const syncAPI = {
  getStatus: () => api.get('/sync/status'),
};

/** Promote CSV statement rows (statement_policy_lines) into customers + policies */
export const importAPI = {
  statementSummary: () => api.get('/import/statement-lines/summary'),
  statementLinesToPolicies: () => api.post('/import/statement-lines'),
  listStatementLines: () => api.get('/statement-lines'),
  /** multipart FormData with keys: file, replace_existing, promote_to_dashboard */
  uploadStatementCsv: (formData) => api.post('/import/statement-csv', formData),
};

/** Monthly CSV export (policies + customer fields); opens as file download */
export const exportAPI = {
  downloadPoliciesMonthly: ({ year, month, by }) =>
    api.get('/export/policies-csv', {
      params: { year, month, by },
      responseType: 'blob',
    }),
  /** ZIP: customers, addresses, policies, renewal_history, statement_policy_lines + README */
  downloadFullDataZip: () =>
    api.get('/export/full-data-zip', {
      responseType: 'blob',
    }),
};

/** Dashboard statistics (payments, renewals, trends) */
export const statisticsAPI = {
  getDashboard: () => api.get('/statistics/dashboard'),
};

/** Google Sign-In flow + session info */
export const authAPI = {
  /** Trade a Google ID token for a backend JWT + user profile. */
  loginWithGoogle: (idToken) => api.post('/auth/google', { id_token: idToken }),
  /** Current session owner (404/401 if token missing or expired). */
  me: () => api.get('/auth/me'),
  /** Stateless logout — client drops its own token; server acknowledges. */
  logout: () => api.post('/auth/logout'),
};

/** Admin-only user management */
export const usersAPI = {
  list: (params) => api.get('/users', { params }),
  get: (id) => api.get(`/users/${id}`),
  create: (data) => api.post('/users', data),
  update: (id, data) => api.put(`/users/${id}`, data),
  setStatus: (id, isActive) => api.put(`/users/${id}/status`, { is_active: isActive }),
  delete: (id) => api.delete(`/users/${id}`),
};

export default api;
