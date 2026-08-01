"""Auth user: human accounts and service accounts."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Union

from app.core.auth.Group import Group
from app.core.auth.Role import Role
from data.database import get_db
from data.models.RefreshTokenModel import RefreshTokenModel
from data.models.ServiceTokenModel import ServiceTokenModel
from data.models.UserGroupModel import UserGroupModel
from data.models.UserModel import UserModel
from utils import logger
from utils.helpers import asjson, generate_unique_id
from utils.security import hash_password, verify_password

if TYPE_CHECKING:
    from app.core.auth.ServiceToken import ServiceToken
    from app.core.auth.Session import Session


class UserError(Exception):
    """Raised when a user cannot be created, updated, or deleted."""


class InvalidCredentialsError(UserError):
    """Raised when a login attempt cannot be authenticated."""


class PermissionDeniedError(UserError):
    """Raised when a user lacks a required permission."""


class User:
    """A principal that can authenticate, plus everything it can do.

    Two kinds, distinguished by `is_service`:

    - **Human user** — has a password, logs in with `login()` and gets a
      `Session` (JWT access token + refresh token).
    - **Service account** — never has a password; calls `issue_token()` to
      mint a `ServiceToken` and authenticates with that instead.

    Permissions are the **union** of every group's role, so joining more
    groups only ever adds rights. Every mutation persists immediately.
    """

    def __init__(
        self,
        id: str,
        username: str,
        email: str = None,
        password_hash: str = None,
        is_service: bool = False,
        is_active: bool = True,
        groups: dict[str, Group] = None,
    ):
        self.__id: str = id
        self.__username: str = username
        self.__email: str = email
        self.__password_hash: str = password_hash
        self.__is_service: bool = is_service
        self.__is_active: bool = is_active
        self.__groups: dict[str, Group] = groups if groups is not None else {}
        logger.debug("User constructed", username=username, is_service=is_service)

    @classmethod
    def __from_record(cls, record: UserModel) -> "User":
        user = cls(
            id=record.id,
            username=record.username,
            email=record.email,
            password_hash=record.password_hash,
            is_service=record.is_service,
            is_active=record.is_active,
        )
        user.__load_groups()
        return user

    def __load_groups(self) -> None:
        with get_db() as db:
            group_ids = [
                record.group_id
                for record in db.query(UserGroupModel).filter_by(user_id=self.__id).all()
            ]

        self.__groups = {}
        for group_id in group_ids:
            group = Group.get_by_id(group_id)
            if group:
                self.__groups[group.name] = group

    @classmethod
    def create(
        cls,
        username: str,
        password: str,
        email: str = None,
        groups: list[Union[Group, str]] = None,
    ) -> "User":
        """Create a human user. Service accounts use `create_service_account`."""
        if not password:
            raise UserError(f"A password is required for user: {username}")

        user = cls.__insert(
            username=username,
            email=email,
            password_hash=hash_password(password),
            is_service=False,
        )
        logger.info("User created", username=username)

        for group in groups or []:
            user.add_to_group(group)
        return user

    @classmethod
    def create_service_account(
        cls, username: str, groups: list[Union[Group, str]] = None
    ) -> "User":
        """Create a service account: no password, ever — token access only."""
        user = cls.__insert(username=username, email=None, password_hash=None, is_service=True)
        logger.info("Service account created", username=username)

        for group in groups or []:
            user.add_to_group(group)
        return user

    @classmethod
    def __insert(cls, username: str, email: str, password_hash: str, is_service: bool) -> "User":
        user_id = generate_unique_id()
        with get_db() as db:
            if db.query(UserModel).filter_by(username=username).first():
                raise UserError(f"User already exists: {username}")

            db.add(UserModel(
                id=user_id,
                username=username,
                email=email,
                password_hash=password_hash,
                is_service=is_service,
                is_active=True,
            ))
            db.commit()

        return cls(
            id=user_id,
            username=username,
            email=email,
            password_hash=password_hash,
            is_service=is_service,
        )

    @classmethod
    def get(cls, username: str) -> Union["User", None]:
        with get_db() as db:
            record = db.query(UserModel).filter_by(username=username).first()
            if not record:
                logger.debug("User not found", username=username)
                return None
            return cls.__from_record(record)

    @classmethod
    def get_by_id(cls, user_id: str) -> Union["User", None]:
        with get_db() as db:
            record = db.query(UserModel).filter_by(id=user_id).first()
            if not record:
                logger.debug("User not found", user_id=user_id)
                return None
            return cls.__from_record(record)

    @classmethod
    def all(cls) -> dict[str, "User"]:
        """Return every user keyed by username."""
        with get_db() as db:
            records = db.query(UserModel).all()
        users = {record.username: cls.__from_record(record) for record in records}
        logger.debug("All users loaded", count=len(users))
        return users

    def delete(self) -> bool:
        """Delete this user along with its memberships and issued tokens."""
        with get_db() as db:
            record = db.query(UserModel).filter_by(id=self.__id).first()
            if not record:
                logger.warning("Delete user failed: not found", username=self.__username)
                return False

            db.query(UserGroupModel).filter_by(user_id=self.__id).delete()
            db.query(RefreshTokenModel).filter_by(user_id=self.__id).delete()
            db.query(ServiceTokenModel).filter_by(user_id=self.__id).delete()
            db.delete(record)
            db.commit()

        logger.info("User deleted", username=self.__username)
        return True

    # --- credentials -------------------------------------------------------

    def set_password(self, password: str) -> None:
        """Set this user's password. Service accounts have none by design."""
        if self.__is_service:
            raise UserError(f"Service accounts cannot have a password: {self.__username}")
        if not password:
            raise UserError("Password must not be empty")

        password_hash = hash_password(password)
        self.__update(password_hash=password_hash)
        self.__password_hash = password_hash
        logger.info("Password updated", username=self.__username)

    def change_password(self, old_password: str, new_password: str) -> None:
        """Rotate the password after re-verifying the current one."""
        if not self.verify_password(old_password):
            logger.warning("Password change rejected", username=self.__username)
            raise InvalidCredentialsError("Invalid current password")
        self.set_password(new_password)

    def verify_password(self, password: str) -> bool:
        if self.__is_service or not self.__password_hash:
            return False
        return verify_password(self.__password_hash, password)

    def login(self, password: str) -> "Session":
        """Verify the password and open a session (access + refresh tokens)."""
        from app.core.auth.Session import Session

        if self.__is_service:
            logger.warning("Login rejected for service account", username=self.__username)
            raise InvalidCredentialsError("Service accounts authenticate with a token, not a password")
        if not self.__is_active:
            logger.warning("Login rejected for inactive user", username=self.__username)
            raise InvalidCredentialsError("Invalid username or password")
        if not self.verify_password(password):
            logger.warning("Login rejected: wrong password", username=self.__username)
            raise InvalidCredentialsError("Invalid username or password")

        logger.info("User logged in", username=self.__username)
        return Session.issue(self)

    @classmethod
    def authenticate(cls, username: str, password: str) -> "Session":
        """Look up `username` and log in, without revealing whether it exists."""
        user = cls.get(username)
        if user is None:
            logger.warning("Login rejected: unknown user", username=username)
            raise InvalidCredentialsError("Invalid username or password")
        return user.login(password)

    def issue_token(self, name: str, expires_at: datetime = None) -> "ServiceToken":
        """Mint an API token for this service account (raw secret returned once)."""
        from app.core.auth.ServiceToken import ServiceToken

        return ServiceToken.issue(self, name, expires_at)

    @property
    def tokens(self) -> list["ServiceToken"]:
        from app.core.auth.ServiceToken import ServiceToken

        return ServiceToken.all_for(self)

    # --- membership and permissions ------------------------------

    def add_to_group(self, group: Union[Group, str]) -> None:
        group = self.__resolve_group(group)

        with get_db() as db:
            existing = db.query(UserGroupModel).filter_by(
                user_id=self.__id, group_id=group.id
            ).first()
            if existing:
                self.__groups[group.name] = group
                return

            db.add(UserGroupModel(user_id=self.__id, group_id=group.id))
            db.commit()

        self.__groups[group.name] = group
        logger.info("User added to group", username=self.__username, group=group.name)

    def remove_from_group(self, group: Union[Group, str]) -> None:
        group = self.__resolve_group(group)

        with get_db() as db:
            db.query(UserGroupModel).filter_by(user_id=self.__id, group_id=group.id).delete()
            db.commit()

        self.__groups.pop(group.name, None)
        logger.info("User removed from group", username=self.__username, group=group.name)

    def __resolve_group(self, group: Union[Group, str]) -> Group:
        if isinstance(group, Group):
            return group

        resolved = Group.get(group)
        if resolved is None:
            raise UserError(f"Group not found: {group}")
        return resolved

    @property
    def groups(self) -> dict[str, Group]:
        return self.__groups

    @property
    def roles(self) -> dict[str, Role]:
        """Every role reachable through this user's groups, keyed by name."""
        return {
            group.role.name: group.role
            for group in self.__groups.values()
            if group.role is not None
        }

    @property
    def permissions(self) -> set[str]:
        """Union of every group's role permissions — membership only adds rights."""
        permissions: set[str] = set()
        for role in self.roles.values():
            permissions.update(role.permissions)
        return permissions

    def has_permission(self, permission: str) -> bool:
        return any(group.has_permission(permission) for group in self.__groups.values())

    def require_permission(self, permission: str) -> None:
        if not self.has_permission(permission):
            logger.warning(
                "Permission denied", username=self.__username, permission=permission
            )
            raise PermissionDeniedError(
                f"User '{self.__username}' lacks permission '{permission}'"
            )

    # --- account state ---------------------------------------------

    def activate(self) -> None:
        self.__update(is_active=True)
        self.__is_active = True
        logger.info("User activated", username=self.__username)

    def deactivate(self) -> None:
        """Disable the account: no new logins, and existing tokens stop working."""
        self.__update(is_active=False)
        self.__is_active = False
        logger.info("User deactivated", username=self.__username)

    def set_email(self, email: str) -> None:
        self.__update(email=email)
        self.__email = email

    def __update(self, **fields) -> None:
        with get_db() as db:
            record = db.query(UserModel).filter_by(id=self.__id).first()
            if not record:
                raise UserError(f"User not found: {self.__username}")
            for key, value in fields.items():
                setattr(record, key, value)
            db.commit()

    @property
    def id(self) -> str:
        return self.__id

    @property
    def username(self) -> str:
        return self.__username

    @property
    def email(self) -> str:
        return self.__email

    @property
    def password_hash(self) -> str:
        return self.__password_hash

    @property
    def is_service(self) -> bool:
        return self.__is_service

    @property
    def is_active(self) -> bool:
        return self.__is_active

    @property
    def info(self):
        return asjson({
            "id": self.__id,
            "username": self.__username,
            "email": self.__email,
            "is_service": self.__is_service,
            "is_active": self.__is_active,
            "groups": list(self.__groups.keys()),
            "permissions": sorted(self.permissions),
        })

    def __str__(self):
        return self.info

    def __repr__(self):
        return self.__username
