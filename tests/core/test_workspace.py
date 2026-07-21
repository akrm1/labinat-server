import pytest

from data import database
from data.models.ProjectModel import ProjectModel
from data.models.ProjectFactoryModel import ProjectFactoryModel
from data.models.FactoryModel import FactoryModel
from data.models.FrameModel import FrameModel
from data.models.BlockModel import BlockModel
from core.Workspace import Workspace
from core.Catalog import Catalog
from core.resources.Factory import Factory
from core.resources.Frame import Frame


@pytest.fixture
def db(tmp_path):
    db_path = tmp_path / "test.db"
    database.init_db({"url": f"sqlite:///{db_path}", "logging": False})
    yield
    database.engine.dispose()


@pytest.fixture
def workspace(tmp_path, db):
    return Workspace({"path": str(tmp_path / "workspace")})


@pytest.fixture
def catalog(tmp_path):
    return Catalog({"path": str(tmp_path / "catalog")})


def make_factory_with_table_frame(tmp_path, factory_name="backend-fastapi", version="v1", catalog=None):
    # When reconstructed later via Workspace.get_project/get_all_projects, frame
    # paths are derived from `catalog.get_factory_path(...)`, so the on-disk
    # structure must live there too -- not under an arbitrary tmp_path root.
    factory_path = catalog.get_factory_path(factory_name) if catalog else tmp_path / "factories" / factory_name
    factory = Factory(name=factory_name, version=version, data={}, path=factory_path)

    frame_data = {"properties": {"name": {"type": "string"}}, "required": ["name"]}
    frame_path = factory_path.joinpath(version, "frames", "table")
    frame = Frame(id=f"{factory_name}:{version}.table", name="table", data=frame_data, path=frame_path)
    factory.add_frame(frame)

    if catalog:
        # Mirrors what Catalog.create_factory/create_frame would have already
        # done: a FactoryModel/FrameModel row in the DB, plus the on-disk
        # frame structure (module.py, concretes/, bindings/) that Frame.load()
        # reads when Workspace reconstructs a Factory from the DB.
        (frame_path / "concretes").mkdir(parents=True, exist_ok=True)
        (frame_path / "bindings").mkdir(parents=True, exist_ok=True)
        (frame_path / "module.py").write_text("# frame module\n")

        with database.get_db() as db:
            db.add(FactoryModel(name=factory_name, version=version, data={}))
            db.add(FrameModel(factory=factory_name, factory_version=version, name="table", data=frame_data))
            db.commit()

    return factory


def test_create_project_persists_record_and_creates_directories(workspace):
    project = workspace.create_project(name="Test Project", description="a description")

    assert project.name == "Test Project"
    assert project.path.exists()
    assert project.src.exists()

    with database.get_db() as db:
        record = db.query(ProjectModel).filter_by(id=project.id).first()
        assert record is not None
        assert record.name == "Test Project"
        assert record.description == "a description"


def test_create_project_with_factories_creates_project_factory_records(workspace, tmp_path):
    factory = make_factory_with_table_frame(tmp_path)
    project = workspace.create_project(name="Test", factories=[factory])

    assert project.get_factory("backend-fastapi") is factory
    assert project.get_factory_path("backend-fastapi").exists()

    with database.get_db() as db:
        record = db.query(ProjectFactoryModel).filter_by(project_id=project.id).first()
        assert record.factory == "backend-fastapi"
        assert record.factory_version == "v1"


def test_delete_project_removes_record_and_directory(workspace):
    project = workspace.create_project(name="ToDelete")
    project_path = project.path
    assert project_path.exists()

    assert workspace.delete_project(project.id) is True
    assert not project_path.exists()

    with database.get_db() as db:
        assert db.query(ProjectModel).filter_by(id=project.id).first() is None

    assert workspace.delete_project(project.id) is False


def test_create_block_persists_record_and_validates(workspace, tmp_path):
    factory = make_factory_with_table_frame(tmp_path)
    project = workspace.create_project(name="Test", factories=[factory])

    block = workspace.create_block(
        project, frame_id="backend-fastapi.table", block_name="users_table", data={"name": "Users"}
    )

    assert block is not None
    assert block.name == "users_table"

    with database.get_db() as db:
        record = db.query(BlockModel).filter_by(project_id=project.id, name="users_table").first()
        assert record is not None
        assert record.data == {"name": "Users"}


def test_create_block_raises_when_data_fails_frame_validation(workspace, tmp_path):
    factory = make_factory_with_table_frame(tmp_path)
    project = workspace.create_project(name="Test", factories=[factory])

    with pytest.raises(Exception):
        workspace.create_block(
            project, frame_id="backend-fastapi.table", block_name="bad_block", data={"name": 123}
        )


def test_create_block_returns_none_for_unknown_factory(workspace, tmp_path):
    factory = make_factory_with_table_frame(tmp_path)
    project = workspace.create_project(name="Test", factories=[factory])

    result = workspace.create_block(
        project, frame_id="nonexistent-factory.table", block_name="x", data={}
    )
    assert result is None


def test_create_block_returns_none_for_unknown_frame(workspace, tmp_path):
    """Regression test: previously `factory.get_frame(...)` was dereferenced
    before checking whether `factory` itself was found, so an unknown
    factory name raised AttributeError instead of returning None."""
    factory = make_factory_with_table_frame(tmp_path)
    project = workspace.create_project(name="Test", factories=[factory])

    result = workspace.create_block(
        project, frame_id="backend-fastapi.nonexistent-frame", block_name="x", data={}
    )
    assert result is None


def test_get_blocks_scoped_to_project_and_names(workspace, tmp_path):
    factory = make_factory_with_table_frame(tmp_path)
    project_a = workspace.create_project(name="A", factories=[factory])
    project_b = workspace.create_project(name="B", factories=[factory])

    workspace.create_block(project_a, "backend-fastapi.table", "t1", {"name": "T1"})
    workspace.create_block(project_a, "backend-fastapi.table", "t2", {"name": "T2"})
    workspace.create_block(project_b, "backend-fastapi.table", "t1", {"name": "OtherT1"})

    blocks = workspace.get_blocks(project_a, ["t1", "t2"])

    assert set(blocks.keys()) == {"t1", "t2"}
    assert blocks["t1"].spec["name"] == "T1"  # not project_b's "OtherT1"


def test_delete_blocks_scoped_to_project_and_names(workspace, tmp_path):
    """Regression test for the historical `filter_by` misuse: deleting by
    name must not affect blocks with the same name in a different project."""
    factory = make_factory_with_table_frame(tmp_path)
    project_a = workspace.create_project(name="A", factories=[factory])
    project_b = workspace.create_project(name="B", factories=[factory])

    workspace.create_block(project_a, "backend-fastapi.table", "t1", {"name": "T1"})
    workspace.create_block(project_b, "backend-fastapi.table", "t1", {"name": "OtherT1"})

    assert workspace.delete_blocks(project_a, ["t1"]) is True

    with database.get_db() as db:
        remaining = db.query(BlockModel).filter(BlockModel.name == "t1").all()
        assert len(remaining) == 1
        assert remaining[0].project_id == project_b.id


def test_get_project_reconstructs_factories_and_blocks(workspace, catalog, tmp_path):
    """Regression test: `get_project` previously reconstructed bare `Factory`
    objects with no frames loaded from the DB, so any project with blocks
    crashed with `AttributeError: 'NoneType' object has no attribute
    'get_frame'` when reloaded."""
    factory = make_factory_with_table_frame(tmp_path, catalog=catalog)
    project = workspace.create_project(name="Test", factories=[factory])
    workspace.create_block(project, "backend-fastapi.table", "users_table", {"name": "Users"})

    reloaded = workspace.get_project(project.id, catalog)

    assert reloaded is not None
    assert reloaded.name == "Test"
    assert "backend-fastapi" in reloaded.factories
    assert reloaded.get_factory("backend-fastapi").get_frame("table") is not None
    assert "users_table" in reloaded.blocks
    assert reloaded.blocks["users_table"].spec["name"] == "Users"


def test_get_project_returns_none_for_unknown_id(workspace, catalog):
    assert workspace.get_project("nonexistent", catalog) is None


def test_get_all_projects_returns_every_project(workspace, catalog, tmp_path):
    factory = make_factory_with_table_frame(tmp_path, catalog=catalog)
    workspace.create_project(name="A", factories=[factory])
    workspace.create_project(name="B", factories=[factory])

    all_projects = workspace.get_all_projects(catalog)

    assert len(all_projects) == 2
    assert {p.name for p in all_projects.values()} == {"A", "B"}
    for project in all_projects.values():
        assert project.get_factory("backend-fastapi").get_frame("table") is not None
