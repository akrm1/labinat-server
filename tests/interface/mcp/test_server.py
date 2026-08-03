"""The server assembles and exposes the expected tool surface."""

import asyncio

from app.interface.mcp.app import create_app


EXPECTED_TOOLS = {
    # catalog
    "list_factories", "get_factory", "create_factory", "get_frame", "create_frame",
    # projects / blocks
    "list_projects", "get_project", "create_project", "delete_project", "add_factory",
    "list_blocks", "get_block", "create_block", "delete_blocks",
    # operations
    "build", "emit", "package", "run", "debug",
}


def test_create_app_registers_every_tool():
    mcp = create_app()
    names = {tool.name for tool in asyncio.run(mcp.list_tools())}
    assert names == EXPECTED_TOOLS


def test_read_tools_require_no_arguments():
    mcp = create_app()
    tools = {tool.name: tool for tool in asyncio.run(mcp.list_tools())}
    assert tools["list_factories"].inputSchema.get("required", []) == []
    assert tools["list_projects"].inputSchema.get("required", []) == []
    assert set(tools["create_project"].inputSchema.get("required", [])) == {"name"}
