import logging
import os
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.api.session import router as session_router
from app.api.workspaces import router as workspaces_router
from app.api.feeds import router as feeds_router
from app.api.reports import router as reports_router
from app.api.feedback import router as feedback_router
from app.api.content import router as content_router
from app.api.runs import router as runs_router
from app.api.preferences import router as preferences_router

# ── Logging setup ────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("sme-news")

# ── Application ──────────────────────────────────────────────────────
app = FastAPI(
    title="SME News Admin API",
    version=settings.APP_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)


# ── Startup: run migrations and seed ─────────────────────────────────
# Fail-fast philosophy: every critical initialization step (config validation,
# DB migration, seed/bootstrap) aborts the process via SystemExit on failure.
# This prevents the app from serving traffic in a partially-initialized state.
@app.on_event("startup")
def startup():
    # Skip auto-migration in test environment
    if os.environ.get("TESTING") == "1":
        return

    # ── Validate required OpenCode configuration ────────────────────
    required_fields = [
        ("OPENCODE_BASE_URL", settings.OPENCODE_BASE_URL),
        ("OPENCODE_DEFAULT_MODEL", settings.OPENCODE_DEFAULT_MODEL),
        ("OPENCODE_DEFAULT_AGENT", settings.OPENCODE_DEFAULT_AGENT),
        ("OPENCODE_WORKSPACE_DIR", settings.OPENCODE_WORKSPACE_DIR),
    ]
    missing_or_empty = [
        name for name, value in required_fields if not value or not value.strip()
    ]
    if settings.OPENCODE_TIMEOUT_SECONDS <= 0:
        missing_or_empty.append("OPENCODE_TIMEOUT_SECONDS (must be > 0)")
    if missing_or_empty:
        msg = (
            "FATAL: Required OpenCode configuration is missing or invalid: "
            + ", ".join(missing_or_empty)
            + ". Set these environment variables and restart."
        )
        logger.critical(msg)
        raise SystemExit(msg)

    logger.info(
        "OpenCode configuration validated: base_url=%s model=%s agent=%s timeout=%ds",
        settings.OPENCODE_BASE_URL,
        settings.OPENCODE_DEFAULT_MODEL,
        settings.OPENCODE_DEFAULT_AGENT,
        settings.OPENCODE_TIMEOUT_SECONDS,
    )

    # ── CRITICAL INITIALIZATION (must succeed — abort on failure) ─────
    import subprocess

    logger.info("Running database migrations...")
    try:
        subprocess.run(["alembic", "upgrade", "head"], check=True, capture_output=True)
        logger.info("Migrations complete")
    except subprocess.CalledProcessError as e:
        stderr_output = e.stderr.decode() if e.stderr else str(e)
        msg = f"FATAL: Database migration failed: {stderr_output}"
        logger.critical(msg)
        raise SystemExit(msg)

    # ── CRITICAL INITIALIZATION: seed data and admin bootstrap ────────
    try:
        from app.db.session import SessionLocal
        from app.models import Workspace

        db = SessionLocal()
        count = db.query(Workspace).count()
        if count == 0:
            logger.info("No data found, running seed...")
            from app.seed import seed_all

            seed_all(db)
            logger.info("Seed complete")
        from app.services.session import bootstrap_admin_user

        admin_user = bootstrap_admin_user(db)
        db.commit()
        logger.info("Admin user ready: %s", admin_user.username)
        db.close()
    except Exception as e:
        msg = f"FATAL: Seed/bootstrap failed: {e}"
        logger.critical(msg)
        raise SystemExit(msg)

    # ── OPTIONAL INITIALIZATION (safe to skip on failure) ────────────


# ── CORS ─────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request ID + logging middleware ──────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    start = time.time()
    logger.info(
        "request_id=%s method=%s path=%s started",
        request_id,
        request.method,
        request.url.path,
    )
    response = await call_next(request)
    duration_ms = (time.time() - start) * 1000
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request_id=%s method=%s path=%s status=%d duration_ms=%.1f",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


# ── Dependency health checks ───────────────────────────────────────────


def check_database() -> tuple[str, str | None]:
    """Check database connectivity. Returns (status, error_message)."""
    try:
        from sqlalchemy import text

        from app.db.session import engine

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return "ok", None
    except Exception as e:
        return "failed", str(e)


def check_redis() -> tuple[str, str | None]:
    """Check Redis connectivity (optional dependency).

    If REDIS_URL is not configured, the check is skipped and reports "ok".
    """
    redis_url = getattr(settings, "REDIS_URL", "")
    if not redis_url or not redis_url.strip():
        return "ok", None  # not configured — optional dependency
    try:
        import redis

        client = redis.from_url(redis_url, socket_timeout=2)
        client.ping()
        client.close()
        return "ok", None
    except Exception as e:
        return "failed", str(e)


def check_opencode() -> tuple[str, str | None]:
    """Check that OpenCode adapter configuration exists."""
    if not settings.OPENCODE_BASE_URL or not settings.OPENCODE_BASE_URL.strip():
        return "failed", "OPENCODE_BASE_URL is not configured"
    return "ok", None


# ── Health endpoint (backward compatible) ──────────────────────────────
@app.get("/api/health")
def health():
    return {"status": "ok", "version": settings.APP_VERSION}


# ── Liveness endpoint ──────────────────────────────────────────────────
@app.get("/api/healthz")
def healthz():
    """Liveness probe — process is alive, no dependency checks."""
    return {"status": "ok"}


# ── Readiness endpoint ─────────────────────────────────────────────────
@app.get("/api/ready")
def readiness():
    """Readiness probe — checks critical dependencies before serving traffic."""
    checks: dict[str, tuple[str, str | None]] = {
        "database": check_database(),
        "redis": check_redis(),
        "opencode": check_opencode(),
    }

    all_ok = all(status == "ok" for status, _ in checks.values())
    errors: dict[str, str] = {
        name: error for name, (status, error) in checks.items() if error is not None
    }

    body: dict = {
        "status": "ok" if all_ok else "degraded",
        "checks": {name: status for name, (status, _) in checks.items()},
    }
    if errors:
        body["errors"] = errors

    return JSONResponse(content=body, status_code=200 if all_ok else 503)


# ── Routers ──────────────────────────────────────────────────────────
app.include_router(session_router)
app.include_router(workspaces_router)
app.include_router(feeds_router)
app.include_router(reports_router)
app.include_router(feedback_router)
app.include_router(content_router)
app.include_router(runs_router)
app.include_router(preferences_router)


# ── Run with: uvicorn app.main:app --reload ─────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
