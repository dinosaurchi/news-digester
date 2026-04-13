"""Celery application and Beat schedule for Pass 6 pipeline tasks."""

from celery import Celery

from app.config import settings

celery_app = Celery(
    "sme_news_admin",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "scan-scheduled-workspaces": {
            "task": "app.tasks.pipeline.run_scheduled_workspaces",
            "schedule": 300.0,
        }
    },
)

celery_app.autodiscover_tasks(["app.tasks"])

# Ensure task modules are imported so the worker can resolve them by name.
# Must come after celery_app is defined to avoid circular imports.
import app.tasks.pipeline  # noqa: F401, E402
