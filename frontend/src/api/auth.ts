import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";

const API_BASE_URL = import.meta.env.VITE_API_URL ?? "";
const REFRESH_TOKEN_KEY = "pretoffice.refresh";

let accessToken: string | null = null;
let refreshPromise: Promise<string | null> | null = null;
let onSessionExpired: (() => void) | null = null;

type RetriableRequest = InternalAxiosRequestConfig & {
  _retried?: boolean;
};

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

export function setAccessToken(token: string | null) {
  accessToken = token;
}

export function setSessionExpiredHandler(handler: (() => void) | null) {
  onSessionExpired = handler;
}

export function getRefreshToken() {
  return sessionStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setRefreshToken(token: string | null) {
  if (token) {
    // Interim browser storage: replace with an httpOnly backend cookie before production.
    sessionStorage.setItem(REFRESH_TOKEN_KEY, token);
  } else {
    sessionStorage.removeItem(REFRESH_TOKEN_KEY);
  }
}

api.interceptors.request.use((config) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

async function refreshAccessToken() {
  const refresh = getRefreshToken();
  if (!refresh) {
    return null;
  }
  if (!refreshPromise) {
    refreshPromise = axios
      .post<{ access: string; refresh?: string }>(
        `${API_BASE_URL}/api/auth/token/refresh/`,
        { refresh },
        { headers: { "Content-Type": "application/json" } },
      )
      .then(({ data }) => {
        setAccessToken(data.access);
        if (data.refresh) {
          setRefreshToken(data.refresh);
        }
        return data.access;
      })
      .catch(() => {
        setAccessToken(null);
        setRefreshToken(null);
        onSessionExpired?.();
        return null;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const request = error.config as RetriableRequest | undefined;
    const isAuthenticationRequest =
      request?.url?.includes("/api/auth/login/") ||
      request?.url?.includes("/api/auth/register/") ||
      request?.url?.includes("/api/auth/token/refresh/");
    if (
      error.response?.status !== 401 ||
      !request ||
      request._retried ||
      isAuthenticationRequest
    ) {
      return Promise.reject(error);
    }

    request._retried = true;
    const token = await refreshAccessToken();
    if (!token) {
      return Promise.reject(error);
    }
    request.headers.Authorization = `Bearer ${token}`;
    return api(request);
  },
);

export function errorMessage(error: unknown) {
  if (axios.isAxiosError(error)) {
    if (!error.response) {
      return "Le serveur est injoignable. Vérifiez votre connexion.";
    }
    if (error.response.status === 429) {
      return "Trop de tentatives. Veuillez patienter avant de réessayer.";
    }
    const body = error.response.data as
      | { detail?: string; errors?: Record<string, string[] | string> }
      | undefined;
    if (body?.detail) {
      return body.detail;
    }
    const firstError = body?.errors
      ? Object.values(body.errors)[0]
      : undefined;
    if (Array.isArray(firstError)) {
      return firstError[0] ?? "La requête n'a pas pu être traitée.";
    }
    if (typeof firstError === "string") {
      return firstError;
    }
    return "La requête n'a pas pu être traitée.";
  }
  return "Une erreur inattendue est survenue.";
}
