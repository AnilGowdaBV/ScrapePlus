# Current Architecture

LiSeSca is currently a browser-side Tampermonkey userscript. The source is an ES module tree under `src/`, bundled by Rollup into the root-level `lisesca.user.js` IIFE. `src/index.js` is the entry point and calls `Controller.init()`.

The current runtime is coupled to a LinkedIn tab. It reads and mutates the page DOM, navigates by assigning `window.location.href`, injects a floating UI panel, and persists progress through Tampermonkey `GM_*` storage APIs. There is no server, database, frontend application, HTTP API, migration system, or persistent search history.

The main runtime relationships are:

- `src/index.js` initializes `src/people/controller.js`.
- `src/people/controller.js` coordinates page detection, SPA navigation, UI, state, emulation, extraction, pagination, optional AI scoring, and output.
- `src/jobs/controller.js` is also wired into the shared UI and controller lifecycle. Jobs are outside the requested V1 scope and should remain untouched until the replacement architecture is verified.
- `src/ui/ui.js` creates the userscript panel directly with DOM APIs and CSS injected through `GM_addStyle`.
- `src/shared/state.js` stores the active scrape session and buffers serialized records through `GM_getValue` and `GM_setValue`.
- `rollup.config.js` emits a Tampermonkey userscript with external SheetJS and Turndown `@require` dependencies.

The root `lisesca.user.js` is generated/bundled output, not an independent application entry point. The repository currently has no dedicated lint configuration, TypeScript configuration, Python configuration, migrations, or environment template.

# People Search Flow

1. The userscript loads on LinkedIn pages and `Controller.init()` loads Tampermonkey configuration, injects styles, installs `SpaHandler`, and builds the panel for supported pages.
2. `PageDetector` recognizes People Search by substring matching against `linkedin.com/search/results/people`. It also recognizes Jobs pages, which is legacy scope for this migration.
3. The People UI lets the user choose a page count and optional AI rating, then calls `Controller.startScraping()`.
4. The controller reads the current URL through `Paginator`, removes the `page` parameter for a base URL, and starts a Tampermonkey-backed session.
5. `Emulator.emulateHumanScan()` performs randomized scrolling, synthetic mouse events, and delays before extraction. This behavior is explicitly unsuitable for the target platform because V1 must not implement stealth or anti-bot evasion.
6. `Extractor.extractCurrentPage()` waits up to ten seconds for `div[role="listitem"]` cards, parses each card independently, logs malformed cards, and continues.
7. The current extractor reads the title link, then derives name, profile URL, connection degree, description, and location from nearby DOM structure. It returns legacy fields: `fullName`, `description`, `profileUrl`, and empty-string/zero fallbacks.
8. Optional AI scoring can filter people after extraction. This is not part of the requested V1 workflow and must not be used to infer roles or classify leads.
9. Extracted records are appended to a serialized browser buffer. There is no durable database record, deduplication, normalized schema, search run, or partial-failure accounting.
10. When more pages are requested, `State.advancePage()` increments the page and `Paginator.navigateToPage()` preserves the stored base URL while setting only `page`, then performs a full navigation. The next page resumes from Tampermonkey state.
11. Completion leaves the buffer in a userscript summary UI. `Output` can trigger browser downloads in XLSX, CSV, and Markdown formats.

# Reusable Components

The following concepts are useful, subject to conversion into browser-independent, typed, testable modules:

- People result-card extraction boundaries in `src/people/extractor.js`: wait for result cards, parse cards independently, log/continue on malformed cards, and keep individual field extraction isolated.
- The current semantic selector intent in `src/selectors/people.js`: use role/data attributes instead of generated LinkedIn class names, while moving selectors into a dedicated configuration with explicit field selectors.
- Profile URL cleaning in `Extractor.cleanProfileUrl()`: removing tracking query/hash data is a starting point, but it must become a reusable, carefully validated canonical LinkedIn profile URL normalizer.
- The pagination concept in `src/people/paginator.js`: parse the current page and preserve a base URL. It must be redesigned to accept the original URL and change only the pagination parameter without losing any filters.
- Per-record failure isolation in `extractCurrentPage()`: this maps to a normalized extraction result plus a parse-error counter and structured logging.
- The output field mapping and RFC 4180-style CSV escaping in `src/people/output.js`: these are useful concepts for a backend export service after replacing browser download behavior and legacy columns.
- Existing page and card fixture opportunities: the current DOM assumptions provide a starting point for realistic static HTML fixtures, though selectors must not be treated as permanent.
- Existing source comments and documented page flow in `README.md`: useful historical context, but the README currently describes a different product and must be updated only during the appropriate migration phase.

# Components To Replace

- `src/index.js` and the userscript bootstrap: replace with separate FastAPI and React/Vite entry points while retaining the original userscript source until migration is verified.
- `src/people/controller.js`: replace the browser state machine with backend search orchestration and a service/provider boundary. It currently mixes lifecycle, UI, AI, navigation, persistence, and extraction concerns.
- `src/people/emulator.js`: do not port. Randomized scrolling, synthetic mouse movement, and bot-detection avoidance conflict with the access rules. The provider must stop and report login, CAPTCHA, restriction, or authentication challenges.
- `src/shared/state.js`: replace Tampermonkey key/value session state with SQLAlchemy entities and service-level transactions.
- `src/shared/config.js`: replace browser-persisted API keys and timing settings with typed server configuration and environment variables. Secrets must remain backend-only.
- `src/shared/page-detector.js` and `src/shared/spa-handler.js`: replace with provider/browser lifecycle handling. URL recognition should be strict URL validation, not substring checks.
- `src/selectors/people.js`: expand into a dedicated selector configuration owned by the scraper/provider layer, with field-level fallbacks and fixture tests.
- `src/people/output.js`: replace with backend CSV/XLSX export services using the normalized output contract and `openpyxl`; exclude internal IDs and `raw_data` by default.
- `src/ui/ui.js`: replace the injected floating panel with a responsive React dashboard using TanStack Query for search creation, status polling, history, results, and export actions.
- `src/shared/ai-client.js` and AI scoring paths: exclude from People Search V1. No AI role inference or lead scoring is permitted by the product requirements.
- Jobs modules and their UI wiring: do not port into V1. Keep them as legacy code until a later, explicitly scoped decision.

# Target Architecture

The repository should evolve into a monorepo with separate application boundaries:

```text
frontend/                 React + TypeScript + Vite + TanStack Query
backend/                  FastAPI + Pydantic v2 + SQLAlchemy 2.x + Alembic
scraper/                  People Search parsing, selectors, pagination, providers
database/                 Local SQLite data and migration-related runtime assets
scripts/                  Development and operational helpers
docs/                     Architecture and migration documentation
tests/                    Cross-boundary fixtures and contract tests
```

The exact folder split may be adjusted if a better Python package layout emerges, but ownership must remain explicit: routes handle HTTP, services handle business workflows, providers handle browser/search access, parsers normalize extracted data, and repositories/database code handle persistence.

The original userscript should remain in place during migration. Phase 2 should add the smallest runnable application skeleton on a dedicated `feature/people-search-platform` branch rather than deleting or rewriting the legacy implementation.

# Backend Architecture

FastAPI should expose thin route handlers under `backend/app/api/`. Pydantic v2 schemas define request/response contracts. Service classes coordinate search creation, provider execution, status transitions, deduplication, persistence, history, deletion, and export. Provider implementations must not be called directly from route handlers.

The backend should validate the supplied URL before creating a search. `validate_people_search_url()` must require a valid HTTPS LinkedIn hostname and a People Search pathname such as `/search/results/people/`; it must reject Jobs, feed, non-LinkedIn, and malformed URLs. The exact original URL, including all query parameters, must be stored unchanged as the source of truth.

Search execution should create a `Search` and a `SearchRun`, transition status through `QUEUED`, `RUNNING`, `COMPLETED`, `PARTIAL`, `FAILED`, or `CANCELLED`, and record page/record counters. Structured logs should include `search_id`, provider, page, found/saved counts, duration, and error details without credentials, cookies, tokens, or secrets.

The provider must report access challenges and unexpected pages as visible failures. It must not bypass CAPTCHA, authentication, rate limits, access controls, or session protections.

# Frontend Architecture

The React/Vite frontend should provide the desktop-first dashboard described in the product requirements, with responsive support for laptop and tablet widths. TanStack Query should manage search creation, status polling with a sensible interval, search history, paginated/sortable/filterable results, and export requests.

The main page needs exact People Search URL input, immediate validation feedback, max-page selection, Start Search, progress details, results table, history, empty/loading/error/partial states, and CSV/XLSX actions. It must communicate only with backend APIs; no LinkedIn credentials, provider secrets, scraping selectors, or API keys may be placed in frontend code.

# Database Architecture

Use SQLAlchemy 2.x models and Alembic migrations with SQLite as the initial database. Keep database access behind models/repositories/services so PostgreSQL can replace SQLite later.

Required entities:

- `Search`: `id`, exact `search_url`, `search_type=PEOPLE`, lifecycle status, timestamps, totals, and error message.
- `SearchRun`: provider execution metadata, page counters, record counters, timestamps, status, and error message.
- `Lead`: `search_id`, source/external identity, normalized person fields, optional fields, `raw_data`, and timestamps.

Lead values must remain nullable when absent. Deduplicate within a search by canonical profile URL first, then external ID, then a cautious name/location/company fallback. Avoid broad fuzzy merging. Add appropriate indexes and uniqueness constraints only where they cannot discard distinct people.

# Provider Architecture

Define a replaceable `PeopleSearchProvider` interface with an operation equivalent to `search(search_url, max_pages=None)`. The initial implementation can be a `BrowserPeopleSearchProvider`, but the application service must depend on the interface so another provider can be added without changing the frontend, API contracts, database, or exports.

The provider should delegate to isolated components:

- URL-preserving `PeopleSearchPaginator` that parses and updates only pagination-related values.
- Dedicated People selectors with semantic attributes and easy-to-update fallbacks.
- Card parser/extractor that normalizes text, profile URLs, nullable fields, and preserves `raw_data`.
- Record-level error handling that continues after malformed cards and reports partial extraction.

Company data must be taken only from an explicitly available result-card field. The provider must store `company_name=null` when the card does not expose it and must not visit every profile for V1 enrichment. It must never infer roles, companies, or other missing information.

# API Design

Initial contracts should be:

- `POST /api/searches`: accept `{ search_url, max_pages }`, validate the complete URL, create a queued People search, and return its ID and status.
- `GET /api/searches`: return search history with URL, dates, status, page counters, and result counters.
- `GET /api/searches/{search_id}`: return status, provider, page progress, record counters, timestamps, and errors.
- `GET /api/searches/{search_id}/results`: return paginated leads with sorting, text search, and supported filters.
- `DELETE /api/searches/{search_id}`: require a valid search identifier, delete associated leads/runs safely, and return an explicit result.
- Export endpoints for CSV and XLSX, using display columns only: Person Name, Title, Headline, Company, Location, LinkedIn Profile URL, and Connection Degree.

API schemas should use stable names such as `person_name`, `person_title`, `headline`, `company_name`, `location`, and `linkedin_profile_url`. Optional values should be `null`, not invented placeholders. Export errors and partial-search status must be visible to the UI.

# Migration Phases

1. **Phase 1 - Inspection and plan:** completed by this document. Preserve the legacy implementation and record current behavior, boundaries, risks, and questions.
2. **Phase 2 - Application architecture:** create the smallest frontend/backend/scraper package skeleton, configuration templates, dependency files, health/startup paths, and initial test layout. Do not yet rewrite the legacy extractor or implement the full search workflow.
3. **Phase 3 - People provider:** implement URL validation, URL-preserving pagination, selector configuration, normalized extraction, profile URL normalization, fixtures, and provider access-state handling.
4. **Phase 4 - SQLite persistence:** add SQLAlchemy models, repositories/services, Alembic migrations, indexes, lifecycle state handling, and cautious deduplication.
5. **Phase 5 - Search API:** add routes, background execution strategy, search/run progress, error reporting, deletion safeguards, and API tests.
6. **Phase 6 - React dashboard:** add URL input, max-page controls, validation, search creation, TanStack Query polling, and responsive layout.
7. **Phase 7 - Results and history:** add the professional table, pagination, sorting/search/filtering, history actions, empty/loading/error/partial states, and profile links.
8. **Phase 8 - Export:** add CSV and `openpyxl` XLSX exports with contract tests and no internal IDs/raw data by default.
9. **Phase 9 - Testing and hardening:** add unit, fixture, API, persistence, export, and end-to-end contract coverage; run Ruff, mypy where practical, TypeScript strict checks, pytest, and startup checks.
10. **Phase 10 - Cleanup and documentation:** update README commands and architecture docs, verify the replacement, then decide what legacy userscript/jobs files can be retired. Do not delete them before verification.

Each implementation phase should run its relevant tests, lint/type checks, and startup verification, then report changed files, dependencies, test results, and remaining issues. Phase 2 must wait for explicit instruction: `Continue with Phase 2`.

# Risks

- LinkedIn DOM structure and selectors can change without notice; semantic attributes and fixture-backed selector isolation reduce, but do not remove, this risk.
- LinkedIn may require login or present CAPTCHA/access restrictions. The application must stop and report these states rather than attempting bypasses.
- The existing scraper uses browser-local navigation and state, while the target requires server-side orchestration and durable status. This is a behavioral redesign, not a direct file move.
- The original implementation has no company extraction or `raw_data` contract, so company availability in result cards must be confirmed with fixtures before promising non-null values.
- Current extraction uses empty strings and `0` for absent fields; mapping these to nullable normalized fields must be explicit to avoid fabricating data.
- Current pagination assumes a `page` parameter. LinkedIn pagination may change, so pagination must be isolated and tested against preserved URL examples.
- The current buffer has no deduplication. Adding uniqueness constraints without a cautious identity strategy could merge distinct people or drop valid records.
- Browser userscript external dependencies and globals (`GM_*`, SheetJS, Turndown, `XLSX`) cannot be reused directly by the backend.
- Running long provider operations inside request handlers would make API behavior unreliable; the execution model and cancellation semantics need an explicit decision.
- SQLite is suitable for initial local use but has concurrency limitations; service/repository boundaries should keep a later PostgreSQL migration practical.
- The repository currently contains Jobs and AI behavior that can distract from the People-only V1 scope and create accidental security or product-scope regressions.
- No automated formatter/linter/typecheck baseline exists today, so the new architecture must establish quality gates without requiring an unrelated legacy rewrite.

# Open Technical Questions

- Which legitimate browser execution model will the first provider use: a separately controlled browser session, a browser extension/bridge, or another user-authorized mechanism? The answer determines provider boundaries and deployment requirements.
- Should the first backend execute one search synchronously through a managed background task, use a job queue, or use a local worker process? What concurrency and cancellation guarantees are required?
- How will the user authorize the provider session without exposing credentials, cookies, or session tokens to the backend or frontend?
- What exact LinkedIn result-card markup is currently available for `company_name`, `headline`, connection degree, profile image, education, and company URL? This must be answered with sanitized, realistic fixtures.
- Which LinkedIn hostname variants should be accepted (`www.linkedin.com` versus `linkedin.com`), and should HTTP be rejected in all environments?
- What is the expected default and maximum `max_pages`, and how should an omitted value behave?
- Should a repeated exact search URL create a new Search every time, reuse history, or offer both behaviors?
- What result sorting and filtering fields are required for the first dashboard release?
- What retention, deletion, and export authorization rules are needed for stored public result data?
- What is the preferred local development database path, and should the SQLite file be ignored by Git?
- When exactly should the generated legacy `lisesca.user.js` be rebuilt during migration, and should it remain a supported artifact until Phase 10?
