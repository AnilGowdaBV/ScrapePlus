import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import {
  createSearch,
  deleteSearch,
  getSearch,
  getSearchResults,
  getSearches,
} from "../api/client";
import type {
  CreateSearchPayload,
  PaginatedSearches,
  SearchStatus,
} from "../types/api";

const ACTIVE_STATUSES: SearchStatus[] = ["QUEUED", "RUNNING"];

export function useSearchHistory() {
  return useQuery({
    queryKey: ["searches"],
    queryFn: () => getSearches(),
    refetchInterval: (query) => {
      const items = query.state.data?.items ?? [];
      return items.some((search) => ACTIVE_STATUSES.includes(search.status))
        ? 3000
        : false;
    },
  });
}

export function useSelectedSearch(searchId: number | null) {
  return useQuery({
    queryKey: ["search", searchId],
    queryFn: () => getSearch(searchId as number),
    enabled: searchId !== null,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status && ACTIVE_STATUSES.includes(status) ? 2500 : false;
    },
  });
}

export function useSearchResults(
  searchId: number | null,
  page: number,
  pageSize: number,
  isActive: boolean = false,
) {
  return useQuery({
    queryKey: ["search-results", searchId, page, pageSize],
    queryFn: () => getSearchResults(searchId as number, page, pageSize),
    enabled: searchId !== null,
    placeholderData: (previous) => previous,
    refetchInterval: isActive ? 3000 : false,
  });
}

export function useCreateSearch() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateSearchPayload) => createSearch(payload),
    onSuccess: (created) => {
      void queryClient.invalidateQueries({ queryKey: ["searches"] });
      void queryClient.invalidateQueries({ queryKey: ["search", created.search_id] });
    },
  });
}

export function useDeleteSearch() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (searchId: number) => deleteSearch(searchId),
    onSuccess: (_, searchId) => {
      // Optimistically remove deleted search from cached searches list so stale data is not re-selected
      queryClient.setQueriesData<PaginatedSearches>(
        { queryKey: ["searches"] },
        (old) => {
          if (!old) return old;
          return {
            ...old,
            items: old.items.filter((item) => item.id !== searchId),
            total: Math.max(0, old.total - 1),
          };
        },
      );
      void queryClient.removeQueries({ queryKey: ["search", searchId] });
      void queryClient.removeQueries({ queryKey: ["search-results", searchId] });
      void queryClient.invalidateQueries({ queryKey: ["searches"] });
    },
  });
}