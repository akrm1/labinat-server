"""Project tools: workspace CRUD, factory attachment, and blocks."""

from typing import List, Optional

from app.interface.mcp.auth import authorize
from app.interface.mcp.tools._common import ToolError, catalog, load_project, workspace
from app.interface.permissions import PROJECT_READ as READ, PROJECT_WRITE as WRITE
from app.interface.serializers import block_to_dict, project_to_dict


def register(mcp) -> None:
    @mcp.tool()
    def list_projects() -> list:
        """List every project in the workspace."""
        authorize(READ)
        return [project_to_dict(project) for project in workspace().get_all_projects(catalog()).values()]

    @mcp.tool()
    def get_project(project_id: str) -> dict:
        """Get one project by id, including its factories and blocks."""
        authorize(READ)
        return project_to_dict(load_project(project_id))

    @mcp.tool()
    def create_project(
        name: str,
        description: str = "",
        config: Optional[dict] = None,
        factories: Optional[List[dict]] = None,
    ) -> dict:
        """Create a project. `factories` is a list of {"name", "version"} refs to
        attach on creation. The project name must not contain dots."""
        authorize(WRITE)
        resolved = []
        for ref in factories or []:
            factory = catalog().get_factory(ref["name"], ref["version"])
            if factory is None:
                raise ToolError(f"Factory not found: {ref['name']}:{ref['version']}")
            resolved.append(factory)

        project = workspace().create_project(name, description, config or {}, resolved)
        return project_to_dict(project)

    @mcp.tool()
    def delete_project(project_id: str) -> dict:
        """Delete a project (and its on-disk workspace) by id."""
        authorize(WRITE)
        if not workspace().delete_project(project_id):
            raise ToolError(f"Project not found: {project_id}")
        return {"message": "project deleted", "project_id": project_id}

    @mcp.tool()
    def add_factory(project_id: str, name: str, version: str) -> dict:
        """Attach an existing factory version to a project."""
        authorize(WRITE)
        factory = catalog().get_factory(name, version)
        if factory is None:
            raise ToolError(f"Factory not found: {name}:{version}")
        if not workspace().add_factory_to_project(project_id, factory):
            raise ToolError(f"Project not found: {project_id}")
        return {"message": "factory attached", "project_id": project_id, "factory": f"{name}:{version}"}

    @mcp.tool()
    def list_blocks(project_id: str) -> list:
        """List every block in a project."""
        authorize(READ)
        project = load_project(project_id)
        return [block_to_dict(block) for block in project.blocks.values()]

    @mcp.tool()
    def get_block(project_id: str, block_name: str) -> dict:
        """Get one block from a project by name."""
        authorize(READ)
        project = load_project(project_id)
        block = project.get_block(block_name)
        if block is None:
            raise ToolError(f"Block not found: {block_name}")
        return block_to_dict(block)

    @mcp.tool()
    def create_block(project_id: str, frame_id: str, name: str, data: Optional[dict] = None) -> dict:
        """Create a block (an instance of a frame) in a project. The block name
        must not contain dots."""
        authorize(WRITE)
        project = load_project(project_id)
        block = workspace().create_block(project, frame_id, name, data or {})
        if block is None:
            raise ToolError("Could not create block (unknown frame or invalid data)")
        return block_to_dict(block)

    @mcp.tool()
    def delete_blocks(project_id: str, names: List[str]) -> dict:
        """Delete the named blocks from a project."""
        authorize(WRITE)
        project = load_project(project_id)
        workspace().delete_blocks(project, names)
        return {"message": "blocks deleted", "project_id": project_id, "names": names}
