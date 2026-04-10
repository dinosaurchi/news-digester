"""Seeded end-to-end backend integration tests.

These tests create a fresh workspace, seed deterministic feed fixtures,
run the real ``run-now`` API path, and verify that content import,
run metadata, report generation, and report-source resolution all work
without depending on pre-existing manual data.
"""

from datetime import datetime, timedelta, timezone

from app.services.pipeline_steps import FeedFetchResult
from app.tests.conftest import TestingSessionLocal
from app.tests.test_runs import (
    _create_feed,
    _create_workspace,
    _create_workspace_profile,
    _create_workspace_settings,
)


def _fetch_step(detail_json: dict) -> dict:
    return next(step for step in detail_json["steps"] if step["name"] == "fetch_feeds")


class TestSeededEndToEndPipeline:
    """End-to-end pipeline coverage with deterministic seeded fixtures."""

    def test_fresh_workspace_run_now_generates_report_with_resolvable_sources(
        self, client, monkeypatch
    ):
        ws_id = _create_workspace(client)
        _create_workspace_profile(
            client,
            ws_id,
            priority_themes=["AI", "automation", "cloud"],
        )
        _create_workspace_settings(
            client,
            ws_id,
            thresholds={
                "min_relevance_score": 0.1,
                "min_final_score": 0.1,
                "max_articles_per_report": 15,
            },
        )

        feed_ids = [
            _create_feed(client, ws_id, name="Tech News Feed", url="https://tech.example.com/rss"),
            _create_feed(
                client,
                ws_id,
                name="Industry Feed",
                url="https://industry.example.com/rss",
            ),
            _create_feed(client, ws_id, name="Cloud Feed", url="https://cloud.example.com/rss"),
        ]

        now = datetime.now(timezone.utc)
        entries_by_url = {
            "https://tech.example.com/rss": [
                {
                    "title": "AI Breakthrough in Healthcare Diagnostics",
                    "url": "https://tech.example.com/ai-healthcare",
                    "source_name": "Tech News Feed",
                    "published_at": now - timedelta(hours=1),
                    "author": "Reporter",
                    "summary": "AI diagnostics are improving patient triage.",
                    "raw_text": "Detailed article about AI diagnostics in healthcare.",
                },
                {
                    "title": "Cloud Computing Trends for 2026",
                    "url": "https://tech.example.com/cloud-trends",
                    "source_name": "Tech News Feed",
                    "published_at": now - timedelta(hours=2),
                    "author": "Reporter",
                    "summary": "Enterprises are consolidating cloud spend.",
                    "raw_text": "Detailed article about cloud cost optimization.",
                },
            ],
            "https://industry.example.com/rss": [
                {
                    "title": "Manufacturing Sector Embraces Automation",
                    "url": "https://industry.example.com/manufacturing-auto",
                    "source_name": "Industry Feed",
                    "published_at": now - timedelta(hours=3),
                    "author": "Analyst",
                    "summary": "Factories are scaling robotics deployments.",
                    "raw_text": "Detailed article about factory automation.",
                },
                {
                    "title": "Supply Chain Innovations Post-Pandemic",
                    "url": "https://industry.example.com/supply-chain",
                    "source_name": "Industry Feed",
                    "published_at": now - timedelta(hours=4),
                    "author": "Analyst",
                    "summary": "Vendors are using AI to rebalance logistics.",
                    "raw_text": "Detailed article about supply-chain analytics.",
                },
            ],
            "https://cloud.example.com/rss": [
                {
                    "title": "FinOps Teams Standardize Cloud Guardrails",
                    "url": "https://cloud.example.com/finops-guardrails",
                    "source_name": "Cloud Feed",
                    "published_at": now - timedelta(hours=5),
                    "author": "Editor",
                    "summary": "Cloud governance is moving into daily operations.",
                    "raw_text": "Detailed article about cloud governance and FinOps.",
                }
            ],
        }

        monkeypatch.setattr(
            "app.services.pipeline.fetch_feed",
            lambda feed: FeedFetchResult(
                success=True,
                entries=entries_by_url[feed.url],
                error=None,
                source_title=feed.name,
            ),
        )

        run_resp = client.post(f"/api/workspaces/{ws_id}/run-now")
        assert run_resp.status_code == 201
        run_id = run_resp.json()["id"]
        assert run_resp.json()["status"] == "success"

        detail_resp = client.get(f"/api/runs/{run_id}")
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        fetch_step = _fetch_step(detail)
        assert fetch_step["metadata"]["feedsAttempted"] == 3
        assert fetch_step["metadata"]["feedsSucceeded"] == 3
        assert fetch_step["metadata"]["feedsFailed"] == 0
        assert fetch_step["metadata"]["entriesFetched"] == 5
        assert fetch_step["metadata"]["entriesImported"] == 5
        assert fetch_step["metadata"]["entriesSkipped"] == 0
        assert len(fetch_step["metadata"]["feedDetails"]) == 3

        report_ids = detail["links"]["reports"]
        assert len(report_ids) == 1
        report_id = report_ids[0]

        report_resp = client.get(f"/api/reports/{report_id}")
        assert report_resp.status_code == 200
        assert report_resp.json()["status"] == "published"
        assert report_resp.json()["messageCount"] >= 1

        msg_resp = client.get(f"/api/report-threads/{report_id}/messages")
        assert msg_resp.status_code == 200
        messages = msg_resp.json()
        system_messages = [m for m in messages if m["role"] == "system"]
        assert len(system_messages) == 1
        system_message = system_messages[0]
        assert "AI Breakthrough in Healthcare Diagnostics" in system_message["content"]

        source_ids = system_message["metadata"]["sources"]
        assert len(source_ids) > 0
        assert all(not source_id.startswith("http") for source_id in source_ids)

        for source_id in source_ids:
            content_resp = client.get(f"/api/content/{source_id}")
            assert content_resp.status_code == 200
            assert content_resp.json()["workspaceId"] == ws_id

        db = TestingSessionLocal()
        try:
            from app.models.content import ContentItem

            db_count = (
                db.query(ContentItem).filter(ContentItem.workspace_id == ws_id).count()
            )
            assert db_count == 5
        finally:
            db.close()

        assert len(feed_ids) == 3

    def test_fresh_workspace_second_run_is_idempotent(self, client, monkeypatch):
        ws_id = _create_workspace(client)
        _create_workspace_profile(client, ws_id, priority_themes=["AI", "automation"])
        _create_workspace_settings(client, ws_id)

        _create_feed(client, ws_id, name="Source X", url="https://source-x.example.com/rss")
        _create_feed(client, ws_id, name="Source Y", url="https://source-y.example.com/rss")

        now = datetime.now(timezone.utc)
        entries_by_url = {
            "https://source-x.example.com/rss": [
                {
                    "title": "First article from Source X",
                    "url": "https://source-x.example.com/article-1",
                    "source_name": "Source X",
                    "published_at": now - timedelta(hours=1),
                    "author": "Writer",
                    "summary": "Source X summary one.",
                    "raw_text": "Source X article one body.",
                },
                {
                    "title": "Second article from Source X",
                    "url": "https://source-x.example.com/article-2",
                    "source_name": "Source X",
                    "published_at": now - timedelta(hours=2),
                    "author": "Writer",
                    "summary": "Source X summary two.",
                    "raw_text": "Source X article two body.",
                },
            ],
            "https://source-y.example.com/rss": [
                {
                    "title": "First article from Source Y",
                    "url": "https://source-y.example.com/article-1",
                    "source_name": "Source Y",
                    "published_at": now - timedelta(hours=3),
                    "author": "Writer",
                    "summary": "Source Y summary one.",
                    "raw_text": "Source Y article one body.",
                },
                {
                    "title": "Second article from Source Y",
                    "url": "https://source-y.example.com/article-2",
                    "source_name": "Source Y",
                    "published_at": now - timedelta(hours=4),
                    "author": "Writer",
                    "summary": "Source Y summary two.",
                    "raw_text": "Source Y article two body.",
                },
            ],
        }

        monkeypatch.setattr(
            "app.services.pipeline.fetch_feed",
            lambda feed: FeedFetchResult(
                success=True,
                entries=entries_by_url[feed.url],
                error=None,
                source_title=feed.name,
            ),
        )

        first_run_resp = client.post(f"/api/workspaces/{ws_id}/run-now")
        assert first_run_resp.status_code == 201
        first_run_id = first_run_resp.json()["id"]

        second_run_resp = client.post(f"/api/workspaces/{ws_id}/run-now")
        assert second_run_resp.status_code == 201
        second_run_id = second_run_resp.json()["id"]

        second_detail_resp = client.get(f"/api/runs/{second_run_id}")
        assert second_detail_resp.status_code == 200
        second_detail = second_detail_resp.json()
        fetch_step = _fetch_step(second_detail)
        assert fetch_step["metadata"]["feedsAttempted"] == 2
        assert fetch_step["metadata"]["feedsSucceeded"] == 2
        assert fetch_step["metadata"]["feedsFailed"] == 0
        assert fetch_step["metadata"]["entriesFetched"] == 4
        assert fetch_step["metadata"]["entriesImported"] == 0
        assert fetch_step["metadata"]["entriesSkipped"] == 4

        db = TestingSessionLocal()
        try:
            from app.models.content import ContentItem
            from app.models.run import ProcessingRun

            content_count = (
                db.query(ContentItem).filter(ContentItem.workspace_id == ws_id).count()
            )
            run_count = db.query(ProcessingRun).filter(ProcessingRun.workspace_id == ws_id).count()
            assert content_count == 4
            assert run_count == 2
        finally:
            db.close()

        assert first_run_id != second_run_id
