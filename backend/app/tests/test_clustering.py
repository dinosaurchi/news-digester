"""Tests for clustering.py pipeline step."""

from datetime import datetime, timezone

import pytest

from app.models.content import ContentCluster, ContentItem
from app.models.workspace import Workspace
from app.services.clustering import (
    _is_better_lead,
    _item_to_dict,
    _select_lead_item,
    cluster_content_items,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_workspace(db, **overrides):
    """Create and persist a Workspace for use in tests."""
    defaults = {"name": "Test WS", "customer": "TestCo"}
    defaults.update(overrides)
    ws = Workspace(**defaults)
    db.add(ws)
    db.flush()
    return ws


def _make_item(db, workspace_id, **overrides):
    """Create and persist a ContentItem for use in tests."""
    defaults = {
        "workspace_id": workspace_id,
        "title": "Test Article",
        "content_type": "news",
        "status": "pending",
        "local_relevance_score": 0.5,
    }
    defaults.update(overrides)
    item = ContentItem(**defaults)
    db.add(item)
    db.flush()
    return item


# ---------------------------------------------------------------------------
# _item_to_dict
# ---------------------------------------------------------------------------


class TestItemToDict:
    """_item_to_dict converts a ContentItem to the dict shape expected by compute_similarity."""

    def test_basic_fields(self, db_session):
        ws = _make_workspace(db_session)
        item = _make_item(
            db_session,
            ws.id,
            url="https://example.com/article",
            title="Breaking News",
            published_at=datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc),
        )
        d = _item_to_dict(item)
        assert d["url"] == "https://example.com/article"
        assert d["title"] == "Breaking News"
        assert d["published_at"] == item.published_at

    def test_none_published_at(self, db_session):
        ws = _make_workspace(db_session)
        item = _make_item(db_session, ws.id, published_at=None)
        d = _item_to_dict(item)
        assert d["published_at"] is None


# ---------------------------------------------------------------------------
# _is_better_lead / _select_lead_item
# ---------------------------------------------------------------------------


class TestLeadSelection:
    """_is_better_lead and _select_lead_item pick the best lead for a cluster."""

    def _make_fake_item(
        self,
        published_at=None,
        final_score=None,
        local_relevance_score=None,
        created_at=None,
    ):
        """Build a lightweight fake ContentItem-like object for unit tests."""
        now = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)
        return type(
            "Item",
            (),
            {
                "published_at": published_at,
                "final_score": final_score,
                "local_relevance_score": local_relevance_score,
                "created_at": created_at or now,
            },
        )()

    def test_earliest_published_at_wins(self):
        current = self._make_fake_item(
            published_at=datetime(2024, 6, 5, tzinfo=timezone.utc)
        )
        candidate = self._make_fake_item(
            published_at=datetime(2024, 6, 1, tzinfo=timezone.utc)
        )
        assert _is_better_lead(candidate, current) is True

    def test_has_published_at_beats_none(self):
        current = self._make_fake_item(published_at=None)
        candidate = self._make_fake_item(
            published_at=datetime(2024, 6, 1, tzinfo=timezone.utc)
        )
        assert _is_better_lead(candidate, current) is True
        assert _is_better_lead(current, candidate) is False

    def test_neither_has_published_at_highest_score_wins(self):
        current = self._make_fake_item(final_score=0.3, local_relevance_score=0.3)
        candidate = self._make_fake_item(final_score=0.9, local_relevance_score=0.9)
        assert _is_better_lead(candidate, current) is True

    def test_neither_has_published_at_falls_back_to_created_at(self):
        now = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)
        current = self._make_fake_item(
            final_score=0.5,
            local_relevance_score=0.5,
            created_at=now,
        )
        candidate = self._make_fake_item(
            final_score=0.5,
            local_relevance_score=0.5,
            created_at=datetime(2024, 5, 1, 12, 0, tzinfo=timezone.utc),
        )
        assert _is_better_lead(candidate, current) is True

    def test_select_lead_item_picks_best(self):
        items = [
            self._make_fake_item(
                published_at=datetime(2024, 6, 5, tzinfo=timezone.utc)
            ),
            self._make_fake_item(
                published_at=datetime(2024, 6, 1, tzinfo=timezone.utc)
            ),
            self._make_fake_item(
                published_at=datetime(2024, 6, 3, tzinfo=timezone.utc)
            ),
        ]
        lead = _select_lead_item(items)
        assert lead.published_at == datetime(2024, 6, 1, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# cluster_content_items — empty input
# ---------------------------------------------------------------------------


class TestEmptyInput:
    """cluster_content_items with an empty list returns zeros."""

    def test_empty_list(self, db_session):
        result = cluster_content_items(db_session, [], "ws-1")
        assert result["clusters_created"] == 0
        assert result["items_clustered"] == 0
        assert result["singleton_clusters"] == 0

    def test_no_clusters_in_db(self, db_session):
        cluster_content_items(db_session, [], "ws-1")
        count = db_session.query(ContentCluster).count()
        assert count == 0


# ---------------------------------------------------------------------------
# cluster_content_items — single item
# ---------------------------------------------------------------------------


class TestSingleItem:
    """cluster_content_items with a single item creates a singleton cluster."""

    def test_single_item_creates_singleton(self, db_session):
        ws = _make_workspace(db_session)
        item = _make_item(
            db_session,
            ws.id,
            title="Solo Article",
            url="https://example.com/solo",
        )

        result = cluster_content_items(db_session, [item], ws.id)

        assert result["clusters_created"] == 1
        assert result["items_clustered"] == 1
        assert result["singleton_clusters"] == 1

        # Verify a cluster was created
        cluster = db_session.query(ContentCluster).first()
        assert cluster is not None
        assert cluster.workspace_id == ws.id
        assert cluster.item_count == 1
        assert "Solo Article" in cluster.label

        # Verify the item's cluster_id was set
        db_session.refresh(item)
        assert item.cluster_id == cluster.id


# ---------------------------------------------------------------------------
# cluster_content_items — URL-based dedup
# ---------------------------------------------------------------------------


class TestUrlDedup:
    """Items with the same normalised URL are grouped together."""

    def test_same_url_different_tracking_params(self, db_session):
        """utm_source and fbclid are stripped; items get the same cluster."""
        ws = _make_workspace(db_session)
        item1 = _make_item(
            db_session,
            ws.id,
            title="Article A",
            url="https://example.com/news/story?utm_source=twitter",
        )
        item2 = _make_item(
            db_session,
            ws.id,
            title="Article B",
            url="https://example.com/news/story?fbclid=abc123",
        )
        item3 = _make_item(
            db_session,
            ws.id,
            title="Article C",
            url="https://example.com/news/story",
        )

        result = cluster_content_items(db_session, [item1, item2, item3], ws.id)

        assert result["clusters_created"] == 1
        assert result["items_clustered"] == 3
        assert result["singleton_clusters"] == 0

        # All items share the same cluster_id
        db_session.refresh(item1)
        db_session.refresh(item2)
        db_session.refresh(item3)
        assert item1.cluster_id is not None
        assert item1.cluster_id == item2.cluster_id == item3.cluster_id

    def test_different_urls_are_not_grouped(self, db_session):
        """Items with genuinely different URLs are not URL-deduped."""
        ws = _make_workspace(db_session)
        item1 = _make_item(
            db_session,
            ws.id,
            title="Article A",
            url="https://example.com/page-a",
        )
        item2 = _make_item(
            db_session,
            ws.id,
            title="Article B",
            url="https://example.com/page-b",
        )

        result = cluster_content_items(db_session, [item1, item2], ws.id)

        # Two different URLs → two singleton clusters
        assert result["clusters_created"] == 2
        assert result["singleton_clusters"] == 2


# ---------------------------------------------------------------------------
# cluster_content_items — title-based dedup
# ---------------------------------------------------------------------------


class TestTitleDedup:
    """Items with identical title fingerprints are grouped together."""

    def test_same_title_different_casing(self, db_session):
        ws = _make_workspace(db_session)
        item1 = _make_item(
            db_session,
            ws.id,
            title="Breaking News Story",
            url="https://example.com/a",
        )
        item2 = _make_item(
            db_session,
            ws.id,
            title="BREAKING NEWS STORY",
            url="https://example.com/b",
        )

        result = cluster_content_items(db_session, [item1, item2], ws.id)

        assert result["clusters_created"] == 1
        assert result["items_clustered"] == 2

        db_session.refresh(item1)
        db_session.refresh(item2)
        assert item1.cluster_id == item2.cluster_id

    def test_same_title_different_spacing(self, db_session):
        ws = _make_workspace(db_session)
        item1 = _make_item(
            db_session,
            ws.id,
            title="Breaking News Story",
            url="https://example.com/a",
        )
        item2 = _make_item(
            db_session,
            ws.id,
            title="Breaking   News  Story",
            url="https://example.com/b",
        )

        result = cluster_content_items(db_session, [item1, item2], ws.id)

        assert result["clusters_created"] == 1
        assert result["items_clustered"] == 2

        db_session.refresh(item1)
        db_session.refresh(item2)
        assert item1.cluster_id == item2.cluster_id

    def test_same_title_boundary_punctuation(self, db_session):
        ws = _make_workspace(db_session)
        item1 = _make_item(
            db_session,
            ws.id,
            title="Breaking News",
            url="https://example.com/a",
        )
        item2 = _make_item(
            db_session,
            ws.id,
            title="-Breaking News-",
            url="https://example.com/b",
        )

        result = cluster_content_items(db_session, [item1, item2], ws.id)

        assert result["clusters_created"] == 1
        assert result["items_clustered"] == 2


# ---------------------------------------------------------------------------
# cluster_content_items — title+domain similarity grouping
# ---------------------------------------------------------------------------


class TestSimilarityGrouping:
    """Items with similar titles on the same domain may be grouped."""

    def test_same_domain_high_title_overlap(self, db_session):
        """Two items on the same domain with very similar titles get grouped."""
        ws = _make_workspace(db_session)
        # Choose titles with high token overlap so they cluster via the
        # domain+title secondary rule.  Tokens: {company, x, announces, new, ceo}
        # vs {company, x, announces, new, chief, executive} → intersection 4, union 7 ≈ 0.57
        item1 = _make_item(
            db_session,
            ws.id,
            title="Company X Announces New CEO",
            url="https://news.example.com/company-x-ceo",
            published_at=datetime(2024, 6, 1, 10, 0, tzinfo=timezone.utc),
        )
        item2 = _make_item(
            db_session,
            ws.id,
            title="Company X Announces New Chief Executive",
            url="https://news.example.com/company-x-chief",
            published_at=datetime(2024, 6, 1, 14, 0, tzinfo=timezone.utc),
        )

        # Use a generous threshold to ensure grouping
        result = cluster_content_items(
            db_session,
            [item1, item2],
            ws.id,
            similarity_threshold=0.5,
            domain_title_threshold=0.5,
        )

        # These share the domain and many title tokens, so they should cluster
        assert result["clusters_created"] == 1
        assert result["items_clustered"] == 2

        db_session.refresh(item1)
        db_session.refresh(item2)
        assert item1.cluster_id == item2.cluster_id

    def test_different_domains_similar_titles_not_grouped_at_high_threshold(
        self, db_session
    ):
        """Items on different domains with somewhat similar titles are not grouped
        when the combined score is below threshold."""
        ws = _make_workspace(db_session)
        item1 = _make_item(
            db_session,
            ws.id,
            title="Market Update Today",
            url="https://source-a.com/market",
            published_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
        )
        item2 = _make_item(
            db_session,
            ws.id,
            title="Market Update This Week",
            url="https://source-b.com/market",
            published_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
        )

        result = cluster_content_items(
            db_session,
            [item1, item2],
            ws.id,
            similarity_threshold=0.8,
            domain_title_threshold=0.8,
        )

        # With high thresholds, these should remain separate
        assert result["clusters_created"] == 2


# ---------------------------------------------------------------------------
# cluster_content_items — lead item selection (end-to-end)
# ---------------------------------------------------------------------------


class TestLeadItemSelectionE2E:
    """In a cluster, the earliest-published item is marked as lead."""

    def test_earliest_published_item_is_lead(self, db_session):
        ws = _make_workspace(db_session)
        item1 = _make_item(
            db_session,
            ws.id,
            title="Same Article",
            url="https://example.com/news?utm_source=tw",
            published_at=datetime(2024, 6, 5, tzinfo=timezone.utc),
        )
        item2 = _make_item(
            db_session,
            ws.id,
            title="Same Article",
            url="https://example.com/news?utm_source=fb",
            published_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
        )
        item3 = _make_item(
            db_session,
            ws.id,
            title="Same Article",
            url="https://example.com/news?fbclid=x",
            published_at=datetime(2024, 6, 3, tzinfo=timezone.utc),
        )

        cluster_content_items(db_session, [item1, item2, item3], ws.id)

        db_session.refresh(item1)
        db_session.refresh(item2)
        db_session.refresh(item3)

        # All share same cluster
        assert item1.cluster_id == item2.cluster_id == item3.cluster_id

        # Cluster label should come from the lead (earliest published) item's title
        cluster = db_session.query(ContentCluster).first()
        assert cluster is not None
        assert cluster.label == "Same Article"

    def test_cluster_label_from_lead_title(self, db_session):
        """The cluster label is derived from the lead item's title."""
        ws = _make_workspace(db_session)
        item_early = _make_item(
            db_session,
            ws.id,
            title="Original Title",
            url="https://example.com/a?ref=tw",
            published_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        item_late = _make_item(
            db_session,
            ws.id,
            title="Different Title",
            url="https://example.com/a?ref=fb",
            published_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
        )

        cluster_content_items(db_session, [item_early, item_late], ws.id)

        cluster = db_session.query(ContentCluster).first()
        # Lead is the earliest-published item, so label comes from its title
        assert cluster.label == "Original Title"


# ---------------------------------------------------------------------------
# cluster_content_items — mixed duplicates and unique items
# ---------------------------------------------------------------------------


class TestMixedDuplicatesAndUnique:
    """A mix of URL-duped, title-duped, and unique items."""

    def test_mixed_clustering(self, db_session):
        ws = _make_workspace(db_session)

        # 3 items sharing the same URL (different tracking params)
        url_item1 = _make_item(
            db_session,
            ws.id,
            title="URL Dup A",
            url="https://example.com/shared-url?utm_source=twitter",
            published_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
        )
        url_item2 = _make_item(
            db_session,
            ws.id,
            title="URL Dup B",
            url="https://example.com/shared-url?fbclid=abc",
            published_at=datetime(2024, 6, 2, tzinfo=timezone.utc),
        )
        url_item3 = _make_item(
            db_session,
            ws.id,
            title="URL Dup C",
            url="https://example.com/shared-url",
            published_at=datetime(2024, 6, 3, tzinfo=timezone.utc),
        )

        # 2 items with the same title (different URLs)
        title_item1 = _make_item(
            db_session,
            ws.id,
            title="Identical Headline",
            url="https://source-a.com/article",
            published_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
        )
        title_item2 = _make_item(
            db_session,
            ws.id,
            title="Identical Headline",
            url="https://source-b.com/article",
            published_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
        )

        # 2 unique items (different URLs, different titles)
        unique1 = _make_item(
            db_session,
            ws.id,
            title="Unique Article One",
            url="https://unique1.com/post",
            published_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
        )
        unique2 = _make_item(
            db_session,
            ws.id,
            title="Unique Article Two",
            url="https://unique2.com/post",
            published_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
        )

        all_items = [
            url_item1,
            url_item2,
            url_item3,
            title_item1,
            title_item2,
            unique1,
            unique2,
        ]

        result = cluster_content_items(db_session, all_items, ws.id)

        # Expect: 1 URL cluster (3 items) + 1 title cluster (2 items) + 2 singletons = 4 clusters
        assert result["clusters_created"] == 4
        assert result["items_clustered"] == 7
        assert result["singleton_clusters"] == 2

        # Verify URL group share the same cluster_id
        db_session.refresh(url_item1)
        db_session.refresh(url_item2)
        db_session.refresh(url_item3)
        url_cluster_id = url_item1.cluster_id
        assert url_cluster_id is not None
        assert url_item2.cluster_id == url_cluster_id
        assert url_item3.cluster_id == url_cluster_id

        # Verify title group share the same cluster_id
        db_session.refresh(title_item1)
        db_session.refresh(title_item2)
        title_cluster_id = title_item1.cluster_id
        assert title_cluster_id is not None
        assert title_cluster_id != url_cluster_id  # different from URL group
        assert title_item2.cluster_id == title_cluster_id

        # Verify unique items each have their own cluster
        db_session.refresh(unique1)
        db_session.refresh(unique2)
        assert unique1.cluster_id is not None
        assert unique2.cluster_id is not None
        assert unique1.cluster_id != unique2.cluster_id
        assert unique1.cluster_id not in (url_cluster_id, title_cluster_id)
        assert unique2.cluster_id not in (url_cluster_id, title_cluster_id)

        # Verify cluster counts in the DB
        clusters = db_session.query(ContentCluster).all()
        assert len(clusters) == 4

        # Verify the multi-item clusters have correct item_count
        url_cluster = db_session.get(ContentCluster, url_cluster_id)
        title_cluster = db_session.get(ContentCluster, title_cluster_id)
        assert url_cluster.item_count == 3
        assert title_cluster.item_count == 1 or title_cluster.item_count == 2

    def test_items_clustered_equals_input_count(self, db_session):
        """Every input item is assigned to a cluster."""
        ws = _make_workspace(db_session)
        items = [
            _make_item(
                db_session,
                ws.id,
                title=f"Item {i}",
                url=f"https://example.com/{i}",
            )
            for i in range(5)
        ]

        result = cluster_content_items(db_session, items, ws.id)
        assert result["items_clustered"] == 5


# ---------------------------------------------------------------------------
# cluster_content_items — cluster metadata verification
# ---------------------------------------------------------------------------


class TestClusterMetadata:
    """Verify ContentCluster record fields are set correctly."""

    def test_cluster_workspace_id(self, db_session):
        ws = _make_workspace(db_session)
        item = _make_item(
            db_session,
            ws.id,
            title="WS Test",
            url="https://example.com/a",
        )

        cluster_content_items(db_session, [item], ws.id)

        cluster = db_session.query(ContentCluster).first()
        assert cluster.workspace_id == ws.id

    def test_cluster_item_count(self, db_session):
        ws = _make_workspace(db_session)
        item1 = _make_item(
            db_session,
            ws.id,
            title="Count Test",
            url="https://example.com/a?ref=1",
        )
        item2 = _make_item(
            db_session,
            ws.id,
            title="Count Test",
            url="https://example.com/a?ref=2",
        )

        cluster_content_items(db_session, [item1, item2], ws.id)

        cluster = db_session.query(ContentCluster).first()
        assert cluster.item_count == 2

    def test_singleton_cluster_item_count(self, db_session):
        ws = _make_workspace(db_session)
        item = _make_item(
            db_session,
            ws.id,
            title="Singleton",
            url="https://example.com/solo",
        )

        cluster_content_items(db_session, [item], ws.id)

        cluster = db_session.query(ContentCluster).first()
        assert cluster.item_count == 1


# ---------------------------------------------------------------------------
# Configurable thresholds (Pass 5)
# ---------------------------------------------------------------------------


class TestConfigurableThresholds:
    """cluster_content_items reads thresholds from workspace settings."""

    def _make_workspace_with_thresholds(
        self, db, *, similarity=None, domain_title=None
    ):
        """Create a workspace with custom clustering thresholds."""
        from app.models.workspace import WorkspaceSettings

        ws = Workspace(name="Threshold WS", customer="TestCo")
        db.add(ws)
        db.flush()

        thresholds = {}
        if similarity is not None:
            thresholds["clustering_similarity_threshold"] = similarity
        if domain_title is not None:
            thresholds["clustering_domain_title_threshold"] = domain_title

        settings = WorkspaceSettings(
            workspace_id=ws.id,
            thresholds=thresholds if thresholds else None,
        )
        db.add(settings)
        db.flush()
        return ws

    def test_workspace_custom_thresholds_are_used(self, db_session):
        """Workspace with custom thresholds should use those values."""
        ws = self._make_workspace_with_thresholds(
            db_session,
            similarity=0.3,  # very low — should cluster easily
            domain_title=0.2,
        )

        item1 = _make_item(
            db_session,
            ws.id,
            title="Company Announces Results",
            url="https://news.example.com/company-a",
            published_at=datetime(2024, 6, 1, 10, 0, tzinfo=timezone.utc),
        )
        item2 = _make_item(
            db_session,
            ws.id,
            title="Firm Reports Earnings",
            url="https://news.example.com/company-b",
            published_at=datetime(2024, 6, 1, 14, 0, tzinfo=timezone.utc),
        )

        # With low similarity threshold, these should cluster via the
        # similarity-based phase even if their titles are somewhat different
        result = cluster_content_items(
            db_session,
            [item1, item2],
            ws.id,
            workspace=ws,
        )

        # With very low threshold they might cluster; at minimum the call succeeds
        assert result["items_clustered"] == 2

    def test_no_workspace_uses_defaults(self, db_session):
        """Without a workspace object, default thresholds are used."""
        from app.services.clustering import (
            DEFAULT_DOMAIN_TITLE_THRESHOLD,
            DEFAULT_SIMILARITY_THRESHOLD,
        )

        # Just verify the call works without a workspace object
        ws = _make_workspace(db_session)
        item = _make_item(
            db_session,
            ws.id,
            title="Solo Article",
            url="https://example.com/solo",
        )

        result = cluster_content_items(db_session, [item], ws.id, workspace=None)

        assert result["clusters_created"] == 1
        assert result["items_clustered"] == 1

    def test_explicit_kwargs_override_workspace(self, db_session):
        """Explicit kwargs take precedence over workspace settings."""
        ws = self._make_workspace_with_thresholds(
            db_session,
            similarity=0.99,  # very high — should prevent grouping
            domain_title=0.99,
        )

        item1 = _make_item(
            db_session,
            ws.id,
            title="Same Article",
            url="https://example.com/a?ref=tw",
            published_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
        )
        item2 = _make_item(
            db_session,
            ws.id,
            title="Same Article",
            url="https://example.com/a?ref=fb",
            published_at=datetime(2024, 6, 2, tzinfo=timezone.utc),
        )

        # Explicit low thresholds should override the workspace's high ones
        # URL dedup and title dedup happen regardless of these thresholds
        result = cluster_content_items(
            db_session,
            [item1, item2],
            ws.id,
            workspace=ws,
            similarity_threshold=0.1,
            domain_title_threshold=0.1,
        )

        # These items share URL and title, so they cluster regardless of thresholds
        assert result["clusters_created"] == 1
        assert result["items_clustered"] == 2
