from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, ForeignKey, PrimaryKeyConstraint, ForeignKeyConstraint
from data.models.BaseModel import BaseModel


class ProjectFactoryModel(BaseModel):
    __tablename__ = "project_factories"

    project_id:      Mapped[str] = mapped_column(String,      nullable=False)
    factory:         Mapped[str] = mapped_column(String(100), nullable=False)
    factory_version: Mapped[str] = mapped_column(String(50),  nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("project_id", "factory", "factory_version"),
        ForeignKeyConstraint(["project_id"], ["projects.id"]),
        ForeignKeyConstraint(
            ["factory", "factory_version"],
            ["factories.name", "factories.version"]
        ),
    )
