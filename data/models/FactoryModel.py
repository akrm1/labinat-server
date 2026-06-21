from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, PrimaryKeyConstraint
from sqlalchemy.types import JSON
from data.models.BaseModel import BaseModel


class FactoryModel(BaseModel):
    __tablename__ = "factories"

    name:    Mapped[str]  = mapped_column(String(100), nullable=False)
    version: Mapped[str]  = mapped_column(String(50),  nullable=False)
    data:    Mapped[dict] = mapped_column(JSON,         nullable=True)

    __table_args__ = (
        PrimaryKeyConstraint("name", "version"),
    )
