"""Turn domain objects into JSON-serializable dicts for API responses."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.resources.Factory import Factory
    from app.core.resources.Frame import Frame
    from app.core.resources.Block import Block
    from app.core.Project import Project
    from app.core.auth.User import User
    from app.core.auth.Role import Role
    from app.core.auth.Group import Group
    from app.core.auth.ServiceToken import ServiceToken


def factory_to_dict(factory: "Factory") -> dict:
    return {
        "id": factory.id,
        "name": factory.name,
        "version": factory.version,
        "description": factory.spec.get("description", ""),
        "frames": list(factory.frames.keys()),
        "config": factory.config,
        "pipelines": factory.pipelines,
        "maps": factory.spec.get("maps", {}),
    }


def frame_to_dict(frame: "Frame") -> dict:
    return {
        "id": frame.id,
        "name": frame.name,
        "spec": frame.spec.data,
        "concretes": list(frame.concretes.keys()),
    }


def block_to_dict(block: "Block") -> dict:
    return {
        "id": block.id,
        "name": block.name,
        "frame": block.frame.name,
        "data": block.spec.data,
    }


def project_to_dict(project: "Project") -> dict:
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "created_at": project.created_at.isoformat(),
        "config": project.config,
        "factories": list(project.factories.keys()),
        "blocks": list(project.blocks.keys()),
    }


def user_to_dict(user: "User") -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_service": user.is_service,
        "is_active": user.is_active,
        "groups": list(user.groups.keys()),
        "permissions": sorted(user.permissions),
    }


def role_to_dict(role: "Role") -> dict:
    return {
        "id": role.id,
        "name": role.name,
        "description": role.description,
        "permissions": role.permissions,
    }


def group_to_dict(group: "Group") -> dict:
    return {
        "id": group.id,
        "name": group.name,
        "description": group.description,
        "role": group.role.name if group.role else None,
        "permissions": group.permissions,
    }


def service_token_to_dict(token: "ServiceToken") -> dict:
    payload = {
        "id": token.id,
        "user_id": token.user_id,
        "name": token.name,
        "expires_at": token.expires_at.isoformat() if token.expires_at else None,
        "revoked_at": token.revoked_at.isoformat() if token.revoked_at else None,
        "last_used_at": token.last_used_at.isoformat() if token.last_used_at else None,
        "is_active": token.is_active,
    }
    if token.secret is not None:
        payload["secret"] = token.secret
    return payload
