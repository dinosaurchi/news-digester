"""Tests for flexible topic matching in scoring feedback adjustments.

Covers Pass 2a of the feedback loop repair — word-level matching for topic
preferences so that realistic content produces non-zero matches.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.services.scoring import (
    _compute_feedback_adjustment,
    _topic_matches_text,
)


# ---------------------------------------------------------------------------
# Direct helper tests
# ---------------------------------------------------------------------------


class TestTopicMatchesText:
    """Unit tests for the _topic_matches_text helper function."""

    def test_multiword_topic_matches_when_all_words_present(self):
        """All component words present in any order → match."""
        assert _topic_matches_text("Generative AI", "New generative models using AI")

    def test_multiword_topic_no_match_when_partial_words(self):
        """Only some component words present → no match."""
        assert not _topic_matches_text("Generative AI", "New AI model released")

    def test_single_word_topic_matches_with_boundary(self):
        """Standalone single word → match."""
        assert _topic_matches_text("AI", "AI is transforming industries")

    def test_single_word_topic_no_false_positive(self):
        """Substring occurrence inside another word → no match."""
        assert not _topic_matches_text("AI", "The email said MAIN and PAIR")

    def test_multiword_topic_no_false_positive_from_component_word_substring(self):
        """Component word 'ai' inside 'email' must not cause a false positive."""
        # "ai" appears inside "email" — the multi-word topic should NOT match
        assert not _topic_matches_text("ai computing", "email about computing trends")

    def test_multiword_topic_no_false_positive_short_word_in_longer_word(self):
        """Component word 'or' should not match inside 'word', 'order', etc."""
        assert not _topic_matches_text("or machine", "word machine learning")

    def test_case_insensitive_matching(self):
        assert _topic_matches_text("edge computing", "EDGE COMPUTING trends")

    def test_topic_matching_with_realistic_data(self):
        """Article about 'Enterprise AI' should not match 'Generative AI'."""
        text = "Enterprise AI Adoption Reaches 40% Quarter-over-Quarter Growth"
        assert not _topic_matches_text("Generative AI", text)

    def test_topic_matching_regression_exact_phrase_still_works(self):
        """Single-word topic that used to match via substring still matches."""
        assert _topic_matches_text(
            "cybersecurity", "New cybersecurity regulations proposed"
        )

    def test_empty_topic_never_matches(self):
        assert not _topic_matches_text("", "AI is transforming industries")

    def test_whitespace_only_topic_never_matches(self):
        assert not _topic_matches_text("   ", "AI is transforming industries")

    def test_empty_text_never_matches(self):
        assert not _topic_matches_text("AI", "")

    def test_single_character_word_boundary(self):
        """Single character topic uses word boundaries."""
        assert _topic_matches_text("I", "I am here")
        assert not _topic_matches_text("I", "team is winning")

    def test_multiword_words_in_different_order(self):
        """Words can appear in any order."""
        assert _topic_matches_text(
            "cloud security", "Security in the cloud is critical"
        )

    def test_multiword_with_punctuation_in_text(self):
        """Punctuation in text does not prevent a match."""
        assert _topic_matches_text(
            "machine learning", "AI, machine-learning breakthrough!"
        )

    def test_topic_with_extra_whitespace(self):
        """Extra whitespace in topic is handled gracefully."""
        assert _topic_matches_text("  Generative  AI  ", "generative ai models")


# ---------------------------------------------------------------------------
# Integration with _compute_feedback_adjustment
# ---------------------------------------------------------------------------


class TestFeedbackAdjustmentTopicMatching:
    """Verify that _compute_feedback_adjustment uses word-level matching."""

    def test_multiword_topic_matches_when_all_words_present(self):
        now = datetime.now(timezone.utc)
        adj, topics, sources = _compute_feedback_adjustment(
            "New generative models using AI",
            "SomeSource",
            [{"key": "Generative AI", "weight": 2.0, "updated_at": now}],
            [],
        )
        assert adj > 0
        assert len(topics) == 1
        assert topics[0]["key"] == "Generative AI"

    def test_multiword_topic_no_match_when_partial_words(self):
        now = datetime.now(timezone.utc)
        adj, topics, sources = _compute_feedback_adjustment(
            "New AI model released",
            "SomeSource",
            [{"key": "Generative AI", "weight": 2.0, "updated_at": now}],
            [],
        )
        assert adj == 0.0
        assert topics == []

    def test_single_word_topic_matches_with_boundary(self):
        now = datetime.now(timezone.utc)
        adj, topics, sources = _compute_feedback_adjustment(
            "AI is transforming industries",
            "SomeSource",
            [{"key": "AI", "weight": 1.0, "updated_at": now}],
            [],
        )
        assert adj > 0
        assert len(topics) == 1

    def test_single_word_topic_no_false_positive(self):
        now = datetime.now(timezone.utc)
        adj, topics, sources = _compute_feedback_adjustment(
            "The email said MAIN and PAIR",
            "SomeSource",
            [{"key": "AI", "weight": 1.0, "updated_at": now}],
            [],
        )
        assert adj == 0.0
        assert topics == []

    def test_case_insensitive_matching(self):
        now = datetime.now(timezone.utc)
        adj, topics, sources = _compute_feedback_adjustment(
            "EDGE COMPUTING trends",
            "SomeSource",
            [{"key": "edge computing", "weight": 1.0, "updated_at": now}],
            [],
        )
        assert adj > 0
        assert len(topics) == 1

    def test_topic_matching_with_realistic_data(self):
        now = datetime.now(timezone.utc)
        adj, topics, sources = _compute_feedback_adjustment(
            "Enterprise AI Adoption Reaches 40% Quarter-over-Quarter Growth",
            "SomeSource",
            [{"key": "Generative AI", "weight": 1.0, "updated_at": now}],
            [],
        )
        assert adj == 0.0
        assert topics == []

    def test_topic_matching_regression_exact_phrase_still_works(self):
        now = datetime.now(timezone.utc)
        adj, topics, sources = _compute_feedback_adjustment(
            "New cybersecurity regulations proposed",
            "SomeSource",
            [{"key": "cybersecurity", "weight": 1.0, "updated_at": now}],
            [],
        )
        assert adj > 0
        assert len(topics) == 1
        assert topics[0]["key"] == "cybersecurity"
