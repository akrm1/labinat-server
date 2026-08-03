"""MCP surface for labinat: the domain exposed as Model Context Protocol tools.

The same domain layer the REST API uses, presented as MCP tools so an agent
(Cursor, Claude Desktop, ...) can drive labinat. It is served over Streamable HTTP
by `app.server`, mounted on the same app as the REST API; because it is
network-exposed, every request carries a labinat bearer token and each tool
enforces the same permissions as the REST surface.
"""

from app.interface.mcp.app import create_app

__all__ = ["create_app"]
