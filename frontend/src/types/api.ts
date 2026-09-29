export type SearchStatus =
  | "QUEUED"
  | "RUNNING"
  | "COMPLETED"
  | "PARTIAL"
  | "FAILED"
  | "CANCELLED";

export type SearchRun = {
  id: number;
  provider: string;
  status: SearchStatus;
  started_at: string | null;
  completed_at: string | null;
  pages_requested: number;
  pages_processed: number;
  records_found: number;
  records_saved: number;
  error_message: string | null;
};

export type SearchSummary = {
  id: number;
  search_url: string;
  search_type: "PEOPLE";
  status: SearchStatus;
  created_at: string;
  total_leads: number;
  latest_run: SearchRun | null;
};

export type SearchDetail = SearchSummary & {
  updated_at: string;
  started_at: string | null;
  completed_at: string | null;
  total_results: number;
  error_message: string | null;
};

export type LeadResult = {
  id: number;
  external_id: string | null;
  person_name: string | null;
  person_title: string | null;
  headline: string | null;
  company_name: string | null;
  company_url: string | null;
  linkedin_profile_url: string | null;
  location: string | null;
  profile_image_url: string | null;
  connection_degree: string | null;
  education: string | null;
};

export type PaginatedSearches = {
  items: SearchSummary[];
  page: number;
  page_size: number;
  total: number;
};

export type PaginatedLeadResults = {
  items: LeadResult[];
  page: number;
  page_size: number;
  total: number;
};

export type CreateSearchPayload = {
  search_url: string;
  max_pages: number;
};

export type CreateSearchResponse = {
  search_id: number;
  run_id: number;
  status: SearchStatus;
};