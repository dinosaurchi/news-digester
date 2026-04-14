"""Content Pydantic DTOs."""

from typing import Optional

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
    llm_score: Optional[float] = Field(default=None, alias="llmScore")
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


class ScoreBreakdown(BaseModel):
    relevance: float
    llm: float
    freshness: float
    source_authority: float


class ContentDetailOut(ContentItemOut):
    body: str
    score_breakdown: ScoreBreakdown = Field(alias="scoreBreakdown")
    cluster_items: Optional[list[dict]] = Field(default=None, alias="clusterItems")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


def _content_item_to_out(item) -> dict:
    """Convert a ContentItem ORM object to camelCase dict."""
    linked_report_ids = []
    if item.report_id:
        linked_report_ids.append(item.report_id)

    llm_score = item.llm_score
    breakdown = item.score_breakdown_json or {}
    if llm_score is None and isinstance(breakdown, dict):
        scores = breakdown.get("scores")
        if isinstance(scores, dict):
            bm25_score = scores.get("bm25", scores.get("llm"))
            if isinstance(bm25_score, (int, float)):
                llm_score = float(bm25_score)

    return {
        "id": item.id,
        "workspaceId": item.workspace_id,
        "title": item.title,
        "source": item.source_name,
        "sourceUrl": item.url,
        "publishedAt": item.published_at.isoformat() if item.published_at else None,
        "type": item.content_type,
        "relevanceScore": item.local_relevance_score,
        "llmScore": llm_score,
        "finalScore": item.final_score,
        "status": item.status,
        "clusterId": item.cluster_id,
        "snippet": item.summary_snippet,
        "body": item.raw_text,
        "inclusionReason": item.inclusion_reason,
        "exclusionReason": item.exclusion_reason,
        "linkedReportIds": linked_report_ids if linked_report_ids else None,
    }
