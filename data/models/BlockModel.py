from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, PrimaryKeyConstraint, ForeignKeyConstraint
from sqlalchemy.types import JSON
from data.models.BaseModel import BaseModel, TimestampMixin


class BlockModel(BaseModel, TimestampMixin):
    __tablename__ = "blocks"

    project_id:      Mapped[str]  = mapped_column(String,      nullable=False)
    factory:         Mapped[str]  = mapped_column(String(100), nullable=False)
    factory_version: Mapped[str]  = mapped_column(String(50),  nullable=False)
    frame:           Mapped[str]  = mapped_column(String(100), nullable=False)
    name:            Mapped[str]  = mapped_column(String(255), nullable=False)
    data:            Mapped[dict] = mapped_column(JSON,        nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("project_id", "factory", "factory_version", "frame", "name"),
        ForeignKeyConstraint(["project_id"], ["projects.id"]),
        ForeignKeyConstraint(
            ["factory", "factory_version"],
            ["factories.name", "factories.version"]
        ),
    )
