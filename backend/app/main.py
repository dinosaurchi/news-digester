import logging
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
