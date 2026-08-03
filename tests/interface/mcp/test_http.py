"""End-to-end test of the unified server: REST + MCP on one app/port.

Serves the composed app (`app.server.create()`) on an ephemeral port in a
background thread, then confirms both surfaces answer there — the REST API under
its routes and the MCP server under `/mcp` — with the same bearer auth and RBAC
enforced on each.
"""

import asyncio
import contextlib
import socket
import threading
import time

import httpx
import pytest
import uvicorn
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from app import server
from tests.interface.mcp.conftest import mint_token


def _free_port() -> int:
    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@contextlib.contextmanager
def _running(app, port: int):
    uv = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=uv.run, daemon=True)
    thread.start()
    try:
        deadline = time.time() + 10
        while not uv.started and time.time() < deadline:
            time.sleep(0.05)
        assert uv.started, "server did not start in time"
        yield
    finally:
        uv.should_exit = True
        thread.join(timeout=5)


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _mcp_call(url: str, token: str, tool: str, arguments: dict):
    async with streamablehttp_client(url, headers=_bearer(token)) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return await session.call_tool(tool, arguments)


async def _mcp_list_tools(url: str, token: str):
    async with streamablehttp_client(url, headers=_bearer(token)) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return await session.list_tools()


def test_unified_server_serves_rest_and_mcp_on_one_port(env):
    admin = mint_token("admin", ["*"])
    reader = mint_token("reader", ["catalog:read", "project:read"])

    app = server.create()
    port = _free_port()
    base = f"http://127.0.0.1:{port}"
    mcp_url = f"{base}/mcp"

    with _running(app, port):
        # --- REST surface, same port ---
        assert httpx.get(f"{base}/health").status_code == 200
        assert httpx.get(f"{base}/catalog/factories").status_code in (401, 403)  # no token
        authed = httpx.get(f"{base}/catalog/factories", headers=_bearer(admin))
        assert authed.status_code == 200

        # --- MCP surface, same port, mounted at /mcp ---
        with pytest.raises(Exception):  # unauthenticated never reaches a tool
            asyncio.run(_mcp_call(mcp_url, "", "list_projects", {}))

        tools = asyncio.run(_mcp_list_tools(mcp_url, admin))
        assert len(tools.tools) == 19

        created = asyncio.run(_mcp_call(mcp_url, admin, "create_project", {"name": "demo"}))
        assert created.isError is False

        read_ok = asyncio.run(_mcp_call(mcp_url, reader, "list_factories", {}))
        assert read_ok.isError is False

        write_denied = asyncio.run(_mcp_call(mcp_url, reader, "create_project", {"name": "nope"}))
        assert write_denied.isError is True
        assert "project:write" in write_denied.content[0].text
