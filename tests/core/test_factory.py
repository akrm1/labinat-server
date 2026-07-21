from pathlib import Path

from core.resources.Factory import Factory


class FakeFrame:
    def __init__(self, name):
        self.name = name


def make_factory(data=None, path=None, version="v1"):
    return Factory(name="backend-fastapi", version=version, data=data or {}, path=path or Path("/tmp/nonexistent"))


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


def test_maps_config_lifecycle_default_to_empty_dict():
    factory = make_factory(data={})
    assert factory.maps == {}
    assert factory.config == {}
    assert factory.lifecycle == {}


def test_maps_config_lifecycle_return_declared_values():
    factory = make_factory(data={
        "maps": {"status": {"active": "ACTIVE"}},
        "config": {"a": 1},
        "lifecycle": {"build": ["step1"]},
    })

    assert factory.maps == {"status": {"active": "ACTIVE"}}
    assert factory.config == {"a": 1}
    assert factory.lifecycle == {"build": ["step1"]}


def test_reload_resets_frames_and_updates_fields(tmp_path):
    factory = make_factory(path=tmp_path)
    factory.add_frame(FakeFrame("table"))
    assert factory.frames

    factory.reload(version="v2")

    assert factory.frames == {}
    assert factory.version == "v2"
    assert factory.id == "backend-fastapi:v2"
