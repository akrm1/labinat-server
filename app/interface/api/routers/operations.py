"""Project lifecycle operations, streamed live as Server-Sent Events.

Each endpoint returns `text/event-stream`: a `start` event, a `log` event per
line as the operation runs, then a terminal `completed`/`error`/`cancelled`
event. Disconnecting the request cancels the operation and stops any subprocess.
"""

from fastapi import APIRouter, Depends, Request

from app.interface.api.deps import get_catalog, get_workspace, require_permission
from app.interface.api.operations import stream_operation
from app.interface.api.routers.projects import load_project
from app.interface.permissions import PROJECT_EXECUTE as EXECUTE
from app.core.Catalog import Catalog
from app.core.Workspace import Workspace

router = APIRouter(prefix="/projects/{project_id}", tags=["operations"])


@router.post("/build")
def build(
    project_id: str,
    request: Request,
    workspace: Workspace = Depends(get_workspace),
    catalog: Catalog = Depends(get_catalog),
    _=Depends(require_permission(EXECUTE)),
):
    project = load_project(project_id, workspace, catalog)
    return stream_operation(request, project.build)


@router.post("/emit")
def emit(
    project_id: str,
    request: Request,
    workspace: Workspace = Depends(get_workspace),
    catalog: Catalog = Depends(get_catalog),
    _=Depends(require_permission(EXECUTE)),
):
    project = load_project(project_id, workspace, catalog)
    return stream_operation(request, project.emit, result_serializer=lambda paths: [str(p) for p in paths])


@router.post("/run")
def run(
    project_id: str,
    request: Request,
    workspace: Workspace = Depends(get_workspace),
    catalog: Catalog = Depends(get_catalog),
    _=Depends(require_permission(EXECUTE)),
):
    project = load_project(project_id, workspace, catalog)
    return stream_operation(request, project.run)


@router.post("/debug")
def debug(
    project_id: str,
    request: Request,
    workspace: Workspace = Depends(get_workspace),
    catalog: Catalog = Depends(get_catalog),
    _=Depends(require_permission(EXECUTE)),
):
    project = load_project(project_id, workspace, catalog)
    return stream_operation(request, project.debug)


@router.post("/package")
def package(
    project_id: str,
    request: Request,
    tool: str = "docker",
    workspace: Workspace = Depends(get_workspace),
    catalog: Catalog = Depends(get_catalog),
    _=Depends(require_permission(EXECUTE)),
):
    project = load_project(project_id, workspace, catalog)
    return stream_operation(request, lambda: project.package(tool), result_serializer=lambda tags: tags)
