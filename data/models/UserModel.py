from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean
from data.models.BaseModel import BaseModel, TimestampMixin


class UserModel(BaseModel, TimestampMixin):
    """A principal that can authenticate.

    Human users authenticate with a password and get a `RefreshTokenModel`
    session. Service accounts (`is_service=True`) never have a password —
    they authenticate with a `ServiceTokenModel` token only.
    """

    __tablename__ = "users"

    id:            Mapped[str]  = mapped_column(String,      primary_key=True)
    username:      Mapped[str]  = mapped_column(String(100), nullable=False, unique=True)
    email:         Mapped[str]  = mapped_column(String(255), nullable=True,  unique=True)
    password_hash: Mapped[str]  = mapped_column(String,      nullable=True)
    is_service:    Mapped[bool] = mapped_column(Boolean,     nullable=False, default=False)
    is_active:     Mapped[bool] = mapped_column(Boolean,     nullable=False, default=True)
