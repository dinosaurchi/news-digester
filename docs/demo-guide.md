# Demo Guide

How to set up and run a smooth demonstration of the SME News Admin platform.

## Prerequisites

| Requirement | Details |
|---|---|
| Docker + Compose | For full containerized stack |
| curl | For preflight checks |
| Node.js 18+ / npm | For frontend development |
| Python 3.11+ | For backend development |

## Environment Variables

Create a `.env` file in the project root (or use `.env.example` as a template):

```bash
# Required
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/sme_news
REDIS_URL=redis://localhost:6379/0
OPENCODE_BASE_URL=http://opencode-agent-adapter:8080
OPENCODE_DEFAULT_MODEL=opencode/gpt-5-nano
OPENCODE_DEFAULT_AGENT=general
OPENCODE_WORKSPACE_DIR=/workspace
OPENCODE_TIMEOUT_SECONDS=60

# Optional (defaults shown)
DEBUG=false
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin
SECRET_KEY=dev-secret-key-change-in-production
```

## Startup Instructions

### Docker (recommended)

```bash
make up
```

This starts all services: frontend, backend, PostgreSQL, Redis, Celery worker, and Celery Beat.

### Local Development

Terminal 1 — Backend:
```bash
cd backend
pip install -r requirements.txt
make backend
```

Terminal 2 — Frontend:
```bash
npm install
npm run dev
```

## Preflight Check

Before presenting or testing, run the preflight script to verify the system is ready:

```bash
# Default target: http://localhost:8000
make preflight

# Custom target
BASE_URL=http://myhost:8000 make preflight

# Direct script usage
./scripts/preflight.sh
```

The preflight checks:

1. **Liveness** — `GET /api/healthz` returns 200
2. **Readiness** — `GET /api/ready` returns 200 (database, Redis, OpenCode config all pass)
3. **Critical routes** — `/api/healthz`, `/api/ready`, `/api/workspaces` respond
4. **Feed validation** — TechCrunch RSS is reachable (best-effort, non-blocking)

Color-coded output:
- Green = pass
- Red = fail
- Yellow = warning (non-blocking)

Exit codes:
- `0` = system is ready
- `1` = one or more critical checks failed

## Demo Workspace Setup

After the backend starts and the database is seeded, create a demo workspace:

```bash
make demo-seed
```

This creates a **Demo Workspace** with:

- A business profile with priority themes (Generative AI, Cybersecurity Regulations, etc.)
- Pre-configured settings (daily schedule, relevance thresholds)
- Three known-good feeds:
  - TechCrunch RSS
  - BBC News
  - Ars Technica

The demo seed is **idempotent** — running it multiple times is safe. If the workspace already exists, it skips creation.

### Direct CLI usage

```bash
cd backend && python -m app.demo_seed
```

## What To Do If a Feed Fails

Feeds can fail for various reasons (network issues, DNS, source site changes). Here's the troubleshooting flow:

### 1. Check feed status

In the UI, go to **Workspaces > Demo Workspace > Feeds**. Look for feeds with status `error`.

### 2. Try re-fetching

Click the **Test** button on the feed to attempt a fresh fetch.

### 3. Switch to a backup feed

If a feed is consistently failing, replace it with one of these backup choices:

| Feed | URL | Notes |
|---|---|---|
| Hacker News | `https://hnrss.org/frontpage` | Very reliable, tech-focused |
| The Verge | `https://www.theverge.com/rss/index.xml` | Tech and culture |
| Wired | `https://www.wired.com/feed/rss` | Innovation and tech |
| Reuters Tech | `https://www.reutersagency.com/feed/?best-regions=europe&post_type=best` | General tech news |
| MIT Technology Review | `https://www.technologyreview.com/feed/` | Deep tech analysis |

### 4. Common failure patterns

| Symptom | Likely cause | Fix |
|---|---|---|
| `Connection timed out` | Network/firewall blocking outbound | Check proxy settings |
| `DNS resolution failed` | DNS issue or VPN interference | Try alternate DNS (8.8.8.8) |
| `HTTP 403 Forbidden` | Source blocks automated requests | Switch to backup feed |
| `HTTP 301/302` | URL changed | Update feed URL |
| Empty feed | Source temporarily empty | Wait and retry |

## What To Do If OpenCode Adapter Is Unavailable

The OpenCode adapter is required for report generation. If it's unavailable:

### Check the readiness endpoint

```bash
curl -s http://localhost:8000/api/ready | python -m json.tool
```

If `opencode` shows `failed`, the adapter configuration is missing or incorrect.

### Verify environment variables

```bash
echo $OPENCODE_BASE_URL
echo $OPENCODE_DEFAULT_MODEL
echo $OPENCODE_DEFAULT_AGENT
echo $OPENCODE_WORKSPACE_DIR
```

All must be set and non-empty.

### The adapter is a config-only check

The `/api/ready` endpoint only verifies that the OpenCode configuration variables are set — it does not make a live HTTP call to the adapter. If the check fails, it's a configuration issue, not a connectivity issue.

## Manual Full-Flow Test

Follow these steps to verify the entire system end-to-end:

### 1. Preflight

```bash
make preflight
```

### 2. Demo seed

```bash
make demo-seed
```

### 3. Login

Open `http://localhost:3000` (or your configured frontend URL) and log in with the admin credentials.

### 4. Verify workspace

- Navigate to **Workspaces** — you should see "Demo Workspace" in the list
- Click into it and verify the **Overview** page loads

### 5. Check feeds

- Go to **Feeds** tab — verify 3 feeds are listed
- Click **Test** on one feed to verify fetch works

### 6. Check content

- Go to **Content** tab — verify content items appear (may be empty on first run)
- If empty, trigger a run (see step 7) and check back

### 7. Trigger a processing run

- Go to **Runs** tab
- Click **Run Now** to trigger a manual intelligence cycle
- Verify the run appears in the list with a success status

### 8. Check reports

- Go to **Reports** tab
- If a run completed successfully, verify a report was generated
- Open the report thread and verify content renders

### 9. Verify API health

```bash
# Liveness
curl -s http://localhost:8000/api/healthz

# Readiness
curl -s http://localhost:8000/api/ready | python -m json.tool

# API docs
open http://localhost:8000/api/docs
```

### 10. Check settings

- Go to **Settings** tab
- Verify schedule, scoring thresholds, and retention settings are as expected
- Optionally enable the schedule for automated runs

## Quick Reference

| Command | Description |
|---|---|
| `make up` | Start all services with Docker |
| `make down` | Stop all services |
| `make preflight` | Run readiness checks |
| `make demo-seed` | Create demo workspace |
| `make backend` | Start backend locally |
| `make backend-test` | Run backend tests |
| `make ci` | Full CI (lint, typecheck, test, build) |
