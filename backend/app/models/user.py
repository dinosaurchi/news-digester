"""User identity model."""

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.workspace import _now, _uuid


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    username: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(500), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="admin")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    created_at: Mapped[str] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[str | None] = mapped_column(
        DateTime, default=_now, onupdate=_now
    )
