import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000",
  headers: { "Content-Type": "application/json" },
  withCredentials: true,
  timeout: 30000,
});

let refreshPromise = null;

async function refreshAccessToken() {
  const { data } = await axios.post(
    `${import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"}/auth/refresh`,
    {},
    { timeout: 15000, withCredentials: true }
  );
  return data.access_token;
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    if (error.response?.status !== 401 || original?._retry) {
      if (error.response?.status === 401) window.dispatchEvent(new Event("auth:unauthorized"));
      return Promise.reject(error);
    }

    if (original.url?.includes("/auth/login") || original.url?.includes("/auth/refresh")) {
      window.dispatchEvent(new Event("auth:unauthorized"));
      return Promise.reject(error);
    }

    original._retry = true;
    try {
      if (!refreshPromise) refreshPromise = refreshAccessToken().finally(() => { refreshPromise = null; });
      await refreshPromise;
      return api(original);
    } catch {
      window.dispatchEvent(new Event("auth:unauthorized"));
      return Promise.reject(error);
    }
  }
);

export async function restoreSession() {
  return refreshAccessToken();
}

export default api;
