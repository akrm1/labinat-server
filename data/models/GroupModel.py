from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, ForeignKeyConstraint
from data.models.BaseModel import BaseModel, TimestampMixin


class GroupModel(BaseModel, TimestampMixin):
    """An org bucket of users bound to one `RoleModel`.

    `role_id` may be null for a group created without an assigned role yet
    (contributes no permissions until one is set).
    """

    __tablename__ = "groups"

    id:          Mapped[str] = mapped_column(String,      primary_key=True)
    name:        Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text,        nullable=True)
    role_id:     Mapped[str] = mapped_column(String,      nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(["role_id"], ["roles.id"]),
    )
