"""Resolve a bearer token to the user behind it.

Shared by every surface: the REST API's auth dependency and the MCP server's
token verifier both call `authenticate_bearer`, so the two accept the exact same
credentials — a human session access token or a service-account token.
"""

from typing import Optional

from app.base.Tokenizer import TokenError
from app.core.auth.ServiceToken import ServiceToken
from app.core.auth.Session import Session
from app.core.auth.User import User


def authenticate_bearer(token: str) -> Optional[User]:
    """Return the user for a bearer token: a human session, else a service token.

    Returns None when the token matches neither, letting each surface decide how
    to signal the failure (HTTP 401, MCP auth error, ...).
    """
    for resolver in (Session.authenticate, ServiceToken.authenticate):
        try:
            return resolver(token)
        except TokenError:
            continue
    return None
