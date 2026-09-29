import type {
  CreateSearchPayload,
  CreateSearchResponse,
  PaginatedLeadResults,
  PaginatedSearches,
  SearchDetail,
} from "../types/api";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";
const STORAGE_COOKIE_KEY = "scrapeplus_linkedin_li_at";

export function getDeviceCookie(): string | null {
  try {
    return localStorage.getItem(STORAGE_COOKIE_KEY);
  } catch {
    return null;
  }
}

export function saveDeviceCookie(cookie: string): void {
  try {
    localStorage.setItem(STORAGE_COOKIE_KEY, cookie.trim());
  } catch {}
}

export function clearDeviceCookie(): void {
  try {
    localStorage.removeItem(STORAGE_COOKIE_KEY);
  } catch {}
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const deviceCookie = getDeviceCookie();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(deviceCookie ? { "X-LinkedIn-Cookie": deviceCookie } : {}),
    ...(init?.headers as Record<string, string>),
  };

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
  });

  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) message = body.detail;
    } catch {
      // Keep the safe HTTP fallback when the response is not JSON.
    }
    throw new Error(message);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export function createSearch(payload: CreateSearchPayload) {
  const deviceCookie = getDeviceCookie();
  return request<CreateSearchResponse>("/api/searches", {
    method: "POST",
    body: JSON.stringify({
      ...payload,
      session_cookie: deviceCookie || undefined,
    }),
  });
}

export function getSearches(page = 1, pageSize = 20) {
  return request<PaginatedSearches>(
    `/api/searches?page=${page}&page_size=${pageSize}`,
  );
}

export function getSearch(searchId: number) {
  return request<SearchDetail>(`/api/searches/${searchId}`);
}

export function getSearchResults(searchId: number, page = 1, pageSize = 25) {
  return request<PaginatedLeadResults>(
    `/api/searches/${searchId}/results?page=${page}&page_size=${pageSize}`,
  );
}

export function deleteSearch(searchId: number) {
  return request<void>(`/api/searches/${searchId}`, { method: "DELETE" });
}

export function getExportCsvUrl(searchId: number): string {
  return `${API_BASE_URL}/api/searches/${searchId}/export/csv`;
}

export function getExportXlsxUrl(searchId: number): string {
  return `${API_BASE_URL}/api/searches/${searchId}/export/xlsx`;
}

export interface LinkedInSessionStatus {
  connected: boolean;
  masked_cookie: string | null;
}

export async function getLinkedInSession(): Promise<LinkedInSessionStatus> {
  const localCookie = getDeviceCookie();
  if (localCookie) {
    const masked =
      localCookie.length > 10
        ? `${localCookie.slice(0, 6)}...${localCookie.slice(-4)}`
        : "******";
    return { connected: true, masked_cookie: masked };
  }
  try {
    return await request<LinkedInSessionStatus>("/api/settings/linkedin-session");
  } catch {
    return { connected: false, masked_cookie: null };
  }
}

export async function saveLinkedInSession(li_at: string): Promise<LinkedInSessionStatus> {
  saveDeviceCookie(li_at);
  try {
    return await request<LinkedInSessionStatus>("/api/settings/linkedin-session", {
      method: "POST",
      body: JSON.stringify({ li_at }),
    });
  } catch {
    // Graceful fallback to client-side storage if server endpoint is pending deployment
    const masked =
      li_at.length > 10
        ? `${li_at.slice(0, 6)}...${li_at.slice(-4)}`
        : "******";
    return { connected: true, masked_cookie: masked };
  }
}

export async function disconnectLinkedInSession(): Promise<LinkedInSessionStatus> {
  clearDeviceCookie();
  try {
    return await request<LinkedInSessionStatus>("/api/settings/linkedin-session", {
      method: "DELETE",
    });
  } catch {
    return { connected: false, masked_cookie: null };
  }
}

export interface LoginResponse {
  status: "SUCCESS" | "REQUIRES_2FA" | "CAPTCHA" | "ERROR";
  session_id?: string;
  cookie?: string;
  masked_cookie?: string;
  message: string;
}

export function loginWithCredentials(payload: { email: string; password: string }) {
  return request<LoginResponse>("/api/settings/login-credentials", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function submit2Fa(payload: { session_id: string; code: string }) {
  return request<LoginResponse>("/api/settings/submit-2fa", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function openLoginBrowser() {
  return request<{ message: string }>("/api/settings/open-login-browser", {
    method: "POST",
  });
}