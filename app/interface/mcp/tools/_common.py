"""Shared helpers for MCP tools: domain access with clear errors."""

from __future__ import annotations

from app import controller
from app.core.Catalog import Catalog
from app.core.Project import Project
from app.core.Workspace import Workspace


class ToolError(Exception):
    """A tool precondition failed (missing resource, not initialized, ...).

    Raised for expected, user-facing failures so FastMCP reports a clean message
    instead of a traceback.
    """


def catalog() -> Catalog:
    if controller.catalog is None:
        raise ToolError("Catalog is not initialized")
    return controller.catalog


def workspace() -> Workspace:
    if controller.workspace is None:
        raise ToolError("Workspace is not initialized")
    return controller.workspace


def load_project(project_id: str) -> Project:
    project = workspace().get_project(project_id, catalog())
    if project is None:
        raise ToolError(f"Project not found: {project_id}")
    return project
