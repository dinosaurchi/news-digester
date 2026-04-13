#!/usr/bin/env bash
# preflight.sh — Deterministic readiness check for SME News Admin
#
# Usage:
#   ./scripts/preflight.sh                  # defaults to http://localhost:8000
#   BASE_URL=http://myhost:8000 ./scripts/preflight.sh
#
# Exit codes:
#   0 = all checks passed (system is ready)
#   1 = one or more checks failed
set -euo pipefail

# ── Configuration ──────────────────────────────────────────────────────────
BASE_URL="${BASE_URL:-http://localhost:8000}"
TIMEOUT="${PREFLIGHT_TIMEOUT:-5}"

# ── Color helpers ──────────────────────────────────────────────────────────
if [[ -t 1 ]]; then
    GREEN="\033[0;32m"
    RED="\033[0;31m"
    YELLOW="\033[0;33m"
    CYAN="\033[0;36m"
    BOLD="\033[1m"
    RESET="\033[0m"
else
    GREEN="" RED="" YELLOW="" CYAN="" BOLD="" RESET=""
fi

pass_count=0
fail_count=0
warn_count=0

# ── Helpers ────────────────────────────────────────────────────────────────
check_pass() {
    echo -e "  ${GREEN}PASS${RESET}  $1"
    ((pass_count++))
}

check_fail() {
    echo -e "  ${RED}FAIL${RESET}  $1"
    ((fail_count++))
}

check_warn() {
    echo -e "  ${YELLOW}WARN${RESET}  $1"
    ((warn_count++))
}

section() {
    echo -e "\n${BOLD}${CYAN}── $1 ──${RESET}"
}

# ── Preflight checks ──────────────────────────────────────────────────────

echo -e "${BOLD}SME News Admin — Preflight Check${RESET}"
echo -e "  Target: ${BASE_URL}"

# 1. Liveness
section "Liveness"
if HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" "${BASE_URL}/api/healthz" 2>/dev/null); then
    if [[ "$HTTP_CODE" == "200" ]]; then
        BODY=$(curl -s --max-time "$TIMEOUT" "${BASE_URL}/api/healthz" 2>/dev/null || echo '{}')
        check_pass "/api/healthz returned 200 — ${BODY}"
    else
        check_fail "/api/healthz returned HTTP ${HTTP_CODE}"
    fi
else
    check_fail "/api/healthz unreachable (is the backend running?)"
fi

# 2. Readiness with dependency checks
section "Readiness"
READY_HTTP=""
READY_BODY=""
if READY_HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" "${BASE_URL}/api/ready" 2>/dev/null); then
    READY_BODY=$(curl -s --max-time "$TIMEOUT" "${BASE_URL}/api/ready" 2>/dev/null || echo '{}')
    if [[ "$READY_HTTP" == "200" ]]; then
        check_pass "/api/ready returned 200 — all checks passed"
        echo -e "  ${CYAN}      Body: ${READY_BODY}${RESET}"
    else
        check_fail "/api/ready returned HTTP ${READY_HTTP} — system degraded"
        echo -e "  ${RED}      Body: ${READY_BODY}${RESET}"
    fi
else
    check_fail "/api/ready unreachable"
fi

# 3. Critical route checks
section "Critical Routes"
for route in "/api/healthz" "/api/ready" "/api/workspaces"; do
    if HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" "${BASE_URL}${route}" 2>/dev/null); then
        if [[ "$HTTP_CODE" =~ ^2 ]]; then
            check_pass "${route} → HTTP ${HTTP_CODE}"
        elif [[ "$HTTP_CODE" =~ ^4 ]]; then
            # 4xx is acceptable for routes requiring auth (e.g., /api/workspaces)
            check_warn "${route} → HTTP ${HTTP_CODE} (may require auth)"
        else
            check_fail "${route} → HTTP ${HTTP_CODE}"
        fi
    else
        check_fail "${route} → unreachable"
    fi
done

# 4. Feed validation (best-effort, optional)
section "Feed Validation (best-effort)"
TEST_FEED_URL="https://techcrunch.com/feed/"
if HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" "${TEST_FEED_URL}" 2>/dev/null); then
    if [[ "$HTTP_CODE" =~ ^2 ]]; then
        check_pass "TechCrunch RSS reachable (HTTP ${HTTP_CODE})"
    else
        check_warn "TechCrunch RSS returned HTTP ${HTTP_CODE} (external source may be flaky)"
    fi
else
    check_warn "TechCrunch RSS unreachable (network or DNS issue — not blocking)"
fi

# ── Summary ────────────────────────────────────────────────────────────────
echo -e "\n${BOLD}──────────────────────────────────────${RESET}"
TOTAL=$((pass_count + fail_count + warn_count))
echo -e "  Results: ${GREEN}${pass_count} passed${RESET}, ${RED}${fail_count} failed${RESET}, ${YELLOW}${warn_count} warnings${RESET} (${TOTAL} total)"

if [[ "$fail_count" -gt 0 ]]; then
    echo -e "\n  ${RED}${BOLD}SYSTEM NOT READY${RESET} — fix the failures above before proceeding."
    exit 1
else
    echo -e "\n  ${GREEN}${BOLD}SYSTEM READY${RESET} — all critical checks passed."
    exit 0
fi
