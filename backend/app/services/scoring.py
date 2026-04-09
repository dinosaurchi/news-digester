"""Pure utility functions for cheap relevance scoring of content items."""

from __future__ import annotations

import math
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Keyword matching
# ---------------------------------------------------------------------------


def compute_keyword_score(text: str, keywords: list[str]) -> float:
    """Return a normalised 0.0–1.0 score based on keyword match ratio.

    The score is the fraction of *keywords* found (case-insensitive) in *text*.
    Returns 0.0 when either *text* or *keywords* is empty.
    """
    if not text or not keywords:
        return 0.0

    lower_text = text.lower()
    matched = sum(1 for kw in keywords if kw.lower() in lower_text)
    return matched / len(keywords)


# ---------------------------------------------------------------------------
# Competitor mention detection
# ---------------------------------------------------------------------------


def compute_competitor_mention_score(
    text: str,
    competitors: list[str],
) -> float:
    """Return 1.0 if any competitor name appears in *text*, else 0.0.

    Matching is case-insensitive and partial-word (substring).
    """
    if not text or not competitors:
        return 0.0

    lower_text = text.lower()
    for name in competitors:
        if name.lower() in lower_text:
            return 1.0
    return 0.0


# ---------------------------------------------------------------------------
# Excluded topic detection
# ---------------------------------------------------------------------------


def compute_excluded_topic_score(
    text: str,
    excluded_topics: list[str],
) -> float:
    """Return 1.0 if any excluded topic term appears in *text*, else 0.0.

    A score of 1.0 signals the content should be excluded.
    """
    if not text or not excluded_topics:
        return 0.0

    lower_text = text.lower()
    for topic in excluded_topics:
        if topic.lower() in lower_text:
            return 1.0
    return 0.0


# ---------------------------------------------------------------------------
# Freshness / recency
# ---------------------------------------------------------------------------


def compute_freshness_score(
    published_at: datetime | None,
    max_age_hours: float = 168.0,
) -> float:
    """Return a linear-decay freshness score between 0.0 and 1.0.

    * Just published  → 1.0
    * ``max_age_hours`` old  → 0.0
    * Older than ``max_age_hours``  → 0.0
    * ``published_at`` is ``None``  → 0.5 (neutral)
    """
    if published_at is None:
        return 0.5

    now = datetime.now(timezone.utc)

    # Ensure both datetimes are timezone-aware for correct arithmetic.
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)

    age_seconds = (now - published_at).total_seconds()
    max_age_seconds = max_age_hours * 3600.0

    if age_seconds <= 0:
        return 1.0
    if age_seconds >= max_age_seconds:
        return 0.0

    return 1.0 - (age_seconds / max_age_seconds)


# ---------------------------------------------------------------------------
# Source authority
# ---------------------------------------------------------------------------


def compute_source_authority_score(
    domain: str,
    trusted_domains: list[str] | None = None,
) -> float:
    """Return a source-authority score.

    * domain is in ``trusted_domains`` → 1.0
    * ``trusted_domains`` is empty or ``None`` → 0.5 (neutral)
    * otherwise → 0.3
    """
    if not domain:
        return 0.3

    if trusted_domains is None or len(trusted_domains) == 0:
        return 0.5

    lower_domain = domain.lower()
    lower_trusted = {d.lower() for d in trusted_domains}

    if lower_domain in lower_trusted:
        return 1.0

    return 0.3


# ---------------------------------------------------------------------------
# BM25-style scoring (simplified, per-document)
# ---------------------------------------------------------------------------


def compute_bm25_score(text: str, query_terms: list[str]) -> float:
    """Return a simplified BM25-style score based on term frequency.

    The text is tokenised by whitespace and lowercased.  For each *query_term*
    the raw term frequency (TF) in the text is computed.  The final score is
    the average of ``log(1 + tf)`` across all query terms (missing terms
    contribute 0), capped at 1.0.

    Returns 0.0 when *text* or *query_terms* is empty.
    """
    if not text or not query_terms:
        return 0.0

    tokens = text.lower().split()
    if not tokens:
        return 0.0

    # Build term frequencies
    tf: dict[str, int] = {}
    for token in tokens:
        tf[token] = tf.get(token, 0) + 1

    # Sum log(1 + tf) for each query term present
    raw_score = 0.0
    for term in query_terms:
        term_lower = term.lower()
        if term_lower in tf:
            raw_score += math.log(1 + tf[term_lower])

    # Normalise by number of query terms so the score reflects match density
    normalised = raw_score / len(query_terms)
    return min(normalised, 1.0)


# ---------------------------------------------------------------------------
# Combined scoring
# ---------------------------------------------------------------------------

# Default weights for the combined relevance score.
_WEIGHTS: dict[str, float] = {
    "keyword": 0.25,
    "competitor_mention": 0.20,
    "freshness": 0.20,
    "source_authority": 0.15,
    "bm25": 0.20,
}


def compute_combined_score(scores: dict) -> tuple[float, dict]:
    """Compute a weighted combined relevance score from individual scores.

    Parameters
    ----------
    scores:
        A dict that may contain any of the keys ``keyword``,
        ``competitor_mention``, ``freshness``, ``source_authority``, ``bm25``.
        Missing keys default to 0.0.

    Returns
    -------
    (combined_score, breakdown) where:
    - ``combined_score`` is the weighted sum.
    - ``breakdown`` is a JSON-serialisable dict containing the individual
      scores, the weights used, and the final combined score.
    """
    combined = 0.0
    breakdown: dict = {
        "weights": dict(_WEIGHTS),
        "scores": {},
    }

    for key, weight in _WEIGHTS.items():
        value = float(scores.get(key, 0.0))
        breakdown["scores"][key] = value
        combined += weight * value

    # Clamp to [0, 1]
    combined = max(0.0, min(1.0, combined))

    breakdown["combined_score"] = combined
    return combined, breakdown
