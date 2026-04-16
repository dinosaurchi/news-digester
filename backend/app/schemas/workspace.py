from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional


# ── Schedule sub-schema ──────────────────────────────────────────────


class ScheduleSchema(BaseModel):
    enabled: bool = False
    frequency: str = Field("daily", pattern=r"^(daily|twice_daily|weekly|monthly)$")
    time_of_day: str = Field("08:00", alias="timeOfDay")
    timezone: str = "UTC"

    model_config = {"populate_by_name": True, "from_attributes": True}


class ThresholdsSchema(BaseModel):
    min_relevance_score: float = Field(0.65, alias="minRelevanceScore")
    min_final_score: float = Field(0.70, alias="minFinalScore")
    max_articles_per_report: int = Field(15, alias="maxArticlesPerReport")
    trusted_domains: list[str] | None = Field(None, alias="trustedDomains")
    scoring_weights: dict[str, float] | None = Field(None, alias="scoringWeights")
    content_type_weights: dict[str, float] | None = Field(
        None, alias="contentTypeWeights"
    )
    clustering_similarity_threshold: float | None = Field(
        None, alias="clusteringSimilarityThreshold"
    )
    clustering_domain_title_threshold: float | None = Field(
        None, alias="clusteringDomainTitleThreshold"
    )

    model_config = {"populate_by_name": True, "from_attributes": True, "extra": "allow"}

    def to_canonical_dict(self) -> dict:
        """Return a snake_case dict suitable for persistence and scorer consumption.

        The scorer reads ``min_relevance_score``, ``min_final_score``,
        ``trusted_domains``, ``scoring_weights``, ``content_type_weights``,
        etc.  This method ensures those keys are always present regardless of
        whether the input used camelCase aliases or snake_case field names.
        """
        return self.model_dump(by_alias=False)


class RetentionSchema(BaseModel):
    content_days: int = Field(90, alias="contentDays")
    report_days: int = Field(365, alias="reportDays")
    run_history_days: int = Field(180, alias="runHistoryDays")

    model_config = {"populate_by_name": True, "from_attributes": True}


class EmailDeliverySchema(BaseModel):
    enabled: bool = False
    recipients: list[str] = Field(default_factory=list)
    subject_prefix: str = Field("[Intel Report]", alias="subjectPrefix")

    model_config = {"populate_by_name": True, "from_attributes": True}


# ── Workspace DTOs ───────────────────────────────────────────────────


class WorkspaceCreate(BaseModel):
    name: str
    customer: str
    status: str = "active"


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = None
    customer: Optional[str] = None
    status: Optional[str] = None


class WorkspaceOut(BaseModel):
    id: str
    name: str
    customer: str
    status: str
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    feed_count: int = Field(0, alias="feedCount")
    last_report_at: Optional[datetime] = Field(None, alias="lastReportAt")
    next_run_at: Optional[datetime] = Field(None, alias="nextRunAt")

    model_config = {"populate_by_name": True, "from_attributes": True}


# ── WorkspaceProfile DTOs ────────────────────────────────────────────


class WorkspaceProfileIn(BaseModel):
    business_name: Optional[str] = Field(None, alias="businessName", min_length=2)
    description: Optional[str] = None
    products: list[str] = Field(default_factory=list)
    competitors: list[str] = Field(default_factory=list)
    priority_themes: list[str] = Field(default_factory=list, alias="priorityThemes")
    excluded_topics: list[str] = Field(default_factory=list, alias="excludedTopics")
    notes: Optional[str] = None

    model_config = {"populate_by_name": True}


class WorkspaceProfileOut(BaseModel):
    id: str
    workspace_id: str = Field(alias="workspaceId")
    business_name: str = Field("", alias="businessName")
    description: str = ""
    products: list[str] = Field(default_factory=list)
    competitors: list[str] = Field(default_factory=list)
    priority_themes: list[str] = Field(default_factory=list, alias="priorityThemes")
    excluded_topics: list[str] = Field(default_factory=list, alias="excludedTopics")
    notes: str = ""
    updated_at: Optional[datetime] = Field(None, alias="updatedAt")

    model_config = {"populate_by_name": True, "from_attributes": True}


# ── WorkspaceSettings DTOs ───────────────────────────────────────────


class WorkspaceSettingsIn(BaseModel):
    schedule: Optional[ScheduleSchema] = None
    report_style: Optional[str] = Field(None, alias="reportStyle")
    thresholds: Optional[ThresholdsSchema] = None
    retention: Optional[RetentionSchema] = None
    email_delivery: Optional[EmailDeliverySchema] = Field(None, alias="emailDelivery")

    model_config = {"populate_by_name": True}


class WorkspaceSettingsOut(BaseModel):
    id: str
    workspace_id: str = Field(alias="workspaceId")
    schedule: ScheduleSchema = Field(default_factory=ScheduleSchema)
    report_style: str = Field("detailed", alias="reportStyle")
    thresholds: ThresholdsSchema = Field(default_factory=ThresholdsSchema)
    retention: RetentionSchema = Field(default_factory=RetentionSchema)
    email_delivery: EmailDeliverySchema = Field(
        default_factory=EmailDeliverySchema, alias="emailDelivery"
    )
    updated_at: Optional[datetime] = Field(None, alias="updatedAt")

    model_config = {"populate_by_name": True, "from_attributes": True}
