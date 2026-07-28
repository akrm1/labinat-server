from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, ForeignKeyConstraint
from data.models.BaseModel import BaseModel, TimestampMixin


class RefreshTokenModel(BaseModel, TimestampMixin):
    """A rotatable refresh token for a human user session, stored hashed.

    `created_at` (from `TimestampMixin`) marks issuance. Rotation on refresh
    sets `revoked_at` on the old row and inserts a new one.
    """

    __tablename__ = "refresh_tokens"

    id:         Mapped[str]      = mapped_column(String,   primary_key=True)
    user_id:    Mapped[str]      = mapped_column(String,   nullable=False)
    token_hash: Mapped[str]      = mapped_column(String,   nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
