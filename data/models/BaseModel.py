from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped
from sqlalchemy import DateTime
from datetime import datetime

from utils.helpers import utcnow


class BaseModel(DeclarativeBase):
    pass


class TimestampMixin:
    # Naive UTC (see `utils.helpers.utcnow`) so these round-trip through
    # SQLite the same way as other persisted timestamps (e.g. `expires_at`),
    # and never raise a naive-vs-aware `TypeError` if compared against one.
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, onupdate=utcnow)
