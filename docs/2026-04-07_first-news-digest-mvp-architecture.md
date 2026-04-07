# News Digest MVP — Admin-UI-First Architecture

## 1. Goal

Build an MVP system for SME owners that:

- collects news/articles/papers from configured sources
- filters items relevant to a customer’s business
- generates a scheduled report
- stores the report in a centralized Admin UI
- allows iterative tuning via feedback
- defers email delivery until later

This MVP should optimize for:

- centralized debugging
- relevance quality
- explainability
- low operational complexity
- easy future extension to email delivery

---

## 2. MVP product direction

For MVP, use an **Admin-UI-first** design instead of sending reports directly by email.

### Why this is better for MVP

This approach makes it easier to:

- inspect raw fetched content
- understand why items were filtered in/out
- review generated reports before delivery
- compare results across runs
- debug ingestion, ranking, and summarization separately
- iterate quickly on prompts, rules, and configuration

Email can be added later as a simple delivery layer that forwards an already-generated report.

---

## 3. Core product model

The top-level entity is a **Workspace**.

A workspace represents one customer/business monitoring setup.

Each workspace contains:

- business profile
- topic priorities
- competitor list
- source/feed configuration
- report schedule
- prompt/config preferences
- report history
- feedback history

---

## 4. High-level workflow

1. Admin creates a workspace
2. Admin configures business profile, priorities, feeds, competitors, and schedule
3. System fetches content on schedule
4. System parses and normalizes content
5. System deduplicates and clusters similar items
6. System performs first-pass filtering using local ML + rules
7. System uses LLM on shortlisted items for deeper scoring/explanation
8. System generates a report in Markdown
9. System stores the report in the database
10. Report appears in the Report tab
11. Admin can inspect the report in rendered GitHub-style Markdown preview
12. Admin can inspect source items used and feedback/tune the workspace
13. Later, email delivery can forward the generated report to the customer

---

## 5. Recommended MVP UI / information architecture

### 5.1 Workspaces page

Purpose:
- list all customers/workspaces
- create new workspace
- inspect health/status at a glance

Columns:
- workspace name
- customer/company name
- status
- next scheduled run
- last run time
- last report time

Actions:
- create workspace
- open workspace
- run now

---

### 5.2 Workspace detail tabs

#### A. Profile
Contains:
- business name
- business description
- products/services
- competitors
- important themes/topics
- excluded topics
- notes for report relevance

#### B. Feeds
Contains:
- RSS/news sources
- competitor URLs
- papers/blog feeds
- source status
- fetch settings
- source enable/disable toggles

#### C. Content
Contains fetched content items and their processing status.

Suggested fields:
- title
- source
- published_at
- content type
- dedup cluster id
- local relevance score
- LLM score
- final score
- status (filtered out / shortlisted / included)
- explanation

This tab is important for debugging.

#### D. Reports
Contains scheduled/generated reports.

Suggested list fields:
- report title
- period/date
- status
- created_at
- run id

Detail page:
- rendered Markdown preview
- raw Markdown tab
- source items used
- regenerate action

#### E. Feedback
Contains:
- explicit feedback on report quality
- feedback on individual items
- topic/source/entity preferences
- report-style preferences

#### F. Runs
Contains:
- fetch runs
- processing runs
- report generation runs
- status
- duration
- error details
- logs

This tab is also important for debugging.

---

## 6. Report behavior

For MVP, reports should be generated and stored as Markdown.

Each report should include:

- executive summary
- top highlights
- opportunities
- risks
- competitor/market signals
- optional “worth watching” items
- links to source items

Suggested report states:
- draft
- generated
- reviewed
- published

For MVP, “published” means visible in the UI report list.

---

## 7. Workflow states

### 7.1 Content item states

- fetched
- parsed
- deduped
- filtered_out
- shortlisted
- included_in_report

### 7.2 Run states

- queued
- running
- succeeded
- failed

### 7.3 Report states

- draft
- generated
- reviewed
- published

---

## 8. ML / LLM responsibilities

### 8.1 No ML / No LLM
Use deterministic logic for:

- workspace creation/config
- source fetching
- scheduling
- storage
- report persistence
- UI rendering
- feedback capture
- email forwarding later

### 8.2 Local ML
Use local ML for first-pass screening:

#### Dedup / clustering
- MinHash or SimHash for near-duplicate detection
- sentence embeddings + cosine similarity for semantic grouping
- DBSCAN or Agglomerative Clustering for clustering

#### First-pass relevance filtering
Use:
- rules / keywords
- BM25
- embeddings similarity
- optional simple classifier:
  - Logistic Regression
  - Linear SVM
  - LightGBM (later if enough data)

### 8.3 LLM
Use LLM only for:

- deeper relevance judgment on shortlisted items
- “why this matters” explanation
- executive report generation
- action/risk/opportunity wording

This keeps cost and complexity lower.

---

## 9. Best-fit stack for this MVP

### 9.1 Backend

Recommended:
- **Python**
- **FastAPI**
- **SQLAlchemy** or **SQLModel**
- **Pydantic**

Why:
- strong ecosystem for content extraction, NLP, embeddings, ranking, and ML
- simple integration with LLM APIs
- easy worker/job implementation
- fast MVP iteration

---

### 9.2 Database

Recommended:
- **PostgreSQL**
- **pgvector**

Why:
- source of truth for workspaces, feeds, content, reports, feedback, and runs
- vector support for semantic similarity and retrieval
- avoids adding a separate vector DB in MVP

---

### 9.3 Queue / scheduler

Recommended:
- **Celery**
- **Celery Beat**
- **Redis**

Why:
- fetch jobs
- parse/process jobs
- scoring jobs
- report generation jobs
- periodic scheduling

---

### 9.4 Content ingestion / extraction

Recommended:
- **httpx**
- **feedparser**
- **Trafilatura**
- **BeautifulSoup / lxml**
- **PyMuPDF** for PDFs when needed

---

### 9.5 Local ML / ranking

Recommended:
- **sentence-transformers**
- **scikit-learn**
- **rank-bm25** or equivalent BM25 package
- **SimHash/MinHash library**
- optional **LightGBM** later

Recommended layered pipeline:
1. rules/keywords
2. BM25
3. embedding similarity
4. optional simple classifier
5. LLM only on shortlisted items

---

### 9.6 LLM integration

Recommended:
- one external LLM provider for:
  - final relevance reasoning
  - item explanation
  - report writing

Guideline:
- do not use the LLM for the whole pipeline
- place it late in the flow after local filtering

---

### 9.7 Frontend / Admin UI

Recommended:
- **Next.js**
- **React**
- **TypeScript**
- **Tailwind CSS**
- Markdown renderer with GitHub-style preview

---

### 9.8 Deployment

Recommended MVP deployment via Docker Compose:
- api
- worker
- scheduler
- postgres
- redis
- frontend

Optional later:
- local embedding service
- object storage
- monitoring stack

---

## 10. Best-fit architecture summary

### MVP stack summary
- **Backend:** Python + FastAPI
- **DB:** PostgreSQL + pgvector
- **Workers / scheduling:** Celery + Celery Beat + Redis
- **Extraction:** Trafilatura + feedparser + httpx + BeautifulSoup/lxml
- **Local ML:** sentence-transformers + scikit-learn + BM25 + MinHash/SimHash
- **LLM:** one external LLM provider for shortlist reasoning and report generation
- **Frontend:** Next.js + React + TypeScript + Tailwind
- **Deployment:** Docker Compose

This is the best balance of:
- speed to MVP
- maintainability
- debuggability
- cost control
- future extensibility

---

## 11. Suggested database entities

Core entities:
- Workspace
- WorkspaceProfile
- FeedSource
- ContentItem
- ContentCluster
- ProcessingRun
- Report
- ReportSourceItem
- FeedbackEvent
- TopicPreference
- SourcePreference
- EntityPreference
- SummaryPreference

Example relationships:
- Workspace has many FeedSources
- Workspace has many ContentItems
- Workspace has many Reports
- Report has many ReportSourceItems
- Workspace has many FeedbackEvents
- Workspace has many Preferences
- ProcessingRun belongs to Workspace

---

## 12. Suggested API surface

### Workspace
- create workspace
- list workspaces
- get workspace detail
- update workspace profile/config
- delete/archive workspace

### Feeds
- add feed
- update feed
- enable/disable feed
- list feeds
- test feed fetch

### Content
- list content items
- get content item detail
- filter by status/date/source
- inspect scores/explanations

### Reports
- list reports
- get report detail
- get raw markdown
- regenerate report
- run now
- publish report

### Feedback
- mark useful/not useful
- more like this / less like this
- update topic/source/entity preferences
- update report style preferences

### Runs
- list runs
- get run detail
- inspect logs/errors

---

## 13. Suggested MVP implementation phases

### Phase 1 — Core workspace + report pipeline
- workspace CRUD
- feed CRUD
- scheduled fetch jobs
- content extraction/storage
- reports tab with Markdown preview

### Phase 2 — Filtering + scoring
- dedup/clustering
- first-pass local ML relevance
- shortlist generation
- LLM-based report generation

### Phase 3 — Debuggability and tuning
- content tab
- runs/logs tab
- source-item traceability
- regenerate / run-now actions

### Phase 4 — Feedback learning
- explicit feedback capture
- preference updates
- improved ranking behavior

### Phase 5 — Delivery layer later
- manual email send
- scheduled email forwarding
- future Slack/Telegram delivery if desired

---

## 14. Recommended MVP decisions

Keep for MVP:
- workspace-based architecture
- centralized Admin UI
- reports stored in DB
- Markdown report detail page
- content inspection tab
- runs/logs tab
- local ML first-pass filtering
- LLM only on shortlisted items

Defer until later:
- customer-facing email automation
- chat assistant UX
- complex agent memory system
- autonomous multi-channel bot
- separate vector DB
- Temporal
- advanced online learning/bandits

---

## 15. Final recommendation

For MVP, the best direction is:

- **Admin UI first**
- **Workspace-based**
- **Centralized report generation**
- **Stored Markdown reports**
- **Content + Runs tabs for debugging**
- **Python/FastAPI/Postgres/pgvector/Celery/Redis/Next.js stack**
- **Local ML for first-pass filtering**
- **LLM only for shortlist explanation and final report generation**
- **Email deferred to later as a delivery layer**

This gives the cleanest path to validating the core value of the product:
**whether the system can consistently produce useful, relevant daily business reports.**
