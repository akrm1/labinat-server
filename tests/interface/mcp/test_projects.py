"""Project lifecycle through the MCP tools."""

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from tests.interface.mcp.conftest import call, call_one


def test_create_get_list_delete_project(server):
    created = call_one(server, "create_project", name="demo", description="a demo")
    assert created["name"] == "demo"
    assert created["description"] == "a demo"
    project_id = created["id"]

    fetched = call_one(server, "get_project", project_id=project_id)
    assert fetched["id"] == project_id

    listed = call(server, "list_projects")
    assert [p["id"] for p in listed] == [project_id]

    deleted = call_one(server, "delete_project", project_id=project_id)
    assert deleted["project_id"] == project_id
    assert call(server, "list_projects") == []


def test_get_missing_project_raises(server):
    with pytest.raises(ToolError) as exc:
        call(server, "get_project", project_id="does-not-exist")
    assert "Project not found" in str(exc.value)


def test_delete_missing_project_raises(server):
    with pytest.raises(ToolError):
        call(server, "delete_project", project_id="does-not-exist")


def test_add_factory_to_project_reports_missing_factory(server):
    created = call_one(server, "create_project", name="demo")
    with pytest.raises(ToolError) as exc:
        call(server, "add_factory", project_id=created["id"], name="ghost", version="1")
    assert "Factory not found" in str(exc.value)


def test_create_block_with_unknown_frame_raises(server):
    created = call_one(server, "create_project", name="demo")
    with pytest.raises(ToolError) as exc:
        call(server, "create_block", project_id=created["id"], frame_id="ghost.frame", name="b", data={})
    assert "Could not create block" in str(exc.value)
