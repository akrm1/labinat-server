"""Server controller: bootstrap, compose the surfaces, and launch.

`main.py` is the orchestrator: it calls `start()` (bootstrap), then `run()` (serve),
then `shutdown()`. `run()` builds a single ASGI app that serves both surfaces — the
REST API with the MCP server mounted under the configured `mcp:` path — so one
process, one port, and one bootstrap back the whole ecosystem.
"""

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from app import bootstrap
from app.interface.api.app import create_app as create_api
from app.interface.mcp.app import create_app as create_mcp
from utils import logger


def start() -> dict:
    """Bootstrap the server (config → logger/db/controller → auth); returns config."""

    bootstrap.load()

    token_secret = bootstrap.create_token_secret()
    bootstrap.init(token_secret)
    bootstrap.create_admin()

    return bootstrap.config


def _derive_public_url(host: str, port: int) -> str:
    """Turn the bind host/port into a URL clients can actually reach.

    `0.0.0.0`/`::` mean "listen on every interface" — they are not dialable — so we
    advertise `localhost` instead. Used as the default for MCP's OAuth resource
    metadata when no explicit `public_url` override is configured.
    """
    advertised = "localhost" if host in ("0.0.0.0", "::", "") else host
    return f"http://{advertised}:{port}"


def create(host: str = "0.0.0.0", port: int = 8000) -> FastAPI:
    """Compose the served app: the REST API with the MCP surface mounted alongside.

    MCP is served over Streamable HTTP; its session manager must run for the life
    of the process, so it is driven from the API app's lifespan. When `mcp.enabled`
    is false the REST API is served on its own. `host`/`port` are the resolved bind
    address (what `run()` serves on); they seed MCP's advertised URL unless an
    explicit `public_url` override is set.
    """

    server_options = (bootstrap.config or {}).get("server") or {}
    options = server_options.get("mcp") or {}
    if not options.get("enabled", True):
        return create_api()

    path = options.get("path", "/mcp")
    public_url = options.get("public_url") or _derive_public_url(host, port)

    mcp = create_mcp(secure=True, public_url=public_url)
    mcp_app = mcp.streamable_http_app()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        # Drive the MCP transport for as long as the server is up. Mounted
        # sub-apps don't receive lifespan events, so run it from here.
        async with mcp.session_manager.run():
            yield

    api = create_api(lifespan=lifespan)
    api.mount(path, mcp_app)
    return api


def run(host: str, port: int, reload: bool = False) -> None:
    """Serve the composed app (REST + MCP) with uvicorn. Blocks until stopped."""

    uvicorn.run(create(host, port), host=host, port=port, reload=reload)


def shutdown() -> None:
    """Collapse any in-flight operations so no subprocess is left orphaned."""

    from app.interface.api import operations

    collapsed = operations.collapse()
    if collapsed:
        logger.info("Collapsed running operations on shutdown", operations=collapsed)
