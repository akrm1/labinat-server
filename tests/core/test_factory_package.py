"""Tests for factory package export/import (M3)."""

from pathlib import Path
import tarfile

import pytest

from data import database
from data.models.FactoryModel import FactoryModel
from data.models.FrameModel import FrameModel
from app.core.Catalog import Catalog
from app.base.Packager import PackagerError

FORMAT_VERSION = 1


@pytest.fixture
def db(tmp_path):
    db_path = tmp_path / "test.db"
    database.init_db({"url": f"sqlite:///{db_path}", "logging": False})
    yield
    database.engine.dispose()


@pytest.fixture
def catalog(tmp_path, db):
    catalog_path = tmp_path / "catalog"
    (catalog_path / "schemas").mkdir(parents=True)
    repo_schemas = Path(__file__).resolve().parents[2] / "catalog" / "schemas"
    for name in ("factory_schema.json", "frame_schema.json"):
        (catalog_path / "schemas" / name).write_text(
            (repo_schemas / name).read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    (catalog_path / "factories").mkdir(parents=True)
    (catalog_path / "templates").mkdir(parents=True)
    (catalog_path / "templates" / "frame_module.py.j2").write_text(
        "# {{ frame.name }}\ndef loader(properties: dict, concrete: str) -> dict:\n    return properties\n",
        encoding="utf-8",
    )
    return Catalog({"path": str(catalog_path)})


def seed_factory(catalog: Catalog, name="demo", version="v1", with_frame=True):
    factory = catalog.create_factory(
        factory_name=name,
        factory_version=version,
        data={"description": "Demo factory", "pipelines": {}},
        frames=["table"] if with_frame else [],
    )
    if with_frame:
        frame_data = {
            "name": "table",
            "factory": name,
            "description": "A table",
            "concretes": [
                {"name": "model", "extension": "py", "destination": "models/{{ block.spec.name }}.py"}
            ],
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        }
        catalog.update_frame(name, version, "table", frame_data)
        frame_path = factory.version_path / "frames" / "table"
        (frame_path / "concretes" / "model.py.j2").write_text("class {{ block.spec.name }}: pass\n")
        (frame_path / "bindings" / "var.j2").write_text("{{ src.block.name }}")
        (factory.version_path / "base" / "readme.txt.j2").write_text("app={{ app.name }}")
    return catalog.get_factory(name, version)


def test_export_factory_creates_archive_with_manifest_and_specs(catalog, tmp_path):
    seed_factory(catalog)
    archive = catalog.export_factory("demo", "v1", tmp_path / "out")

    assert archive.exists()
    assert archive.name == "demo-v1.tar.gz"

    with tarfile.open(archive, "r:gz") as tar:
        names = set(tar.getnames())
    assert "MANIFEST.json" in names
    assert "factory/demo/v1/factory.json" in names
    assert "factory/demo/v1/frames/table/frame.json" in names
    assert "factory/demo/v1/frames/table/concretes/model.py.j2" in names
    assert "factory/demo/v1/base/readme.txt.j2" in names


def test_export_uses_db_specs_not_disk_json(catalog, tmp_path):
    factory = seed_factory(catalog)
    # Stale Spec files on disk must not affect the archive (DB is source of truth).
    (factory.version_path / "factory.json").write_text(
        '{"description": "stale on disk"}', encoding="utf-8"
    )

    archive = catalog.export_factory("demo", "v1", tmp_path)
    extract = tmp_path / "extract"
    extract.mkdir()
    with tarfile.open(archive, "r:gz") as tar:
        try:
            tar.extractall(extract, filter="data")
        except TypeError:
            tar.extractall(extract)

    import json
    packaged = json.loads((extract / "factory/demo/v1/factory.json").read_text())
    assert packaged.get("description") == "Demo factory"


def test_export_import_round_trip(catalog, tmp_path):
    seed_factory(catalog)
    archive = catalog.export_factory("demo", "v1", tmp_path)

    with database.get_db() as db:
        db.query(FrameModel).delete()
        db.query(FactoryModel).delete()
        db.commit()
    import shutil
    shutil.rmtree(catalog.get_factory_path("demo"))

    imported = catalog.import_factory(archive)
    assert imported.id == "demo:v1"
    assert imported.spec.get("description") == "Demo factory"
    assert "table" in imported.frames
    assert imported.frames["table"].spec.get("description") == "A table"
    assert (imported.version_path / "frames" / "table" / "concretes" / "model.py.j2").exists()
    # Specs live in DB only — not as JSON on catalog disk.
    assert not (imported.version_path / "factory.json").exists()
    assert not (imported.version_path / "frames" / "table" / "frame.json").exists()


def test_import_rejects_existing_without_overwrite(catalog, tmp_path):
    seed_factory(catalog)
    archive = catalog.export_factory("demo", "v1", tmp_path)

    with pytest.raises(PackagerError, match="already exists"):
        catalog.import_factory(archive, overwrite=False)


def test_import_overwrite_replaces_existing(catalog, tmp_path):
    seed_factory(catalog)
    archive = catalog.export_factory("demo", "v1", tmp_path)

    catalog.update_factory("demo", "v1", {"description": "changed locally"})
    imported = catalog.import_factory(archive, overwrite=True)
    assert imported.spec.get("description") == "Demo factory"


def test_import_rejects_path_traversal(catalog, tmp_path):
    evil = tmp_path / "evil.tar.gz"
    with tarfile.open(evil, "w:gz") as tar:
        info = tarfile.TarInfo(name="../escape.txt")
        data = b"nope"
        info.size = len(data)
        import io
        tar.addfile(info, io.BytesIO(data))

    with pytest.raises(PackagerError, match="Unsafe"):
        catalog.import_factory(evil)


def test_import_rejects_bad_format_version(catalog, tmp_path):
    seed_factory(catalog)
    archive = catalog.export_factory("demo", "v1", tmp_path)

    extract_dir = tmp_path / "extract"
    extract_dir.mkdir()
    with tarfile.open(archive, "r:gz") as tar:
        try:
            tar.extractall(extract_dir, filter="data")
        except TypeError:
            tar.extractall(extract_dir)
    manifest_path = extract_dir / "MANIFEST.json"
    import json
    manifest = json.loads(manifest_path.read_text())
    manifest["format_version"] = FORMAT_VERSION + 99
    manifest_path.write_text(json.dumps(manifest))

    bad = tmp_path / "bad.tar.gz"
    with tarfile.open(bad, "w:gz") as tar:
        for path in extract_dir.rglob("*"):
            if path.is_file():
                tar.add(path, arcname=path.relative_to(extract_dir).as_posix())

    with pytest.raises(PackagerError, match="format_version"):
        catalog.import_factory(bad)


def test_export_missing_factory_raises(catalog, tmp_path):
    with pytest.raises(PackagerError, match="not found"):
        catalog.export_factory("missing", "v1", tmp_path)
