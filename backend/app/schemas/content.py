"""Content Pydantic DTOs."""

from typing import Any, Optional

from pydantic import BaseModel, Field, ConfigDict


class ContentItemOut(BaseModel):
    id: str
    workspace_id: str = Field(alias="workspaceId")
    title: str
    source: Optional[str] = None
    source_url: Optional[str] = Field(default=None, alias="sourceUrl")
    published_at: Optional[str] = Field(default=None, alias="publishedAt")
    type: str
    relevance_score: Optional[float] = Field(default=None, alias="relevanceScore")
    bm25_score: Optional[float] = Field(default=None, alias="bm25Score")
    final_score: Optional[float] = Field(default=None, alias="finalScore")
    status: str
    cluster_id: Optional[str] = Field(default=None, alias="clusterId")
    snippet: Optional[str] = None
    body: Optional[str] = None
    inclusion_reason: Optional[str] = Field(default=None, alias="inclusionReason")
    exclusion_reason: Optional[str] = Field(default=None, alias="exclusionReason")
    linked_report_ids: Optional[list[str]] = Field(
        default=None, alias="linkedReportIds"
    )

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ThemeMatch(BaseModel):
    """Theme match metadata showing which priority themes matched/unmatched."""

    matched: list[str] = Field(default_factory=list)
    unmatched: list[str] = Field(default_factory=list)
    normalized_themes: Optional[list[str]] = Field(default=None)
    decomposed_themes: Optional[dict[str, list[str]]] = Field(default=None)


class CompetitorMatch(BaseModel):
    """Competitor match metadata showing which competitors matched/unmatched."""

    matched: list[str] = Field(default_factory=list)
    unmatched: list[str] = Field(default_factory=list)
    normalized_competitors: Optional[list[str]] = Field(default=None)
    competitor_aliases: Optional[dict[str, list[str]]] = Field(default=None)


class MultiSignalBoost(BaseModel):
    """Multi-signal boost applied when multiple distinct themes match."""

    bonus: float
    distinct_matched_themes: int


class FeedbackDetails(BaseModel):
    """User feedback details that influenced the score."""

    topicsMatched: list[str] = Field(default_factory=list)
    sourcesMatched: list[str] = Field(default_factory=list)
    eventCount: int = 0


class ScoreBreakdown(BaseModel):
    """Score breakdown showing individual scoring components.

    All scoring is deterministic/lexical. No LLM or semantic model is used
    for content scoring — LLM is only used for shortlist reranking and
    report generation.
    """

    relevance: float
    bm25: float
    freshness: float
    source_authority: float
    feedbackAdjustment: Optional[float] = Field(default=None)
    feedback: Optional[FeedbackDetails] = Field(default=None)
    theme_match: Optional[ThemeMatch] = Field(default=None)
    competitor_match: Optional[CompetitorMatch] = Field(default=None)
    multi_signal_boost: Optional[MultiSignalBoost] = Field(default=None)
    filter_reason: Optional[str] = Field(default=None)
    min_relevance_threshold: Optional[float] = Field(default=None)


class ContentDetailOut(ContentItemOut):
    body: str
    score_breakdown: dict[str, Any] = Field(alias="scoreBreakdown")
    cluster_items: Optional[list[dict]] = Field(default=None, alias="clusterItems")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


def _content_item_to_out(item) -> dict:
    """Convert a ContentItem ORM object to camelCase dict."""
    linked_report_ids = []
    if item.report_id:
        linked_report_ids.append(item.report_id)

    bm25_score = item.llm_score
    breakdown = item.score_breakdown_json or {}
    if bm25_score is None and isinstance(breakdown, dict):
        scores = breakdown.get("scores")
        if isinstance(scores, dict):
            bm25_score = scores.get("bm25", scores.get("llm"))
            if isinstance(bm25_score, (int, float)):
                bm25_score = float(bm25_score)

    return {
        "id": item.id,
        "workspaceId": item.workspace_id,
        "title": item.title,
        "source": item.source_name,
        "sourceUrl": item.url,
        "publishedAt": item.published_at.isoformat() if item.published_at else None,
        "type": item.content_type,
        "relevanceScore": item.local_relevance_score,
        "bm25Score": bm25_score,
        "finalScore": item.final_score,
        "status": item.status,
        "clusterId": item.cluster_id,
        "snippet": item.summary_snippet,
        "body": item.raw_text,
        "inclusionReason": item.inclusion_reason,
        "exclusionReason": item.exclusion_reason,
        "linkedReportIds": linked_report_ids if linked_report_ids else None,
    }
