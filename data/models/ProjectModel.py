from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text
from sqlalchemy.types import JSON
from data.models.BaseModel import BaseModel, TimestampMixin
from datetime import datetime, timezone
from sqlalchemy.types import DateTime


class ProjectModel(BaseModel, TimestampMixin):
    __tablename__ = "projects"

    id:          Mapped[str] = mapped_column(String,      primary_key=True)
    name:        Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text,        nullable=True)
    config:      Mapped[dict]= mapped_column(JSON,        nullable=True)
    created_at:  Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
