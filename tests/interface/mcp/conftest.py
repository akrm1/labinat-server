"""Fixtures for MCP tests.

The MCP server bypasses auth (it runs in-process under the caller's trust), so
these fixtures only set up an isolated SQLite DB and a temp catalog/workspace,
then hand back an assembled FastMCP server plus small helpers for calling tools.
"""

import asyncio
import json

import pytest

from app import controller
from app.core.auth.Group import Group
from app.core.auth.Role import Role
from app.core.auth.Session import Session
from app.core.auth.User import User
from app.interface.mcp import auth
from app.interface.mcp.app import create_app
from data import database
from utils import logger


@pytest.fixture
def env(tmp_path):
    logger.init({"name": "test-mcp", "level": "debug", "handlers": {"console": {}}})

    db_path = tmp_path / "mcp.db"
    database.init_db({"url": f"sqlite:///{db_path}", "logging": False})
    Session.init("test-secret", "HS256", 15, 30)

    catalog_dir = tmp_path / "catalog"
    workspace_dir = tmp_path / "workspace"
    (catalog_dir / "factories").mkdir(parents=True)
    (catalog_dir / "schemas").mkdir(parents=True)
    workspace_dir.mkdir(parents=True)
    controller.init({"path": str(catalog_dir)}, {"path": str(workspace_dir)})

    yield {"tmp_path": tmp_path, "catalog_dir": catalog_dir, "workspace_dir": workspace_dir}

    database.engine.dispose()
    logger.reset()
    # The auth toggle is process-global; keep it from leaking between tests.
    auth.set_auth_enabled(False)


def mint_token(username: str, permissions: list[str]) -> str:
    """Seed a user with a role granting `permissions` and return an access token."""
    role = Role.get_or_create(f"{username}-role", permissions=permissions)
    group = Group.get_or_create(f"{username}-group", role=role)
    user = User.create(username, "pw", groups=[group])
    return Session.issue(user).access_token


@pytest.fixture
def server(env):
    return create_app()


def call(server, tool: str, **arguments):
    """Invoke a tool and return its result as parsed JSON.

    FastMCP converts a returned value into content blocks (one per list item, or
    one for a dict). We parse each block's text back into Python so tests can
    assert on native structures.
    """
    blocks = asyncio.run(server.call_tool(tool, arguments))
    return [json.loads(block.text) for block in blocks]


def call_one(server, tool: str, **arguments) -> dict:
    """Invoke a tool expected to return a single object; return that dict."""
    results = call(server, tool, **arguments)
    assert len(results) == 1, f"expected one result, got {len(results)}"
    return results[0]
