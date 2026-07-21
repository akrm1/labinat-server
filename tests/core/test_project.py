from pathlib import Path
from datetime import datetime, timezone

import pytest

from core.Project import Project
from core.resources.Factory import Factory


class FakeFrame:
    def __init__(self, name):
        self.name = name


class FakeBlock:
    def __init__(self, name, frame_name):
        self.name = name
        self.frame = FakeFrame(frame_name)


def make_project(config=None):
    return Project(
        id="p1",
        name="Test Project",
        path=Path("/tmp/proj"),
        created_at=datetime.now(timezone.utc),
        config=config or {},
    )


def test_add_factory_and_get_factory_round_trip():
    factory = Factory(name="backend-fastapi", version="v1", data={}, path=Path("/tmp"))
    project = make_project()
    project.add_factory(factory)

    assert project.get_factory("backend-fastapi") is factory
    assert project.get_factory("missing") is None
    assert project.factories == {"backend-fastapi": factory}


def test_add_block_and_get_block_round_trip():
    project = make_project()
    block = FakeBlock("users_table", "table")
    project.add_block(block)

    assert project.get_block("users_table") is block
    assert project.get_block("missing") is None


def test_get_block_type_returns_frame_name_or_none():
    project = make_project()
    project.add_block(FakeBlock("users_table", "table"))

    assert project.get_block_type("users_table") == "table"
    assert project.get_block_type("missing") is None


def test_path_helpers():
    project = make_project()

    assert project.src == project.path / "src"
    assert project.get_factory_path("backend-fastapi") == project.src / "backend-fastapi"


def make_factory_with_config_schema():
    # `Factory.config` reads the "config" key, which wraps the factory's
    # slice of the *project* config schema (see catalog/schemas/factory_schema.json).
    return Factory(
        name="backend-fastapi",
        version="v1",
        data={"config": {"properties": {"port": {"type": "integer"}}, "required": ["port"]}},
        path=Path("/tmp"),
    )


def test_validate_config_passes_for_valid_config():
    factory = make_factory_with_config_schema()
    project = make_project(config={"app": {"name": "MyApp"}, "backend-fastapi": {"port": 8080}})
    project.add_factory(factory)

    project.validate_config()  # should not raise


def test_validate_config_raises_for_missing_required_field():
    factory = make_factory_with_config_schema()
    project = make_project(config={"app": {"name": "MyApp"}, "backend-fastapi": {}})
    project.add_factory(factory)

    with pytest.raises(Exception):
        project.validate_config()


def test_validate_config_raises_when_app_name_missing():
    project = make_project(config={"app": {}})

    with pytest.raises(Exception):
        project.validate_config()
