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
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceProfile, WorkspaceSettings
from app.models.feed import FeedSource
from app.services.session import hash_password

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
        "min_relevance_score": 0.65,
        "min_final_score": 0.70,
        "max_articles_per_report": 15,
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

        logger.info("Demo workspace seed data prepared.")
    except Exception:
        logger.exception("Demo workspace seed failed")
        raise


METAL_EARTH_WORKSPACE_ID = "ws-metalearth-001"

MANH_USER = {
    "username": "manh",
    "password": "abc123",
    "display_name": "Manh",
    "role": "admin",
}

METAL_EARTH_WORKSPACE = {
    "id": METAL_EARTH_WORKSPACE_ID,
    "name": "Metal Earth",
    "customer": "Fascinations Inc.",
    "status": "active",
}

METAL_EARTH_PROFILE = {
    "business_name": "Metal Earth",
    "description": (
        "Metal Earth, by Fascinations Inc. (Seattle, WA), produces laser-cut 3D metal "
        "model kits assembled from steel sheets — no glue or solder required. Product "
        "lines span Classic, Premium Series, and Licensed collections featuring Star Wars, "
        "Marvel, Harry Potter, Transformers, Lord of the Rings, Batman, Star Trek, and "
        "more. Categories include aviation, architecture, vehicles, space, tanks, ships, "
        "dinosaurs, and wildlife."
    ),
    "products": [
        "3D laser-cut steel model kits",
        "Licensed franchise model kits (Star Wars, Marvel, Harry Potter, etc.)",
        "Premium Series large-scale metal models",
        "Aviation & military model kits (Boeing, Lockheed Martin, Cessna)",
        "Architecture landmark model kits",
        "Gift Box Sets and accessories",
    ],
    "competitors": [
        "Piececool (Chinese 3D metal puzzles)",
        "UGEARS (wooden mechanical model kits)",
        "Tenyo Metallic Nano (Japanese licensee, same factory)",
        "HK Nanyuan / MU Model (AliExpress metal model brands)",
        "Professor Puzzle (UK distributor & competitor)",
    ],
    "priority_themes": [
        "licensed merchandise and IP deals",
        "Star Wars, Marvel, Disney franchise developments",
        "toy industry trends and Toy Fair announcements",
        "hobby retail channel and specialty store trends",
        "3D model kit and metal puzzle market",
        "new entertainment franchises with licensing potential",
        "Hasbro, Mattel, and major toy company strategies",
        "collectibles and gift product trends",
        "aerospace and aviation milestones",
    ],
    "excluded_topics": [
        "cryptocurrency and blockchain",
        "enterprise SaaS and cloud infrastructure",
        "general software engineering",
        "pharmaceutical and biotech",
        "real estate investment",
    ],
    "notes": (
        "Prioritize: (1) new licensed IP/franchise deals that Metal Earth could pursue, "
        "(2) competitor product launches or market moves, (3) toy/hobby retail channel "
        "signals (Toy Fair, retail partnerships, e-commerce trends), (4) entertainment "
        "releases (movies, series) that could drive collectible demand, and (5) "
        "aerospace/architecture news inspiring future product lines."
    ),
}

METAL_EARTH_SETTINGS = {
    "schedule": {
        "enabled": False,
        "frequency": "daily",
        "timeOfDay": "08:00",
        "timezone": "UTC",
    },
    "report_style": "detailed",
    "thresholds": {
        "min_relevance_score": 0.15,
        "min_final_score": 0.15,
        "max_articles_per_report": 10,
        "trusted_domains": [
            "toybook.com",
            "licenseglobal.com",
            "thepopinsider.com",
            "hasbro.com",
            "mattel.com",
            "disney.com",
            "starwars.com",
            "marvel.com",
            "anbmedia.com",
        ],
    },
    "retention": {
        "contentDays": 90,
        "reportDays": 365,
        "runHistoryDays": 180,
    },
    "email_delivery": {
        "enabled": False,
        "recipients": [],
        "subjectPrefix": "[Metal Earth Intel]",
    },
}

METAL_EARTH_FEEDS = [
    {
        "name": "The Toy Book — toy industry news",
        "url": "https://toybook.com/feed/",
        "type": "rss",
        "status": "healthy",
        "cadence": "daily",
        "tags": ["toy", "industry"],
    },
    {
        "name": "The Pop Insider — pop culture & collectibles",
        "url": "https://thepopinsider.com/feed/",
        "type": "rss",
        "status": "healthy",
        "cadence": "daily",
        "tags": ["pop-culture", "collectibles"],
    },
    {
        "name": "aNb Media / TFE Magazine — toy industry",
        "url": "https://www.anbmedia.com/feed/",
        "type": "rss",
        "status": "healthy",
        "cadence": "daily",
        "tags": ["toy", "hobby"],
    },
    {
        "name": "Make: — maker projects & scale modeling",
        "url": "https://makezine.com/feed/",
        "type": "rss",
        "status": "healthy",
        "cadence": "daily",
        "tags": ["maker", "diy", "hobby"],
    },
    {
        "name": "The Mary Sue — pop culture & entertainment",
        "url": "https://www.themarysue.com/feed/",
        "type": "rss",
        "status": "healthy",
        "cadence": "daily",
        "tags": ["pop-culture", "entertainment"],
    },
]


def seed_manh_user(db) -> None:
    """Create the 'manh' user if it does not already exist."""
    existing = db.query(User).filter(User.username == MANH_USER["username"]).first()
    if existing:
        logger.info("User '%s' already exists. Skipping.", MANH_USER["username"])
        return
    user = User(
        username=MANH_USER["username"],
        password_hash=hash_password(MANH_USER["password"]),
        display_name=MANH_USER["display_name"],
        role=MANH_USER["role"],
        status="active",
    )
    db.add(user)
    db.flush()
    logger.info("Created user: %s", user.username)


def seed_metal_earth(db) -> None:
    """Create the Metal Earth workspace with profile, settings, and feeds."""
    existing = (
        db.query(Workspace).filter(Workspace.id == METAL_EARTH_WORKSPACE_ID).first()
    )
    if existing:
        logger.info(
            "Metal Earth workspace '%s' (id=%s) already exists. Skipping seed.",
            existing.name,
            existing.id,
        )
        return

    now = datetime.now(timezone.utc)

    ws = Workspace(
        id=METAL_EARTH_WORKSPACE_ID,
        name=METAL_EARTH_WORKSPACE["name"],
        customer=METAL_EARTH_WORKSPACE["customer"],
        status=METAL_EARTH_WORKSPACE["status"],
        created_at=now,
        updated_at=now,
    )
    db.add(ws)
    db.flush()
    logger.info("Created Metal Earth workspace: %s", ws.name)

    profile = WorkspaceProfile(
        id=uuid.uuid4().hex,
        workspace_id=ws.id,
        **METAL_EARTH_PROFILE,
        created_at=now,
        updated_at=now,
    )
    db.add(profile)
    logger.info("Created Metal Earth profile")

    settings = WorkspaceSettings(
        id=uuid.uuid4().hex,
        workspace_id=ws.id,
        **METAL_EARTH_SETTINGS,
        updated_at=now,
    )
    db.add(settings)
    logger.info("Created Metal Earth settings")

    for feed_data in METAL_EARTH_FEEDS:
        feed = FeedSource(
            id=uuid.uuid4().hex,
            workspace_id=ws.id,
            **feed_data,
            created_at=now,
            updated_at=now,
        )
        db.add(feed)
    logger.info("Created %d Metal Earth feeds", len(METAL_EARTH_FEEDS))


def seed_demo_cli() -> None:
    """CLI entry point for demo seed (creates its own session)."""
    db = SessionLocal()
    try:
        seed_demo(db)
        seed_manh_user(db)
        seed_metal_earth(db)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    seed_demo_cli()
