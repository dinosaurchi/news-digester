"""Tests for /api/workspaces/{id}/settings endpoints."""

import pytest

from app.config import Settings


# ---------------------------------------------------------------------------
# OpenCode configuration validation (Settings class)
# ---------------------------------------------------------------------------


class TestOpenCodeConfigValidation:
    """Settings validation rejects missing or invalid OpenCode configuration."""

    def test_valid_config_passes(self):
        """All required OpenCode fields present and valid → no error."""
        s = Settings(
            OPENCODE_BASE_URL="http://localhost:9001",
            OPENCODE_TIMEOUT_SECONDS=60,
            OPENCODE_DEFAULT_MODEL="gpt-5",
            OPENCODE_DEFAULT_AGENT="general",
            OPENCODE_WORKSPACE_DIR="/workspace",
        )
        assert s.OPENCODE_BASE_URL == "http://localhost:9001"

    def test_missing_base_url_raises(self):
        """Empty OPENCODE_BASE_URL → ValueError."""
        with pytest.raises(ValueError, match="OPENCODE_BASE_URL"):
            Settings(
                OPENCODE_BASE_URL="",
                OPENCODE_TIMEOUT_SECONDS=60,
                OPENCODE_DEFAULT_MODEL="gpt-5",
                OPENCODE_DEFAULT_AGENT="general",
                OPENCODE_WORKSPACE_DIR="/workspace",
            )

    def test_whitespace_base_url_raises(self):
        """Whitespace-only OPENCODE_BASE_URL → ValueError."""
        with pytest.raises(ValueError, match="OPENCODE_BASE_URL"):
            Settings(
                OPENCODE_BASE_URL="   ",
                OPENCODE_TIMEOUT_SECONDS=60,
                OPENCODE_DEFAULT_MODEL="gpt-5",
                OPENCODE_DEFAULT_AGENT="general",
                OPENCODE_WORKSPACE_DIR="/workspace",
            )

    def test_missing_default_model_raises(self):
        """Empty OPENCODE_DEFAULT_MODEL → ValueError."""
        with pytest.raises(ValueError, match="OPENCODE_DEFAULT_MODEL"):
            Settings(
                OPENCODE_BASE_URL="http://localhost:9001",
                OPENCODE_TIMEOUT_SECONDS=60,
                OPENCODE_DEFAULT_MODEL="",
                OPENCODE_DEFAULT_AGENT="general",
                OPENCODE_WORKSPACE_DIR="/workspace",
            )

    def test_missing_default_agent_raises(self):
        """Empty OPENCODE_DEFAULT_AGENT → ValueError."""
        with pytest.raises(ValueError, match="OPENCODE_DEFAULT_AGENT"):
            Settings(
                OPENCODE_BASE_URL="http://localhost:9001",
                OPENCODE_TIMEOUT_SECONDS=60,
                OPENCODE_DEFAULT_MODEL="gpt-5",
                OPENCODE_DEFAULT_AGENT="",
                OPENCODE_WORKSPACE_DIR="/workspace",
            )

    def test_missing_workspace_dir_raises(self):
        """Empty OPENCODE_WORKSPACE_DIR → ValueError."""
        with pytest.raises(ValueError, match="OPENCODE_WORKSPACE_DIR"):
            Settings(
                OPENCODE_BASE_URL="http://localhost:9001",
                OPENCODE_TIMEOUT_SECONDS=60,
                OPENCODE_DEFAULT_MODEL="gpt-5",
                OPENCODE_DEFAULT_AGENT="general",
                OPENCODE_WORKSPACE_DIR="",
            )

    def test_timeout_zero_raises(self):
        """OPENCODE_TIMEOUT_SECONDS=0 → ValueError."""
        with pytest.raises(ValueError, match="OPENCODE_TIMEOUT_SECONDS"):
            Settings(
                OPENCODE_BASE_URL="http://localhost:9001",
                OPENCODE_TIMEOUT_SECONDS=0,
                OPENCODE_DEFAULT_MODEL="gpt-5",
                OPENCODE_DEFAULT_AGENT="general",
                OPENCODE_WORKSPACE_DIR="/workspace",
            )

    def test_timeout_negative_raises(self):
        """OPENCODE_TIMEOUT_SECONDS=-1 → ValueError."""
        with pytest.raises(ValueError, match="OPENCODE_TIMEOUT_SECONDS"):
            Settings(
                OPENCODE_BASE_URL="http://localhost:9001",
                OPENCODE_TIMEOUT_SECONDS=-1,
                OPENCODE_DEFAULT_MODEL="gpt-5",
                OPENCODE_DEFAULT_AGENT="general",
                OPENCODE_WORKSPACE_DIR="/workspace",
            )

    def test_multiple_missing_fields_all_reported(self):
        """Multiple missing fields are all listed in the error message."""
        with pytest.raises(
            ValueError, match="OPENCODE_BASE_URL.*OPENCODE_DEFAULT_MODEL"
        ):
            Settings(
                OPENCODE_BASE_URL="",
                OPENCODE_TIMEOUT_SECONDS=60,
                OPENCODE_DEFAULT_MODEL="",
                OPENCODE_DEFAULT_AGENT="general",
                OPENCODE_WORKSPACE_DIR="/workspace",
            )

    def test_no_enabled_flag_exists(self):
        """Settings class does not have an OPENCODE_ENABLED attribute."""
        assert not hasattr(Settings(), "OPENCODE_ENABLED")


# ---------------------------------------------------------------------------
# Workspace settings API
# ---------------------------------------------------------------------------


def _create_workspace(client):
    """Helper: create a workspace and return its ID."""
    resp = client.post(
        "/api/workspaces", json={"name": "Settings WS", "customer": "Co"}
    )
    return resp.json()["id"]


class TestGetSettings:
    """GET /api/workspaces/{id}/settings"""

    def test_get_settings_creates_default(self, client):
        ws_id = _create_workspace(client)

        resp = client.get(f"/api/workspaces/{ws_id}/settings")
        assert resp.status_code == 200

        data = resp.json()
        assert data["workspaceId"] == ws_id
        assert "schedule" in data
        assert "reportStyle" in data
        assert "thresholds" in data
        assert "retention" in data
        assert "emailDelivery" in data
        assert "updatedAt" in data

        # Verify default schedule
        schedule = data["schedule"]
        assert schedule["enabled"] is False
        assert schedule["frequency"] == "daily"
        assert schedule["timeOfDay"] == "08:00"
        assert schedule["timezone"] == "UTC"

        # Verify default thresholds
        thresholds = data["thresholds"]
        assert thresholds["minRelevanceScore"] == 0.65
        assert thresholds["minFinalScore"] == 0.70
        assert thresholds["maxArticlesPerReport"] == 15

        # Verify default retention
        retention = data["retention"]
        assert retention["contentDays"] == 90
        assert retention["reportDays"] == 365
        assert retention["runHistoryDays"] == 180

        # Verify default email delivery
        email = data["emailDelivery"]
        assert email["enabled"] is False
        assert email["recipients"] == []
        assert email["subjectPrefix"] == "[Intel Report]"

    def test_get_settings_returns_camel_case(self, client):
        ws_id = _create_workspace(client)

        resp = client.get(f"/api/workspaces/{ws_id}/settings")
        data = resp.json()

        expected_keys = [
            "id",
            "workspaceId",
            "schedule",
            "reportStyle",
            "thresholds",
            "retention",
            "emailDelivery",
            "updatedAt",
        ]
        for key in expected_keys:
            assert key in data, f"Missing camelCase key: {key}"


class TestPutSettings:
    """PUT /api/workspaces/{id}/settings"""

    def test_put_settings(self, client):
        ws_id = _create_workspace(client)

        payload = {
            "schedule": {
                "enabled": True,
                "frequency": "weekly",
                "timeOfDay": "09:30",
                "timezone": "Europe/Berlin",
            },
            "reportStyle": "concise",
            "thresholds": {
                "minRelevanceScore": 0.80,
                "minFinalScore": 0.85,
                "maxArticlesPerReport": 5,
            },
            "retention": {
                "contentDays": 30,
                "reportDays": 180,
                "runHistoryDays": 60,
            },
            "emailDelivery": {
                "enabled": True,
                "recipients": ["boss@example.com"],
                "subjectPrefix": "[Weekly Intel]",
            },
        }

        resp = client.put(f"/api/workspaces/{ws_id}/settings", json=payload)
        assert resp.status_code == 200

        data = resp.json()
        assert data["schedule"]["enabled"] is True
        assert data["schedule"]["frequency"] == "weekly"
        assert data["schedule"]["timeOfDay"] == "09:30"
        assert data["schedule"]["timezone"] == "Europe/Berlin"
        assert data["reportStyle"] == "concise"
        assert data["thresholds"]["minRelevanceScore"] == 0.80
        assert data["retention"]["contentDays"] == 30
        assert data["emailDelivery"]["enabled"] is True
        assert data["emailDelivery"]["recipients"] == ["boss@example.com"]

    def test_put_settings_partial_update(self, client):
        """Updating only reportStyle leaves other settings unchanged."""
        ws_id = _create_workspace(client)

        resp = client.put(
            f"/api/workspaces/{ws_id}/settings",
            json={"reportStyle": "bulleted"},
        )
        assert resp.status_code == 200

        data = resp.json()
        assert data["reportStyle"] == "bulleted"
        # Other fields should keep their defaults
        assert data["schedule"]["frequency"] == "daily"
        assert data["schedule"]["enabled"] is False

    def test_put_settings_validation(self, client):
        """Invalid schedule frequency → 422."""
        ws_id = _create_workspace(client)

        resp = client.put(
            f"/api/workspaces/{ws_id}/settings",
            json={"schedule": {"frequency": "every_minute"}},
        )
        assert resp.status_code == 422

    def test_put_settings_not_found(self, client):
        resp = client.put(
            "/api/workspaces/nonexistent-id/settings",
            json={"reportStyle": "concise"},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Canonical threshold key normalisation (Pass 1)
# ---------------------------------------------------------------------------


class TestThresholdKeyCanonicalisation:
    """PUT stores snake_case in DB; GET returns camelCase to the client."""

    def test_put_settings_normalizes_camelcase_threshold_keys(self, client):
        """PUT with camelCase keys stores snake_case in DB."""
        ws_id = _create_workspace(client)

        payload = {
            "thresholds": {
                "minRelevanceScore": 0.80,
                "minFinalScore": 0.85,
                "maxArticlesPerReport": 5,
            },
        }
        resp = client.put(f"/api/workspaces/{ws_id}/settings", json=payload)
        assert resp.status_code == 200

        # Verify DB has snake_case keys (round-trip via GET)
        resp2 = client.get(f"/api/workspaces/{ws_id}/settings")
        assert resp2.status_code == 200

        # The API response must still use camelCase
        thresholds = resp2.json()["thresholds"]
        assert thresholds["minRelevanceScore"] == 0.80
        assert thresholds["minFinalScore"] == 0.85
        assert thresholds["maxArticlesPerReport"] == 5

    def test_put_settings_normalizes_trusted_domains_alias(self, client):
        """PUT with trustedDomains stores as trusted_domains in DB."""
        ws_id = _create_workspace(client)

        payload = {
            "thresholds": {
                "trustedDomains": ["reuters.com", "bbc.com"],
            },
        }
        resp = client.put(f"/api/workspaces/{ws_id}/settings", json=payload)
        assert resp.status_code == 200

        # API response must return camelCase alias
        thresholds = resp.json()["thresholds"]
        assert thresholds["trustedDomains"] == ["reuters.com", "bbc.com"]

    def test_settings_round_trip_exposes_expected_threshold_keys(self, client):
        """GET returns camelCase; DB stores snake_case (verified via scorer path)."""
        ws_id = _create_workspace(client)

        # PUT with a full set of threshold keys
        payload = {
            "thresholds": {
                "minRelevanceScore": 0.55,
                "minFinalScore": 0.60,
                "maxArticlesPerReport": 10,
                "trustedDomains": ["example.com"],
                "scoringWeights": {"keyword": 0.50, "bm25": 0.25},
                "contentTypeWeights": {"news": 1.0, "blog": 0.3},
            },
        }
        resp = client.put(f"/api/workspaces/{ws_id}/settings", json=payload)
        assert resp.status_code == 200

        # GET must return all keys in camelCase
        thresholds = resp.json()["thresholds"]
        assert thresholds["minRelevanceScore"] == 0.55
        assert thresholds["minFinalScore"] == 0.60
        assert thresholds["maxArticlesPerReport"] == 10
        assert thresholds["trustedDomains"] == ["example.com"]
        assert thresholds["scoringWeights"]["keyword"] == 0.50
        assert thresholds["contentTypeWeights"]["news"] == 1.0

    def test_put_settings_accepts_snake_case_input(self, client):
        """PUT with snake_case field names also works (populate_by_name)."""
        ws_id = _create_workspace(client)

        payload = {
            "thresholds": {
                "min_relevance_score": 0.90,
                "min_final_score": 0.95,
                "max_articles_per_report": 3,
                "trusted_domains": ["trusted.org"],
            },
        }
        resp = client.put(f"/api/workspaces/{ws_id}/settings", json=payload)
        assert resp.status_code == 200

        # API response should always be camelCase
        thresholds = resp.json()["thresholds"]
        assert thresholds["minRelevanceScore"] == 0.90
        assert thresholds["minFinalScore"] == 0.95
        assert thresholds["maxArticlesPerReport"] == 3
        assert thresholds["trustedDomains"] == ["trusted.org"]

    def test_default_settings_have_camel_case_threshold_keys(self, client):
        """Freshly created default settings return camelCase threshold keys."""
        ws_id = _create_workspace(client)

        resp = client.get(f"/api/workspaces/{ws_id}/settings")
        thresholds = resp.json()["thresholds"]

        # All expected camelCase keys must be present
        assert "minRelevanceScore" in thresholds
        assert "minFinalScore" in thresholds
        assert "maxArticlesPerReport" in thresholds
