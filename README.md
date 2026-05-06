<p align="center"><img src="docs/logo.svg" alt="SME News Admin" width="150"></p>

<h1 align="center">News Digester</h1>

<p align="center">AI-powered news intelligence workspace admin dashboard</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg" alt="PRs Welcome">
</p>

---

News Digester is a full-stack admin dashboard for managing AI-powered news intelligence workspaces. It provides tools to configure data sources, monitor intelligence cycle runs, review generated reports, and tune relevance scoring — all from a single interface. Built with React, FastAPI, PostgreSQL, and Celery for background processing.

## Features

### Intelligence Management
- **Workspace Management** — Create and manage customer reporting environments
- **Business Profiles** — Define intelligence context with products, competitors, and priority themes
- **Feed Management** — Configure RSS feeds, website scrapers, competitor pages, and blog sources
- **Content Inspection** — Review fetched content with multi-factor relevance scoring and source attribution

### AI Reporting
- **Intelligence Reports** — Chat-style report threads with source inspection, voting, and regeneration
- **Operational Runs** — Monitor intelligence cycle execution with step-by-step timelines and error tracking
- **Feedback & Preferences** — Transparency dashboard showing how user feedback influences report tuning

### Operations
- **Settings** — Configure scheduling, scoring thresholds, data retention, and email delivery
- **Health Endpoints** — Liveness (`/api/healthz`) and readiness (`/api/ready`) probes for container orchestration
- **Background Processing** — Celery worker and Beat for scheduled pipeline execution

## Quick Start

### Docker (Recommended)

```bash
git clone https://github.com/dinosaurchi/news-digester.git
cd news-digester
cp .env.example .env   # Configure your environment
make up                 # Start all services
```

This starts the frontend, backend, PostgreSQL, Redis, Celery worker, and Celery Beat. The backend automatically runs migrations and seeds initial data on first start.

- **Frontend**: [http://localhost:3000](http://localhost:3000)
- **API docs**: [http://localhost:8000/api/docs](http://localhost:8000/api/docs)

Default dev credentials are `admin` / `admin` — change `ADMIN_USERNAME` and `ADMIN_PASSWORD` before any shared deployment.

### Local Development

```bash
# Frontend
npm install
npm run dev

# Backend API
cd backend
pip install -r requirements.txt
make backend

# Background services (optional)
make worker
make beat
```

### Production Build

```bash
make build
```

## Architecture

React frontend served by Vite, FastAPI backend with SQLAlchemy ORM, PostgreSQL for persistence, Redis as Celery broker, and Celery worker/Beat for background pipeline processing. The backend follows a **fail-fast** philosophy — on startup it validates configuration, runs database migrations, and bootstraps seed data, aborting immediately if any step fails.

```
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── api/          # API route handlers
│   │   ├── db/           # Database session and base
│   │   ├── models/       # SQLAlchemy ORM models
│   │   ├── schemas/      # Pydantic request/response schemas
│   │   ├── services/     # Business logic layer
│   │   └── tasks/        # Celery tasks and pipeline helpers
│   ├── alembic/          # Database migrations
│   └── tests/            # pytest test suite
├── src/                  # React frontend
│   ├── components/       # Shared UI components
│   ├── hooks/            # Custom React hooks
│   ├── lib/              # API client, schemas, store, utils
│   ├── pages/            # Route-level page components
│   └── router/           # React Router configuration
├── docs/                 # Documentation
├── Makefile              # Development commands
└── docker-compose.yml    # Container orchestration
```

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | React 19 | UI framework |
| | TypeScript 5.9 | Type safety |
| | Vite 6 | Build tool and dev server |
| | Tailwind CSS v4 | Utility-first styling |
| | React Router v7 | Client-side routing |
| | TanStack Query v5 | Data fetching, caching, and mutations |
| | Zustand v5 | Global state management |
| | React Hook Form + Zod | Form handling and validation |
| **Backend** | FastAPI | REST API framework |
| | SQLAlchemy + Alembic | ORM and database migrations |
| | PostgreSQL | Production database |
| | Redis | Celery message broker |
| | Celery | Background task processing |
| | pytest | Test framework |

## Documentation

- [Contributing Guide](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Security Policy](SECURITY.md)
- [Demo Guide](docs/demo-guide.md)
- [Post-Deploy QA](docs/QA_POST_DEPLOY.md)

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://sme:sme@localhost:5432/sme_news` |
| `REDIS_URL` | Redis connection string for Celery broker/backend | `redis://localhost:6379/0` |
| `CORS_ORIGINS` | Allowed CORS origins (comma-separated) | `http://localhost:3000` |
| `DEBUG` | Enable debug logging | `false` |
| `TESTING` | Skip auto-migration on startup (set to `1` for tests) | — |

## API Documentation

Interactive API documentation is available at:

- **Swagger UI**: [`/api/docs`](http://localhost:8000/api/docs)
- **ReDoc**: [`/api/redoc`](http://localhost:8000/api/redoc)

The API covers workspace management, feeds, content, reports, runs, feedback, preferences, and settings — all under `/api/`.

## Testing

```bash
# Full CI (linting, type checking, tests, build)
make ci

# Frontend tests only
npm run test -- --run

# Backend tests only
make backend-test
# or: cd backend && python -m pytest --tb=short
```

Backend tests use an in-memory SQLite database with `TESTING=1` to skip auto-migration.

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

## Acknowledgments

Built with [React](https://react.dev), [FastAPI](https://fastapi.tiangolo.com), [PostgreSQL](https://www.postgresql.org), [Celery](https://docs.celeryq.dev), and [Tailwind CSS](https://tailwindcss.com).
