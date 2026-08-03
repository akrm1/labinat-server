"""FastMCP application factory.

Pure assembly of the MCP surface: the tools plus, when secured, bearer auth. Like
the REST `create_app`, it knows nothing about process lifecycle — `app.server`
builds it, mounts its Streamable HTTP app, and drives its session manager.

The transport path is left at root (`/`); `app.server` mounts the whole app under
the configured `mcp:` path so the public endpoint is e.g. `/mcp`.
"""

from typing import Optional

from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP

from app.interface.mcp import auth
from app.interface.mcp.tools import register_all

INSTRUCTIONS = (
    "Manage a labinat catalog and workspace: browse and author factories and "
    "frames, create projects and blocks, and build/emit/package projects. Names "
    "(factory, frame, project, block) must not contain dots."
)


def create_app(*, secure: bool = False, public_url: Optional[str] = None) -> FastMCP:
    """Assemble the FastMCP server with all labinat tools registered.

    When `secure` is set, every request must present a valid labinat bearer token
    and tools enforce permissions; leave it off for local, trusted use (e.g. tests
    calling tools directly). `public_url` is advertised in OAuth resource metadata.
    """
    settings: dict = {"streamable_http_path": "/"}
    verifier = None

    if secure:
        base_url = public_url or "http://localhost"
        settings["auth"] = AuthSettings(
            issuer_url=base_url,
            resource_server_url=base_url,
            required_scopes=[],
        )
        verifier = auth.LabinatTokenVerifier()

    auth.set_auth_enabled(secure)

    mcp = FastMCP("labinat", instructions=INSTRUCTIONS, token_verifier=verifier, **settings)
    register_all(mcp)
    return mcp
