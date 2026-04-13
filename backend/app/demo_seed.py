"""Demo seed — creates a known-good demo workspace for presentations and testing.

Run with:
    cd backend && python -m app.demo_seed
Or via Makefile:
    make demo-seed

This is idempotent: running it multiple times is safe.
"""

import logging
import uuid
from datetime import datetime, timezone

from app.db.session import SessionLocal
from app.models.workspace import Workspace, WorkspaceProfile, WorkspaceSettings
from app.models.feed import FeedSource

logger = logging.getLogger(__name__)

# Fixed ID so we can look up and skip the workspace if it already exists.
DEMO_WORKSPACE_ID = "ws-demo-001"

DEMO_WORKSPACE = {
    "id": DEMO_WORKSPACE_ID,
    "name": "Demo Workspace",
    "customer": "Demo Organization",
    "status": "active",
}

DEMO_PROFILE = {
    "business_name": "Demo Organization",
    "description": (
        "A demo workspace for showcasing the SME News Admin intelligence platform. "
        "Configured with known-good feeds and priority themes for a smooth demonstration."
    ),
    "products": [
        "CloudStack Pro",
        "AI-Flow Engine",
        "DataGuard Shield",
    ],
    "competitors": [
        "CloudGiant",
        "DataNexus Corp.",
        "SoftSystems International",
    ],
    "priority_themes": [
        "Generative AI",
        "Hybrid Cloud Architecture",
        "Cybersecurity Regulations",
        "Edge Computing",
        "AI Compliance",
    ],
    "excluded_topics": [
        "Consumer hardware",
        "Gaming",
        "Cryptocurrency",
        "Consumer social media",
    ],
    "notes": "Demo workspace — safe to reset at any time.",
}

DEMO_SETTINGS = {
    "schedule": {
        "enabled": False,
        "frequency": "daily",
        "timeOfDay": "08:00",
        "timezone": "America/New_York",
    },
    "report_style": "detailed",
    "thresholds": {
        "minRelevanceScore": 0.65,
        "minFinalScore": 0.70,
        "maxArticlesPerReport": 15,
    },
    "retention": {
        "contentDays": 90,
        "reportDays": 365,
        "runHistoryDays": 180,
    },
    "email_delivery": {
        "enabled": False,
        "recipients": [],
        "subjectPrefix": "[Demo Intel]",
    },
}

# Known-good feeds that are widely available and rarely go down.
# These can be used as backup choices if other feeds are flaky.
DEMO_FEEDS = [
    {
        "name": "TechCrunch RSS",
        "url": "https://techcrunch.com/feed/",
        "type": "rss",
        "status": "healthy",
        "cadence": "daily",
        "tags": ["tech", "startups"],
    },
    {
        "name": "BBC News",
        "url": "http://feeds.bbci.co.uk/news/rss.xml",
        "type": "rss",
        "status": "healthy",
        "cadence": "daily",
        "tags": ["news", "world"],
    },
    {
        "name": "Ars Technica",
        "url": "https://feeds.arstechnica.com/arstechnica/features",
        "type": "rss",
        "status": "healthy",
        "cadence": "daily",
        "tags": ["tech", "science"],
    },
]

# Backup feed choices for flaky sources.
BACKUP_FEEDS = [
    {
        "name": "Hacker News",
        "url": "https://hnrss.org/frontpage",
        "type": "rss",
        "status": "healthy",
        "cadence": "hourly",
        "tags": ["tech", "startups"],
    },
    {
        "name": "The Verge",
        "url": "https://www.theverge.com/rss/index.xml",
        "type": "rss",
        "status": "healthy",
        "cadence": "daily",
        "tags": ["tech", "culture"],
    },
    {
        "name": "Wired",
        "url": "https://www.wired.com/feed/rss",
        "type": "rss",
        "status": "healthy",
        "cadence": "daily",
        "tags": ["tech", "innovation"],
    },
]


def seed_demo(db) -> None:
    """Create (or verify) the demo workspace. Idempotent.

    Accepts an existing database session so it can be called from
    the FastAPI startup event, tests, or the CLI entry point.
    """
    try:
        # Check if the demo workspace already exists.
        existing = db.query(Workspace).filter(Workspace.id == DEMO_WORKSPACE_ID).first()
        if existing:
            logger.info(
                "Demo workspace '%s' (id=%s) already exists. Skipping seed.",
                existing.name,
                existing.id,
            )
            return

        now = datetime.now(timezone.utc)

        # ── Workspace ──────────────────────────────────────────────────
        ws = Workspace(
            id=DEMO_WORKSPACE_ID,
            name=DEMO_WORKSPACE["name"],
            customer=DEMO_WORKSPACE["customer"],
            status=DEMO_WORKSPACE["status"],
            created_at=now,
            updated_at=now,
        )
        db.add(ws)
        db.flush()
        logger.info("Created demo workspace: %s", ws.name)

        # ── Profile ────────────────────────────────────────────────────
        profile = WorkspaceProfile(
            id=uuid.uuid4().hex,
            workspace_id=ws.id,
            **DEMO_PROFILE,
            created_at=now,
            updated_at=now,
        )
        db.add(profile)
        logger.info("Created demo profile")

        # ── Settings ───────────────────────────────────────────────────
        settings = WorkspaceSettings(
            id=uuid.uuid4().hex,
            workspace_id=ws.id,
            **DEMO_SETTINGS,
            updated_at=now,
        )
        db.add(settings)
        logger.info("Created demo settings")

        # ── Feeds ──────────────────────────────────────────────────────
        for feed_data in DEMO_FEEDS:
            feed = FeedSource(
                id=uuid.uuid4().hex,
                workspace_id=ws.id,
                **feed_data,
                created_at=now,
                updated_at=now,
            )
            db.add(feed)
        logger.info("Created %d demo feeds", len(DEMO_FEEDS))

        db.commit()
        logger.info("Demo seed completed successfully.")
    except Exception:
        db.rollback()
        logger.exception("Demo seed failed")
        raise


def seed_demo_cli() -> None:
    """CLI entry point for demo seed (creates its own session)."""
    db = SessionLocal()
    try:
        seed_demo(db)
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    seed_demo_cli()
