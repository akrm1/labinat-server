"""RBAC administration: users, service accounts, roles, and groups."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from app.api import schemas
from app.api.deps import require_permission
from app.api.serializers import (
    user_to_dict,
    role_to_dict,
    group_to_dict,
    service_token_to_dict,
)
from app.core.auth.User import User
from app.core.auth.Role import Role
from app.core.auth.Group import Group
from app.core.auth.ServiceToken import ServiceToken

router = APIRouter(prefix="/admin", tags=["admin"])

READ = "admin:read"
WRITE = "admin:write"


def _get_user(username: str) -> User:
    user = User.get(username)
    if user is None:
        raise HTTPException(status_code=404, detail=f"User not found: {username}")
    return user


# --- users ----------------------------------------------------------------

@router.get("/users")
def list_users(_=Depends(require_permission(READ))):
    return [user_to_dict(u) for u in User.all().values()]


@router.post("/users", status_code=201)
def create_user(body: schemas.UserCreateRequest, _=Depends(require_permission(WRITE))):
    user = User.create(body.username, body.password, email=body.email, groups=body.groups or None)
    return user_to_dict(user)


@router.post("/service-accounts", status_code=201)
def create_service_account(body: schemas.ServiceAccountCreateRequest, _=Depends(require_permission(WRITE))):
    user = User.create_service_account(body.username, groups=body.groups or None)
    return user_to_dict(user)


@router.get("/users/{username}")
def get_user(username: str, _=Depends(require_permission(READ))):
    return user_to_dict(_get_user(username))


@router.delete("/users/{username}")
def delete_user(username: str, _=Depends(require_permission(WRITE))):
    _get_user(username).delete()
    return {"message": "user deleted"}


@router.post("/users/{username}/activate")
def activate_user(username: str, _=Depends(require_permission(WRITE))):
    _get_user(username).activate()
    return {"message": "user activated"}


@router.post("/users/{username}/deactivate")
def deactivate_user(username: str, _=Depends(require_permission(WRITE))):
    _get_user(username).deactivate()
    return {"message": "user deactivated"}


@router.post("/users/{username}/groups")
def add_user_to_group(username: str, body: schemas.GroupMembershipRequest, _=Depends(require_permission(WRITE))):
    _get_user(username).add_to_group(body.group)
    return {"message": "user added to group"}


@router.delete("/users/{username}/groups/{group}")
def remove_user_from_group(username: str, group: str, _=Depends(require_permission(WRITE))):
    _get_user(username).remove_from_group(group)
    return {"message": "user removed from group"}


# --- service tokens -------------------------------------------------------

@router.get("/users/{username}/tokens")
def list_tokens(username: str, _=Depends(require_permission(READ))):
    return [service_token_to_dict(t) for t in _get_user(username).tokens]


@router.post("/users/{username}/tokens", status_code=201)
def issue_token(username: str, body: schemas.ServiceTokenCreateRequest, _=Depends(require_permission(WRITE))):
    expires_at = datetime.fromisoformat(body.expires_at) if body.expires_at else None
    token = _get_user(username).issue_token(body.name, expires_at)
    return service_token_to_dict(token)


@router.delete("/users/{username}/tokens/{name}")
def revoke_token(username: str, name: str, _=Depends(require_permission(WRITE))):
    token = ServiceToken.get(_get_user(username), name)
    if token is None:
        raise HTTPException(status_code=404, detail=f"Token not found: {name}")
    token.revoke()
    return {"message": "token revoked"}


# --- roles ----------------------------------------------------------------

@router.get("/roles")
def list_roles(_=Depends(require_permission(READ))):
    return [role_to_dict(r) for r in Role.all().values()]


@router.post("/roles", status_code=201)
def create_role(body: schemas.RoleCreateRequest, _=Depends(require_permission(WRITE))):
    role = Role.create(body.name, permissions=body.permissions, description=body.description)
    return role_to_dict(role)


@router.get("/roles/{name}")
def get_role(name: str, _=Depends(require_permission(READ))):
    role = Role.get(name)
    if role is None:
        raise HTTPException(status_code=404, detail=f"Role not found: {name}")
    return role_to_dict(role)


@router.delete("/roles/{name}")
def delete_role(name: str, _=Depends(require_permission(WRITE))):
    role = Role.get(name)
    if role is None:
        raise HTTPException(status_code=404, detail=f"Role not found: {name}")
    role.delete()
    return {"message": "role deleted"}


@router.put("/roles/{name}/permissions")
def set_role_permissions(name: str, body: schemas.RolePermissionsRequest, _=Depends(require_permission(WRITE))):
    role = Role.get(name)
    if role is None:
        raise HTTPException(status_code=404, detail=f"Role not found: {name}")
    role.set_permissions(body.permissions)
    return role_to_dict(role)


# --- groups ---------------------------------------------------------------

@router.get("/groups")
def list_groups(_=Depends(require_permission(READ))):
    return [group_to_dict(g) for g in Group.all().values()]


@router.post("/groups", status_code=201)
def create_group(body: schemas.GroupCreateRequest, _=Depends(require_permission(WRITE))):
    group = Group.create(body.name, role=body.role, description=body.description)
    return group_to_dict(group)


@router.get("/groups/{name}")
def get_group(name: str, _=Depends(require_permission(READ))):
    group = Group.get(name)
    if group is None:
        raise HTTPException(status_code=404, detail=f"Group not found: {name}")
    return group_to_dict(group)


@router.delete("/groups/{name}")
def delete_group(name: str, _=Depends(require_permission(WRITE))):
    group = Group.get(name)
    if group is None:
        raise HTTPException(status_code=404, detail=f"Group not found: {name}")
    group.delete()
    return {"message": "group deleted"}


@router.put("/groups/{name}/role")
def set_group_role(name: str, body: schemas.GroupRoleRequest, _=Depends(require_permission(WRITE))):
    group = Group.get(name)
    if group is None:
        raise HTTPException(status_code=404, detail=f"Group not found: {name}")
    group.set_role(body.role)
    return group_to_dict(group)
