"""MCP tool registrations, grouped by domain area.

Each module exposes a ``register(mcp)`` that attaches its tools to the FastMCP
instance. Keeping them split mirrors the REST routers and keeps the surface easy
to scan.
"""

from app.interface.mcp.tools import catalog, operations, projects


def register_all(mcp) -> None:
    catalog.register(mcp)
    projects.register(mcp)
    operations.register(mcp)


__all__ = ["register_all", "catalog", "projects", "operations"]
