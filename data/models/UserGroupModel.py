from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, PrimaryKeyConstraint, ForeignKeyConstraint
from data.models.BaseModel import BaseModel


class UserGroupModel(BaseModel):
    """Membership: which groups a user belongs to.

    A user's effective permissions are the union of every membership's
    group role — more groups only ever add rights.
    """

    __tablename__ = "user_groups"

    user_id:  Mapped[str] = mapped_column(String, nullable=False)
    group_id: Mapped[str] = mapped_column(String, nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("user_id", "group_id"),
        ForeignKeyConstraint(["user_id"], ["users.id"]),
        ForeignKeyConstraint(["group_id"], ["groups.id"]),
    )
