import type {
  CreateSearchPayload,
  CreateSearchResponse,
  PaginatedLeadResults,
  PaginatedSearches,
  SearchDetail,
} from "../types/api";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
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
  return request<CreateSearchResponse>("/api/searches", {
    method: "POST",
    body: JSON.stringify(payload),
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