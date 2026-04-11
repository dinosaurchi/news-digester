import logging
import os
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

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

    import subprocess

    logger.info("Running database migrations...")
    try:
        subprocess.run(["alembic", "upgrade", "head"], check=True, capture_output=True)
        logger.info("Migrations complete")
    except subprocess.CalledProcessError as e:
        logger.error(f"Migration failed: {e.stderr.decode()}")
    # Run seed if no data exists
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
        logger.error(f"Seed check failed: {e}")


# ── CORS ─────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request logging middleware ───────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start) * 1000
    logger.info(
        "%s %s → %d (%.1fms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


# ── Health endpoint ──────────────────────────────────────────────────
@app.get("/api/health")
def health():
    return {"status": "ok", "version": settings.APP_VERSION}


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
