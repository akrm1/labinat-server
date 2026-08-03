"""Catalog: factory and frame CRUD, plus package import/export."""

from fastapi import APIRouter, Depends, HTTPException

from app.interface.api import schemas
from app.interface.api.deps import get_catalog, require_permission
from app.interface.permissions import CATALOG_READ as READ, CATALOG_WRITE as WRITE
from app.interface.serializers import factory_to_dict, frame_to_dict
from app.core.Catalog import Catalog

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/factories")
def list_factories(catalog: Catalog = Depends(get_catalog), _=Depends(require_permission(READ))):
    return [factory_to_dict(factory) for factory in catalog.get_all_factories().values()]


@router.post("/factories", status_code=201)
def create_factory(
    body: schemas.FactoryCreateRequest,
    catalog: Catalog = Depends(get_catalog),
    _=Depends(require_permission(WRITE)),
):
    factory = catalog.create_factory(body.name, body.version, body.data, body.frames)
    return factory_to_dict(factory)


@router.get("/factories/{name}/{version}")
def get_factory(name: str, version: str, catalog: Catalog = Depends(get_catalog), _=Depends(require_permission(READ))):
    factory = catalog.get_factory(name, version)
    if factory is None:
        raise HTTPException(status_code=404, detail=f"Factory not found: {name}:{version}")
    return factory_to_dict(factory)


@router.put("/factories/{name}/{version}")
def update_factory(
    name: str,
    version: str,
    body: schemas.FactoryUpdateRequest,
    catalog: Catalog = Depends(get_catalog),
    _=Depends(require_permission(WRITE)),
):
    if not catalog.update_factory(name, version, body.data):
        raise HTTPException(status_code=404, detail=f"Factory not found: {name}:{version}")
    return {"message": "factory updated"}


@router.delete("/factories/{name}/{version}")
def delete_factory_version(name: str, version: str, catalog: Catalog = Depends(get_catalog), _=Depends(require_permission(WRITE))):
    if not catalog.delete_factory_version(name, version):
        raise HTTPException(status_code=404, detail=f"Factory not found: {name}:{version}")
    return {"message": "factory version deleted"}


@router.post("/factories/{name}/{version}/frames", status_code=201)
def create_frame(
    name: str,
    version: str,
    body: schemas.FrameCreateRequest,
    catalog: Catalog = Depends(get_catalog),
    _=Depends(require_permission(WRITE)),
):
    frame = catalog.create_frame(name, version, body.name, body.data)
    if frame is None:
        raise HTTPException(status_code=409, detail="Frame already exists or factory not found")
    return frame_to_dict(frame)


@router.get("/factories/{name}/{version}/frames/{frame}")
def get_frame(name: str, version: str, frame: str, catalog: Catalog = Depends(get_catalog), _=Depends(require_permission(READ))):
    result = catalog.get_frame(name, version, frame)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Frame not found: {name}:{version}.{frame}")
    return frame_to_dict(result)


@router.put("/factories/{name}/{version}/frames/{frame}")
def update_frame(
    name: str,
    version: str,
    frame: str,
    body: schemas.FrameUpdateRequest,
    catalog: Catalog = Depends(get_catalog),
    _=Depends(require_permission(WRITE)),
):
    if not catalog.update_frame(name, version, frame, body.data):
        raise HTTPException(status_code=404, detail=f"Frame not found: {name}:{version}.{frame}")
    return {"message": "frame updated"}


@router.delete("/factories/{name}/{version}/frames/{frame}")
def delete_frame(name: str, version: str, frame: str, catalog: Catalog = Depends(get_catalog), _=Depends(require_permission(WRITE))):
    if not catalog.delete_frame(name, version, frame):
        raise HTTPException(status_code=404, detail=f"Frame not found: {name}:{version}.{frame}")
    return {"message": "frame deleted"}


@router.post("/factories/{name}/{version}/export")
def export_factory(
    name: str,
    version: str,
    dest_path: str,
    catalog: Catalog = Depends(get_catalog),
    _=Depends(require_permission(READ)),
):
    archive = catalog.export_factory(name, version, dest_path)
    return {"archive_path": str(archive)}


@router.post("/import")
def import_factory(
    archive_path: str,
    overwrite: bool = False,
    catalog: Catalog = Depends(get_catalog),
    _=Depends(require_permission(WRITE)),
):
    factory = catalog.import_factory(archive_path, overwrite=overwrite)
    return factory_to_dict(factory)
