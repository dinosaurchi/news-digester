# QA Post-Deploy Verification

> **Living document** — update as the app evolves. Last reviewed: 2026-04-10.

This guide provides a step-by-step procedure for verifying the feed ingestion pipeline after a fresh deploy. All commands assume you are running from the project root.

---

## 1. Prerequisites

1. **Build and start all services:**

   ```bash
   make up
   ```

2. **Confirm all containers are healthy:**

   ```bash
   docker compose ps
   ```

   All services (`db`, `redis`, `backend`, `worker`, `beat`, `app`) should show `running` / `healthy`.

3. **Default credentials:**

   - URL: `http://localhost:3000`
   - Username: `admin`
   - Password: `admin`

---

## 2. API QA Checklist (curl)

Set a base URL variable for convenience:

```bash
BASE="http://localhost:3000/api"
```

### Health & Auth

**2.1 Health check**

```bash
curl -s "$BASE/health" | python3 -m json.tool
```

Expected: `{ "status": "ok", "version": "<semver>" }`

**2.2 Login and capture session cookie**

```bash
curl -s -c /tmp/qa_cookies \
  -X POST "$BASE/session/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}' | python3 -m json.tool
```

Expected: `{ "user": { "id": "...", "username": "admin", "displayName": "Admin", "role": "admin" } }`

**2.3 Verify authenticated session**

```bash
curl -s -b /tmp/qa_cookies "$BASE/session/me" | python3 -m json.tool
```

Expected: Same user object as login response.

### Workspace & Feeds

**2.4 Create a fresh QA workspace**

```bash
WS=$(curl -s -b /tmp/qa_cookies \
  -X POST "$BASE/workspaces" \
  -H "Content-Type: application/json" \
  -d '{"name":"QA Workspace","customer":"QA Co"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
echo "Workspace ID: $WS"
```

**2.5 Add reliable RSS feeds**

```bash
curl -s -b /tmp/qa_cookies \
  -X POST "$BASE/workspaces/$WS/feeds" \
  -H "Content-Type: application/json" \
  -d '{"name":"Hacker News","url":"https://hnrss.org/frontpage","type":"rss","cadence":"daily"}'

curl -s -b /tmp/qa_cookies \
  -X POST "$BASE/workspaces/$WS/feeds" \
  -H "Content-Type: application/json" \
  -d '{"name":"BBC News - Technology","url":"http://feeds.bbci.co.uk/news/technology/rss.xml","type":"rss","cadence":"daily"}'

curl -s -b /tmp/qa_cookies \
  -X POST "$BASE/workspaces/$WS/feeds" \
  -H "Content-Type: application/json" \
  -d '{"name":"Reuters Technology","url":"https://feeds.reuters.com/reuters/technologyNews","type":"rss","cadence":"daily"}'
```

**2.6 List feeds and capture IDs**

```bash
curl -s -b /tmp/qa_cookies "$BASE/workspaces/$WS/feeds" | python3 -m json.tool
```

Note the feed `id` values for the next step.

**2.7 Test a feed**

```bash
FEED_ID="<id from step 2.6>"
curl -s -b /tmp/qa_cookies \
  -X POST "$BASE/feeds/$FEED_ID/test" | python3 -m json.tool
```

Expected: `{ "success": true, "articlesFound": <int > 0>, "feedId": "...", ... }`

### Pipeline Run

**2.8 Trigger a pipeline run**

```bash
RUN=$(curl -s -b /tmp/qa_cookies \
  -X POST "$BASE/workspaces/$WS/run-now" \
  -H "Content-Type: application/json" | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
echo "Run ID: $RUN"
```

Expected: HTTP 201, response contains `"status": "success"` (or `"running"` if async).

**2.9 Verify run detail with fetch metadata**

```bash
curl -s -b /tmp/qa_cookies "$BASE/runs/$RUN" | python3 -m json.tool
```

Verify in the `steps` array there is a fetch step whose `metadata` includes:

| Field | Expected |
|-------|----------|
| `feedsAttempted` | Equals number of feeds added |
| `feedsSucceeded` | >= 1 |
| `feedsFailed` | 0 (all valid feeds) |
| `entriesFetched` | > 0 |
| `entriesImported` | > 0 |
| `entriesSkipped` | >= 0 |

Also verify `links.reports` contains at least one report ID.

### Idempotency

**2.10 Run the pipeline a second time**

```bash
RUN2=$(curl -s -b /tmp/qa_cookies \
  -X POST "$BASE/workspaces/$WS/run-now" \
  -H "Content-Type: application/json" | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
curl -s -b /tmp/qa_cookies "$BASE/runs/$RUN2" | python3 -m json.tool
```

Verify `entriesImported` is 0 or very low (only genuinely new articles should be imported). `entriesSkipped` should account for already-seen entries.

### Feed Error / Recovery

**2.11 Add a broken feed**

```bash
BROKEN=$(curl -s -b /tmp/qa_cookies \
  -X POST "$BASE/workspaces/$WS/feeds" \
  -H "Content-Type: application/json" \
  -d '{"name":"Broken Feed","url":"http://localhost:9999/nonexistent","type":"rss","cadence":"daily"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
echo "Broken feed ID: $BROKEN"
```

**2.12 Test the broken feed — expect failure**

```bash
curl -s -b /tmp/qa_cookies \
  -X POST "$BASE/feeds/$BROKEN/test" | python3 -m json.tool
```

Expected:

- `"success": false`
- `"lastError"` is a non-null string
- `"lastErrorAt"` is a non-null ISO timestamp

**2.13 Verify feed status via GET**

```bash
curl -s -b /tmp/qa_cookies "$BASE/feeds/$BROKEN" | python3 -m json.tool
```

Verify: `status` is `"error"`, `lastError` is set, `lastErrorAt` is set, `lastFetchedAt` is null (never succeeded).

**2.14 Fix the feed URL to a valid one**

```bash
curl -s -b /tmp/qa_cookies \
  -X PATCH "$BASE/feeds/$BROKEN" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://hnrss.org/newest"}' | python3 -m json.tool
```

**2.15 Re-test — expect recovery**

```bash
curl -s -b /tmp/qa_cookies \
  -X POST "$BASE/feeds/$BROKEN/test" | python3 -m json.tool
```

Verify:

- `"success": true`
- `"articlesFound"` > 0

**2.16 Confirm feed status is healthy**

```bash
curl -s -b /tmp/qa_cookies "$BASE/feeds/$BROKEN" | python3 -m json.tool
```

Verify: `status` is `"healthy"`, `lastError` is `null`, `lastErrorAt` is `null`, `lastFetchedAt` is updated to a recent ISO timestamp.

### Report Verification

**2.17 List reports for the workspace**

```bash
REPORTS=$(curl -s -b /tmp/qa_cookies "$BASE/workspaces/$WS/reports")
echo "$REPORTS" | python3 -m json.tool
```

Verify: the list is non-empty. Note a `report_id`.

**2.18 Get report summary**

```bash
REPORT_ID="<id from step 2.17>"
curl -s -b /tmp/qa_cookies "$BASE/reports/$REPORT_ID" | python3 -m json.tool
```

Verify: `title` is non-empty, `status` is `"published"`, `messageCount` >= 1.

**2.19 Get report thread messages (verify content)**

```bash
curl -s -b /tmp/qa_cookies "$BASE/report-threads/$REPORT_ID/messages" | python3 -m json.tool
```

Verify: at least one `system` message with non-empty `content` (the generated report markdown).

**2.20 Verify report sources resolve to valid content items**

Extract source IDs from the report message metadata, then verify each resolves:

```bash
# Extract source IDs from the first system message
SOURCE_IDS=$(curl -s -b /tmp/qa_cookies \
  "$BASE/report-threads/$REPORT_ID/messages" \
  | python3 -c "
import sys, json
msgs = json.load(sys.stdin)
for m in msgs:
    if m['role'] == 'system' and m.get('metadata', {}).get('sources'):
        print(' '.join(m['metadata']['sources']))
        break
")

# Verify each source resolves
for SID in $SOURCE_IDS; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" -b /tmp/qa_cookies "$BASE/content/$SID")
  echo "Content $SID → HTTP $STATUS"
done
```

Expected: all source IDs return HTTP 200.

### Session Cleanup

**2.21 Logout**

```bash
curl -s -b /tmp/qa_cookies -c /tmp/qa_cookies \
  -X POST "$BASE/session/logout" | python3 -m json.tool
```

Expected: `{ "ok": true }`

**2.22 Verify session is invalidated**

```bash
curl -s -b /tmp/qa_cookies -o /dev/null -w "%{http_code}" "$BASE/session/me"
```

Expected: HTTP 401.

---

## 3. Web UI QA Checklist

Open `http://localhost:3000` in a browser.

| # | Step | Expected |
|---|------|----------|
| 1 | Login with **admin** / **admin** | Redirected to dashboard; user avatar/name shown |
| 2 | Navigate to **QA Workspace** | Workspace detail page loads with correct name and customer |
| 3 | Add feeds if not already present | Feed cards appear in the feed list |
| 4 | Trigger a run from the UI (Run Now button) | Run starts; status indicator shows progress |
| 5 | Confirm run completes | Run status changes to "success"; ingestion counts visible |
| 6 | Confirm imported content appears | Content tab shows entries with titles, scores, sources |
| 7 | Confirm healthy feed indicator | Feed cards show green/healthy status for valid feeds |
| 8 | Open run detail view | Steps list visible; fetch step shows feed counts and entry counts |
| 9 | Open the generated report | Report thread page loads with rendered markdown |
| 10 | Open report sources | Source links resolve to content item detail pages |
| 11 | Refresh browser (F5) | Session restored; no redirect to login |
| 12 | Logout | Redirected to login page; protected routes no longer accessible |

---

## 4. Fresh Workspace Flow — Curated Feed Set

Use these reliable RSS feeds when creating a fresh workspace for QA:

| Feed | URL | Notes |
|------|-----|-------|
| Hacker News (front page) | `https://hnrss.org/frontpage` | ~30 items, updates frequently |
| BBC News — Technology | `http://feeds.bbci.co.uk/news/technology/rss.xml` | Broad tech coverage |
| Reuters — Technology | `https://feeds.reuters.com/reuters/technologyNews` | Mainstream tech wire |

**Quick-create command:**

```bash
WS=$(curl -s -b /tmp/qa_cookies \
  -X POST "$BASE/workspaces" \
  -H "Content-Type: application/json" \
  -d '{"name":"QA Workspace","customer":"QA Co"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")

for FEED in \
  '{"name":"Hacker News","url":"https://hnrss.org/frontpage","type":"rss"}' \
  '{"name":"BBC Tech","url":"http://feeds.bbci.co.uk/news/technology/rss.xml","type":"rss"}' \
  '{"name":"Reuters Tech","url":"https://feeds.reuters.com/reuters/technologyNews","type":"rss"}'; do
  curl -s -b /tmp/qa_cookies \
    -X POST "$BASE/workspaces/$WS/feeds" \
    -H "Content-Type: application/json" \
    -d "$FEED" > /dev/null
done

echo "Workspace $WS ready with 3 feeds"
```
