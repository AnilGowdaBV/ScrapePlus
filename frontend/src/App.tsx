import { useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useEffect, useRef, useState } from "react";

import {
  useCreateSearch,
  useDeleteSearch,
  useSearchHistory,
  useSearchResults,
  useSelectedSearch,
} from "./hooks/useSearches";
import {
  disconnectLinkedInSession,
  getExportCsvUrl,
  getExportXlsxUrl,
  getLinkedInSession,
  openLoginBrowser,
  saveLinkedInSession,
} from "./api/client";
import type { SearchStatus } from "./types/api";

type HealthResponse = { status: string; service: string };

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

const TERMINAL_STATUSES: SearchStatus[] = [
  "COMPLETED",
  "PARTIAL",
  "FAILED",
  "CANCELLED",
];

async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/api/health`);
  if (!response.ok) throw new Error("Backend unavailable");
  return response.json() as Promise<HealthResponse>;
}

function formatDate(value: string | null | undefined) {
  if (!value) return "Not available";
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function statusLabel(status: SearchStatus) {
  return status.charAt(0) + status.slice(1).toLowerCase();
}

function isPeopleSearchUrl(value: string) {
  try {
    const url = new URL(value);
    return (
      url.protocol === "https:" &&
      (url.hostname === "linkedin.com" || url.hostname === "www.linkedin.com") &&
      url.pathname.replace(/\/$/, "") === "/search/results/people"
    );
  } catch {
    return false;
  }
}

function getErrorMessage(error: unknown) {
  return error instanceof Error
    ? error.message
    : "Something went wrong. Please try again.";
}

export default function App() {
  const queryClient = useQueryClient();
  const health = useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
    retry: false,
  });
  const linkedinSession = useQuery({
    queryKey: ["linkedin-session"],
    queryFn: getLinkedInSession,
    retry: false,
  });
  const history = useSearchHistory();
  const createMutation = useCreateSearch();
  const deleteMutation = useDeleteSearch();
  const [selectedSearchId, setSelectedSearchId] = useState<number | null>(null);
  const [resultPage, setResultPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [url, setUrl] = useState("");
  const [maxPages, setMaxPages] = useState(5);
  const [formError, setFormError] = useState<string | null>(null);
  const hasInitializedRef = useRef(false);

  // LinkedIn Connect Modal state
  const [isConnectModalOpen, setIsConnectModalOpen] = useState(false);
  const [cookieInput, setCookieInput] = useState("");
  const [sessionSaving, setSessionSaving] = useState(false);
  const [sessionError, setSessionError] = useState<string | null>(null);
  const [openingBrowser, setOpeningBrowser] = useState(false);
  const [browserMsg, setBrowserMsg] = useState<string | null>(null);

  async function handleOpenBrowser() {
    setOpeningBrowser(true);
    setBrowserMsg(null);
    setSessionError(null);
    try {
      const res = await openLoginBrowser();
      setBrowserMsg(res.message);
      // Auto-poll session status to detect when user finishes logging in
      const interval = setInterval(async () => {
        try {
          const status = await getLinkedInSession();
          if (status.connected) {
            clearInterval(interval);
            await linkedinSession.refetch();
            setBrowserMsg("🎉 Logged in and session saved successfully!");
          }
        } catch {
          // Ignore polling errors
        }
      }, 3000);
      setTimeout(() => clearInterval(interval), 120000);
    } catch (err) {
      setSessionError(getErrorMessage(err));
    } finally {
      setOpeningBrowser(false);
    }
  }

  async function handleSaveSession() {
    if (!cookieInput.trim()) {
      setSessionError("Please paste your li_at cookie.");
      return;
    }
    setSessionSaving(true);
    setSessionError(null);
    try {
      await saveLinkedInSession(cookieInput.trim());
      await linkedinSession.refetch();
      setCookieInput("");
      setIsConnectModalOpen(false);
    } catch (err) {
      setSessionError(getErrorMessage(err));
    } finally {
      setSessionSaving(false);
    }
  }

  async function handleDisconnectSession() {
    if (!window.confirm("Disconnect your saved LinkedIn session?")) return;
    setSessionSaving(true);
    try {
      await disconnectLinkedInSession();
      await linkedinSession.refetch();
      setIsConnectModalOpen(false);
    } catch (err) {
      setSessionError(getErrorMessage(err));
    } finally {
      setSessionSaving(false);
    }
  }

  const selectedSearch = useSelectedSearch(selectedSearchId);
  const isSearchActive =
    selectedSearch.data?.status === "QUEUED" ||
    selectedSearch.data?.status === "RUNNING";
  const results = useSearchResults(
    selectedSearchId,
    resultPage,
    pageSize,
    isSearchActive,
  );

  // Auto-select the first search only on initial page load if not already chosen
  useEffect(() => {
    if (!hasInitializedRef.current && history.data?.items && history.data.items.length > 0) {
      setSelectedSearchId(history.data.items[0].id);
      hasInitializedRef.current = true;
    }
  }, [history.data]);

  useEffect(() => {
    setResultPage(1);
  }, [selectedSearchId, pageSize]);

  // When search reaches terminal state, refresh results and searches list
  useEffect(() => {
    const status = selectedSearch.data?.status;
    if (
      selectedSearchId !== null &&
      status &&
      TERMINAL_STATUSES.includes(status)
    ) {
      void queryClient.invalidateQueries({
        queryKey: ["search-results", selectedSearchId],
      });
      void queryClient.invalidateQueries({
        queryKey: ["searches"],
      });
    }
  }, [queryClient, selectedSearch.data?.status, selectedSearchId]);

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);
    if (!url.trim()) {
      setFormError("Paste a LinkedIn People Search URL to begin.");
      return;
    }
    if (!isPeopleSearchUrl(url.trim())) {
      setFormError("Use a valid HTTPS LinkedIn People Search URL.");
      return;
    }
    if (!Number.isInteger(maxPages) || maxPages < 1) {
      setFormError("Max pages must be at least 1.");
      return;
    }
    createMutation.mutate(
      { search_url: url.trim(), max_pages: maxPages },
      {
        onSuccess: (created) => {
          setSelectedSearchId(created.search_id);
          hasInitializedRef.current = true;
          setResultPage(1);
          setUrl("");
        },
        onError: (error) => setFormError(getErrorMessage(error)),
      },
    );
  }

  function deleteSelectedSearch() {
    if (selectedSearchId === null) return;
    if (!window.confirm("Delete this search and all of its saved leads?")) return;
    const idToDelete = selectedSearchId;
    setSelectedSearchId(null);
    deleteMutation.mutate(idToDelete, {
      onError: (error) => setFormError(getErrorMessage(error)),
    });
  }

  const run = selectedSearch.data?.latest_run;
  const totalPages = results.data
    ? Math.max(1, Math.ceil(results.data.total / pageSize))
    : 1;

  return (
    <div className="dashboard-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="ScrapePulse home">
          <span className="brand-mark" aria-hidden="true">⚡</span>
          <span>ScrapePulse</span>
        </a>
        <div className="header-actions">
          <button
            type="button"
            className={`linkedin-connect-btn ${linkedinSession.data?.connected ? "connected" : ""}`}
            onClick={() => setIsConnectModalOpen(true)}
          >
            <span className="btn-icon">{linkedinSession.data?.connected ? "✓" : "🔗"}</span>
            <span>{linkedinSession.data?.connected ? "LinkedIn Connected" : "Connect LinkedIn"}</span>
          </button>
          <div className="connection-indicator" role="status">
            <span className={`connection-dot ${health.isSuccess ? "online" : ""}`} aria-hidden="true" />
            {health.isLoading
              ? "Connecting"
              : health.isSuccess
                ? "Backend connected"
                : "Backend unavailable"}
          </div>
        </div>
      </header>

      <main className="dashboard-content">
        <section className="intro-row">
          <div>
            <p className="section-kicker">High-Intent People Search</p>
            <h1>Turn a search into a working lead list.</h1>
            <p className="intro-copy">
              Paste the exact People Search URL from LinkedIn. Your search filters stay
              intact while ScrapePulse captures all verified profiles.
            </p>
          </div>
          <div className="workflow-note">
            <span>01</span><strong>Paste</strong><span>02</span><strong>Process</strong><span>03</span><strong>Export</strong>
          </div>
        </section>

        <section className="new-search-panel" aria-labelledby="new-search-title">
          <div className="panel-heading">
            <div><p className="section-kicker">New search</p><h2 id="new-search-title">Start with a People Search URL</h2></div>
            <span className="scope-tag">PEOPLE ONLY</span>
          </div>
          <form className="search-form" onSubmit={submitSearch}>
            <label className="url-field">
              <span>LinkedIn People Search URL</span>
              <input value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://www.linkedin.com/search/results/people/?..." title={url || undefined} autoComplete="off" />
            </label>
            <label className="pages-field">
              <span>Max pages</span>
              <input type="number" min="1" max="1000" value={maxPages} onChange={(event) => setMaxPages(Number(event.target.value))} />
            </label>
            <button className="primary-button" type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending ? "Starting..." : "Start Search"}<span aria-hidden="true">→</span>
            </button>
          </form>
          {formError && <p className="error-message" role="alert">{formError}</p>}
        </section>

        <section className="workspace-grid">
          <aside className="history-panel" aria-labelledby="history-title">
            <div className="panel-heading compact"><div><p className="section-kicker">Workspace</p><h2 id="history-title">Search history</h2></div><span className="count-pill">{history.data?.total ?? 0}</span></div>
            {history.isLoading && <div className="muted-state">Loading searches...</div>}
            {history.isError && <div className="inline-error">{getErrorMessage(history.error)}</div>}
            {history.data?.items.length === 0 && <div className="muted-state">No searches yet.<br />Your saved searches will appear here.</div>}
            <div className="history-list">
              {history.data?.items.map((search) => (
                <button className={`history-item ${selectedSearchId === search.id ? "selected" : ""}`} key={search.id} onClick={() => setSelectedSearchId(search.id)}>
                  <span className="history-item-top"><span className={`status-badge status-${search.status.toLowerCase()}`}>{statusLabel(search.status)}</span><span>#{search.id}</span></span>
                  <strong title={search.search_url}>{search.search_url}</strong>
                  <span className="history-meta">{search.total_leads} leads · {formatDate(search.created_at)}</span>
                </button>
              ))}
            </div>
          </aside>

          <div className="detail-column">
            {!selectedSearchId && <section className="empty-detail"><span className="empty-mark">↗</span><h2>Select a search to inspect its leads</h2><p>Start a new search above or choose one from your history.</p></section>}
            {selectedSearch.isLoading && <section className="state-panel">Loading search details...</section>}
            {selectedSearch.isError && <section className="state-panel error-message">{getErrorMessage(selectedSearch.error)}</section>}
            {selectedSearch.data && <>
              <section className="status-panel">
                <div className="status-panel-main"><div><p className="section-kicker">Selected search <span className="mono">#{selectedSearch.data.id}</span></p><h2 title={selectedSearch.data.search_url}>{selectedSearch.data.search_url}</h2></div><span className={`status-badge large status-${selectedSearch.data.status.toLowerCase()}`}>{statusLabel(selectedSearch.data.status)}</span></div>
                <div className="metrics-row">
                  <div><span>Status</span><strong>{statusLabel(selectedSearch.data.status)}</strong></div>
                  <div><span>People saved</span><strong>{selectedSearch.data.total_leads}</strong></div>
                  <div><span>Pages</span><strong>{run ? `${run.pages_processed} / ${run.pages_requested}` : "Not started"}</strong></div>
                  <div><span>Records found</span><strong>{run?.records_found ?? 0}</strong></div>
                </div>
                <div className="timestamps"><span>Started {formatDate(selectedSearch.data.started_at)}</span><span>Completed {formatDate(selectedSearch.data.completed_at)}</span><span>Provider {run?.provider ?? "Not assigned"}</span><button className="text-button danger" onClick={deleteSelectedSearch} disabled={deleteMutation.isPending}>Delete search</button></div>
                {selectedSearch.data.error_message && (
                  <div className="status-error-box">
                    <p className="error-message" role="alert">{selectedSearch.data.error_message}</p>
                    {selectedSearch.data.error_message.includes("LOGIN_REQUIRED") && (
                      <div className="login-prompt-banner">
                        <div>
                          <strong>LinkedIn Login Required</strong>
                          <p>LinkedIn requires an active session to view people search results.</p>
                        </div>
                        <button
                          type="button"
                          className="primary-button small"
                          onClick={() => setIsConnectModalOpen(true)}
                        >
                          Connect LinkedIn Session
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </section>

              <section className="results-panel" aria-labelledby="results-title">
                <div className="panel-heading compact">
                  <div>
                    <p className="section-kicker">Lead records</p>
                    <h2 id="results-title">People found</h2>
                  </div>
                  <div className="results-actions">
                    <div className="export-actions">
                      <a
                        href={
                          selectedSearch.data?.total_leads && selectedSearchId
                            ? getExportCsvUrl(selectedSearchId)
                            : undefined
                        }
                        download
                        className={`export-button ${
                          !selectedSearch.data?.total_leads ? "disabled" : ""
                        }`}
                        aria-disabled={!selectedSearch.data?.total_leads}
                        title={
                          selectedSearch.data?.total_leads
                            ? "Export leads as CSV"
                            : "No leads to export"
                        }
                        onClick={(event) => {
                          if (!selectedSearch.data?.total_leads) event.preventDefault();
                        }}
                      >
                        Export CSV
                      </a>
                      <a
                        href={
                          selectedSearch.data?.total_leads && selectedSearchId
                            ? getExportXlsxUrl(selectedSearchId)
                            : undefined
                        }
                        download
                        className={`export-button ${
                          !selectedSearch.data?.total_leads ? "disabled" : ""
                        }`}
                        aria-disabled={!selectedSearch.data?.total_leads}
                        title={
                          selectedSearch.data?.total_leads
                            ? "Export leads as XLSX"
                            : "No leads to export"
                        }
                        onClick={(event) => {
                          if (!selectedSearch.data?.total_leads) event.preventDefault();
                        }}
                      >
                        Export XLSX
                      </a>
                    </div>
                    <label className="page-size-label">
                      Rows{" "}
                      <select
                        value={pageSize}
                        onChange={(event) => setPageSize(Number(event.target.value))}
                      >
                        <option value="25">25</option>
                        <option value="50">50</option>
                        <option value="100">100</option>
                      </select>
                    </label>
                  </div>
                </div>
                {results.isLoading && <div className="muted-state">Loading leads...</div>}
                {results.isError && <div className="inline-error">{getErrorMessage(results.error)}</div>}
                {!results.isLoading && results.data?.items.length === 0 && <div className="muted-state centered">No leads found for this search.</div>}
                {results.data && results.data.items.length > 0 && <div className="table-wrap"><table><thead><tr><th>Company</th><th>Person</th><th>Title / headline</th><th>Location</th><th>LinkedIn</th></tr></thead><tbody>{results.data.items.map((lead) => <tr key={lead.id}><td><strong>{lead.company_name ?? "—"}</strong></td><td>{lead.person_name ?? "—"}</td><td><span>{lead.person_title ?? "—"}</span>{lead.headline && <small>{lead.headline}</small>}</td><td>{lead.location ?? "—"}</td><td>{lead.linkedin_profile_url ? <a className="profile-link" href={lead.linkedin_profile_url} target="_blank" rel="noreferrer">View profile ↗</a> : <span className="muted">—</span>}</td></tr>)}</tbody></table></div>}
                {results.data && results.data.total > 0 && <div className="pagination"><span>{(resultPage - 1) * pageSize + 1}–{Math.min(resultPage * pageSize, results.data.total)} of {results.data.total}</span><div><button className="page-button" disabled={resultPage <= 1 || results.isFetching} onClick={() => setResultPage((page) => page - 1)}>← Previous</button><span className="page-number">Page {resultPage} of {totalPages}</span><button className="page-button" disabled={resultPage >= totalPages || results.isFetching} onClick={() => setResultPage((page) => page + 1)}>Next →</button></div></div>}
              </section>
            </>}
          </div>
        </section>
      </main>

      {isConnectModalOpen && (
        <div className="modal-backdrop" onClick={() => setIsConnectModalOpen(false)}>
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div>
                <h3>Connect LinkedIn Account</h3>
                <p className="modal-subtitle">Authenticate your session to scrape search results</p>
              </div>
              <button
                type="button"
                className="modal-close"
                onClick={() => setIsConnectModalOpen(false)}
                aria-label="Close modal"
              >
                ✕
              </button>
            </div>

            <div className="modal-body">
              {linkedinSession.data?.connected ? (
                <div className="connected-status-card">
                  <div>
                    <div className="badge-connected">✅ LinkedIn Session Connected</div>
                    <p>Your session cookie is active ({linkedinSession.data.masked_cookie}).</p>
                  </div>
                  <button
                    type="button"
                    className="text-button danger"
                    onClick={handleDisconnectSession}
                    disabled={sessionSaving}
                  >
                    Disconnect
                  </button>
                </div>
              ) : null}

              <div className="login-browser-card">
                <div>
                  <h4>✨ Recommended: One-Click Browser Login</h4>
                  <p>
                    Click below to open LinkedIn in Chrome. Simply enter your LinkedIn email and password to log in. ScrapePlus will save your session automatically!
                  </p>
                </div>
                <button
                  type="button"
                  className="primary-button full-width"
                  onClick={handleOpenBrowser}
                  disabled={openingBrowser}
                >
                  {openingBrowser ? "Opening Chrome..." : "🚀 Open LinkedIn in Chrome to Log In"}
                </button>
                {browserMsg && <p className="success-banner">{browserMsg}</p>}
              </div>

              <div className="divider-row">
                <span>OR MANUAL COOKIE</span>
              </div>

              <div className="instructions-card">
                <h4>How to get your session cookie (30 seconds):</h4>
                <ol>
                  <li>
                    Open <a href="https://www.linkedin.com" target="_blank" rel="noreferrer">LinkedIn.com</a> in your browser and ensure you are logged in.
                  </li>
                  <li>
                    Press <strong>F12</strong> (or right-click ➔ <em>Inspect</em>) to open Developer Tools.
                  </li>
                  <li>
                    Click the <strong>Application</strong> tab (or <em>Storage</em> in Firefox) ➔ expand <strong>Cookies</strong> on the left ➔ click <code>https://www.linkedin.com</code>.
                  </li>
                  <li>
                    Find the cookie named <strong><code>li_at</code></strong>, double-click its value, copy it, and paste it below.
                  </li>
                </ol>
              </div>

              <label className="modal-input-label">
                <span>LinkedIn <code>li_at</code> Cookie</span>
                <textarea
                  className="cookie-textarea"
                  rows={2}
                  value={cookieInput}
                  onChange={(e) => setCookieInput(e.target.value)}
                  placeholder="AQEDAT... (paste your li_at cookie here)"
                />
              </label>
              {sessionError && <p className="error-message" role="alert">{sessionError}</p>}
            </div>

            <div className="modal-footer">
              <button
                type="button"
                className="secondary-button"
                onClick={() => setIsConnectModalOpen(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="primary-button"
                onClick={handleSaveSession}
                disabled={sessionSaving || !cookieInput.trim()}
              >
                {sessionSaving ? "Saving..." : "Save & Connect"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
