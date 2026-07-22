from pathlib import Path

import pytest

from core.resources.Factory import Factory
from base.Spec import Spec
from utils.helpers import load_json


class FakeFrame:
    def __init__(self, name):
        self.name = name


def make_factory(data=None, path=None, version="v1"):
    return Factory(name="backend-fastapi", version=version, data=data or {}, path=path or Path("/tmp/nonexistent"))


def factory_schema():
    return load_json(Path(__file__).resolve().parents[2] / "catalog" / "schemas" / "factory_schema.json")


def test_id_combines_name_and_version():
    factory = make_factory()
    assert factory.id == "backend-fastapi:v1"


def test_version_path_appends_version_to_path(tmp_path):
    factory = make_factory(path=tmp_path)
    assert factory.version_path == tmp_path / "v1"


def test_add_frame_and_get_frame_round_trip():
    factory = make_factory()
    frame = FakeFrame("table")
    factory.add_frame(frame)

    assert factory.get_frame("table") is frame
    assert factory.get_frame("missing") is None


def test_maps_config_pipelines_default_to_empty_dict():
    factory = make_factory(data={})
    assert factory.maps == {}
    assert factory.config == {}
    assert factory.pipelines == {}


def test_maps_config_pipelines_return_declared_values():
    factory = make_factory(data={
        "maps": {"status": {"active": "ACTIVE"}},
        "config": {"a": 1},
        "pipelines": {"build": [{"name": "step1", "cmd": "echo ok"}]},
    })

    assert factory.maps == {"status": {"active": "ACTIVE"}}
    assert factory.config == {"a": 1}
    assert factory.pipelines == {"build": [{"name": "step1", "cmd": "echo ok"}]}


def test_reload_resets_frames_and_updates_fields(tmp_path):
    factory = make_factory(path=tmp_path)
    factory.add_frame(FakeFrame("table"))
    assert factory.frames

    factory.reload(version="v2")

    assert factory.frames == {}
    assert factory.version == "v2"
    assert factory.id == "backend-fastapi:v2"


def test_factory_schema_allows_empty_data_and_missing_pipelines():
    Spec({}).validate(factory_schema())
    Spec({"description": "minimal"}).validate(factory_schema())


def test_factory_schema_accepts_any_subset_of_pipelines():
    Spec({
        "pipelines": {
            "init": [{"name": "install", "cmd": "poetry install"}],
            "run": [{"name": "serve", "cmd": "uvicorn app:app"}],
        }
    }).validate(factory_schema())


def test_factory_schema_rejects_unknown_pipeline_name():
    with pytest.raises(Exception):
        Spec({
            "pipelines": {
                "rebuild": [{"name": "old", "cmd": "echo no"}],
            }
        }).validate(factory_schema())


def test_factory_schema_rejects_legacy_lifecycle_key():
    with pytest.raises(Exception):
        Spec({
            "lifecycle": {
                "build": [{"name": "old", "cmd": "echo no"}],
            }
        }).validate(factory_schema())
