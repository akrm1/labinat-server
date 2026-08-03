"""Authentication and authorization for the networked MCP server.

The MCP server is exposed over HTTP, so every request must present a labinat
bearer token — a human session access token or a service-account token, the same
credentials the REST API accepts. `LabinatTokenVerifier` plugs into FastMCP's
bearer-auth middleware to validate that token and surface the caller's permissions
as scopes; `authorize()` then gates individual tools on a required permission.

Authorization fails closed: when auth is enabled but no authenticated identity is
present on the call, access is denied rather than allowed.
"""

from typing import Optional

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.fastmcp.exceptions import ToolError

from app.core.auth.Role import Role
from app.interface.identity import authenticate_bearer


# Whether the running server requires authentication. Set when the server is
# assembled: HTTP serving enables it; in-process/local use (tests) leaves it off.
_auth_enabled = False


def set_auth_enabled(enabled: bool) -> None:
    global _auth_enabled
    _auth_enabled = enabled


class LabinatTokenVerifier(TokenVerifier):
    """Verify a labinat bearer token and expose the user's permissions as scopes."""

    async def verify_token(self, token: str) -> Optional[AccessToken]:
        user = authenticate_bearer(token)
        if user is None:
            return None
        return AccessToken(
            token=token,
            client_id=str(user.id),
            scopes=sorted(user.permissions),
            expires_at=None,
        )


def authorize(permission: str) -> None:
    """Require `permission` on the caller, or raise.

    A wildcard (`*`) scope grants everything. When auth is disabled the check is a
    no-op (local, trusted use). When auth is enabled but the identity is missing,
    access is denied — the check fails closed.
    """
    access = get_access_token()
    if access is None:
        if _auth_enabled:
            raise ToolError("Authentication required")
        return

    scopes = access.scopes or []
    if Role.WILDCARD in scopes or permission in scopes:
        return
    raise ToolError(f"Missing required permission: {permission}")
