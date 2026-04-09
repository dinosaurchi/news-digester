"""FeedSource Pydantic DTOs."""

from typing import Literal, Optional

from pydantic import BaseModel, Field, ConfigDict


class FeedCreate(BaseModel):
    name: str = Field(min_length=1)
    url: str = Field(min_length=1)
    type: Literal["rss", "website", "competitor", "blog"]
    cadence: Literal["hourly", "daily", "weekly"] = "daily"
    tags: list[str] = Field(default_factory=list)


class FeedUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1)
    url: Optional[str] = Field(default=None, min_length=1)
    type: Optional[Literal["rss", "website", "competitor", "blog"]] = None
    cadence: Optional[Literal["hourly", "daily", "weekly"]] = None
    tags: Optional[list[str]] = None


class FeedOut(BaseModel):
    id: str
    workspace_id: str = Field(alias="workspaceId")
    name: str
    url: str
    type: str
    status: str
    last_fetched_at: Optional[str] = Field(default=None, alias="lastFetchedAt")
    last_error: Optional[str] = Field(default=None, alias="lastError")
    cadence: str
    tags: list[str] = Field(default_factory=list)
    created_at: Optional[str] = Field(default=None, alias="createdAt")
    updated_at: Optional[str] = Field(default=None, alias="updatedAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


def _feed_to_out(feed) -> dict:
    """Convert a FeedSource ORM object to camelCase dict."""
    return {
        "id": feed.id,
        "workspaceId": feed.workspace_id,
        "name": feed.name,
        "url": feed.url,
        "type": feed.type,
        "status": feed.status,
        "lastFetchedAt": feed.last_fetched_at.isoformat()
        if feed.last_fetched_at
        else None,
        "lastError": feed.last_error,
        "cadence": feed.cadence,
        "tags": feed.tags or [],
        "createdAt": feed.created_at.isoformat() if feed.created_at else None,
        "updatedAt": feed.updated_at.isoformat() if feed.updated_at else None,
    }
