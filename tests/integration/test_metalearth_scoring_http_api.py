"""HTTP-level integration tests for Metal Earth scoring.

These tests exercise the full scoring pipeline through the HTTP API layer,
verifying that camelCase API inputs are correctly normalized to snake_case
for the scoring service and that API responses expose the right diagnostic
fields.

The pattern:
1. Create workspace / profile / settings **through the HTTP API**.
2. Seed content items via direct ORM (no content creation endpoint exists).
3. Call ``score_content_items()`` to score the items (no scoring HTTP endpoint).
4. Verify results **through HTTP GET responses**.

Important: When settings are PUT via the API, ``ThresholdsSchema`` applies its
defaults (``minFinalScore=0.70``, ``minRelevanceScore=0.65``).  Tests that
only want ``minRelevanceScore`` to gate must also set ``minFinalScore: 0``
to disable the secondary filter.

Usage:
    cd backend && python -m pytest ../tests/integration/test_metalearth_scoring_http_api.py -v
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.services.scoring import score_content_items


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_item(db, ws_id, **overrides):
    """Create a ContentItem with sensible defaults via ORM."""
    from app.models.content import ContentItem

    defaults = {
        "workspace_id": ws_id,
        "title": "Generic news article",
        "url": "https://example.com/article",
        "source_name": "Example News",
        "content_type": "news",
        "summary_snippet": "A summary of the article.",
        "published_at": datetime.now(timezone.utc),
        "status": "pending",
    }
    defaults.update(overrides)
    item = ContentItem(**defaults)
    db.add(item)
    db.flush()
    return item


def _create_workspace_via_api(client):
    """Create a workspace through the HTTP API and return the ID."""
    resp = client.post(
        "/api/workspaces",
        json={
            "name": "Metal Earth Models",
            "customer": "MetalEarthCo",
        },
    )
    assert resp.status_code == 201, f"create workspace failed: {resp.text}"
    return resp.json()["id"]


def _put_settings_via_api(client, ws_id, thresholds):
    """PUT workspace settings through the HTTP API using camelCase keys."""
    resp = client.put(
        f"/api/workspaces/{ws_id}/settings",
        json={
            "thresholds": thresholds,
        },
    )
    assert resp.status_code == 200, f"put settings failed: {resp.text}"
    return resp.json()


def _put_profile_via_api(
    client, ws_id, *, priority_themes=None, competitors=None, excluded_topics=None
):
    """PUT workspace profile through the HTTP API."""
    body = {}
    if priority_themes is not None:
        body["priorityThemes"] = priority_themes
    if competitors is not None:
        body["competitors"] = competitors
    if excluded_topics is not None:
        body["excludedTopics"] = excluded_topics
    resp = client.put(f"/api/workspaces/{ws_id}/profile", json=body)
    assert resp.status_code == 200, f"put profile failed: {resp.text}"
    return resp.json()


def _score_and_commit(db, ws_id, items):
    """Score items via the service layer and commit so API can read results."""
    from app.models.workspace import Workspace

    db.commit()  # commit ORM items so API sessions can see them
    ws = db.query(Workspace).filter(Workspace.id == ws_id).first()
    score_content_items(db, items, ws)
    db.commit()  # commit scored results so API can read them


# ---------------------------------------------------------------------------
# Test 1: camelCase settings → scoring runtime
# ---------------------------------------------------------------------------


class TestApiSettingsCamelCaseAffectsScoring:
    """PUT settings with camelCase keys must affect scoring at runtime."""

    def test_api_settings_write_with_camelcase_affects_scoring_runtime(
        self, client, db_session
    ):
        """Verify camelCase minRelevanceScore persists and gates content."""
        ws_id = _create_workspace_via_api(client)

        # Set minRelevanceScore via the API (camelCase).
        # Set minFinalScore to 0 to disable the secondary filter so only
        # minRelevanceScore controls inclusion (ThresholdsSchema defaults
        # minFinalScore to 0.70 which would override our threshold).
        _put_settings_via_api(
            client,
            ws_id,
            {
                "minRelevanceScore": 0.40,
                "minFinalScore": 0.0,
            },
        )

        # Set profile themes so scoring has signal
        _put_profile_via_api(
            client,
            ws_id,
            priority_themes=[
                "metal earth",
                "3d model",
                "model kit",
                "collectibles",
                "toy industry",
            ],
        )

        # Create a strong Metal Earth article via ORM
        strong_item = _make_item(
            db_session,
            ws_id,
            title=(
                "Hasbro announces new Star Wars licensed franchise "
                "collectible model kit series"
            ),
            summary_snippet=(
                "Hasbro has signed a major licensing deal with Disney for Star Wars "
                "collectibles, expanding their toy industry portfolio with premium "
                "metal earth model kits. The new series features iconic spacecraft."
            ),
            content_type="news",
            url="https://toybook.com/hasbro-star-wars-model-kits",
        )

        # Create a weak article via ORM
        weak_item = _make_item(
            db_session,
            ws_id,
            title="New DIY craft trend gaining popularity",
            summary_snippet="DIY crafting continues to grow as a hobby trend.",
            content_type="news",
            url="https://lifestyle.com/diy-craft-trend",
        )

        _score_and_commit(db_session, ws_id, [strong_item, weak_item])

        # Verify via content list API
        resp = client.get(f"/api/workspaces/{ws_id}/content")
        assert resp.status_code == 200
        items = resp.json()

        # The strong article should be included, the weak one excluded
        strong_entry = next((i for i in items if i["id"] == strong_item.id), None)
        weak_entry = next((i for i in items if i["id"] == weak_item.id), None)

        assert strong_entry is not None, "Strong article should appear in API"
        assert strong_entry["status"] == "included", (
            f"Strong article should be included, got {strong_entry['status']}"
        )
        assert weak_entry is not None, "Weak article should appear in API"
        assert weak_entry["status"] == "excluded", (
            f"Weak article should be excluded, got {weak_entry['status']}"
        )


# ---------------------------------------------------------------------------
# Test 2: trustedDomains → source authority boost
# ---------------------------------------------------------------------------


class TestApiTrustedDomainsAffectsScoring:
    """PUT settings with trustedDomains (camelCase) must boost authority."""

    def test_api_trusted_domains_write_affects_source_authority_runtime(
        self, client, db_session
    ):
        """Trusted domain gets authority boost visible in content detail API."""
        ws_id = _create_workspace_via_api(client)

        # Set trustedDomains via camelCase API; disable minFinalScore filter
        _put_settings_via_api(
            client,
            ws_id,
            {
                "trustedDomains": ["toybook.com", "licenseglobal.com"],
                "minFinalScore": 0.0,
            },
        )

        _put_profile_via_api(
            client,
            ws_id,
            priority_themes=[
                "model kit",
                "collectibles",
            ],
        )

        # Same content from trusted domain
        trusted_item = _make_item(
            db_session,
            ws_id,
            title="New Star Wars model kit announced",
            summary_snippet="A new Star Wars collectible model kit is coming soon.",
            content_type="news",
            url="https://toybook.com/star-wars-model-kit",
        )

        # Same content from untrusted domain
        untrusted_item = _make_item(
            db_session,
            ws_id,
            title="New Star Wars model kit announced",
            summary_snippet="A new Star Wars collectible model kit is coming soon.",
            content_type="news",
            url="https://random-blog.xyz/star-wars-model-kit",
        )

        _score_and_commit(db_session, ws_id, [trusted_item, untrusted_item])

        # Verify via content detail API — trusted domain should have higher authority
        resp_trusted = client.get(f"/api/content/{trusted_item.id}")
        assert resp_trusted.status_code == 200
        detail_trusted = resp_trusted.json()
        assert "scoreBreakdown" in detail_trusted
        assert detail_trusted["scoreBreakdown"]["sourceAuthority"] > 0

        resp_untrusted = client.get(f"/api/content/{untrusted_item.id}")
        assert resp_untrusted.status_code == 200
        detail_untrusted = resp_untrusted.json()
        assert "scoreBreakdown" in detail_untrusted

        # Trusted authority should be strictly higher
        assert (
            detail_trusted["scoreBreakdown"]["sourceAuthority"]
            > detail_untrusted["scoreBreakdown"]["sourceAuthority"]
        ), "Trusted domain should have higher sourceAuthority in API response"


# ---------------------------------------------------------------------------
# Test 3: content detail API exposes theme/competitor/filter diagnostics
# ---------------------------------------------------------------------------


class TestContentDetailApiDiagnostics:
    """Content detail API must expose scoreBreakdown with diagnostic fields."""

    def test_content_detail_api_exposes_theme_competitor_filter_diagnostics(
        self, client, db_session
    ):
        """Verify scoreBreakdown contains themeMatch, competitorMatch, filterReason."""
        ws_id = _create_workspace_via_api(client)

        _put_settings_via_api(
            client,
            ws_id,
            {
                "minRelevanceScore": 0.15,
                "minFinalScore": 0.0,
            },
        )

        _put_profile_via_api(
            client,
            ws_id,
            priority_themes=[
                "metal earth",
                "3d model",
                "model kit",
                "star wars",
                "collectibles",
                "hobby",
            ],
            competitors=["Fascinations", "Piececool", "UGEARS"],
            excluded_topics=["cryptocurrency", "celebrity gossip"],
        )

        # Theme + competitor matching article
        theme_item = _make_item(
            db_session,
            ws_id,
            title="Piececool releases new Star Wars metal model kit collection",
            summary_snippet=(
                "Piececool's new Star Wars 3D metal puzzle series features iconic "
                "spacecraft and vehicles. The collectible model kits are now available."
            ),
            content_type="news",
            url="https://hobbynews.com/piececool-star-wars",
        )

        # Excluded topic article
        excluded_item = _make_item(
            db_session,
            ws_id,
            title="Bitcoin reaches new all-time high as cryptocurrency surges",
            summary_snippet="The cryptocurrency market continues to grow rapidly.",
            content_type="news",
            url="https://crypto.com/bitcoin-high",
        )

        _score_and_commit(db_session, ws_id, [theme_item, excluded_item])

        # Check theme item detail
        resp = client.get(f"/api/content/{theme_item.id}")
        assert resp.status_code == 200
        detail = resp.json()
        breakdown = detail["scoreBreakdown"]

        # themeMatch must be present
        assert "themeMatch" in breakdown, "scoreBreakdown must contain themeMatch"
        theme_match = breakdown["themeMatch"]
        assert "matched" in theme_match
        assert "unmatched" in theme_match

        # competitorMatch must be present
        assert "competitorMatch" in breakdown, (
            "scoreBreakdown must contain competitorMatch"
        )
        comp_match = breakdown["competitorMatch"]
        assert "matched" in comp_match
        # Piececool should be in matched competitors
        assert any("piececool" in c.lower() for c in comp_match.get("matched", [])), (
            "Piececool should appear as a matched competitor"
        )

        # Check excluded item detail
        resp_ex = client.get(f"/api/content/{excluded_item.id}")
        assert resp_ex.status_code == 200
        detail_ex = resp_ex.json()
        breakdown_ex = detail_ex["scoreBreakdown"]

        # filterReason must be present for excluded items
        assert "filterReason" in breakdown_ex, (
            "scoreBreakdown must contain filterReason for excluded items"
        )

        # minRelevanceThreshold may be present
        if "minRelevanceThreshold" in breakdown_ex:
            assert isinstance(breakdown_ex["minRelevanceThreshold"], (int, float))


# ---------------------------------------------------------------------------
# Test 4: nonzero threshold excludes weak items in standard flow
# ---------------------------------------------------------------------------


class TestNonzeroThresholdExcludesWeakItems:
    """Nonzero minRelevanceScore via API should exclude weak content."""

    def test_nonzero_threshold_excludes_weak_items_in_standard_metalearth_flow(
        self, client, db_session
    ):
        """Weak items get status='excluded' when threshold > 0 via camelCase API."""
        ws_id = _create_workspace_via_api(client)

        # Set minRelevanceScore to 0.30 via camelCase API; disable minFinalScore.
        # Note: the baseline score for a recent "news" article with neutral source
        # authority and no theme matches is ~0.225 (freshness=1.0*0.15 +
        # authority=0.5*0.15).  We use 0.30 so that weak/noise items are excluded
        # while strong themed items (which score 0.35+) are included.
        _put_settings_via_api(
            client,
            ws_id,
            {
                "minRelevanceScore": 0.30,
                "minFinalScore": 0.0,
            },
        )

        _put_profile_via_api(
            client,
            ws_id,
            priority_themes=[
                "metal earth",
                "3d model",
                "model kit",
                "licensed franchise",
                "collectibles",
                "hobby",
                "toy industry",
                "star wars",
                "marvel",
            ],
            competitors=[
                "Fascinations",
                "Piececool",
                "UGEARS",
            ],
            excluded_topics=[
                "celebrity gossip",
                "sports results",
                "cryptocurrency",
            ],
        )

        # Strong article
        strong = _make_item(
            db_session,
            ws_id,
            title=(
                "Hasbro and Disney announce new Star Wars licensed franchise "
                "collectible model kit series"
            ),
            summary_snippet=(
                "The new Star Wars collectible model kit series from Hasbro and Disney "
                "brings iconic spacecraft to the toy industry. These premium licensed "
                "franchise collectibles expand the metal earth market."
            ),
            content_type="news",
            url="https://toybook.com/star-wars-model-kits",
        )

        # Medium article (competitor mention)
        medium = _make_item(
            db_session,
            ws_id,
            title="Piececool releases new architecture model kit collection",
            summary_snippet=(
                "Piececool's new architecture model kit collection is now available. "
                "The 3D metal puzzles feature famous landmarks."
            ),
            content_type="news",
            url="https://hobbynews.com/piececool-architecture",
        )

        # Weak article — no theme matches at all
        weak = _make_item(
            db_session,
            ws_id,
            title="Local city council approves new zoning regulations",
            summary_snippet=(
                "The city council voted unanimously to approve new zoning regulations "
                "for the downtown area. The changes take effect next month."
            ),
            content_type="news",
            url="https://localnews.com/city-zoning-update",
        )

        # Noise article (excluded topic)
        noise = _make_item(
            db_session,
            ws_id,
            title="Bitcoin reaches new all-time high as cryptocurrency surges",
            summary_snippet="The cryptocurrency market continues to grow rapidly.",
            content_type="news",
            url="https://crypto.com/bitcoin-high",
        )

        _score_and_commit(db_session, ws_id, [strong, medium, weak, noise])

        # Verify via content list API
        resp = client.get(f"/api/workspaces/{ws_id}/content")
        assert resp.status_code == 200
        items_by_id = {i["id"]: i for i in resp.json()}

        # Strong should be included
        assert items_by_id[strong.id]["status"] == "included", (
            f"Strong article should be included, got {items_by_id[strong.id]['status']}"
        )

        # Weak and noise should be excluded
        assert items_by_id[weak.id]["status"] == "excluded", (
            f"Weak article should be excluded, got {items_by_id[weak.id]['status']}"
        )
        assert items_by_id[noise.id]["status"] == "excluded", (
            f"Noise article should be excluded, got {items_by_id[noise.id]['status']}"
        )

        # Filter by included status
        resp_included = client.get(f"/api/workspaces/{ws_id}/content?status=included")
        assert resp_included.status_code == 200
        included_ids = {i["id"] for i in resp_included.json()}
        assert strong.id in included_ids, "Strong article should be in included list"
        assert weak.id not in included_ids, (
            "Weak article should NOT be in included list"
        )
        assert noise.id not in included_ids, (
            "Noise article should NOT be in included list"
        )


# ---------------------------------------------------------------------------
# Test 5: strong Metal Earth article outranks generic noise
# ---------------------------------------------------------------------------


class TestStrongArticleOutranksNoise:
    """Metal Earth article should rank higher than generic noise via API."""

    def test_strong_metalearth_article_outranks_generic_noise_via_api_observation(
        self, client, db_session
    ):
        """Metal Earth article has higher relevanceScore than generic noise."""
        ws_id = _create_workspace_via_api(client)

        _put_settings_via_api(
            client,
            ws_id,
            {
                "minRelevanceScore": 0.10,
                "minFinalScore": 0.0,
            },
        )

        _put_profile_via_api(
            client,
            ws_id,
            priority_themes=[
                "metal earth",
                "3d model",
                "model kit",
                "licensed franchise",
                "collectibles",
                "hobby",
                "toy industry",
                "star wars",
                "marvel",
                "aviation model",
                "architecture model",
                "DIY craft",
            ],
            competitors=[
                "Fascinations",
                "Piececool",
                "UGEARS",
            ],
        )

        # Strong Metal Earth article
        metal_item = _make_item(
            db_session,
            ws_id,
            title=(
                "Hasbro and Disney announce new Star Wars licensed franchise "
                "collectible model kit series"
            ),
            summary_snippet=(
                "The new Star Wars collectible model kit series from Hasbro and Disney "
                "brings iconic spacecraft to the toy industry. These premium licensed "
                "franchise collectibles expand the metal earth market."
            ),
            content_type="news",
            url="https://toybook.com/star-wars-model-kits",
        )

        # Generic unrelated article
        generic_item = _make_item(
            db_session,
            ws_id,
            title="Local weather forecast for the weekend",
            summary_snippet=(
                "Sunny skies expected throughout the weekend with mild temperatures. "
                "No rain is forecast for the region."
            ),
            content_type="news",
            url="https://weathernews.com/weekend-forecast",
        )

        _score_and_commit(db_session, ws_id, [metal_item, generic_item])

        # Verify via content list API — Metal Earth article should have higher score
        resp = client.get(f"/api/workspaces/{ws_id}/content")
        assert resp.status_code == 200
        items_by_id = {i["id"]: i for i in resp.json()}

        metal_score = items_by_id[metal_item.id]["finalScore"]
        generic_score = items_by_id[generic_item.id]["finalScore"]

        assert metal_score is not None, "Metal Earth article should have a finalScore"
        assert generic_score is not None, "Generic article should have a finalScore"
        assert metal_score > generic_score, (
            f"Metal Earth article ({metal_score}) should outrank generic noise "
            f"({generic_score}) via API observation"
        )

        # Verify via content detail API — Metal Earth article should have theme matches
        resp_detail = client.get(f"/api/content/{metal_item.id}")
        assert resp_detail.status_code == 200
        detail = resp_detail.json()
        breakdown = detail["scoreBreakdown"]

        assert "themeMatch" in breakdown, "Metal Earth article should have themeMatch"
        matched_themes = breakdown["themeMatch"].get("matched", [])
        # At least one theme should match
        assert len(matched_themes) > 0, (
            f"Metal Earth article should match at least one theme, got: {matched_themes}"
        )
