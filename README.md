# SME News Admin

A full-stack admin dashboard for managing AI-powered news intelligence workspaces. The application features a React frontend, a FastAPI backend, PostgreSQL for persistence, Redis for task transport, and Celery worker/Beat services for the Pass 6 processing skeleton.

## Features

- **Workspace Management** — Create and manage customer reporting environments
- **Business Profiles** — Define intelligence context with products, competitors, and priority themes
- **Feed Management** — Configure RSS feeds, website scrapers, competitor pages, and blog sources
- **Content Inspection** — Review fetched content with multi-factor relevance scoring and source attribution
- **Intelligence Reports** — Chat-style report threads with source inspection, voting, and regeneration
- **Operational Runs** — Monitor intelligence cycle execution with step-by-step timelines and error tracking
- **Feedback & Preferences** — Transparency dashboard showing how user feedback influences report tuning
- **Settings** — Configure scheduling, scoring thresholds, data retention, and email delivery

## Quick Start

### Prerequisites

- Node.js 18+ and npm
- Python 3.11+ with pip
- Docker and Docker Compose (for containerized deployment)

### Install & Run (Docker)

```bash
make up
```

This starts all services (frontend, backend, PostgreSQL, Redis, Celery worker, Celery Beat). On first start, the backend automatically runs database migrations and seeds initial data.

- **Frontend**: [http://localhost:3000](http://localhost:3000)
- **API docs**: [http://localhost:8000/api/docs](http://localhost:8000/api/docs)

Sign in with the configured administrator account. For a fresh local `.env`, the default dev credentials are `admin` / `admin`; change `ADMIN_USERNAME` and `ADMIN_PASSWORD` before using a shared deployment.

### Local Development

```bash
# Frontend
npm install
npm run dev

# Backend API
cd backend
pip install -r requirements.txt
make backend

# Optional background services for Pass 6
make worker
make beat
```

### Production Build

```bash
make build
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://sme:sme@localhost:5432/sme_news` |
| `REDIS_URL` | Redis connection string for Celery broker/backend | `redis://localhost:6379/0` |
| `CORS_ORIGINS` | Allowed CORS origins (comma-separated) | `http://localhost:3000` |
| `DEBUG` | Enable debug logging | `false` |
| `TESTING` | Skip auto-migration on startup (set to `1` for tests) | — |

## API Overview

The backend exposes a REST API at `/api/`. Key endpoint groups:

| Group | Base Path | Description |
|-------|-----------|-------------|
| **Session** | `/api/session` | Login, logout, session status |
| **Workspaces** | `/api/workspaces` | Workspace CRUD, overview stats |
| **Feeds** | `/api/workspaces/{id}/feeds` | Feed source CRUD, toggle, test |
| **Content** | `/api/workspaces/{id}/content` | Content items list and detail |
| **Reports** | `/api/workspaces/{id}/reports` | Report threads, messages, feedback |
| **Runs** | `/api/workspaces/{id}/runs` | Processing runs, trigger run-now, inspect run links |
| **Feedback** | `/api/workspaces/{id}/feedback` | Feedback events and preferences |
| **Preferences** | `/api/workspaces/{id}/preferences` | Topic, source, entity preferences |
| **Settings** | `/api/workspaces/{id}/settings` | Schedule, scoring, retention config |

Interactive API documentation is available at `/api/docs` (Swagger UI) and `/api/redoc` (ReDoc).

## Project Structure

```
├── backend/                          # FastAPI backend
│   ├── app/
│   │   ├── api/                      # API route handlers
│   │   ├── db/                       # Database session and base
│   │   ├── models/                   # SQLAlchemy ORM models
│   │   ├── schemas/                  # Pydantic request/response schemas
│   │   ├── services/                 # Business logic layer
│   │   ├── tasks/                    # Celery tasks and pipeline helpers
│   │   ├── celery_app.py             # Celery worker/Beat configuration
│   │   ├── seed.py                   # Database seed script
│   │   ├── config.py                 # Settings from environment
│   │   └── main.py                   # FastAPI app setup and startup
│   ├── alembic/                      # Database migrations
│   ├── tests/                        # pytest test suite
│   └── requirements.txt
├── src/                              # React frontend
│   ├── components/                   # Shared UI components
│   ├── hooks/                        # Custom React hooks
│   ├── lib/                          # API client, schemas, store, utils
│   ├── pages/                        # Route-level page components
│   ├── router/                       # React Router configuration
│   ├── types/                        # Domain type definitions
│   ├── globals.css                   # Tailwind CSS v4 imports
│   └── main.tsx                      # App entry point
├── Makefile                          # Development commands
└── docker-compose.yml                # Container orchestration
```

## Routes

| Path | Page | Description |
|------|------|-------------|
| `/login` | Login | Authentication backed by the configured administrator user |
| `/workspaces` | Workspaces | Workspace grid with search, filters, and creation |
| `/workspaces/:id` | Overview | Dashboard with stat cards, recent runs, and quick actions |
| `/workspaces/:id/profile` | Profile | Business profile editor with form validation |
| `/workspaces/:id/feeds` | Feeds | Feed source table with add/edit/delete in slide-over |
| `/workspaces/:id/content` | Content | Sortable/filterable content table with detail drawer |
| `/workspaces/:id/reports` | Reports | Report thread cards with search and status filters |
| `/workspaces/:id/reports/:threadId` | Thread | Chat-style report with source panel, voting, regeneration |
| `/workspaces/:id/runs` | Runs | Run table with detail drawer showing step timeline |
| `/workspaces/:id/feedback` | Feedback | Transparency dashboard with timeline and preferences |
| `/workspaces/:id/settings` | Settings | Schedule, scoring, retention, and email configuration |

## Testing

### Frontend Tests

```bash
npm run test -- --run
```

### Backend Tests

```bash
make backend-test
```

Or directly:

```bash
cd backend && python -m pytest --tb=short
```

Backend tests use an in-memory SQLite database and skip auto-migration via the `TESTING=1` environment variable.

## Fail-Fast Behavior

The backend follows a **fail-fast** philosophy on startup. During the `startup` event the app:

1. **Validates required OpenCode configuration** — aborts with `SystemExit` if `OPENCODE_BASE_URL`, `OPENCODE_DEFAULT_MODEL`, `OPENCODE_DEFAULT_AGENT`, or `OPENCODE_WORKSPACE_DIR` are missing or empty.
2. **Runs database migrations** (`alembic upgrade head`) — aborts if migration fails. No partial migrations are tolerated.
3. **Bootstraps seed data and admin user** — aborts if seeding or admin creation fails.

Each failure logs a `FATAL`-level message and calls `raise SystemExit(msg)`, which prevents uvicorn from serving traffic in a broken state. There are no hidden errors in critical paths.

## Health Endpoints

| Endpoint | Purpose | Behavior |
|----------|---------|----------|
| `GET /api/healthz` | **Liveness** probe | Always returns `200 {"status": "ok"}`. Confirms the process is alive. |
| `GET /api/ready` | **Readiness** probe | Checks database, Redis, and OpenCode configuration. Returns `200` if all healthy, `503 {"status": "degraded", "errors": {...}}` if any dependency is down. |
| `GET /api/health` | Legacy health (backward compatible) | Returns `200 {"status": "ok", "version": "..."}`. |

The readiness endpoint is safe to use as a Kubernetes or load-balancer health check — it will remove the pod from rotation if any critical dependency is unreachable.

## Background Run-Now

`POST /api/workspaces/{id}/run-now` triggers an asynchronous processing pipeline:

1. Creates a `ProcessingRun` record with `status: "queued"`.
2. Dispatches the pipeline to a **Celery worker** via `run_workspace_pipeline.delay()`.
3. Returns **202 Accepted** immediately with `{"runId": "...", "status": "queued", "message": "Pipeline execution queued"}`.

The pipeline status progresses through: `queued` → `running` → `succeeded` / `failed`. Poll `GET /api/runs/{runId}` to track progress.

## Demo Preflight

Before running a demo or presentation, verify that the environment is ready:

```bash
make preflight    # Checks DB, Redis, OpenCode connectivity and config
make demo-seed    # Creates a known-good demo workspace (idempotent)
```

## Manual Full-Flow Tests

End-to-end integration tests that exercise the real OpenCode adapter and live feeds are located in `tests/manual/`:

```bash
# Requires a running backend with valid OpenCode config
cd backend && python ../tests/manual/opencode_full_flow_real_feeds.py
```

These tests are **not** run by `make ci` — they are for ad-hoc verification against real services.

## Celery Background Processing

- Celery Beat runs a lightweight scheduler scan every 5 minutes and enqueues enabled workspaces.
- `nextRunAt` on workspace responses is computed from workspace settings when scheduling is enabled.

### Full CI

```bash
make ci
```

Runs linting, type checking, frontend tests, build, and backend tests.

### Individual Test Commands

```bash
# Full CI (recommended)
make ci

# Backend tests only
cd backend && python -m pytest

# Frontend tests only
npm run test
```

## Tech Stack

| Technology | Purpose |
|------------|---------|
| React 19 | UI framework |
| TypeScript 5.9 | Type safety |
| Vite 6 | Build tool and dev server |
| Tailwind CSS v4 | Utility-first styling |
| React Router v7 | Client-side routing |
| TanStack Query v5 | Data fetching, caching, and mutations |
| Zustand v5 | Global state management |
| React Hook Form + Zod | Form handling and validation |
| Motion (Framer) | Animations and transitions |
| Lucide React | Icon library |
| React Markdown | Markdown rendering in report threads |
| FastAPI | Backend REST API framework |
| SQLAlchemy | Python ORM |
| Alembic | Database migrations |
| PostgreSQL | Production database |
| pytest | Backend test framework |
