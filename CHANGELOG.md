# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - YYYY-MM-DD

### Added

- Workspace management with CRUD operations, search, filters, and overview dashboard
- Business profiles with products, competitors, and priority themes
- Feed management for RSS feeds, website scrapers, competitor pages, and blog sources
- Content inspection with multi-factor relevance scoring and source attribution
- Intelligence reports with chat-style report threads, source inspection, voting, and regeneration
- Operational run monitoring with step-by-step timelines and error tracking
- Feedback and preferences transparency dashboard
- Settings panel for scheduling, scoring thresholds, data retention, and email delivery
- Session-based authentication with configurable admin credentials
- FastAPI backend with PostgreSQL persistence, Redis transport, and Celery worker/Beat
- React frontend with TypeScript, Tailwind CSS v4, React Router v7, TanStack Query v5, and Zustand v5
- Docker Compose deployment with 7-service stack (frontend, backend, PostgreSQL, Redis, Celery worker, Celery Beat)
- Health check endpoints: liveness (`/api/healthz`), readiness (`/api/ready`), and legacy (`/api/health`)
- Fail-fast startup behavior with fatal logging on configuration, migration, or seed failures
- CI pipeline with lint, typecheck, frontend tests, backend tests, and production build
- API documentation via Swagger UI (`/api/docs`) and ReDoc (`/api/redoc`)

[Unreleased]: https://github.com/dinosaurchi/sme-news-admin/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/dinosaurchi/sme-news-admin/releases/tag/v0.1.0
