"""Seed/dev fixture data.

Run with:
    cd backend && python -m app.seed
"""

import logging
from datetime import datetime, timezone

from app.db.session import SessionLocal
from app.models.workspace import Workspace, WorkspaceProfile, WorkspaceSettings
from app.models.feed import FeedSource

logger = logging.getLogger(__name__)

WORKSPACES = [
    {
        "id": "ws-1",
        "name": "TechCorp Strategy",
        "customer": "TechCorp Inc.",
        "status": "active",
        "created_at": datetime(2024, 1, 10, 10, 0, 0, tzinfo=timezone.utc),
        "updated_at": datetime(2024, 3, 20, 15, 30, 0, tzinfo=timezone.utc),
    },
    {
        "id": "ws-2",
        "name": "GreenEnergy Insights",
        "customer": "EcoSolutions Ltd.",
        "status": "active",
        "created_at": datetime(2024, 2, 15, 9, 0, 0, tzinfo=timezone.utc),
        "updated_at": datetime(2024, 3, 19, 11, 20, 0, tzinfo=timezone.utc),
    },
    {
        "id": "ws-3",
        "name": "RetailWatch",
        "customer": "Global Retail Group",
        "status": "paused",
        "created_at": datetime(2023, 11, 5, 14, 0, 0, tzinfo=timezone.utc),
        "updated_at": datetime(2024, 3, 1, 10, 0, 0, tzinfo=timezone.utc),
    },
    {
        "id": "ws-4",
        "name": "FinServ Monitor",
        "customer": "Apex Financial Services",
        "status": "active",
        "created_at": datetime(2024, 1, 22, 8, 30, 0, tzinfo=timezone.utc),
        "updated_at": datetime(2024, 3, 20, 16, 45, 0, tzinfo=timezone.utc),
    },
    {
        "id": "ws-5",
        "name": "HealthTech Radar",
        "customer": "MediCore Laboratories",
        "status": "archived",
        "created_at": datetime(2023, 9, 12, 11, 0, 0, tzinfo=timezone.utc),
        "updated_at": datetime(2024, 2, 15, 9, 0, 0, tzinfo=timezone.utc),
    },
]

PROFILES = [
    {
        "id": "prof-1",
        "workspace_id": "ws-1",
        "business_name": "TechCorp Inc.",
        "description": "A leading provider of enterprise cloud solutions and AI infrastructure, serving Fortune 500 companies across 40+ countries. TechCorp specializes in hybrid cloud deployments, AI-powered data analytics, and cybersecurity solutions for the financial services and healthcare sectors.",
        "products": [
            "CloudStack Pro",
            "AI-Flow Engine",
            "DataGuard Shield",
            "Edge-Connect Hub",
        ],
        "competitors": [
            "CloudGiant",
            "DataNexus Corp.",
            "SoftSystems International",
            "NovaTech Solutions",
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
        "notes": "Focus on enterprise adoption trends and regulatory changes in the EU (AI Act) and US markets. Pay special attention to competitive moves from CloudGiant and DataNexus.",
        "updated_at": datetime(2024, 3, 18, 14, 30, 0, tzinfo=timezone.utc),
    },
    {
        "id": "prof-2",
        "workspace_id": "ws-2",
        "business_name": "EcoSolutions Ltd.",
        "description": "A European clean energy company specializing in solar panel manufacturing, battery storage systems, and smart grid technology. EcoSolutions operates across 15 European countries with a growing presence in the Asia-Pacific region.",
        "products": [
            "SunPower Panels",
            "EcoStore Battery",
            "GridMind Software",
            "GreenConnect IoT",
        ],
        "competitors": [
            "SolarEdge Technologies",
            "Tesla Energy",
            "Vestas Wind Systems",
            "Enphase Energy",
        ],
        "priority_themes": [
            "Solar Energy Policy",
            "Battery Technology",
            "EU Green Deal",
            "Carbon Credits",
            "Smart Grid Innovation",
        ],
        "excluded_topics": [
            "Fossil fuel investments",
            "Nuclear energy debates",
            "Automotive industry",
        ],
        "notes": "Monitor EU renewable energy subsidies and policy changes. Track battery recycling regulations and supply chain developments for lithium and cobalt.",
        "updated_at": datetime(2024, 3, 15, 10, 0, 0, tzinfo=timezone.utc),
    },
    {
        "id": "prof-3",
        "workspace_id": "ws-3",
        "business_name": "Global Retail Group",
        "description": "An international retail conglomerate operating 2,500+ stores across Europe, North America, and Asia. The group manages brands in fashion, electronics, home goods, and grocery retail.",
        "products": [
            "RetailConnect POS",
            "ShopAnalytics Platform",
            "SupplyChain Manager",
        ],
        "competitors": ["Amazon", "Walmart", "Alibaba Group", "Shopify"],
        "priority_themes": [
            "E-commerce Trends",
            "Supply Chain Optimization",
            "Consumer Behavior",
            "Retail Technology",
            "Omnichannel Strategy",
        ],
        "excluded_topics": ["Celebrity gossip", "Entertainment news", "Sports results"],
        "notes": "Workspace paused due to internal restructuring. Resume monitoring in Q2 2024.",
        "updated_at": datetime(2024, 3, 1, 9, 0, 0, tzinfo=timezone.utc),
    },
    {
        "id": "prof-4",
        "workspace_id": "ws-4",
        "business_name": "Apex Financial Services",
        "description": "A multinational investment bank and financial services company headquartered in London, with operations in 30+ countries. Apex provides corporate banking, wealth management, and fintech solutions.",
        "products": [
            "ApexTrade Platform",
            "WealthPilot Advisor",
            "RegTech Suite",
            "PayStream",
        ],
        "competitors": ["Goldman Sachs", "JPMorgan Chase", "HSBC", "Stripe"],
        "priority_themes": [
            "Banking Regulation",
            "Fintech Innovation",
            "Digital Banking",
            "Open Banking",
            "Anti-Money Laundering",
        ],
        "excluded_topics": [
            "Personal finance tips",
            "Credit card promotions",
            "Mortgage rates for consumers",
        ],
        "notes": "Heavy focus on PSD2, Basel IV, and digital currency regulations. Monitor fintech startup ecosystem closely.",
        "updated_at": datetime(2024, 3, 20, 12, 0, 0, tzinfo=timezone.utc),
    },
    {
        "id": "prof-5",
        "workspace_id": "ws-5",
        "business_name": "MediCore Laboratories",
        "description": "A biotech company focused on diagnostic tools, laboratory automation, and health data analytics. MediCore serves hospitals, research institutions, and pharmaceutical companies worldwide.",
        "products": ["DiagnosticsAI", "LabFlow Automation", "HealthData Insights"],
        "competitors": [
            "Thermo Fisher Scientific",
            "Roche Diagnostics",
            "Siemens Healthineers",
        ],
        "priority_themes": [
            "AI in Diagnostics",
            "Lab Automation",
            "Healthcare Regulations",
            "Precision Medicine",
        ],
        "excluded_topics": ["Fitness tracking", "Wellness apps", "Dietary supplements"],
        "notes": "Workspace archived after MediCore was acquired. Data retained for compliance purposes.",
        "updated_at": datetime(2024, 2, 15, 8, 0, 0, tzinfo=timezone.utc),
    },
]

SETTINGS = [
    {
        "id": "settings-1",
        "workspace_id": "ws-1",
        "schedule": {
            "enabled": True,
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
            "enabled": True,
            "recipients": [
                "cto@techcorp.com",
                "strategy@techcorp.com",
                "competitive-intel@techcorp.com",
            ],
            "subjectPrefix": "[TechCorp Intel]",
        },
        "updated_at": datetime(2024, 3, 15, 10, 30, 0, tzinfo=timezone.utc),
    },
    {
        "id": "settings-2",
        "workspace_id": "ws-2",
        "schedule": {
            "enabled": True,
            "frequency": "daily",
            "timeOfDay": "08:00",
            "timezone": "Europe/Berlin",
        },
        "report_style": "bulleted",
        "thresholds": {
            "minRelevanceScore": 0.60,
            "minFinalScore": 0.65,
            "maxArticlesPerReport": 12,
        },
        "retention": {
            "contentDays": 60,
            "reportDays": 365,
            "runHistoryDays": 90,
        },
        "email_delivery": {
            "enabled": True,
            "recipients": [
                "insights@ecosolutions.eu",
                "sustainability@ecosolutions.eu",
            ],
            "subjectPrefix": "[EcoSolutions Energy Intel]",
        },
        "updated_at": datetime(2024, 3, 12, 14, 0, 0, tzinfo=timezone.utc),
    },
    {
        "id": "settings-3",
        "workspace_id": "ws-3",
        "schedule": {
            "enabled": False,
            "frequency": "daily",
            "timeOfDay": "08:00",
            "timezone": "Europe/London",
        },
        "report_style": "concise",
        "thresholds": {
            "minRelevanceScore": 0.55,
            "minFinalScore": 0.60,
            "maxArticlesPerReport": 20,
        },
        "retention": {
            "contentDays": 30,
            "reportDays": 180,
            "runHistoryDays": 60,
        },
        "email_delivery": {
            "enabled": False,
            "recipients": ["retail-intel@globalretailgroup.com"],
            "subjectPrefix": "[RetailWatch]",
        },
        "updated_at": datetime(2024, 3, 1, 9, 0, 0, tzinfo=timezone.utc),
    },
    {
        "id": "settings-4",
        "workspace_id": "ws-4",
        "schedule": {
            "enabled": True,
            "frequency": "twice_daily",
            "timeOfDay": "06:00",
            "timezone": "Europe/London",
        },
        "report_style": "detailed",
        "thresholds": {
            "minRelevanceScore": 0.70,
            "minFinalScore": 0.75,
            "maxArticlesPerReport": 10,
        },
        "retention": {
            "contentDays": 120,
            "reportDays": 365,
            "runHistoryDays": 180,
        },
        "email_delivery": {
            "enabled": True,
            "recipients": ["risk@apexfinancial.com", "compliance@apexfinancial.com"],
            "subjectPrefix": "[Apex FinServ Intel]",
        },
        "updated_at": datetime(2024, 3, 18, 16, 0, 0, tzinfo=timezone.utc),
    },
    {
        "id": "settings-5",
        "workspace_id": "ws-5",
        "schedule": {
            "enabled": False,
            "frequency": "weekly",
            "timeOfDay": "08:00",
            "timezone": "America/New_York",
        },
        "report_style": "concise",
        "thresholds": {
            "minRelevanceScore": 0.50,
            "minFinalScore": 0.55,
            "maxArticlesPerReport": 8,
        },
        "retention": {
            "contentDays": 30,
            "reportDays": 90,
            "runHistoryDays": 30,
        },
        "email_delivery": {
            "enabled": False,
            "recipients": [],
            "subjectPrefix": "[MediCore Intel]",
        },
        "updated_at": datetime(2024, 2, 15, 8, 0, 0, tzinfo=timezone.utc),
    },
]

FEEDS = [
    # ws-1: TechCorp Strategy
    {
        "id": "feed-1",
        "workspace_id": "ws-1",
        "name": "TechCrunch RSS",
        "url": "https://techcrunch.com/feed/",
        "type": "rss",
        "status": "healthy",
        "cadence": "daily",
        "tags": ["tech", "startups"],
        "last_fetched_at": datetime(2024, 3, 20, 8, 0, 0, tzinfo=timezone.utc),
        "created_at": datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        "updated_at": datetime(2024, 3, 20, 8, 0, 0, tzinfo=timezone.utc),
    },
    {
        "id": "feed-2",
        "workspace_id": "ws-1",
        "name": "Ars Technica",
        "url": "https://feeds.arstechnica.com/arstechnica/index",
        "type": "rss",
        "status": "healthy",
        "cadence": "daily",
        "tags": ["tech", "science"],
        "last_fetched_at": datetime(2024, 3, 20, 8, 0, 0, tzinfo=timezone.utc),
        "created_at": datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        "updated_at": datetime(2024, 3, 20, 8, 0, 0, tzinfo=timezone.utc),
    },
    {
        "id": "feed-3",
        "workspace_id": "ws-1",
        "name": "The Verge",
        "url": "https://www.theverge.com/rss/index.xml",
        "type": "website",
        "status": "healthy",
        "cadence": "hourly",
        "tags": ["tech", "culture"],
        "last_fetched_at": datetime(2024, 3, 20, 9, 0, 0, tzinfo=timezone.utc),
        "created_at": datetime(2024, 2, 1, 10, 0, 0, tzinfo=timezone.utc),
        "updated_at": datetime(2024, 3, 20, 9, 0, 0, tzinfo=timezone.utc),
    },
    {
        "id": "feed-4",
        "workspace_id": "ws-1",
        "name": "Wired Blog",
        "url": "https://www.wired.com/feed/rss",
        "type": "blog",
        "status": "healthy",
        "cadence": "daily",
        "tags": ["tech", "innovation"],
        "last_fetched_at": datetime(2024, 3, 19, 8, 0, 0, tzinfo=timezone.utc),
        "created_at": datetime(2024, 2, 10, 10, 0, 0, tzinfo=timezone.utc),
        "updated_at": datetime(2024, 3, 19, 8, 0, 0, tzinfo=timezone.utc),
    },
    {
        "id": "feed-5",
        "workspace_id": "ws-1",
        "name": "Competitor AI News",
        "url": "https://competitor.example.com/feed",
        "type": "competitor",
        "status": "disabled",
        "cadence": "weekly",
        "tags": ["competitor", "ai"],
        "last_fetched_at": None,
        "last_error": None,
        "created_at": datetime(2024, 1, 20, 10, 0, 0, tzinfo=timezone.utc),
        "updated_at": datetime(2024, 2, 15, 12, 0, 0, tzinfo=timezone.utc),
    },
    # ws-2: GreenEnergy Insights
    {
        "id": "feed-6",
        "workspace_id": "ws-2",
        "name": "Clean Energy Wire",
        "url": "https://www.cleanenergywire.org/rss",
        "type": "rss",
        "status": "healthy",
        "cadence": "daily",
        "tags": ["renewable", "policy"],
        "last_fetched_at": datetime(2024, 3, 20, 7, 0, 0, tzinfo=timezone.utc),
        "created_at": datetime(2024, 2, 20, 9, 0, 0, tzinfo=timezone.utc),
        "updated_at": datetime(2024, 3, 20, 7, 0, 0, tzinfo=timezone.utc),
    },
    {
        "id": "feed-7",
        "workspace_id": "ws-2",
        "name": "Solar Power World",
        "url": "https://www.solarpowerworldonline.com/feed/",
        "type": "website",
        "status": "healthy",
        "cadence": "daily",
        "tags": ["solar", "industry"],
        "last_fetched_at": datetime(2024, 3, 20, 7, 0, 0, tzinfo=timezone.utc),
        "created_at": datetime(2024, 2, 20, 9, 0, 0, tzinfo=timezone.utc),
        "updated_at": datetime(2024, 3, 20, 7, 0, 0, tzinfo=timezone.utc),
    },
    {
        "id": "feed-8",
        "workspace_id": "ws-2",
        "name": "Tesla Energy Blog",
        "url": "https://www.tesla.com/blog/rss",
        "type": "competitor",
        "status": "healthy",
        "cadence": "weekly",
        "tags": ["competitor", "battery"],
        "last_fetched_at": datetime(2024, 3, 18, 8, 0, 0, tzinfo=timezone.utc),
        "created_at": datetime(2024, 3, 1, 10, 0, 0, tzinfo=timezone.utc),
        "updated_at": datetime(2024, 3, 18, 8, 0, 0, tzinfo=timezone.utc),
    },
    # ws-3: RetailWatch
    {
        "id": "feed-9",
        "workspace_id": "ws-3",
        "name": "Retail Dive",
        "url": "https://www.retaildive.com/rss/feed",
        "type": "rss",
        "status": "error",
        "cadence": "daily",
        "tags": ["retail", "ecommerce"],
        "last_fetched_at": datetime(2024, 3, 15, 8, 0, 0, tzinfo=timezone.utc),
        "last_error": "Connection timed out",
        "created_at": datetime(2023, 11, 10, 14, 0, 0, tzinfo=timezone.utc),
        "updated_at": datetime(2024, 3, 15, 8, 0, 0, tzinfo=timezone.utc),
    },
    {
        "id": "feed-10",
        "workspace_id": "ws-3",
        "name": "Shopify Blog",
        "url": "https://www.shopify.com/blog/rss",
        "type": "blog",
        "status": "healthy",
        "cadence": "daily",
        "tags": ["ecommerce", "platform"],
        "last_fetched_at": datetime(2024, 3, 20, 8, 0, 0, tzinfo=timezone.utc),
        "created_at": datetime(2023, 11, 10, 14, 0, 0, tzinfo=timezone.utc),
        "updated_at": datetime(2024, 3, 20, 8, 0, 0, tzinfo=timezone.utc),
    },
]


def seed() -> None:
    """Seed the database with fixture data."""
    db = SessionLocal()
    try:
        # Check if data already exists
        existing = db.query(Workspace).first()
        if existing:
            logger.info("Database already has data. Skipping seed.")
            return

        # Create workspaces
        for ws_data in WORKSPACES:
            ws = Workspace(**ws_data)
            db.add(ws)
        logger.info("Created %d workspaces", len(WORKSPACES))

        # Create profiles
        for prof_data in PROFILES:
            prof = WorkspaceProfile(**prof_data)
            db.add(prof)
        logger.info("Created %d profiles", len(PROFILES))

        # Create settings
        for sett_data in SETTINGS:
            sett = WorkspaceSettings(**sett_data)
            db.add(sett)
        logger.info("Created %d settings", len(SETTINGS))

        # Create feeds
        for feed_data in FEEDS:
            feed = FeedSource(**feed_data)
            db.add(feed)
        logger.info("Created %d feeds", len(FEEDS))

        db.commit()
        logger.info("Seed completed successfully.")
    except Exception:
        db.rollback()
        logger.exception("Seed failed")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    seed()
