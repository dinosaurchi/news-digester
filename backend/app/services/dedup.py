"""Pure utility functions for near-duplicate detection and clustering."""

from __future__ import annotations

import hashlib
from datetime import datetime
from urllib.parse import parse_qs, urlparse, urlunparse

# Common tracking / analytics query parameters to strip during URL normalization.
_TRACKING_PARAMS: set[str] = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "utm_id",
    "fbclid",
    "gclid",
    "gclsrc",
    "dclid",
    "msclkid",
    "mc_eid",
    "mc_cid",
    "_ga",
    "_gl",
    "_hsenc",
    "_hsmi",
    "hsCtaTracking",
    "ref",
    "referrer",
    "si",
    "ei",
    "sei",
    "feature",
    "source",
    "action_object_map",
    "action_type_map",
    "action_ref_map",
}

# Punctuation characters that are safe to strip at the *edges* of a title.
_BOUNDARY_PUNCT: str = "|-—:;.,'\"»«''"


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------


def normalize_url(url: str | None) -> str:
    """Return a canonical form of *url* suitable for deduplication.

    Strips common tracking parameters, removes fragments, lowercases the
    hostname, drops trailing slashes, and sorts remaining query parameters.
    """
    if not url:
        return ""

    parsed = urlparse(url.strip())

    # Lowercase hostname
    netloc = parsed.netloc.lower()

    # Remove trailing slash from path
    path = parsed.path
    if path.endswith("/"):
        path = path.rstrip("/")

    # Filter out tracking parameters and sort the rest
    qs: dict[str, list[str]] = parse_qs(parsed.query, keep_blank_values=True)
    filtered: dict[str, list[str]] = {
        k: v for k, v in qs.items() if k.lower() not in _TRACKING_PARAMS
    }
    # Sort keys for deterministic output; flatten values
    sorted_qs = "&".join(f"{k}={'&'.join(v)}" for k, v in sorted(filtered.items()))

    # Reconstruct without fragment
    normalized = urlunparse((parsed.scheme, netloc, path, parsed.params, sorted_qs, ""))
    return normalized


def normalize_title(title: str | None) -> str:
    """Lowercase, trim whitespace, strip boundary punctuation, collapse spaces."""
    if not title:
        return ""

    text = title.strip().lower()
    text = text.strip(_BOUNDARY_PUNCT)
    # Collapse any run of whitespace to a single space
    parts = text.split()
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Fingerprinting
# ---------------------------------------------------------------------------


def title_fingerprint(title: str | None) -> str:
    """SHA-256 hex digest of the normalized title.

    Enables exact-match dedup on titles that may differ only in casing or
    trailing punctuation.
    """
    return hashlib.sha256(normalize_title(title).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Domain helpers
# ---------------------------------------------------------------------------


def extract_domain(url: str | None) -> str:
    """Return the domain (netloc) of *url* with ``www.`` stripped.

    Returns an empty string when *url* is ``None`` or empty.
    """
    if not url:
        return ""

    netloc = urlparse(url.strip()).netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc


# ---------------------------------------------------------------------------
# Similarity metrics
# ---------------------------------------------------------------------------


def _char_trigrams(text: str) -> set[str]:
    """Return the set of character-level trigrams in *text*."""
    return {text[i : i + 3] for i in range(len(text) - 2)}


def trigram_similarity(text1: str, text2: str) -> float:
    """Jaccard similarity over character trigram sets.

    Returns a float between 0.0 (no overlap) and 1.0 (identical).
    """
    if not text1 or not text2:
        return 0.0

    s1 = _char_trigrams(text1)
    s2 = _char_trigrams(text2)

    if not s1 or not s2:
        return 0.0

    intersection = s1 & s2
    union = s1 | s2
    return len(intersection) / len(union)


def token_overlap_similarity(text1: str, text2: str) -> float:
    """Jaccard similarity over whitespace-tokenised word sets.

    Returns a float between 0.0 and 1.0.
    """
    if not text1 or not text2:
        return 0.0

    tokens1 = set(text1.lower().split())
    tokens2 = set(text2.lower().split())

    if not tokens1 or not tokens2:
        return 0.0

    intersection = tokens1 & tokens2
    union = tokens1 | tokens2
    return len(intersection) / len(union)


# ---------------------------------------------------------------------------
# Temporal proximity
# ---------------------------------------------------------------------------


def time_proximity(
    dt1: datetime | None,
    dt2: datetime | None,
    hours: float = 24.0,
) -> bool:
    """Return ``True`` when *dt1* and *dt2* are within *hours* of each other.

    Gracefully handles ``None`` inputs by returning ``False``.
    """
    if dt1 is None or dt2 is None:
        return False

    delta = abs((dt1 - dt2).total_seconds())
    return delta <= hours * 3600


# ---------------------------------------------------------------------------
# Composite similarity (main entry point for the clustering pipeline)
# ---------------------------------------------------------------------------

# Relative weights used to compute the combined score.
_WEIGHT_URL_MATCH: float = 0.35
_WEIGHT_TITLE_SIMILARITY: float = 0.35
_WEIGHT_DOMAIN_MATCH: float = 0.15
_WEIGHT_TIME_PROXIMATE: float = 0.15


def compute_similarity(item1: dict, item2: dict) -> dict:
    """Compare two content-item-like dicts and return similarity signals.

    Expected keys in each dict:
        - ``url`` (str | None)
        - ``title`` (str | None)
        - ``published_at`` (datetime | None)

    Returns a dict with:
        - ``url_match`` (bool) — normalised URLs are identical
        - ``title_similarity`` (float) — token-overlap Jaccard on titles
        - ``domain_match`` (bool) — extracted domains match
        - ``time_proximate`` (bool) — published within 24 h
        - ``combined_score`` (float) — weighted combination of all signals
    """
    url1 = item1.get("url")
    url2 = item2.get("url")
    title1 = item1.get("title")
    title2 = item2.get("title")
    dt1 = item1.get("published_at")
    dt2 = item2.get("published_at")

    norm_url1 = normalize_url(url1)
    norm_url2 = normalize_url(url2)
    url_match = norm_url1 != "" and norm_url1 == norm_url2

    domain_match = extract_domain(url1) != "" and extract_domain(
        url1
    ) == extract_domain(url2)

    title_similarity = token_overlap_similarity(title1 or "", title2 or "")

    proximate = time_proximity(dt1, dt2)

    combined_score = (
        _WEIGHT_URL_MATCH * float(url_match)
        + _WEIGHT_TITLE_SIMILARITY * title_similarity
        + _WEIGHT_DOMAIN_MATCH * float(domain_match)
        + _WEIGHT_TIME_PROXIMATE * float(proximate)
    )

    return {
        "url_match": url_match,
        "title_similarity": title_similarity,
        "domain_match": domain_match,
        "time_proximate": proximate,
        "combined_score": combined_score,
    }
