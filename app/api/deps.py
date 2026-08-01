"""Auth dependencies: resolve a bearer token to a user and gate on permissions."""

from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app import controller
from app.core.Catalog import Catalog
from app.core.Workspace import Workspace
from app.core.auth.Session import Session
from app.core.auth.ServiceToken import ServiceToken
from app.core.auth.User import User
from app.base.Tokenizer import TokenError

bearer_scheme = HTTPBearer(auto_error=True, description="Session access token or service-account token")


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> User:
    """Resolve the bearer token to a user: a human session, else a service token."""
    token = credentials.credentials

    try:
        return Session.authenticate(token)
    except TokenError:
        pass

    try:
        return ServiceToken.authenticate(token)
    except TokenError:
        pass

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_permission(permission: str) -> Callable[..., User]:
    """Build a dependency that requires `permission` on the current user."""

    def dependency(user: User = Depends(get_current_user)) -> User:
        if not user.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: {permission}",
            )
        return user

    return dependency


def get_catalog() -> Catalog:
    if controller.catalog is None:
        raise HTTPException(status_code=503, detail="Catalog not initialized")
    return controller.catalog


def get_workspace() -> Workspace:
    if controller.workspace is None:
        raise HTTPException(status_code=503, detail="Workspace not initialized")
    return controller.workspace
