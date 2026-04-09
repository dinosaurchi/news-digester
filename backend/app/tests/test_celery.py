"""Tests for Celery configuration and scheduling smoke paths."""

from app.celery_app import celery_app
from app.tasks.pipeline import get_scheduled_workspace_ids, run_scheduled_workspaces


def _create_workspace(client, **payload):
    body = {"name": "Scheduled WS", "customer": "Co"}
    body.update(payload)
    return client.post("/api/workspaces", json=body).json()["id"]


class TestCeleryConfig:
    def test_beat_schedule_registered(self):
        schedule = celery_app.conf.beat_schedule
        assert "scan-scheduled-workspaces" in schedule
        assert schedule["scan-scheduled-workspaces"]["task"] == (
            "app.tasks.pipeline.run_scheduled_workspaces"
        )


class TestSchedulerSelection:
    def test_get_scheduled_workspace_ids_only_returns_enabled_active_workspaces(
        self, client, db_session
    ):
        enabled_ws = _create_workspace(client, name="Enabled")
        disabled_ws = _create_workspace(client, name="Disabled")
        archived_ws = _create_workspace(client, name="Archived", status="archived")

        client.put(
            f"/api/workspaces/{enabled_ws}/settings",
            json={
                "schedule": {
                    "enabled": True,
                    "frequency": "daily",
                    "timeOfDay": "09:30",
                    "timezone": "UTC",
                }
            },
        )
        client.put(
            f"/api/workspaces/{disabled_ws}/settings",
            json={
                "schedule": {
                    "enabled": False,
                    "frequency": "daily",
                    "timeOfDay": "09:30",
                    "timezone": "UTC",
                }
            },
        )
        client.put(
            f"/api/workspaces/{archived_ws}/settings",
            json={
                "schedule": {
                    "enabled": True,
                    "frequency": "daily",
                    "timeOfDay": "09:30",
                    "timezone": "UTC",
                }
            },
        )

        workspace_ids = get_scheduled_workspace_ids(db_session)
        assert enabled_ws in workspace_ids
        assert disabled_ws not in workspace_ids
        assert archived_ws not in workspace_ids

    def test_run_scheduled_workspaces_enqueues_enabled_workspaces(
        self, client, monkeypatch
    ):
        enabled_ws = _create_workspace(client)
        client.put(
            f"/api/workspaces/{enabled_ws}/settings",
            json={
                "schedule": {
                    "enabled": True,
                    "frequency": "daily",
                    "timeOfDay": "09:30",
                    "timezone": "UTC",
                }
            },
        )

        calls: list[tuple[str, str]] = []

        def fake_delay(workspace_id: str, run_type: str):
            calls.append((workspace_id, run_type))

        monkeypatch.setattr(
            "app.tasks.pipeline.run_workspace_pipeline.delay",
            fake_delay,
        )
        monkeypatch.setattr(
            "app.tasks.pipeline.get_scheduled_workspace_ids",
            lambda db: [enabled_ws],
        )

        result = run_scheduled_workspaces()
        assert result["enqueued"] == 1
        assert calls == [(enabled_ws, "scheduled")]
