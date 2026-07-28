from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text
from sqlalchemy.types import JSON
from data.models.BaseModel import BaseModel, TimestampMixin


class RoleModel(BaseModel, TimestampMixin):
    """A reusable, customizable permission set.

    Groups reference a role; a user's effective permissions are the union of
    every role reachable through their group memberships (see `core.auth.User`).
    """

    __tablename__ = "roles"

    id:          Mapped[str]  = mapped_column(String,      primary_key=True)
    name:        Mapped[str]  = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str]  = mapped_column(Text,        nullable=True)
    permissions: Mapped[list] = mapped_column(JSON,        nullable=False, default=list)
