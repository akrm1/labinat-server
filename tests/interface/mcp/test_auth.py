"""Unit tests for the MCP token verifier and the authorize() gate."""

import asyncio

import pytest
from mcp.server.auth.provider import AccessToken
from mcp.server.fastmcp.exceptions import ToolError

from app.core.auth.Role import Role
from app.interface.mcp import auth
from tests.interface.mcp.conftest import mint_token


def verify(token: str):
    return asyncio.run(auth.LabinatTokenVerifier().verify_token(token))


def test_verifier_accepts_a_valid_token_and_exposes_permissions(env):
    token = mint_token("svc", ["catalog:read", "project:read"])
    access = verify(token)
    assert access is not None
    assert set(access.scopes) == {"catalog:read", "project:read"}


def test_verifier_rejects_a_bogus_token(env):
    assert verify("not-a-real-token") is None


def test_authorize_is_a_noop_when_auth_disabled(monkeypatch):
    auth.set_auth_enabled(False)
    monkeypatch.setattr(auth, "get_access_token", lambda: None)
    auth.authorize("catalog:write")  # does not raise


def test_authorize_denies_when_auth_enabled_but_no_identity(monkeypatch):
    auth.set_auth_enabled(True)
    monkeypatch.setattr(auth, "get_access_token", lambda: None)
    with pytest.raises(ToolError):
        auth.authorize("catalog:read")
    auth.set_auth_enabled(False)


def test_authorize_allows_matching_scope_and_wildcard(monkeypatch):
    auth.set_auth_enabled(True)
    monkeypatch.setattr(
        auth, "get_access_token",
        lambda: AccessToken(token="t", client_id="1", scopes=["catalog:read"]),
    )
    auth.authorize("catalog:read")  # matching scope

    monkeypatch.setattr(
        auth, "get_access_token",
        lambda: AccessToken(token="t", client_id="1", scopes=[Role.WILDCARD]),
    )
    auth.authorize("anything:goes")  # wildcard

    auth.set_auth_enabled(False)


def test_authorize_denies_missing_scope(monkeypatch):
    auth.set_auth_enabled(True)
    monkeypatch.setattr(
        auth, "get_access_token",
        lambda: AccessToken(token="t", client_id="1", scopes=["catalog:read"]),
    )
    with pytest.raises(ToolError) as exc:
        auth.authorize("project:write")
    assert "project:write" in str(exc.value)
    auth.set_auth_enabled(False)
