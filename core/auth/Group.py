"""Auth group: a bucket of users bound to one role."""

from __future__ import annotations

from typing import TYPE_CHECKING, Union

from core.auth.Role import Role
from data.database import get_db
from data.models.GroupModel import GroupModel
from data.models.UserGroupModel import UserGroupModel
from utils import logger
from utils.helpers import asjson, generate_unique_id

if TYPE_CHECKING:
    from core.auth.User import User


class GroupError(Exception):
    """Raised when a group cannot be created, updated, or deleted."""


class Group:
    """Users are attached to groups; each group grants one role.

    A group without a role grants nothing. Every mutation persists
    immediately.
    """

    def __init__(self, id: str, name: str, role: Role = None, description: str = ""):
        self.__id: str = id
        self.__name: str = name
        self.__role: Role = role
        self.__description: str = description
        logger.debug("Group constructed", group=name, role=role.name if role else None)

    @classmethod
    def __from_record(cls, record: GroupModel) -> "Group":
        role = Role.get_by_id(record.role_id) if record.role_id else None
        return cls(
            id=record.id,
            name=record.name,
            role=role,
            description=record.description or "",
        )

    @classmethod
    def __resolve_role(cls, role: Union[Role, str, None]) -> Union[Role, None]:
        if role is None or isinstance(role, Role):
            return role

        resolved = Role.get(role)
        if resolved is None:
            raise GroupError(f"Role not found: {role}")
        return resolved

    @classmethod
    def create(cls, name: str, role: Union[Role, str] = None, description: str = "") -> "Group":
        role = cls.__resolve_role(role)
        group_id = generate_unique_id()

        with get_db() as db:
            if db.query(GroupModel).filter_by(name=name).first():
                raise GroupError(f"Group already exists: {name}")

            db.add(GroupModel(
                id=group_id,
                name=name,
                description=description,
                role_id=role.id if role else None,
            ))
            db.commit()

        logger.info("Group created", group=name, role=role.name if role else None)
        return cls(id=group_id, name=name, role=role, description=description)

    @classmethod
    def get(cls, name: str) -> Union["Group", None]:
        with get_db() as db:
            record = db.query(GroupModel).filter_by(name=name).first()
            if not record:
                logger.debug("Group not found", group=name)
                return None
            return cls.__from_record(record)

    @classmethod
    def get_by_id(cls, group_id: str) -> Union["Group", None]:
        with get_db() as db:
            record = db.query(GroupModel).filter_by(id=group_id).first()
            if not record:
                logger.debug("Group not found", group_id=group_id)
                return None
            return cls.__from_record(record)

    @classmethod
    def get_or_create(cls, name: str, role: Union[Role, str] = None, description: str = "") -> "Group":
        group = cls.get(name)
        return group if group else cls.create(name, role, description)

    @classmethod
    def all(cls) -> dict[str, "Group"]:
        """Return every group keyed by name."""
        with get_db() as db:
            records = db.query(GroupModel).all()
        groups = {record.name: cls.__from_record(record) for record in records}
        logger.debug("All groups loaded", count=len(groups))
        return groups

    def delete(self) -> bool:
        """Delete this group and every membership pointing at it."""
        with get_db() as db:
            record = db.query(GroupModel).filter_by(id=self.__id).first()
            if not record:
                logger.warning("Delete group failed: not found", group=self.__name)
                return False

            db.query(UserGroupModel).filter_by(group_id=self.__id).delete()
            db.delete(record)
            db.commit()

        logger.info("Group deleted", group=self.__name)
        return True

    def set_role(self, role: Union[Role, str, None]) -> None:
        """Bind this group to a role (or `None` to grant nothing)."""
        role = self.__resolve_role(role)

        with get_db() as db:
            record = db.query(GroupModel).filter_by(id=self.__id).first()
            if not record:
                raise GroupError(f"Group not found: {self.__name}")
            record.role_id = role.id if role else None
            db.commit()

        self.__role = role
        logger.info("Group role updated", group=self.__name, role=role.name if role else None)

    def set_description(self, description: str) -> None:
        with get_db() as db:
            record = db.query(GroupModel).filter_by(id=self.__id).first()
            if not record:
                raise GroupError(f"Group not found: {self.__name}")
            record.description = description
            db.commit()
        self.__description = description

    def add_member(self, user: "User") -> None:
        user.add_to_group(self)

    def remove_member(self, user: "User") -> None:
        user.remove_from_group(self)

    @property
    def members(self) -> dict[str, "User"]:
        """Every user in this group, keyed by username."""
        from core.auth.User import User

        with get_db() as db:
            user_ids = [
                record.user_id
                for record in db.query(UserGroupModel).filter_by(group_id=self.__id).all()
            ]

        members = {}
        for user_id in user_ids:
            user = User.get_by_id(user_id)
            if user:
                members[user.username] = user
        return members

    def has_permission(self, permission: str) -> bool:
        return self.__role.has_permission(permission) if self.__role else False

    @property
    def id(self) -> str:
        return self.__id

    @property
    def name(self) -> str:
        return self.__name

    @property
    def description(self) -> str:
        return self.__description

    @property
    def role(self) -> Union[Role, None]:
        return self.__role

    @property
    def permissions(self) -> list[str]:
        return self.__role.permissions if self.__role else []

    @property
    def info(self):
        return asjson({
            "id": self.__id,
            "name": self.__name,
            "description": self.__description,
            "role": self.__role.name if self.__role else None,
            "permissions": self.permissions,
        })

    def __str__(self):
        return self.info

    def __repr__(self):
        return self.__name
