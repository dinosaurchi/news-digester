"""Tests for feedback event → preference conversion (Pass 1)."""

from app.tests.conftest import TestingSessionLocal


def _create_workspace(client, name="Test WS", customer="Co"):
    resp = client.post("/api/workspaces", json={"name": name, "customer": customer})
    return resp.json()["id"]


class TestTopicPreferenceEventCreatesPreferenceRecord:
    """POST topic_preference feedback creates a TopicPreference row."""

    def test_topic_preference_event_creates_preference_record(self, client):
        ws_id = _create_workspace(client)

        resp = client.post(
            f"/api/workspaces/{ws_id}/feedback",
            json={
                "type": "topic_preference",
                "value": "AI",
                "sentiment": "positive",
            },
        )
        assert resp.status_code == 201

        # Verify the preference was created in the DB
        from app.models.preferences import TopicPreference

        db = TestingSessionLocal()
        try:
            prefs = (
                db.query(TopicPreference)
                .filter(
                    TopicPreference.workspace_id == ws_id,
                    TopicPreference.topic == "AI",
                )
                .all()
            )
            assert len(prefs) == 1
            assert prefs[0].weight > 0
        finally:
            db.close()


class TestSourcePreferenceEventCreatesPreferenceRecord:
    """POST source_preference feedback creates a SourcePreference row."""

    def test_source_preference_event_creates_preference_record(self, client):
        ws_id = _create_workspace(client)

        resp = client.post(
            f"/api/workspaces/{ws_id}/feedback",
            json={
                "type": "source_preference",
                "value": "TechCrunch",
                "sentiment": "positive",
            },
        )
        assert resp.status_code == 201

        from app.models.preferences import SourcePreference

        db = TestingSessionLocal()
        try:
            prefs = (
                db.query(SourcePreference)
                .filter(
                    SourcePreference.workspace_id == ws_id,
                    SourcePreference.source_name == "TechCrunch",
                )
                .all()
            )
            assert len(prefs) == 1
            assert prefs[0].weight > 0
        finally:
            db.close()


class TestNegativeTopicPreferenceCreatesNegativeWeight:
    """Negative sentiment produces a negative weight."""

    def test_negative_topic_preference_creates_negative_weight(self, client):
        ws_id = _create_workspace(client)

        client.post(
            f"/api/workspaces/{ws_id}/feedback",
            json={
                "type": "topic_preference",
                "value": "Clickbait",
                "sentiment": "negative",
            },
        )

        from app.models.preferences import TopicPreference

        db = TestingSessionLocal()
        try:
            pref = (
                db.query(TopicPreference)
                .filter(
                    TopicPreference.workspace_id == ws_id,
                    TopicPreference.topic == "Clickbait",
                )
                .one()
            )
            assert pref.weight < 0
        finally:
            db.close()


class TestRepeatedPositiveFeedbackAccumulatesWeight:
    """Multiple positive events for the same topic accumulate weight."""

    def test_repeated_positive_feedback_accumulates_weight(self, client):
        ws_id = _create_workspace(client)

        from app.models.preferences import TopicPreference

        # First event
        client.post(
            f"/api/workspaces/{ws_id}/feedback",
            json={
                "type": "topic_preference",
                "value": "AI",
                "sentiment": "positive",
            },
        )

        db = TestingSessionLocal()
        try:
            weight_after_one = (
                db.query(TopicPreference)
                .filter(
                    TopicPreference.workspace_id == ws_id,
                    TopicPreference.topic == "AI",
                )
                .one()
                .weight
            )
        finally:
            db.close()

        # Two more positive events
        for _ in range(2):
            client.post(
                f"/api/workspaces/{ws_id}/feedback",
                json={
                    "type": "topic_preference",
                    "value": "AI",
                    "sentiment": "positive",
                },
            )

        db = TestingSessionLocal()
        try:
            weight_after_three = (
                db.query(TopicPreference)
                .filter(
                    TopicPreference.workspace_id == ws_id,
                    TopicPreference.topic == "AI",
                )
                .one()
                .weight
            )
        finally:
            db.close()

        assert weight_after_three > weight_after_one


class TestPreferenceUpdatedAtRefreshedOnNewEvent:
    """Creating a second feedback event for the same topic refreshes updated_at."""

    def test_preference_updated_at_refreshed_on_new_event(self, client):
        import time

        ws_id = _create_workspace(client)

        # First event
        client.post(
            f"/api/workspaces/{ws_id}/feedback",
            json={
                "type": "topic_preference",
                "value": "AI",
                "sentiment": "positive",
            },
        )

        from app.models.preferences import TopicPreference

        db = TestingSessionLocal()
        try:
            created_at = (
                db.query(TopicPreference)
                .filter(
                    TopicPreference.workspace_id == ws_id,
                    TopicPreference.topic == "AI",
                )
                .one()
                .created_at
            )
        finally:
            db.close()

        time.sleep(0.05)  # small delay to ensure distinct timestamp

        # Second event for the same topic
        client.post(
            f"/api/workspaces/{ws_id}/feedback",
            json={
                "type": "topic_preference",
                "value": "AI",
                "sentiment": "positive",
            },
        )

        db = TestingSessionLocal()
        try:
            pref = (
                db.query(TopicPreference)
                .filter(
                    TopicPreference.workspace_id == ws_id,
                    TopicPreference.topic == "AI",
                )
                .one()
            )
            assert pref.updated_at >= created_at
        finally:
            db.close()


class TestFeedbackEventStillCreatedAlongsidePreference:
    """Both FeedbackEvent and TopicPreference rows exist after a POST."""

    def test_feedback_event_still_created_alongside_preference(self, client):
        ws_id = _create_workspace(client)

        resp = client.post(
            f"/api/workspaces/{ws_id}/feedback",
            json={
                "type": "topic_preference",
                "value": "AI",
                "sentiment": "positive",
            },
        )
        assert resp.status_code == 201
        event_id = resp.json()["id"]

        from app.models.preferences import TopicPreference
        from app.models.report import FeedbackEvent

        db = TestingSessionLocal()
        try:
            # FeedbackEvent must exist
            event = db.query(FeedbackEvent).get(event_id)
            assert event is not None

            # TopicPreference must also exist
            pref = (
                db.query(TopicPreference)
                .filter(
                    TopicPreference.workspace_id == ws_id,
                    TopicPreference.topic == "AI",
                )
                .one_or_none()
            )
            assert pref is not None
        finally:
            db.close()


class TestExistingPutPreferencesEndpointStillWorks:
    """PUT /preferences/topics still works correctly (no regression)."""

    def test_existing_put_preferences_endpoint_still_works(self, client):
        ws_id = _create_workspace(client)

        resp = client.put(
            f"/api/workspaces/{ws_id}/preferences/topics",
            json={
                "preferences": [
                    {"topic": "AI", "weight": 2.0},
                    {"topic": "Cloud", "weight": 1.5},
                ]
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["topic"] == "AI"
        assert data[0]["weight"] == 2.0
        assert data[1]["topic"] == "Cloud"
        assert data[1]["weight"] == 1.5

        # Also verify via GET
        resp = client.get(f"/api/workspaces/{ws_id}/preferences/topics")
        assert resp.status_code == 200
        assert len(resp.json()) == 2


class TestFeedbackPreferenceIsolatedByWorkspace:
    """Preferences created by feedback events are workspace-scoped."""

    def test_feedback_preference_isolated_by_workspace(self, client):
        ws_a = _create_workspace(client, name="WS-A", customer="CoA")
        ws_b = _create_workspace(client, name="WS-B", customer="CoB")

        # Create a topic preference feedback event in WS-A
        client.post(
            f"/api/workspaces/{ws_a}/feedback",
            json={
                "type": "topic_preference",
                "value": "AI",
                "sentiment": "positive",
            },
        )

        from app.models.preferences import TopicPreference

        db = TestingSessionLocal()
        try:
            # WS-A should have a preference
            prefs_a = (
                db.query(TopicPreference)
                .filter(TopicPreference.workspace_id == ws_a)
                .all()
            )
            assert len(prefs_a) == 1

            # WS-B should have none
            prefs_b = (
                db.query(TopicPreference)
                .filter(TopicPreference.workspace_id == ws_b)
                .all()
            )
            assert len(prefs_b) == 0
        finally:
            db.close()
