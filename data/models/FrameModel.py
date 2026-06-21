from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, PrimaryKeyConstraint, ForeignKeyConstraint
from sqlalchemy.types import JSON
from data.models.BaseModel import BaseModel


class FrameModel(BaseModel):
    __tablename__ = "frames"

    factory:         Mapped[str]  = mapped_column(String(100), nullable=False)
    factory_version: Mapped[str]  = mapped_column(String(50),  nullable=False)
    name:            Mapped[str]  = mapped_column(String(100), nullable=False)
    data:            Mapped[dict] = mapped_column(JSON,         nullable=True)

    __table_args__ = (
        PrimaryKeyConstraint("factory", "factory_version", "name"),
        ForeignKeyConstraint(
            ["factory", "factory_version"],
            ["factories.name", "factories.version"]
        ),
    )
