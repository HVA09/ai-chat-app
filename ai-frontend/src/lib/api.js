import axios from "axios";

const SESSION_RESTORE_REQUEST_TIMEOUT_MS = 12000;
const SESSION_RESTORE_MAX_DURATION_MS = 70000;
const SESSION_RESTORE_RETRY_DELAYS_MS = [1500, 3000, 5000, 7000, 9000, 10000, 10000, 10000];

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000",
  headers: {
    "Content-Type": "application/json",
  },
  withCredentials: true,
  timeout: 30000,
});

api.interceptors.request.use((config) => config);

let refreshPromise = null;
let restoreSessionPromise = null;

async function refreshAccessToken({ timeout = 15000 } = {}) {
  const { data } = await axios.post(
    `${import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"}/auth/refresh`,
    {},
    { timeout, withCredentials: true }
  );
  return data.access_token;
}

function isTemporaryStartupError(error) {
  if (!error.response) return true;
  return [502, 503, 504].includes(error.response.status);
}

async function restoreSessionWithRetry() {
  const deadline = Date.now() + SESSION_RESTORE_MAX_DURATION_MS;
  let retryAttempt = 0;
  let lastError;

  while (Date.now() < deadline) {
    const remaining = deadline - Date.now();

    try {
      return await refreshAccessToken({
        timeout: Math.max(1, Math.min(SESSION_RESTORE_REQUEST_TIMEOUT_MS, remaining)),
      });
    } catch (error) {
      lastError = error;
      const retryDelay = SESSION_RESTORE_RETRY_DELAYS_MS[retryAttempt];
      retryAttempt += 1;

      // 401 means there is no valid saved session; show the login form right away.
      // Only retry transient gateway/network failures that can occur while Render wakes
      // a free backend after inactivity. Never retry auth failures or other 4xx errors.
      const remainingAfterRequest = deadline - Date.now();
      if (
        !isTemporaryStartupError(error) ||
        retryDelay === undefined ||
        remainingAfterRequest <= retryDelay + 1000
      ) {
        throw error;
      }

      await new Promise((resolve) => setTimeout(resolve, retryDelay));
    }
  }

  throw lastError || new Error("Session restoration exceeded the startup time budget");
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    if (error.response?.status !== 401 || original._retry) {
      if (error.response?.status === 401) {
        window.dispatchEvent(new Event("auth:unauthorized"));
      }
      return Promise.reject(error);
    }

    // لا نحاول تجديد التوكن على مسارات المصادقة نفسها
    if (original.url?.includes("/auth/login") || original.url?.includes("/auth/refresh")) {
      window.dispatchEvent(new Event("auth:unauthorized"));
      return Promise.reject(error);
    }

    original._retry = true;
    try {
      // طلب واحد فقط للتجديد حتى لو عدة طلبات فشلت بنفس الوقت
      if (!refreshPromise) {
        refreshPromise = refreshAccessToken().finally(() => {
          refreshPromise = null;
        });
      }
      const newToken = await refreshPromise;
      return api(original);
    } catch {
      window.dispatchEvent(new Event("auth:unauthorized"));
      return Promise.reject(error);
    }
  }
);

export function restoreSession() {
  // Share one startup refresh across React remounts/retries so concurrent refresh
  // requests cannot race if a user reloads or taps Retry while startup is in progress.
  if (!restoreSessionPromise) {
    restoreSessionPromise = restoreSessionWithRetry().finally(() => {
      restoreSessionPromise = null;
    });
  }
  return restoreSessionPromise;
}

export default api;
