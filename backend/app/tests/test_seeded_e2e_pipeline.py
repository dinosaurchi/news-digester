"""Seeded end-to-end backend integration test.

Verifies that a brand-new workspace can be created, seeded with feeds,
ingested, and turned into a report — all using deterministic fixtures
(mocked HTTP), without depending on pre-existing manual data.
"""

from unittest.mock import patch

from app.models.content import ContentItem
from app.models.run import ProcessingRun
from app.services.pipeline import execute_workspace_run
from app.services.pipeline_steps import FeedFetchResult

from app.tests.test_pipeline_feed_failure import (
    _fake_generate_report,
    _make_entry,
    _make_feed,
    _make_workspace,
    _setup_downstream_mocks,
)


class TestSeededEndToEndPipeline:
    """End-to-end pipeline test with deterministic seeded fixtures."""

    @patch("app.services.pipeline.select_shortlist")
    @patch("app.services.pipeline.generate_report")
    @patch("app.services.pipeline.score_content_items")
    @patch("app.services.pipeline.cluster_content_items")
    @patch("app.services.pipeline.fetch_feed")
    def test_fresh_workspace_full_pipeline_to_report(
        self,
        mock_fetch,
        mock_cluster,
        mock_score,
        mock_report,
        mock_shortlist,
        db_session,
    ):
        """Full pipeline: workspace → feeds → fetch → normalize → cluster → score → shortlist → report."""
        # 1. Create a fresh workspace with 3 feeds
        ws = _make_workspace(db_session, name="E2E Test WS", customer="TestCo")

        feed_a = _make_feed(
            db_session,
            ws.id,
            name="Tech News Feed",
            url="https://tech.example.com/rss",
        )
        feed_b = _make_feed(
            db_session,
            ws.id,
            name="Industry Feed",
            url="https://industry.example.com/rss",
        )
        feed_c = _make_feed(
            db_session,
            ws.id,
            name="Blog Feed",
            url="https://blog.example.com/rss",
            feed_type="blog",
        )

        # 2. Deterministic entries: 2 + 3 + 2 = 7 total
        entries_by_feed = {
            feed_a.id: [
                _make_entry(
                    title="AI Breakthrough in Healthcare Diagnostics",
                    url="https://tech.example.com/ai-healthcare",
                ),
                _make_entry(
                    title="Cloud Computing Trends for 2025",
                    url="https://tech.example.com/cloud-trends",
                ),
            ],
            feed_b.id: [
                _make_entry(
                    title="Manufacturing Sector Embraces Automation",
                    url="https://industry.example.com/manufacturing-auto",
                ),
                _make_entry(
                    title="Supply Chain Innovations Post-Pandemic",
                    url="https://industry.example.com/supply-chain",
                ),
                _make_entry(
                    title="Small Business Grant Programs Announced",
                    url="https://industry.example.com/grants",
                ),
            ],
            feed_c.id: [
                _make_entry(
                    title="Entrepreneurship Lessons from Founders",
                    url="https://blog.example.com/entrepreneurship",
                ),
                _make_entry(
                    title="Remote Work Productivity Tips",
                    url="https://blog.example.com/remote-work",
                ),
            ],
        }

        def fetch_side_effect(feed):
            entries = entries_by_feed.get(feed.id, [])
            return FeedFetchResult(
                success=True,
                entries=entries,
                error=None,
                source_title=feed.name,
            )

        mock_fetch.side_effect = fetch_side_effect
        _setup_downstream_mocks(mock_cluster, mock_score, mock_report, mock_shortlist)

        # 3. Execute the pipeline
        run, items, report = execute_workspace_run(db_session, ws)

        # 4. Assertions

        # Run was created with status "success"
        assert run.status == "success"
        assert run.workspace_id == ws.id
        assert run.finished_at is not None
        assert run.duration_ms is not None

        # Content items were imported (7 total)
        assert len(items) == 7
        db_items = (
            db_session.query(ContentItem)
            .filter(ContentItem.workspace_id == ws.id)
            .all()
        )
        assert len(db_items) == 7

        # Each content item has a valid source_entry_id
        for item in db_items:
            assert item.source_entry_id is not None
            assert len(item.source_entry_id) > 0
            assert item.id is not None

        # Feed statuses were updated to "healthy" with last_fetched_at set
        for feed in [feed_a, feed_b, feed_c]:
            db_session.refresh(feed)
            assert feed.status == "healthy"
            assert feed.last_fetched_at is not None
            assert feed.last_error is None

        # A report was created and linked to the run
        assert report is not None
        assert report.run_id == run.id
        assert report.workspace_id == ws.id

        # Report sources resolve to valid ContentItem records:
        # all items returned from the pipeline are queryable from the DB
        item_ids = {item.id for item in items}
        db_item_ids = {
            row.id
            for row in db_session.query(ContentItem.id)
            .filter(ContentItem.workspace_id == ws.id)
            .all()
        }
        assert item_ids == db_item_ids

    @patch("app.services.pipeline.select_shortlist")
    @patch("app.services.pipeline.generate_report")
    @patch("app.services.pipeline.score_content_items")
    @patch("app.services.pipeline.cluster_content_items")
    @patch("app.services.pipeline.fetch_feed")
    def test_fresh_workspace_idempotent_re_run(
        self,
        mock_fetch,
        mock_cluster,
        mock_score,
        mock_report,
        mock_shortlist,
        db_session,
    ):
        """Running the pipeline twice with the same entries is idempotent."""
        # 1. Create workspace with 2 feeds
        ws = _make_workspace(db_session, name="Idempotent WS", customer="TestCo")

        feed_x = _make_feed(
            db_session,
            ws.id,
            name="Source X",
            url="https://source-x.example.com/rss",
        )
        feed_y = _make_feed(
            db_session,
            ws.id,
            name="Source Y",
            url="https://source-y.example.com/rss",
        )

        # 2. Deterministic entries: 2 + 2 = 4 total
        entries_by_feed = {
            feed_x.id: [
                _make_entry(
                    title="First article from Source X",
                    url="https://source-x.example.com/article-1",
                ),
                _make_entry(
                    title="Second article from Source X",
                    url="https://source-x.example.com/article-2",
                ),
            ],
            feed_y.id: [
                _make_entry(
                    title="First article from Source Y",
                    url="https://source-y.example.com/article-1",
                ),
                _make_entry(
                    title="Second article from Source Y",
                    url="https://source-y.example.com/article-2",
                ),
            ],
        }

        def fetch_side_effect(feed):
            entries = entries_by_feed.get(feed.id, [])
            return FeedFetchResult(
                success=True,
                entries=entries,
                error=None,
                source_title=feed.name,
            )

        mock_fetch.side_effect = fetch_side_effect
        _setup_downstream_mocks(mock_cluster, mock_score, mock_report, mock_shortlist)

        # 3. First run
        run1, items1, report1 = execute_workspace_run(db_session, ws)

        total_after_run1 = (
            db_session.query(ContentItem)
            .filter(ContentItem.workspace_id == ws.id)
            .count()
        )
        assert total_after_run1 == 4
        assert len(items1) == 4

        # 4. Second run (same mocks → same entries returned)
        run2, items2, report2 = execute_workspace_run(db_session, ws)

        # 5. Assertions

        # Second run imported 0 new content items (all skipped as duplicates)
        assert len(items2) == 0

        # Total content items still equals first-run count only
        total_after_run2 = (
            db_session.query(ContentItem)
            .filter(ContentItem.workspace_id == ws.id)
            .count()
        )
        assert total_after_run2 == 4

        # Run count is 2
        run_count = (
            db_session.query(ProcessingRun)
            .filter(ProcessingRun.workspace_id == ws.id)
            .count()
        )
        assert run_count == 2

        # Both runs succeeded with distinct IDs
        assert run1.status == "success"
        assert run2.status == "success"
        assert run1.id != run2.id
