"""Report and Feedback Pydantic DTOs."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


# ── Input schemas ────────────────────────────────────────────────────


class MessageSendIn(BaseModel):
    content: str = Field(min_length=1)


class ThumbIn(BaseModel):
    value: Literal["up", "down"]


class FeedbackCreateIn(BaseModel):
    type: Literal[
        "thumbs_up", "thumbs_down", "comment", "topic_preference", "source_preference"
    ]
    value: Optional[str] = None
    sentiment: Optional[Literal["positive", "negative", "neutral"]] = None
    threadId: Optional[str] = Field(default=None, alias="threadId")
    messageId: Optional[str] = Field(default=None, alias="messageId")

    model_config = {"populate_by_name": True}


# ── Output schemas ───────────────────────────────────────────────────


class MessageOut(BaseModel):
    id: str
    threadId: str = Field(alias="threadId")
    role: str
    content: str
    createdAt: str = Field(alias="createdAt")
    feedback: Optional[str] = None
    metadata: Optional[dict] = None

    model_config = {"populate_by_name": True, "from_attributes": True}


class ThreadOut(BaseModel):
    id: str
    workspaceId: str = Field(alias="workspaceId")
    title: str
    createdAt: str = Field(alias="createdAt")
    updatedAt: Optional[str] = Field(None, alias="updatedAt")
    status: str
    periodStart: Optional[str] = Field(None, alias="periodStart")
    periodEnd: Optional[str] = Field(None, alias="periodEnd")
    runId: Optional[str] = Field(None, alias="runId")
    messageCount: int = Field(alias="messageCount")
    latestHighlight: Optional[str] = Field(None, alias="latestHighlight")

    model_config = {"populate_by_name": True, "from_attributes": True}


class SummaryOut(BaseModel):
    id: str
    threadId: str = Field(alias="threadId")
    title: str
    status: str
    periodStart: Optional[str] = Field(None, alias="periodStart")
    periodEnd: Optional[str] = Field(None, alias="periodEnd")
    createdAt: str = Field(alias="createdAt")
    runId: Optional[str] = Field(None, alias="runId")
    messageCount: int = Field(alias="messageCount")

    model_config = {"populate_by_name": True, "from_attributes": True}


class FeedbackEventOut(BaseModel):
    id: str
    workspaceId: str = Field(alias="workspaceId")
    threadId: Optional[str] = Field(None, alias="threadId")
    messageId: Optional[str] = Field(None, alias="messageId")
    type: str
    value: Optional[str] = None
    sentiment: Optional[str] = None
    createdAt: str = Field(alias="createdAt")
    reportTitle: Optional[str] = Field(None, alias="reportTitle")
    messageExcerpt: Optional[str] = Field(None, alias="messageExcerpt")
    influencedReportCount: Optional[int] = Field(None, alias="influencedReportCount")

    model_config = {"populate_by_name": True, "from_attributes": True}


class FeedbackSummaryOut(BaseModel):
    totalEvents: int = Field(alias="totalEvents")
    thumbsUp: int = Field(alias="thumbsUp")
    thumbsDown: int = Field(alias="thumbsDown")
    netSentiment: int = Field(alias="netSentiment")
    topicPreferences: list[dict] = Field(default_factory=list, alias="topicPreferences")
    sourcePreferences: list[dict] = Field(
        default_factory=list, alias="sourcePreferences"
    )
    reportStylePreferences: list[dict] = Field(
        default_factory=list, alias="reportStylePreferences"
    )

    model_config = {"populate_by_name": True, "from_attributes": True}


# ── Conversion helpers ───────────────────────────────────────────────


def _report_to_thread_out(
    report, message_count: int = 0, latest_highlight: str | None = None
) -> dict:
    """Convert a Report ORM object to ThreadOut-compatible camelCase dict."""
    return {
        "id": report.id,
        "workspaceId": report.workspace_id,
        "title": report.title,
        "createdAt": report.created_at.isoformat() if report.created_at else None,
        "updatedAt": report.updated_at.isoformat() if report.updated_at else None,
        "status": report.status,
        "periodStart": report.period_start.isoformat() if report.period_start else None,
        "periodEnd": report.period_end.isoformat() if report.period_end else None,
        "runId": report.run_id,
        "messageCount": message_count,
        "latestHighlight": latest_highlight,
    }


def _report_to_summary_out(report, message_count: int = 0) -> dict:
    """Convert a Report ORM object to SummaryOut-compatible camelCase dict."""
    return {
        "id": report.id,
        "threadId": report.id,
        "title": report.title,
        "status": report.status,
        "periodStart": report.period_start.isoformat() if report.period_start else None,
        "periodEnd": report.period_end.isoformat() if report.period_end else None,
        "createdAt": report.created_at.isoformat() if report.created_at else None,
        "runId": report.run_id,
        "messageCount": message_count,
    }


def _message_to_out(msg) -> dict:
    """Convert a ReportMessage ORM object to camelCase dict."""
    return {
        "id": msg.id,
        "threadId": msg.thread_id,
        "role": msg.role,
        "content": msg.content,
        "createdAt": msg.created_at.isoformat() if msg.created_at else None,
        "feedback": msg.feedback,
        "metadata": msg.metadata_json,
    }


def _feedback_event_to_out(
    event, report_title: str | None = None, message_excerpt: str | None = None
) -> dict:
    """Convert a FeedbackEvent ORM object to camelCase dict."""
    return {
        "id": event.id,
        "workspaceId": event.workspace_id,
        "threadId": event.thread_id,
        "messageId": event.message_id,
        "type": event.feedback_type,
        "value": event.value,
        "sentiment": event.sentiment,
        "createdAt": event.created_at.isoformat() if event.created_at else None,
        "reportTitle": report_title,
        "messageExcerpt": message_excerpt,
        "influencedReportCount": None,
    }
