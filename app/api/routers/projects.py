"""Workspace: project CRUD, factory attachment, and block CRUD."""

from fastapi import APIRouter, Depends, HTTPException

from app.api import schemas
from app.api.deps import get_catalog, get_workspace, require_permission
from app.api.serializers import project_to_dict, block_to_dict
from app.core.Catalog import Catalog
from app.core.Workspace import Workspace
from app.core.Project import Project

router = APIRouter(prefix="/projects", tags=["projects"])

READ = "project:read"
WRITE = "project:write"


def load_project(project_id: str, workspace: Workspace, catalog: Catalog) -> Project:
    project = workspace.get_project(project_id, catalog)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
    return project


@router.get("")
def list_projects(
    workspace: Workspace = Depends(get_workspace),
    catalog: Catalog = Depends(get_catalog),
    _=Depends(require_permission(READ)),
):
    return [project_to_dict(p) for p in workspace.get_all_projects(catalog).values()]


@router.post("", status_code=201)
def create_project(
    body: schemas.ProjectCreateRequest,
    workspace: Workspace = Depends(get_workspace),
    catalog: Catalog = Depends(get_catalog),
    _=Depends(require_permission(WRITE)),
):
    factories = []
    for ref in body.factories:
        factory = catalog.get_factory(ref.name, ref.version)
        if factory is None:
            raise HTTPException(status_code=400, detail=f"Factory not found: {ref.name}:{ref.version}")
        factories.append(factory)

    project = workspace.create_project(body.name, body.description, body.config, factories)
    return project_to_dict(project)


@router.get("/{project_id}")
def get_project(
    project_id: str,
    workspace: Workspace = Depends(get_workspace),
    catalog: Catalog = Depends(get_catalog),
    _=Depends(require_permission(READ)),
):
    return project_to_dict(load_project(project_id, workspace, catalog))


@router.delete("/{project_id}")
def delete_project(
    project_id: str,
    workspace: Workspace = Depends(get_workspace),
    _=Depends(require_permission(WRITE)),
):
    if not workspace.delete_project(project_id):
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
    return {"message": "project deleted"}


@router.post("/{project_id}/factories")
def add_factory(
    project_id: str,
    body: schemas.AddFactoryRequest,
    workspace: Workspace = Depends(get_workspace),
    catalog: Catalog = Depends(get_catalog),
    _=Depends(require_permission(WRITE)),
):
    factory = catalog.get_factory(body.name, body.version)
    if factory is None:
        raise HTTPException(status_code=400, detail=f"Factory not found: {body.name}:{body.version}")
    if not workspace.add_factory_to_project(project_id, factory):
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
    return {"message": "factory attached"}


@router.get("/{project_id}/blocks")
def list_blocks(
    project_id: str,
    workspace: Workspace = Depends(get_workspace),
    catalog: Catalog = Depends(get_catalog),
    _=Depends(require_permission(READ)),
):
    project = load_project(project_id, workspace, catalog)
    return [block_to_dict(b) for b in project.blocks.values()]


@router.post("/{project_id}/blocks", status_code=201)
def create_block(
    project_id: str,
    body: schemas.BlockCreateRequest,
    workspace: Workspace = Depends(get_workspace),
    catalog: Catalog = Depends(get_catalog),
    _=Depends(require_permission(WRITE)),
):
    project = load_project(project_id, workspace, catalog)
    block = workspace.create_block(project, body.frame_id, body.name, body.data)
    if block is None:
        raise HTTPException(status_code=400, detail="Could not create block (unknown frame or invalid data)")
    return block_to_dict(block)


@router.get("/{project_id}/blocks/{block_name}")
def get_block(
    project_id: str,
    block_name: str,
    workspace: Workspace = Depends(get_workspace),
    catalog: Catalog = Depends(get_catalog),
    _=Depends(require_permission(READ)),
):
    project = load_project(project_id, workspace, catalog)
    block = project.get_block(block_name)
    if block is None:
        raise HTTPException(status_code=404, detail=f"Block not found: {block_name}")
    return block_to_dict(block)


@router.delete("/{project_id}/blocks")
def delete_blocks(
    project_id: str,
    body: schemas.BlockNamesRequest,
    workspace: Workspace = Depends(get_workspace),
    catalog: Catalog = Depends(get_catalog),
    _=Depends(require_permission(WRITE)),
):
    project = load_project(project_id, workspace, catalog)
    workspace.delete_blocks(project, body.names)
    return {"message": "blocks deleted"}
