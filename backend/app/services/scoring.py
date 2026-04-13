"""Pure utility functions for cheap relevance scoring of content items."""

from __future__ import annotations

import logging
import math
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.models.content import ContentItem
from app.models.feed import FeedSource
from app.models.workspace import Workspace

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Feedback adjustment constants
# ---------------------------------------------------------------------------

# Lightweight score adjustment applied per matching preference.
# The raw weight from the preference model (typically -1.0 to +3.0) is
# multiplied by this factor so that feedback never dominates the core score.
_FEEDBACK_ADJUSTMENT_FACTOR: float = 0.05

# Maximum absolute adjustment cap so no single signal can swing a score
# more than this amount.
_FEEDBACK_ADJUSTMENT_CAP: float = 0.15

# Default half-life (in days) for preference time decay.
_FEEDBACK_DECAY_HALF_LIFE_DAYS: float = 30.0


# ---------------------------------------------------------------------------
# Feedback preference time decay
# ---------------------------------------------------------------------------


def _compute_decay_factor(
    updated_at: datetime | None,
    half_life_days: float = _FEEDBACK_DECAY_HALF_LIFE_DAYS,
) -> float:
    """Return an exponential decay multiplier between 0.0 and 1.0.

    Parameters
    ----------
    updated_at:
        The reference timestamp for the preference.  Falls back to
        ``created_at`` by the caller.  If ``None``, returns 0.0 so that
        preferences with no timestamp contribute negligibly.
    half_life_days:
        Number of days after which the weight is halved.  Defaults to 30.

    Returns
    -------
    A float in [0.0, 1.0]:
    - Updated today → ≈1.0
    - Updated ``half_life_days`` ago → ≈0.5
    - Updated 90 days ago (with 30-day half-life) → ≈0.125
    """
    if updated_at is None:
        return 0.0

    now = datetime.now(timezone.utc)

    # Ensure the timestamp is timezone-aware.
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=timezone.utc)

    age_days = (now - updated_at).days
    if age_days <= 0:
        return 1.0

    return 2.0 ** (-(age_days / half_life_days))


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


def compute_document_frequencies(
    items_texts: list[str],
    query_terms: list[str],
) -> dict[str, float]:
    """Compute IDF values for query terms across a batch of item texts.

    For each query term, counts how many item texts contain that term
    (case-insensitive).  Returns ``{term: idf}`` where
    ``idf = log(N / (1 + df))`` and *N* is the total number of items.

    Parameters
    ----------
    items_texts:
        List of text strings (one per item in the batch).
    query_terms:
        List of query terms to compute IDF for.

    Returns
    -------
    Dict mapping each query term (lowercased) to its IDF value.
    Returns an empty dict when *items_texts* or *query_terms* is empty.
    """
    if not items_texts or not query_terms:
        return {}

    N = len(items_texts)

    # Count document frequency for each query term
    df: dict[str, int] = {}
    for term in query_terms:
        term_lower = term.lower()
        count = 0
        for text in items_texts:
            if term_lower in text.lower():
                count += 1
        df[term_lower] = count

    # Compute IDF: log(N / (1 + df)), clamped at 0 so that common terms
    # (appearing in most documents) contribute less than rare terms, but
    # never produce a negative multiplier.
    idf: dict[str, float] = {}
    for term_lower, doc_freq in df.items():
        idf[term_lower] = max(0.0, math.log(N / (1 + doc_freq)))

    return idf


def compute_bm25_score(
    text: str,
    query_terms: list[str],
    idf: dict[str, float] | None = None,
) -> float:
    """Return a simplified BM25-style score based on term frequency.

    The text is tokenised by whitespace and lowercased.  For each *query_term*
    the raw term frequency (TF) in the text is computed.  The final score is
    the average of ``log(1 + tf)`` across all query terms (missing terms
    contribute 0), capped at 1.0.

    When *idf* is provided, each term's ``log(1 + tf)`` is multiplied by its
    IDF value before averaging, so that common terms (appearing in many
    documents) contribute less than rare terms.  When *idf* is ``None``
    (default), the function behaves in TF-only mode, identical to the
    previous implementation.

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

    # Sum log(1 + tf) * idf (when provided) for each query term present
    raw_score = 0.0
    for term in query_terms:
        term_lower = term.lower()
        if term_lower in tf:
            tf_score = math.log(1 + tf[term_lower])
            if idf is not None and term_lower in idf:
                tf_score *= idf[term_lower]
            raw_score += tf_score

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
    "content_type_prior": 0.0,  # disabled by default; enable via workspace settings
}

# ---------------------------------------------------------------------------
# Feed health / reliability scoring
# ---------------------------------------------------------------------------

# Feed success-rate thresholds (configurable).
_FEED_HEALTH_HIGH_THRESHOLD: float = 0.80  # >80% → full weight (1.0)
_FEED_HEALTH_MID_THRESHOLD: float = 0.50  # 50-80% → reduced weight (0.8)
# <50% → low weight (0.5)

# Staleness penalty: additional multiplier for content from stale feeds.
_STALE_FEED_PENALTY: float = 0.5  # stale feeds get this extra multiplier


def compute_feed_health_score(
    feed_success_rate: float,
    is_stale: bool = False,
    *,
    high_threshold: float = _FEED_HEALTH_HIGH_THRESHOLD,
    mid_threshold: float = _FEED_HEALTH_MID_THRESHOLD,
    stale_penalty: float = _STALE_FEED_PENALTY,
) -> float:
    """Return a feed health weight between 0.0 and 1.0.

    Scoring tiers (based on feed success rate):
    - ``>high_threshold`` (default >0.80) → 1.0 (full weight)
    - ``mid_threshold`` to ``high_threshold`` (default 0.50–0.80) → 0.8
    - ``<mid_threshold`` (default <0.50) → 0.5

    An additional *stale_penalty* multiplier is applied when the feed is
    flagged as stale, further downweighting its content.

    When *feed_success_rate* is 0.0 (no fetches attempted yet), returns
    1.0 (neutral — benefit of the doubt).
    """
    if feed_success_rate <= 0.0:
        # No data yet — neutral, no penalty
        return 1.0

    if feed_success_rate > high_threshold:
        weight = 1.0
    elif feed_success_rate >= mid_threshold:
        weight = 0.8
    else:
        weight = 0.5

    # Apply staleness penalty multiplicatively
    if is_stale:
        weight *= stale_penalty

    return max(0.0, min(1.0, weight))


# ---------------------------------------------------------------------------
# Content type prior
# ---------------------------------------------------------------------------

# Default prior weights per content type.  Higher values indicate content
# types that are generally more relevant for a typical news-monitoring
# workspace.  Override per workspace via ``settings.thresholds.content_type_weights``.
_DEFAULT_CONTENT_TYPE_WEIGHTS: dict[str, float] = {
    "news": 1.0,
    "press_release": 0.9,
    "blog": 0.7,
    "competitor": 0.8,
    "forum": 0.5,
    "social": 0.4,
}


def compute_content_type_prior_score(
    content_type: str | None,
    weights: dict[str, float] | None = None,
) -> float:
    """Return a prior score based on the item's content type.

    Parameters
    ----------
    content_type:
        The content type string (e.g. ``"news"``, ``"blog"``).  When
        ``None`` or empty, returns the neutral prior (0.5).
    weights:
        Optional dict mapping content-type strings to prior weights.
        Falls back to :data:`_DEFAULT_CONTENT_TYPE_WEIGHTS` when ``None``.
        Unknown content types receive a neutral prior of 0.5.

    Returns
    -------
    A float between 0.0 and 1.0.
    """
    if not content_type:
        return 0.5  # neutral for unknown / missing

    active_weights = weights if weights is not None else _DEFAULT_CONTENT_TYPE_WEIGHTS
    return float(active_weights.get(content_type.lower(), 0.5))


def _validate_weight_overrides(
    overrides: dict[str, float] | None,
) -> dict[str, float]:
    """Validate and filter weight overrides against ``_WEIGHTS`` keys.

    Only keys present in ``_WEIGHTS`` are kept.  Values must be non-negative
    floats; invalid values are silently skipped (with a warning log) and the
    corresponding default is used instead.

    The caller is responsible for choosing weights that sum to 1.0 — no
    normalisation is performed.

    Returns a dict of validated overrides (may be empty).
    """
    if not overrides:
        return {}

    validated: dict[str, float] = {}
    for key, value in overrides.items():
        if key not in _WEIGHTS:
            continue
        try:
            float_value = float(value)
        except (TypeError, ValueError):
            logger.warning(
                "Ignoring invalid scoring weight for '%s': %r (not a number)",
                key,
                value,
            )
            continue
        if float_value < 0:
            logger.warning(
                "Ignoring negative scoring weight for '%s': %s", key, float_value
            )
            continue
        validated[key] = float_value

    return validated


def compute_combined_score(
    scores: dict,
    weight_overrides: dict[str, float] | None = None,
) -> tuple[float, dict]:
    """Compute a weighted combined relevance score from individual scores.

    Parameters
    ----------
    scores:
        A dict that may contain any of the keys ``keyword``,
        ``competitor_mention``, ``freshness``, ``source_authority``, ``bm25``.
        Missing keys default to 0.0.
    weight_overrides:
        Optional dict mapping weight names to non-negative floats.  Only keys
        that exist in the default ``_WEIGHTS`` are recognised; unknown keys are
        silently ignored.  Missing keys fall back to defaults.

        The caller is responsible for choosing weights that sum to 1.0 — no
        normalisation is performed.

    Returns
    -------
    (combined_score, breakdown) where:
    - ``combined_score`` is the weighted sum.
    - ``breakdown`` is a JSON-serialisable dict containing the individual
      scores, the weights actually used (defaults merged with any valid
      overrides), and the final combined score.
    """
    # Merge validated overrides on top of defaults
    active_weights = dict(_WEIGHTS)
    valid_overrides = _validate_weight_overrides(weight_overrides)
    if valid_overrides:
        active_weights.update(valid_overrides)

    combined = 0.0
    breakdown: dict = {
        "weights": active_weights,
        "scores": {},
    }

    for key, weight in active_weights.items():
        value = float(scores.get(key, 0.0))
        breakdown["scores"][key] = value
        combined += weight * value

    # Clamp to [0, 1]
    combined = max(0.0, min(1.0, combined))

    breakdown["combined_score"] = combined
    return combined, breakdown


# ---------------------------------------------------------------------------
# Pipeline-level scoring: score a batch of ContentItems against a workspace
# ---------------------------------------------------------------------------


def _extract_domain(url: str | None) -> str:
    """Extract the hostname from a URL string, returning empty string on failure."""
    if not url:
        return ""
    # OPTIONAL DEGRADATION: URL parsing failures are expected for malformed
    # URLs.  Returning empty string means the item gets a neutral source-
    # authority score (0.3), which is correct behaviour for an unknown domain.
    try:
        parsed = urlparse(url)
        return parsed.hostname or ""
    except Exception:
        return ""


def _load_feedback_signals(
    db: Session, workspace_id: str
) -> tuple[list[dict], list[dict], int]:
    """Load feedback preferences and event count for a workspace.

    Returns
    -------
    (topic_prefs, source_prefs, feedback_event_count) where:
    - ``topic_prefs`` is a list of dicts, each with keys
      ``key`` (lowercase topic), ``weight``, and ``updated_at`` (datetime or
      None — already falls back to ``created_at``).
    - ``source_prefs`` is a list of dicts with the same shape for source
      preferences.
    - ``feedback_event_count`` is the total number of FeedbackEvent rows.
    """
    topic_prefs: list[dict] = []
    source_prefs: list[dict] = []
    feedback_event_count: int = 0

    try:
        from app.models.preferences import TopicPreference, SourcePreference

        # Load topic preferences (individual rows, not aggregated)
        tp_rows = (
            db.query(TopicPreference)
            .filter(TopicPreference.workspace_id == workspace_id)
            .all()
        )
        for tp in tp_rows:
            topic_prefs.append(
                {
                    "key": tp.topic.lower(),
                    "weight": tp.weight,
                    "updated_at": tp.updated_at or tp.created_at,
                }
            )

        # Load source preferences (individual rows, not aggregated)
        sp_rows = (
            db.query(SourcePreference)
            .filter(SourcePreference.workspace_id == workspace_id)
            .all()
        )
        for sp in sp_rows:
            source_prefs.append(
                {
                    "key": sp.source_name.lower(),
                    "weight": sp.weight,
                    "updated_at": sp.updated_at or sp.created_at,
                }
            )

    # OPTIONAL DEGRADATION: Feedback signals are nice-to-have adjustments that
    # slightly tweak relevance scores.  If preferences cannot be loaded (e.g.
    # the model/table is missing, or the DB query fails), scoring still
    # produces correct results — just without the feedback delta.  Never
    # silently swallow; always log at WARNING so operators can investigate.
    except Exception:
        logger.warning(
            "Could not load preference models for feedback scoring",
            exc_info=True,
        )

    try:
        from app.models.report import FeedbackEvent

        feedback_event_count = (
            db.query(FeedbackEvent)
            .filter(FeedbackEvent.workspace_id == workspace_id)
            .count()
        )
    # OPTIONAL DEGRADATION: Feedback event count is a metadata-only field used
    # for transparency in score breakdowns.  Its absence does not affect
    # scoring correctness.
    except Exception:
        logger.warning("Could not load feedback event count", exc_info=True)

    return topic_prefs, source_prefs, feedback_event_count


def _topic_matches_text(topic_key: str, text: str) -> bool:
    """Check whether a topic preference key matches item text.

    Matching rules:
    - Multi-word topics: all individual words must appear in the text (AND
      logic), each matched as a case-insensitive substring.  The words do
      not need to appear contiguously or in order.
    - Single-word topics: the word is matched using word-boundary regex
      (``\\bword\\b``) to avoid false positives such as "AI" matching
      "MAIL" or "PAIR".
    - Empty or whitespace-only topics never match.
    - Matching is case-insensitive for both topic and text.
    """
    if not topic_key or not topic_key.strip():
        return False

    lower_text = text.lower()
    words = topic_key.lower().split()

    if len(words) == 1:
        # Single-word topic: use word-boundary matching
        pattern = r"\b" + re.escape(words[0]) + r"\b"
        return re.search(pattern, lower_text) is not None

    # Multi-word topic: ALL words must appear as substrings (AND logic)
    return all(word in lower_text for word in words)


def _compute_feedback_adjustment(
    item_text: str,
    source_name: str | None,
    topic_prefs: list[dict],
    source_prefs: list[dict],
) -> tuple[float, list[dict], list[dict]]:
    """Compute a lightweight score adjustment from feedback preferences.

    Each preference's weight is multiplied by a time-decay factor before
    being applied (see :func:`_compute_decay_factor`).

    Returns
    -------
    (adjustment, topics_matched, sources_matched) where:
    - ``adjustment`` is the net score delta (clamped to ±_FEEDBACK_ADJUSTMENT_CAP)
    - ``topics_matched`` lists dicts with matched topic info including
      ``key``, ``original_weight``, ``decayed_weight``, and ``decay_factor``
    - ``sources_matched`` lists dicts with matched source info in the same shape
    """
    adjustment = 0.0
    topics_matched: list[dict] = []
    sources_matched: list[dict] = []

    lower_text = item_text.lower()

    # Topic preference adjustments (with time decay)
    for pref in topic_prefs:
        topic_key = pref["key"]
        if _topic_matches_text(topic_key, lower_text):
            original_weight = pref["weight"]
            decay_factor = _compute_decay_factor(pref["updated_at"])
            decayed_weight = original_weight * decay_factor

            delta = decayed_weight * _FEEDBACK_ADJUSTMENT_FACTOR
            # Clamp individual delta
            delta = max(-_FEEDBACK_ADJUSTMENT_CAP, min(_FEEDBACK_ADJUSTMENT_CAP, delta))
            adjustment += delta

            topics_matched.append(
                {
                    "key": topic_key,
                    "original_weight": original_weight,
                    "decayed_weight": round(decayed_weight, 6),
                    "decay_factor": round(decay_factor, 6),
                }
            )

            logger.debug(
                "Feedback topic '%s': weight=%.3f, decay_factor=%.4f, "
                "decayed_weight=%.3f, delta=%.4f",
                topic_key,
                original_weight,
                decay_factor,
                decayed_weight,
                delta,
            )

    # Source preference adjustments (with time decay)
    if source_name:
        lower_source = source_name.lower()
        for pref in source_prefs:
            src_key = pref["key"]
            if lower_source == src_key or src_key in lower_source:
                original_weight = pref["weight"]
                decay_factor = _compute_decay_factor(pref["updated_at"])
                decayed_weight = original_weight * decay_factor

                delta = decayed_weight * _FEEDBACK_ADJUSTMENT_FACTOR
                delta = max(
                    -_FEEDBACK_ADJUSTMENT_CAP, min(_FEEDBACK_ADJUSTMENT_CAP, delta)
                )
                adjustment += delta

                sources_matched.append(
                    {
                        "key": src_key,
                        "original_weight": original_weight,
                        "decayed_weight": round(decayed_weight, 6),
                        "decay_factor": round(decay_factor, 6),
                    }
                )

                logger.debug(
                    "Feedback source '%s': weight=%.3f, decay_factor=%.4f, "
                    "decayed_weight=%.3f, delta=%.4f",
                    src_key,
                    original_weight,
                    decay_factor,
                    decayed_weight,
                    delta,
                )

    # Clamp total adjustment
    adjustment = max(
        -_FEEDBACK_ADJUSTMENT_CAP, min(_FEEDBACK_ADJUSTMENT_CAP, adjustment)
    )

    return adjustment, topics_matched, sources_matched


def score_content_items(
    db: Session,
    items: list[ContentItem],
    workspace: Workspace,
) -> dict:
    """Score a list of ContentItems using workspace profile/settings.

    For each item the function:
    1. Computes individual scores (keyword, competitor, freshness, source, bm25).
    2. Combines them into a weighted score via ``compute_combined_score``.
    3. Checks excluded topics and the minimum relevance threshold.
    4. Persists the results on the ORM objects and commits.

    Parameters
    ----------
    db:
        SQLAlchemy session (used to flush/persist changes).
    items:
        ContentItem ORM objects to score.
    workspace:
        The workspace whose profile/settings define scoring context.

    Returns
    -------
    A dict with summary metadata::

        {
            "included_count": int,
            "excluded_count": int,
            "avg_score": float,
            "min_score": float,
            "max_score": float,
        }
    """
    # ------------------------------------------------------------------
    # 1. Load workspace context (gracefully handle missing profile/settings)
    # ------------------------------------------------------------------
    profile = workspace.profile
    settings = workspace.settings

    priority_themes: list[str] = (
        list(profile.priority_themes) if profile and profile.priority_themes else []
    )
    competitors: list[str] = (
        list(profile.competitors) if profile and profile.competitors else []
    )
    excluded_topics: list[str] = (
        list(profile.excluded_topics) if profile and profile.excluded_topics else []
    )

    # trusted_domains may live inside settings.thresholds or be absent
    trusted_domains: list[str] | None = None
    if settings and settings.thresholds:
        trusted_domains = settings.thresholds.get("trusted_domains")
        if trusted_domains is not None:
            trusted_domains = list(trusted_domains)

    # Minimum relevance threshold (default 0.1)
    min_relevance_score: float = 0.1
    if settings and settings.thresholds:
        min_relevance_score = float(settings.thresholds.get("min_relevance_score", 0.1))

    # Scoring weight overrides (default: None → use built-in defaults)
    scoring_weights: dict[str, float] | None = None
    if settings and settings.thresholds:
        raw_weights = settings.thresholds.get("scoring_weights")
        if raw_weights is not None and isinstance(raw_weights, dict):
            validated = _validate_weight_overrides(raw_weights)
            if validated:
                scoring_weights = validated
                logger.info(
                    "Applying scoring weight overrides for workspace %s: %s",
                    workspace.id,
                    validated,
                )
            else:
                logger.warning(
                    "scoring_weights configured for workspace %s but all values "
                    "were invalid — falling back to defaults",
                    workspace.id,
                )

    # Content type prior weights (default: use built-in defaults)
    content_type_weights: dict[str, float] | None = None
    if settings and settings.thresholds:
        raw_ct_weights = settings.thresholds.get("content_type_weights")
        if raw_ct_weights is not None and isinstance(raw_ct_weights, dict):
            content_type_weights = {
                str(k): float(v)
                for k, v in raw_ct_weights.items()
                if isinstance(v, (int, float))
            }
            if content_type_weights:
                logger.info(
                    "Applying content type prior overrides for workspace %s: %s",
                    workspace.id,
                    content_type_weights,
                )

    # ------------------------------------------------------------------
    # 1b. Load feedback signals for the workspace
    # ------------------------------------------------------------------
    topic_prefs, source_prefs, feedback_event_count = _load_feedback_signals(
        db, workspace.id
    )

    # ------------------------------------------------------------------
    # 1c. Load feed health data for scoring
    # ------------------------------------------------------------------
    feed_health_map: dict[str, dict] = {}  # feed_id → {success_rate, is_stale}
    try:
        feed_ids = {item.feed_source_id for item in items if item.feed_source_id}
        if feed_ids:
            feed_rows = db.query(FeedSource).filter(FeedSource.id.in_(feed_ids)).all()
            for f in feed_rows:
                feed_health_map[f.id] = {
                    "success_rate": f.fetch_success_rate,
                    "is_stale": f.is_stale,
                }
    except Exception:
        logger.warning("Could not load feed health data", exc_info=True)

    # ------------------------------------------------------------------
    # 1c. Pre-compute item texts and batch IDF for BM25 scoring
    # ------------------------------------------------------------------
    items_texts: list[str] = []
    for item in items:
        parts: list[str] = []
        if item.title:
            parts.append(item.title)
        if item.summary_snippet:
            parts.append(item.summary_snippet)
        elif item.raw_text:
            parts.append(item.raw_text[:1000])
        items_texts.append(" ".join(parts))

    batch_idf: dict[str, float] = compute_document_frequencies(
        items_texts, priority_themes
    )

    # ------------------------------------------------------------------
    # 2. Score each item
    # ------------------------------------------------------------------
    included_count = 0
    excluded_count = 0
    scores_list: list[float] = []

    for idx, item in enumerate(items):
        item_text = items_texts[idx]

        # Compute individual scores
        individual_scores: dict[str, float] = {
            "keyword": compute_keyword_score(item_text, priority_themes),
            "competitor_mention": compute_competitor_mention_score(
                item_text, competitors
            ),
            "freshness": compute_freshness_score(
                item.published_at  # type: ignore[arg-type]
                if not isinstance(item.published_at, str)
                else None,
            ),
            "source_authority": compute_source_authority_score(
                _extract_domain(item.url),
                trusted_domains,
            ),
            "bm25": compute_bm25_score(item_text, priority_themes, idf=batch_idf),
            "content_type_prior": compute_content_type_prior_score(
                item.content_type,
                weights=content_type_weights,
            ),
        }

        # Compute feed health score and apply as a multiplicative weight
        feed_health_score = 1.0
        feed_info = (
            feed_health_map.get(item.feed_source_id) if item.feed_source_id else None
        )
        if feed_info is not None:
            feed_health_score = compute_feed_health_score(
                feed_info["success_rate"],
                feed_info["is_stale"],
            )
            individual_scores["feed_health"] = feed_health_score

        # Combined weighted score
        combined_score, breakdown = compute_combined_score(
            individual_scores,
            weight_overrides=scoring_weights,
        )

        # Check excluded topics
        excluded_score = compute_excluded_topic_score(item_text, excluded_topics)
        breakdown["excluded_topic_score"] = excluded_score

        # Include IDF values in the breakdown for transparency
        if batch_idf:
            breakdown["bm25_idf"] = batch_idf

        # Include content type in breakdown for debugging
        breakdown["content_type"] = item.content_type

        # ------------------------------------------------------------------
        # 2b. Apply feedback adjustment
        # ------------------------------------------------------------------
        feedback_adj, topics_matched, sources_matched = _compute_feedback_adjustment(
            item_text, item.source_name, topic_prefs, source_prefs
        )
        if feedback_adj != 0.0:
            combined_score = max(0.0, min(1.0, combined_score + feedback_adj))
            breakdown["feedback_adjustment"] = feedback_adj

        # ------------------------------------------------------------------
        # 2c. Apply feed health weight (multiplicative)
        # ------------------------------------------------------------------
        if feed_info is not None and feed_health_score < 1.0:
            combined_score = max(0.0, min(1.0, combined_score * feed_health_score))
            breakdown["feed_health_weight"] = feed_health_score
        # Always include feed_health in scores for transparency
        if feed_info is not None:
            breakdown.setdefault("scores", {})["feed_health"] = feed_health_score

        feedback_info: dict = {}
        if topics_matched:
            feedback_info["topics_matched"] = topics_matched
        if sources_matched:
            feedback_info["sources_matched"] = sources_matched
        if feedback_info:
            feedback_info["event_count"] = feedback_event_count
            breakdown["feedback"] = feedback_info

        # ------------------------------------------------------------------
        # 3. Apply filtering rules
        # ------------------------------------------------------------------
        if excluded_score > 0:
            item.status = "excluded"
            item.exclusion_reason = "matched_excluded_topic"
            item.inclusion_reason = None
            breakdown["filter_reason"] = "matched_excluded_topic"
            excluded_count += 1
        elif combined_score < min_relevance_score:
            item.status = "excluded"
            item.exclusion_reason = "below_relevance_threshold"
            item.inclusion_reason = None
            breakdown["filter_reason"] = "below_relevance_threshold"
            breakdown["min_relevance_threshold"] = min_relevance_score
            excluded_count += 1
        else:
            item.status = "included"
            item.exclusion_reason = None
            item.inclusion_reason = f"combined_score={combined_score:.4f}"
            breakdown["filter_reason"] = "included"
            included_count += 1

        # ------------------------------------------------------------------
        # 4. Persist results on the item
        # ------------------------------------------------------------------
        item.score_breakdown_json = breakdown
        item.local_relevance_score = combined_score
        item.final_score = combined_score

        scores_list.append(combined_score)

    # Flush changes to the database
    db.flush()

    # ------------------------------------------------------------------
    # 5. Return summary metadata
    # ------------------------------------------------------------------
    if scores_list:
        avg_score = sum(scores_list) / len(scores_list)
        min_score = min(scores_list)
        max_score = max(scores_list)
    else:
        avg_score = 0.0
        min_score = 0.0
        max_score = 0.0

    return {
        "included_count": included_count,
        "excluded_count": excluded_count,
        "avg_score": avg_score,
        "min_score": min_score,
        "max_score": max_score,
    }
