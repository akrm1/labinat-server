"""Auth role: a named, customizable set of permissions."""

from __future__ import annotations

from typing import Union

from data.database import get_db
from data.models.GroupModel import GroupModel
from data.models.RoleModel import RoleModel
from utils import logger
from utils.helpers import asjson, generate_unique_id


class RoleError(Exception):
    """Raised when a role cannot be created, updated, or deleted."""


class Role:
    """A reusable permission set that groups bind to.

    Permissions are plain strings (e.g. `catalog:write`); the wildcard `*`
    grants everything. Roles are data — created and edited at runtime, never
    hardcoded. Every mutation persists immediately.
    """

    WILDCARD = "*"

    def __init__(self, id: str, name: str, permissions: list[str] = None, description: str = ""):
        self.__id: str = id
        self.__name: str = name
        self.__permissions: list[str] = list(permissions or [])
        self.__description: str = description
        logger.debug("Role constructed", role=name, permissions=self.__permissions)

    @classmethod
    def __from_record(cls, record: RoleModel) -> "Role":
        return cls(
            id=record.id,
            name=record.name,
            permissions=record.permissions,
            description=record.description or "",
        )

    @classmethod
    def create(cls, name: str, permissions: list[str] = None, description: str = "") -> "Role":
        role_id = generate_unique_id()
        with get_db() as db:
            if db.query(RoleModel).filter_by(name=name).first():
                raise RoleError(f"Role already exists: {name}")

            db.add(RoleModel(
                id=role_id,
                name=name,
                description=description,
                permissions=list(permissions or []),
            ))
            db.commit()

        logger.info("Role created", role=name, permissions=list(permissions or []))
        return cls(id=role_id, name=name, permissions=permissions, description=description)

    @classmethod
    def get(cls, name: str) -> Union["Role", None]:
        with get_db() as db:
            record = db.query(RoleModel).filter_by(name=name).first()
            if not record:
                logger.debug("Role not found", role=name)
                return None
            return cls.__from_record(record)

    @classmethod
    def get_by_id(cls, role_id: str) -> Union["Role", None]:
        with get_db() as db:
            record = db.query(RoleModel).filter_by(id=role_id).first()
            if not record:
                logger.debug("Role not found", role_id=role_id)
                return None
            return cls.__from_record(record)

    @classmethod
    def get_or_create(cls, name: str, permissions: list[str] = None, description: str = "") -> "Role":
        role = cls.get(name)
        return role if role else cls.create(name, permissions, description)

    @classmethod
    def all(cls) -> dict[str, "Role"]:
        """Return every role keyed by name."""
        with get_db() as db:
            roles = {record.name: cls.__from_record(record) for record in db.query(RoleModel).all()}
        logger.debug("All roles loaded", count=len(roles))
        return roles

    def delete(self) -> bool:
        """Delete this role. Fails while a group still references it."""
        with get_db() as db:
            record = db.query(RoleModel).filter_by(id=self.__id).first()
            if not record:
                logger.warning("Delete role failed: not found", role=self.__name)
                return False

            group_record = db.query(GroupModel).filter_by(role_id=self.__id).first()
            if group_record:
                raise RoleError(
                    f"Role '{self.__name}' is still assigned to group '{group_record.name}'"
                )

            db.delete(record)
            db.commit()

        logger.info("Role deleted", role=self.__name)
        return True

    def set_permissions(self, permissions: list[str]) -> None:
        """Replace this role's permission list."""
        self.__permissions = list(permissions or [])
        self.__persist()
        logger.info("Role permissions updated", role=self.__name, permissions=self.__permissions)

    def grant(self, permission: str) -> None:
        if permission in self.__permissions:
            return
        self.__permissions.append(permission)
        self.__persist()
        logger.info("Role permission granted", role=self.__name, permission=permission)

    def revoke(self, permission: str) -> None:
        if permission not in self.__permissions:
            return
        self.__permissions.remove(permission)
        self.__persist()
        logger.info("Role permission revoked", role=self.__name, permission=permission)

    def set_description(self, description: str) -> None:
        self.__description = description
        self.__persist()

    def has_permission(self, permission: str) -> bool:
        return self.WILDCARD in self.__permissions or permission in self.__permissions

    def __persist(self) -> None:
        with get_db() as db:
            record = db.query(RoleModel).filter_by(id=self.__id).first()
            if not record:
                raise RoleError(f"Role not found: {self.__name}")
            record.description = self.__description
            record.permissions = list(self.__permissions)
            db.commit()

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
    def permissions(self) -> list[str]:
        return list(self.__permissions)

    @property
    def info(self):
        return asjson({
            "id": self.__id,
            "name": self.__name,
            "description": self.__description,
            "permissions": self.__permissions,
        })

    def __str__(self):
        return self.info

    def __repr__(self):
        return self.__name
