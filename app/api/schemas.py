"""Pydantic request/response models. These drive validation and the OpenAPI docs."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


# --- auth -----------------------------------------------------------------

class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


# --- catalog: factories & frames -----------------------------------------

class FactoryCreateRequest(BaseModel):
    name: str = Field(..., description="Factory name; must not contain '.' or ':'")
    version: str
    data: dict[str, Any] = Field(default_factory=dict, description="Factory spec")
    frames: list[str] = Field(default_factory=list, description="Frame names to scaffold")


class FactoryUpdateRequest(BaseModel):
    data: dict[str, Any]


class FrameCreateRequest(BaseModel):
    name: str = Field(..., description="Frame name; must not contain '.'")
    data: dict[str, Any] = Field(default_factory=dict, description="Frame spec")


class FrameUpdateRequest(BaseModel):
    data: dict[str, Any]


# --- workspace: projects & blocks ----------------------------------------

class FactoryRef(BaseModel):
    name: str
    version: str


class ProjectCreateRequest(BaseModel):
    name: str
    description: str = ""
    config: dict[str, Any] = Field(default_factory=dict)
    factories: list[FactoryRef] = Field(default_factory=list)


class AddFactoryRequest(BaseModel):
    name: str
    version: str


class BlockCreateRequest(BaseModel):
    frame_id: str = Field(..., description="'<factory>.<frame>'")
    name: str
    data: dict[str, Any] = Field(default_factory=dict)


class BlockNamesRequest(BaseModel):
    names: list[str]


# --- RBAC admin -----------------------------------------------------------

class UserCreateRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    groups: list[str] = Field(default_factory=list)


class ServiceAccountCreateRequest(BaseModel):
    username: str
    groups: list[str] = Field(default_factory=list)


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str


class GroupMembershipRequest(BaseModel):
    group: str


class RoleCreateRequest(BaseModel):
    name: str
    permissions: list[str] = Field(default_factory=list)
    description: str = ""


class RolePermissionsRequest(BaseModel):
    permissions: list[str]


class GroupCreateRequest(BaseModel):
    name: str
    role: Optional[str] = None
    description: str = ""


class GroupRoleRequest(BaseModel):
    role: Optional[str] = None


class ServiceTokenCreateRequest(BaseModel):
    name: str
    expires_at: Optional[str] = Field(None, description="ISO 8601 timestamp")


# --- generic --------------------------------------------------------------

class MessageResponse(BaseModel):
    message: str
