from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, ForeignKeyConstraint
from data.models.BaseModel import BaseModel, TimestampMixin


class ServiceTokenModel(BaseModel, TimestampMixin):
    """A long-lived bearer token belonging to a service account, stored hashed.

    Human users authenticate with a password and get a short-lived session
    (`RefreshTokenModel`); service accounts have no password and call the API
    with one of these instead.
    """

    __tablename__ = "service_tokens"

    id:           Mapped[str]      = mapped_column(String,      primary_key=True)
    user_id:      Mapped[str]      = mapped_column(String,      nullable=False)
    name:         Mapped[str]      = mapped_column(String(100), nullable=False)
    token_hash:   Mapped[str]      = mapped_column(String,      nullable=False, unique=True)
    expires_at:   Mapped[datetime] = mapped_column(DateTime,    nullable=True)
    revoked_at:   Mapped[datetime] = mapped_column(DateTime,    nullable=True)
    last_used_at: Mapped[datetime] = mapped_column(DateTime,    nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
