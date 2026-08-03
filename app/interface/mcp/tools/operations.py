"""Operation tools: build/emit/run/debug/package a project.

Unlike the REST API (which streams these over SSE), MCP is request/response — so
each tool runs the operation to completion and returns the captured logs together
with the result. `run` and `debug` can be long-running (they may launch a process
that serves until stopped); prefer `build`/`emit` for quick, returning work.
"""

from app.interface.mcp.auth import authorize
from app.interface.mcp.logs import capture_logs
from app.interface.mcp.tools._common import load_project
from app.interface.permissions import PROJECT_EXECUTE as EXECUTE


def register(mcp) -> None:
    @mcp.tool()
    def build(project_id: str) -> dict:
        """Build a project: run its factories' build pipelines. Returns logs."""
        authorize(EXECUTE)
        project = load_project(project_id)
        with capture_logs() as logs:
            project.build()
        return {"status": "completed", "logs": logs}

    @mcp.tool()
    def emit(project_id: str) -> dict:
        """Emit a project's generated artifacts. Returns the paths and logs."""
        authorize(EXECUTE)
        project = load_project(project_id)
        with capture_logs() as logs:
            paths = project.emit()
        return {"status": "completed", "result": [str(path) for path in paths], "logs": logs}

    @mcp.tool()
    def package(project_id: str, tool: str = "docker") -> dict:
        """Package a project into container image(s) with `tool` (default docker).
        Returns the produced image tags and logs."""
        authorize(EXECUTE)
        project = load_project(project_id)
        with capture_logs() as logs:
            tags = project.package(tool)
        return {"status": "completed", "result": tags, "logs": logs}

    @mcp.tool()
    def run(project_id: str) -> dict:
        """Run a project's run pipeline. May be long-running. Returns logs."""
        authorize(EXECUTE)
        project = load_project(project_id)
        with capture_logs() as logs:
            project.run()
        return {"status": "completed", "logs": logs}

    @mcp.tool()
    def debug(project_id: str) -> dict:
        """Run a project's debug pipeline. May be long-running. Returns logs."""
        authorize(EXECUTE)
        project = load_project(project_id)
        with capture_logs() as logs:
            project.debug()
        return {"status": "completed", "logs": logs}
