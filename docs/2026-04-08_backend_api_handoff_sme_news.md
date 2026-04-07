# Backend/API Handoff — Real Backend Integration for SME News Admin UI

## Goal

Implement the **real backend** for the SME news/reporting Admin UI so the current frontend can gradually replace its mock API layer with real data and actions.

This backend pass should focus first on:

- stable domain model
- clean API contracts
- persistence
- report thread persistence
- run tracking
- feedback persistence
- workspace/feed/settings management
- gradual mock-to-real integration
- explicit frontend mock removal as each real API slice lands

Do **not** start by overbuilding the ML/LLM/news-processing pipeline first.  
The immediate goal is to make the app real and integratable in **thin vertical slices**.

---

## Product context

The product is an Admin UI for managing customer workspaces that:

1. define a customer business profile
2. configure feeds/sources
3. process incoming content
4. generate reports
5. show reports as **threaded chat-like report conversations**
6. capture explicit feedback
7. later send reports by email

The frontend is already built as a **frontend-only Vite app** with a **mock API contract layer**.  
This backend implementation must now provide the real API and persistence to replace those mocks gradually.

The desired end state is not just "backend exists". The desired end state is:

- frontend no longer imports runtime data/actions from `src/mock-api`
- frontend no longer contains page-level demo behavior for production flows
- any temporary stubbed behavior lives behind backend endpoints, not in frontend runtime logic
- `src/mock-api/` is removed or made strictly dev-only and excluded from production builds once replacement is complete

---

## Primary objective

Build a **backend foundation** that supports:

- workspace CRUD
- profile/settings persistence
- feeds CRUD
- reports list/detail
- report thread messages
- content list/detail
- runs list/detail
- feedback persistence
- run-now trigger
- clean API contracts aligned with current frontend DTOs

Only after this backend/API foundation is stable should the heavier ingestion/ML/LLM pipeline be layered in.

---

## Non-goals for the initial backend pass

Do not make these the first priority:

- complex auth
- multi-tenant org/role systems
- email delivery
- real-time websockets
- advanced bandit/online learning
- full autonomous agent framework
- over-engineered workflow orchestration

These can come later.

However, removing frontend fake login/session behavior does require a minimal session/auth boundary.
That minimal boundary is in scope for initial integration even though full auth is not.

---

## Recommended stack

Use the architecture already agreed for MVP unless there is a strong repo-specific reason not to.

### Backend
- Python
- FastAPI
- Pydantic
- SQLAlchemy or SQLModel

### Database
- PostgreSQL
- pgvector

### Jobs / scheduling
- Celery
- Celery Beat
- Redis

### Content extraction / processing later
- httpx
- feedparser
- Trafilatura
- BeautifulSoup/lxml
- PyMuPDF

### Local ML later
- sentence-transformers
- scikit-learn
- BM25
- MinHash/SimHash

### LLM later
- one external LLM provider only for late-stage reasoning and report generation

If the codebase already has a strong justified variant, keep the spirit:
- typed API
- Postgres as source of truth
- async-friendly backend
- clear job model
- clean separation between CRUD/API foundation and processing pipeline

---

## Guiding implementation principles

- backend must match the frontend’s current IA and API needs
- implement in thin slices
- preserve strict typing and clear DTOs
- avoid speculative over-design
- keep report thread model first-class
- support debugging and traceability
- keep API shapes stable and easy to inspect
- make it easy to replace one frontend mock domain at a time
- do not leave frontend pages/components coupled to mock modules once a real slice exists
- move unavoidable early stub behavior behind backend endpoints rather than keeping it in client code
- keep backend persistence models free to differ from DB/storage naming, but freeze the frontend wire contract explicitly
- include tests at every pass
- keep manual QA instructions alongside automated tests

---

## Core backend responsibilities

### 1. Workspace management
Persist workspace metadata and expose CRUD APIs.

### 2. Workspace profile and settings
Persist business profile, relevance settings, themes, competitors, report preferences, and operational config.

### 3. Feed/source management
Persist feed/source configurations and expose CRUD APIs.

### 4. Content persistence
Persist fetched/processed content metadata and expose list/detail APIs even before full pipeline implementation is complete.

### 5. Reports
Persist report entities and expose report list/detail APIs.

### 6. Report thread
Persist thread messages so reports and feedback are modeled as a real thread, not just static documents.

### 7. Runs
Persist processing runs and expose run summary/detail APIs.

### 8. Feedback
Persist explicit feedback events, thumbs up/down, and free-text feedback.

### 9. Run-now trigger
Expose a backend action that creates a run and can later invoke the real processing pipeline.

---

## Data model

The backend should implement a stable relational domain model close to the following.

## Core entities

### Workspace
Top-level customer monitoring unit.

Suggested fields:
- id
- name
- customer_name
- status
- created_at
- updated_at

### WorkspaceProfile
Business context for relevance decisions.

Suggested fields:
- id
- workspace_id
- business_description
- products_services
- competitors_json
- priority_topics_json
- excluded_topics_json
- relevance_notes
- created_at
- updated_at

### WorkspaceSettings
Operational and report settings.

Suggested fields:
- id
- workspace_id
- schedule_cron
- schedule_timezone
- report_style
- report_length
- inclusion_threshold
- retention_days
- email_enabled_placeholder
- created_at
- updated_at

### FeedSource
Configured source/feed for a workspace.

Suggested fields:
- id
- workspace_id
- name
- source_type
- url
- is_enabled
- fetch_cadence
- status
- last_fetched_at
- tags_json
- created_at
- updated_at

### ContentItem
Normalized fetched/processed content item.

Suggested fields:
- id
- workspace_id
- feed_source_id nullable
- title
- url
- source_name
- content_type
- published_at
- author nullable
- summary_snippet nullable
- raw_text nullable
- extracted_metadata_json
- local_relevance_score nullable
- llm_score nullable
- final_score nullable
- status
- cluster_id nullable
- inclusion_reason nullable
- exclusion_reason nullable
- report_id nullable
- created_at
- updated_at

### ContentCluster
Semantic or dedup grouping.

Suggested fields:
- id
- workspace_id
- label nullable
- created_at
- updated_at

### Report
Generated report entity.

Suggested fields:
- id
- workspace_id
- title
- period_start
- period_end
- status
- markdown_body
- created_from_run_id nullable
- created_at
- updated_at
- published_at nullable

### ReportSourceItem
Join table linking reports to included content items.

Suggested fields:
- id
- report_id
- content_item_id
- created_at

### ReportThread
Top-level thread container if needed separately from Report.
You may merge this into Report if simpler, but preserve thread semantics clearly.

Suggested fields:
- id
- workspace_id
- report_id
- title
- status
- created_at
- updated_at

### ReportMessage
Thread message entity.

Suggested fields:
- id
- thread_id
- message_type
- author_type
- author_name nullable
- markdown_body
- metadata_json
- parent_message_id nullable
- sent_at
- created_at
- updated_at

Message types should support at least:
- report
- user_feedback
- agent_response
- system_status

### ProcessingRun
Pipeline run / run-now execution record.

Suggested fields:
- id
- workspace_id
- run_type
- status
- started_at
- finished_at nullable
- duration_ms nullable
- affected_counts_json
- error_summary nullable
- created_at
- updated_at

### ProcessingRunEvent
Timeline/log-like events for a run.

Suggested fields:
- id
- run_id
- step_name
- status
- message
- metadata_json
- created_at

### FeedbackEvent
Explicit feedback from user/admin.

Suggested fields:
- id
- workspace_id
- report_id nullable
- thread_id nullable
- message_id nullable
- content_item_id nullable
- feedback_type
- value
- note nullable
- created_at

### TopicPreference
Suggested fields:
- id
- workspace_id
- topic
- weight
- created_at
- updated_at

### SourcePreference
Suggested fields:
- id
- workspace_id
- source_name
- weight
- created_at
- updated_at

### EntityPreference
Suggested fields:
- id
- workspace_id
- entity_name
- weight
- created_at
- updated_at

---

## State models

The backend may keep richer internal states if needed, but the initial frontend wire contract should match the current frontend DTOs unless and until an explicit adapter is introduced.

## Workspace status
Wire contract for current frontend:
- active
- paused
- archived

## Feed status
Wire contract for current frontend:
- healthy
- warning
- error
- disabled

## Content status
Wire contract for current frontend:
- included
- excluded
- pending

Internal backend states may be richer, but must map explicitly to these values for the current UI contract.

## Report status
Wire contract for current frontend:
- draft
- published
- archived

## Run status
Wire contract for current frontend:
- running
- success
- failed

Internal backend states such as `queued` are allowed, but must not leak into the current frontend DTO without an explicit frontend adapter/update.

## Message role
Wire contract for current frontend:
- system
- user
- agent

## Message type
Suggested internal or extended backend classification:
- report
- user_feedback
- agent_response
- system_status

---

## Frontend wire contract freeze

Unless there is an explicit adapter layer, the initial API responses used by the current frontend should follow the field names and enum values already present in `src/types`.

Rules:

- use camelCase field names in wire DTOs consumed by the current frontend
- backend persistence/schema names may remain snake_case internally
- do not silently substitute semantically similar names on the wire

Examples that should match the current frontend contract:

- Workspace DTO:
  - `customer`, not `customer_name`
  - `createdAt` and `updatedAt`, not `created_at` / `updated_at`
  - `feedCount`, `lastReportAt`, `nextRunAt`
- Run DTO:
  - `type`, not `run_type`
  - `completedAt`, not `finished_at`
  - `error`, not `error_summary`
  - `affectedCounts`
- Content DTO:
  - `source`, `sourceUrl`, `publishedAt`
  - `relevanceScore`, `llmScore`, `finalScore`
  - `inclusionReason`, `exclusionReason`
- Report/thread DTO:
  - `createdAt`, `updatedAt`, `periodStart`, `periodEnd`, `runId`
  - message field `role`, not `author_type`
  - message field `content`, not `markdown_body`

If the backend prefers different external DTOs, the handoff must explicitly assign ownership for a frontend adapter layer before implementation starts.

---

## API design principles

- keep endpoints explicit and boring
- prefer predictable REST-style APIs
- return DTOs that map closely to frontend contract shapes
- support list/detail patterns
- support future pagination even if MVP starts simple
- include created/updated timestamps
- include status fields consistently
- avoid hiding essential state in opaque blobs unless justified

---

## Required API surface

## Session / auth minimum boundary

Full auth is not the priority, but the backend/frontend integration must remove frontend-side fake login and fake session state.

Choose one of these approaches explicitly and document it in implementation:

- preferred: minimal real session endpoints
- fallback: explicit backend-served dev-only stub session

Required minimum API if using session endpoints:

### POST /api/session/login
Accept credentials, establish session, and return current user/session payload.

### GET /api/session/me
Return current authenticated user/session payload for route gating and header rendering.

### POST /api/session/logout
Invalidate the session.

Minimum user/session payload should support the current frontend store shape:

- `id`
- `username`
- `displayName`
- `role`

If this is intentionally stubbed in early phases, the stub must still be backend-served and documented. The frontend must not synthesize a user object locally for production flows.

---

## Workspaces

### GET /api/workspaces
Return workspace summaries.

### POST /api/workspaces
Create workspace.

### GET /api/workspaces/{workspace_id}
Return the base Workspace DTO used by the current frontend.

Do not overload this endpoint with dashboard aggregates unless the response shape is explicitly defined and the frontend adapter is updated accordingly.

The current frontend overview page composes its dashboard from multiple endpoints rather than from one aggregate payload.

### PATCH /api/workspaces/{workspace_id}
Update workspace summary metadata.

### DELETE /api/workspaces/{workspace_id}
Archive or soft-delete workspace.

---

## Workspace profile

### GET /api/workspaces/{workspace_id}/profile
Get workspace profile.

### PUT /api/workspaces/{workspace_id}/profile
Replace/update workspace profile.

---

## Workspace settings

### GET /api/workspaces/{workspace_id}/settings
Get workspace settings.

### PUT /api/workspaces/{workspace_id}/settings
Replace/update workspace settings.

---

## Feeds

### GET /api/workspaces/{workspace_id}/feeds
List feeds.

### POST /api/workspaces/{workspace_id}/feeds
Create feed.

### GET /api/feeds/{feed_id}
Get feed detail.

### PATCH /api/feeds/{feed_id}
Update feed.

### DELETE /api/feeds/{feed_id}
Delete or disable feed.

### POST /api/feeds/{feed_id}/test
Test fetch/validate feed configuration.
May be mocked initially but return realistic result.

---

## Content

### GET /api/workspaces/{workspace_id}/content
List content items with filters.

Support filters such as:
- date range
- source
- status
- included_in_report
- min_score
- max_score

### GET /api/content/{content_item_id}
Get content detail.

---

## Reports

### GET /api/workspaces/{workspace_id}/reports
List reports / report threads.

### GET /api/reports/{report_id}
Get report detail.

### POST /api/reports/{report_id}/regenerate
Regenerate report.
May be stubbed initially if full pipeline is not ready, but keep API shape.

---

## Report threads

### GET /api/workspaces/{workspace_id}/report-threads
List thread summaries if kept separate from reports.

If you merge report/thread concept, keep the frontend mapping clean.

### GET /api/report-threads/{thread_id}
Get thread detail with messages.

### POST /api/report-threads/{thread_id}/messages
Post user feedback message into the thread.

Request should support:
- markdown_body
- optional metadata

Response should return:
- persisted user message
- optionally a mocked or generated agent response message for early phase
- thread updated metadata

If a wrapper object is returned, define it explicitly and keep it stable, for example:
- `userMessage`
- `agentMessage` nullable
- `thread`

### POST /api/report-messages/{message_id}/thumb
Persist thumb up/down feedback for a report message.

Request:
- value: up | down

---

## Runs

### GET /api/workspaces/{workspace_id}/runs
List runs.

### GET /api/runs/{run_id}
Get run detail with timeline/events.

### POST /api/workspaces/{workspace_id}/run-now
Create a new run-now execution.

In early phases:
- create run record
- create initial run events
- optionally create stub report/thread for testing
Later this will trigger real pipeline jobs.

---

## Feedback

### GET /api/workspaces/{workspace_id}/feedback
List feedback events only.

This should support the current feedback timeline UI.

### GET /api/workspaces/{workspace_id}/feedback/summary
Return aggregated feedback summary and preference rollups.

This should support the current feedback summary cards and preference panels.

### POST /api/workspaces/{workspace_id}/feedback
Persist free-form or structured feedback event.

### PUT /api/workspaces/{workspace_id}/preferences/topics
Bulk update topic preferences.

### PUT /api/workspaces/{workspace_id}/preferences/sources
Bulk update source preferences.

### PUT /api/workspaces/{workspace_id}/preferences/entities
Bulk update entity preferences.

---

## DTO alignment requirement

Before coding deeply, compare the current frontend’s mock DTOs to the backend response models.

The backend should either:
- align exactly with frontend DTOs, or
- introduce a thin frontend adapter layer with explicit mapping

Do not let implicit mismatches accumulate.

In addition to DTO alignment, enforce frontend boundary alignment:

- page and component code must not import runtime DTOs or helpers from `src/mock-api`
- shared DTO/filter types should live in a neutral location such as `src/types` or a dedicated shared contract module
- `src/lib/api.ts` should become the sole frontend API boundary and should point to real HTTP calls once a slice is integrated
- session/login behavior must be driven by backend responses rather than frontend-created user/session objects

---

## Implementation strategy

Implement in thin passes.  
Each pass must include:
- implementation
- automated tests
- manual test notes
- acceptance criteria

Do not jump to later passes if earlier passes are unstable.

---

# Pass 1 — Backend skeleton, schema, and workspace foundation

## Scope
Set up backend project structure, database, migrations, core models, minimal session boundary, and workspace CRUD/profile/settings foundation.

## Implementation tasks
- create backend service structure
- configure FastAPI app
- configure DB connection
- set up migrations
- define core models:
  - Workspace
  - WorkspaceProfile
  - WorkspaceSettings
- implement DTOs and validation
- implement minimal session/user DTOs
- implement endpoints:
  - POST /api/session/login
  - GET /api/session/me
  - POST /api/session/logout
  - GET /api/workspaces
  - POST /api/workspaces
  - GET /api/workspaces/{id}
  - PATCH /api/workspaces/{id}
  - DELETE /api/workspaces/{id}
  - GET /api/workspaces/{id}/profile
  - PUT /api/workspaces/{id}/profile
  - GET /api/workspaces/{id}/settings
  - PUT /api/workspaces/{id}/settings
- add seed/dev fixture setup if useful
- add health endpoint
- add clear config/env handling

## Automated tests
- session login/me/logout tests
- model creation tests
- workspace CRUD API tests
- profile/settings validation tests
- archive/delete behavior tests
- not-found tests
- invalid payload tests

## Manual test plan
- login
- refresh authenticated app state
- logout
- create workspace
- edit workspace
- view workspace detail
- edit profile
- edit settings
- archive workspace
- verify DB persistence

## Acceptance criteria
- backend boots cleanly
- migrations run cleanly
- minimal session endpoints work or an explicit backend-served stub session is documented and working
- workspace/profile/settings endpoints work
- responses are typed and stable
- validation failures are handled clearly
- tests pass

---

# Pass 2 — Feeds CRUD and API contract stabilization

## Scope
Implement feed/source management fully enough for the frontend Feeds page to switch from mock to real API.

## Implementation tasks
- define FeedSource model
- implement endpoints:
  - GET /api/workspaces/{id}/feeds
  - POST /api/workspaces/{id}/feeds
  - GET /api/feeds/{feed_id}
  - PATCH /api/feeds/{feed_id}
  - DELETE /api/feeds/{feed_id}
  - POST /api/feeds/{feed_id}/test
- support realistic feed statuses
- define source types and validation
- implement basic feed test behavior
- align DTOs with frontend feed forms/table

## Automated tests
- feed create/list/update/delete tests
- validation tests for source type and URL
- feed test endpoint tests
- workspace/feed relationship tests

## Manual test plan
- add multiple feed types
- edit and disable feeds
- test feed validation endpoint
- verify list/detail/update behavior in UI or API client

## Acceptance criteria
- Feeds page can be wired to real backend
- feed lifecycle is fully supported
- DTOs are stable
- tests pass

---

# Pass 3 — Reports, report threads, and feedback persistence

## Scope
Make reports and report-thread UX real from a persistence/API perspective.

## Implementation tasks
- define models:
  - Report
  - ReportSourceItem
  - ReportThread or equivalent
  - ReportMessage
  - FeedbackEvent
- implement endpoints:
  - GET /api/workspaces/{id}/reports
  - GET /api/reports/{report_id}
  - GET /api/report-threads/{thread_id}
  - POST /api/report-threads/{thread_id}/messages
  - POST /api/report-messages/{message_id}/thumb
  - GET /api/workspaces/{id}/feedback
  - GET /api/workspaces/{id}/feedback/summary
  - POST /api/workspaces/{id}/feedback
- preserve report-thread semantics clearly
- implement persisted thumbs up/down
- implement persisted free-text feedback messages
- for early phase, when feedback message is posted:
  - store user message
  - optionally create mocked agent response record
- include report metadata needed by frontend thread header

## Automated tests
- report list/detail tests
- thread detail tests
- message creation tests
- thumb feedback tests
- feedback summary tests
- feedback list/create tests
- invalid thread/report/message id tests

## Manual test plan
- open report list
- open report thread
- post feedback message
- thumb up/down a report message
- open feedback page summary
- verify stored messages and feedback events
- verify thread reload shows persisted history

## Acceptance criteria
- report thread becomes real, not mock-only
- thumbs and free-text feedback are persisted
- reports list/detail APIs are stable
- feedback page can be wired to real backend
- feedback summary contract is stable
- tests pass

---

# Pass 4 — Content and runs visibility

## Scope
Implement the operator/debugging APIs for Content and Runs.

## Implementation tasks
- define models:
  - ContentItem
  - ContentCluster
  - ProcessingRun
  - ProcessingRunEvent
- implement endpoints:
  - GET /api/workspaces/{id}/content
  - GET /api/content/{content_item_id}
  - GET /api/workspaces/{id}/runs
  - GET /api/runs/{run_id}
- implement filtering for content list
- include detail fields needed by Content detail view:
  - score breakdown
  - reasons
  - cluster/report links
- include run event timeline for Run detail
- add seed fixtures or bootstrap data for dev/testing
- wire run summaries to report/content linkage where possible

## Automated tests
- content list/detail tests
- content filtering tests
- run list/detail tests
- run event tests
- not-found tests
- response shape tests

## Manual test plan
- inspect content list with filters
- inspect content detail
- inspect runs list
- inspect run detail timeline and errors
- verify frontend can replace mock data for these pages

## Acceptance criteria
- Content page can be wired to real backend
- Runs page can be wired to real backend
- operator/debugging information is preserved
- tests pass

---

# Pass 5 — Run-now trigger and thin vertical integration

## Scope
Create a usable run-now backend action and start replacing frontend mock domains with real API slices.

## Implementation tasks
- implement POST /api/workspaces/{id}/run-now
- create ProcessingRun record
- create initial ProcessingRunEvent timeline entries
- optionally create a stub report/thread for early testing
- integrate frontend domains gradually:
  - workspaces
  - profile/settings
  - feeds
  - reports/thread
  - content
  - runs
  - feedback
- add adapter/mapping only where necessary
- preserve frontend behavior and UX
- remove the replaced frontend mock imports and mock runtime logic for each integrated slice
- keep temporary stub behavior on the backend side only where the real pipeline is not ready yet

## Automated tests
- run-now endpoint tests
- run creation + run event tests
- integration tests for key slices
- API contract tests for frontend-critical payloads
- frontend integration tests or smoke checks verifying the real client path is used instead of `src/mock-api`

## Manual test plan
- create workspace
- configure profile/settings/feeds
- trigger run-now
- verify run is created
- verify report/thread appears if stubbed
- verify feedback and thread interactions persist
- verify replaced frontend pages no longer depend on `src/mock-api`

## Acceptance criteria
- frontend can replace major mock slices with real backend
- run-now works and is traceable
- no critical contract mismatch remains
- replaced frontend slices no longer import from `src/mock-api`
- replaced frontend slices do not contain client-side fake business logic for those flows
- tests pass

---

# Pass 5.5 — Frontend mock removal and production-boundary cleanup

## Scope
After the core slices are wired to the real backend, remove remaining frontend-resident mock/demo logic so the production frontend is cleanly separated from backend behavior.

## Implementation tasks
- update `src/lib/api.ts` to use real HTTP-backed modules rather than `@/mock-api`
- remove page/component imports from `src/mock-api`
- move shared filter/DTO types out of `src/mock-api` into neutral shared modules if still needed by the frontend
- remove or replace demo-only client logic in production flows, including:
  - mock login acceptance of arbitrary credentials
  - client-created fake user/session objects for production auth flow
  - demo-only success toasts/actions that imply non-persistent backend behavior
- if authentication is still intentionally deferred, document a clear temporary approach and keep any stub at the backend/API boundary rather than hidden in page logic
- remove `src/mock-api/` entirely when no longer needed, or gate it to local dev/testing only and exclude it from production builds
- update README and run instructions to reflect the real backend dependency and any remaining explicit temporary limitations

## Automated tests
- tests verifying `src/lib/api.ts` uses the real client path
- tests or checks preventing imports from `src/mock-api` in production frontend code
- smoke tests for login, workspace CRUD, feeds, reports/thread, content, runs, and feedback against the real backend

## Manual test plan
- inspect the built frontend bundle path and verify it uses the real backend
- verify login behavior is no longer "any non-empty credentials" unless explicitly documented as a backend-served temporary stub
- verify archive/settings/run-now/report feedback actions persist through the backend
- verify no demo-only UI copy remains in production-facing flows

## Acceptance criteria
- `src/lib/api.ts` no longer imports from `@/mock-api`
- frontend pages/components do not import from `src/mock-api`
- no client-side fake business logic remains in production flows
- login/session state is sourced from backend responses or an explicit backend-served stub session
- any remaining stubbed behavior exists only behind backend endpoints and is explicitly documented
- `src/mock-api/` is removed or excluded from production builds
- tests pass

---

# Pass 6 — Processing pipeline foundation

## Scope
Only after CRUD/API foundation is stable, add the real content-processing skeleton.

## Implementation tasks
- set up Celery worker and Beat
- implement feed fetch job skeleton
- implement content normalization pipeline skeleton
- create ContentItem records from real fetches
- create initial run events around fetch/parse/store phases
- add report generation stub or simple deterministic summarizer first if needed
- keep architecture ready for later:
  - dedup/clustering
  - local ML filtering
  - LLM scoring
  - final report generation

You do not need full intelligence quality in this pass yet.
The goal is a working backend pipeline skeleton that populates real content and runs.

## Automated tests
- job creation tests
- content ingestion persistence tests
- run event generation tests
- scheduling smoke tests where feasible
- parser/extractor unit tests where applicable

## Manual test plan
- configure feed
- trigger run-now
- verify content items are created
- verify run events update
- verify report generation path is at least stub-functional

## Acceptance criteria
- backend can ingest real source data at basic level
- content starts flowing into the system
- run timeline shows meaningful steps
- tests pass

---

# Pass 7 — Relevance pipeline and report generation quality

## Scope
Add the first meaningful intelligence layer after the system foundation is stable.

## Implementation tasks
- implement dedup/clustering skeleton
- implement first-pass filtering:
  - rules
  - BM25
  - embeddings similarity
- persist scores and reasons
- add LLM-based shortlist reasoning only after cheap filtering
- generate report markdown
- create Report, ReportThread, ReportMessage records from real runs
- wire report source items
- update feedback persistence paths if needed

## Automated tests
- scoring pipeline unit tests
- report creation tests
- content-to-report linkage tests
- thread/message creation tests
- failure-path tests around LLM or pipeline fallback behavior

## Manual test plan
- trigger run-now with real feeds
- inspect content scores
- inspect report
- inspect thread
- leave feedback
- verify data persists correctly

## Acceptance criteria
- system can generate a real report from ingested content
- report thread flow becomes fully end-to-end
- content/report linkage is traceable
- tests pass

---

## Testing strategy

Use multiple layers of testing.

### 1. Unit tests
For:
- schema/model validation
- service-layer logic
- DTO mapping
- scoring utilities
- pipeline helpers

### 2. API tests
For:
- endpoint success cases
- validation failures
- not-found cases
- state transitions
- contract stability

### 3. Integration tests
For:
- DB-backed endpoint behavior
- run-now flow
- report thread persistence
- feedback persistence
- content/report/run relationships

### 4. Manual QA
For:
- frontend integration checks
- workflow sanity
- inspectability/debuggability
- thread UX behavior with real backend

---

## API contract verification requirement

At the end of each pass that exposes endpoints used by the frontend:

- compare real response JSON against current frontend mock contract expectations
- update backend or add explicit adapter mapping
- do not silently break the frontend
- keep a small contract test fixture if useful

---

## Error handling requirements

All endpoints should provide:
- clear validation error responses
- consistent not-found behavior
- consistent status/error shape where practical
- safe handling of internal failures
- run failure persistence for background job problems

Do not swallow errors in ways that make operator debugging harder.

---

## Observability requirements

Even in MVP, implement minimal observability:

- structured application logs
- request logging
- run event persistence
- clear error summaries on failed runs
- timestamps everywhere important

This system is operational by nature; it must be debuggable.

---

## Migration and seed requirements

- use proper DB migrations
- keep schema evolution explicit
- include dev seed/bootstrap data if helpful
- seed data should be realistic enough to test frontend integration
- do not require hand-editing DB records for basic development

---

## Suggested repository structure

A reasonable shape would be:

- `backend/app/main.py`
- `backend/app/api/...`
- `backend/app/models/...`
- `backend/app/schemas/...`
- `backend/app/services/...`
- `backend/app/db/...`
- `backend/app/tasks/...`
- `backend/app/tests/...`
- `backend/alembic/...` or equivalent
- `backend/README.md`

If repo structure already exists, adapt sensibly without breaking clarity.

---

## Manual end-to-end scenarios

These scenarios should pass before calling the backend foundation ready.

### Scenario 1 — Workspace setup
- create workspace
- edit profile
- edit settings
- add feeds
- verify persistence

### Scenario 2 — Reports and feedback
- create or seed a report
- open report detail/thread
- send free-text feedback
- thumb up/down a report message
- verify thread and feedback persistence

### Scenario 3 — Content and runs inspection
- seed or create content items
- inspect content list/detail
- create or trigger runs
- inspect run list/detail
- verify operator data is useful

### Scenario 4 — Run-now integration
- trigger run-now
- verify run record created
- verify run events created
- verify downstream stub report/thread behavior if enabled

### Scenario 5 — Frontend mock replacement
- replace one frontend domain at a time with real backend
- verify no regression in UX flow
- verify loading/error states remain correct

### Scenario 6 — Frontend production-boundary audit
- confirm no frontend runtime imports from `src/mock-api`
- confirm no demo-only login/auth shortcuts remain in production codepaths
- confirm remaining stubbed behavior, if any, is served by backend endpoints and documented

---

## Acceptance bar for “move to next step”

You can move past the backend foundation stage when all of the following are true:

- workspace/profile/settings APIs are stable
- feeds APIs are stable
- reports/thread APIs are stable
- feedback persistence works
- content/runs APIs are stable
- run-now works
- frontend can replace core mock slices with real API
- frontend no longer contains production-path mock/demo business logic
- frontend no longer depends on `src/mock-api` at runtime
- automated tests pass
- manual end-to-end scenarios pass

Only then should major effort shift toward advanced intelligence/pipeline quality.

---

## Deliverables

Produce:

1. real backend service with typed APIs
2. migrations and schema
3. persistence for workspaces/profile/settings/feeds/reports/threads/messages/content/runs/feedback
4. run-now trigger
5. tests per pass
6. manual QA notes per pass
7. updated README with:
   - how to run backend
   - env config
   - migrations
   - test commands
   - API overview
   - frontend integration notes

---

## Final instruction

Do not optimize for flashy AI behavior first.

Optimize for:
- correct domain model
- stable APIs
- persistence
- report-thread correctness
- debuggability
- frontend integration safety

Build the backend foundation first, then layer in the real processing pipeline and intelligence in later passes.
