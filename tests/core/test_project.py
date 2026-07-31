from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from core.Project import Project
from core.resources.Factory import Factory
from base.ImageBuilder import ImageBuildError


class FakeFrame:
    def __init__(self, name, frame_id=None):
        self.name = name
        self.id = frame_id or f"backend-fastapi:v1.{name}"


class FakeBlock:
    def __init__(self, name, frame_name, frame_id=None):
        self.name = name
        self.id = f"block.{name}"
        self.frame = FakeFrame(frame_name, frame_id=frame_id)

    def build(self, destination_root):
        destination_root.mkdir(parents=True, exist_ok=True)
        out = destination_root / f"{self.name}.out"
        out.write_text("emitted")
        return [out]


def make_project(config=None, path=None):
    return Project(
        id="p1",
        name="Test Project",
        path=path or Path("/tmp/proj"),
        created_at=datetime.now(timezone.utc),
        config=config or {"app": {"name": "Demo"}},
    )


def make_factory_with_pipelines(pipelines=None, path=None, name="backend-fastapi"):
    return Factory(
        name=name,
        version="v1",
        data={"pipelines": pipelines or {}},
        path=path or Path("/tmp/factory"),
    )


def attach_factory_and_block(project, pipelines=None, path=None, block_name="users"):
    factory = make_factory_with_pipelines(pipelines=pipelines, path=path)
    project.add_factory(factory)
    block = FakeBlock(block_name, "table", frame_id=f"{factory.id}.table")
    project.add_block(block)
    return factory, block


def test_add_factory_and_get_factory_round_trip():
    factory = Factory(name="backend-fastapi", version="v1", data={}, path=Path("/tmp"))
    project = make_project()
    project.add_factory(factory)

    assert project.get_factory("backend-fastapi") is factory
    assert project.get_factory("missing") is None
    assert project.factories == {"backend-fastapi": factory}


def test_add_block_and_get_block_round_trip():
    project = make_project()
    factory, block = attach_factory_and_block(project, block_name="users_table")

    assert project.get_block("users_table") is block
    assert project.get_block("missing") is None
    assert project.get_block_factory("users_table") is factory


def test_get_block_type_returns_frame_name_or_none():
    project = make_project()
    attach_factory_and_block(project, block_name="users_table")

    assert project.get_block_type("users_table") == "table"
    assert project.get_block_type("missing") is None


def test_path_helpers():
    project = make_project()

    assert project.src == project.path / "src"
    assert project.get_factory_path("backend-fastapi") == project.src / "backend-fastapi"


def make_factory_with_config_schema():
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

    project.validate_config()


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


@pytest.mark.parametrize("method_name,pipeline_key", [
    ("init", "init"),
    ("run", "run"),
    ("debug", "debug"),
])
def test_pipeline_methods_execute_declared_actions_with_factory_cwd(tmp_path, method_name, pipeline_key):
    project = make_project(path=tmp_path / "proj")
    factory = make_factory_with_pipelines({
        pipeline_key: [{"name": f"{pipeline_key}-step", "cmd": f"echo {pipeline_key}"}],
    })
    project.add_factory(factory)

    with patch("utils.os.execute", return_value=0) as execute:
        getattr(project, method_name)()

    execute.assert_called_once()
    assert execute.call_args.args[0] == f"echo {pipeline_key}"
    inputs = execute.call_args.args[1]
    assert inputs["app"]["name"] == "Demo"
    assert inputs["factory"]["name"] == "backend-fastapi"
    assert execute.call_args.kwargs["cwd"] == project.get_factory_path("backend-fastapi")


@pytest.mark.parametrize("method_name", ["init", "run", "debug"])
def test_pipeline_methods_are_noop_when_pipelines_missing_or_empty(tmp_path, method_name):
    project = make_project(path=tmp_path / "proj")
    project.add_factory(make_factory_with_pipelines({}))

    with patch("utils.os.execute") as execute:
        getattr(project, method_name)()
        execute.assert_not_called()


def test_pipeline_methods_skip_undeclared_keys_but_run_others(tmp_path):
    project = make_project(path=tmp_path / "proj")
    project.add_factory(make_factory_with_pipelines({
        "init": [{"name": "install", "cmd": "echo init"}],
        "run": [{"name": "serve", "cmd": "echo run"}],
    }))

    with patch("utils.os.execute", return_value=0) as execute:
        project.init()
        project.run()
        project.debug()

    cmds = [call.args[0] for call in execute.call_args_list]
    assert cmds == ["echo init", "echo run"]


def test_pipelines_run_for_each_attached_factory(tmp_path):
    project = make_project(path=tmp_path / "proj")
    project.add_factory(make_factory_with_pipelines(
        {"run": [{"name": "a", "cmd": "echo a"}]},
        path=tmp_path / "factory-a",
        name="backend-fastapi",
    ))
    project.add_factory(make_factory_with_pipelines(
        {"run": [{"name": "b", "cmd": "echo b"}]},
        path=tmp_path / "factory-b",
        name="frontend",
    ))

    with patch("utils.os.execute", return_value=0) as execute:
        project.run()

    cmds = [call.args[0] for call in execute.call_args_list]
    assert cmds == ["echo a", "echo b"]


def test_emit_writes_blocks_into_factory_src(tmp_path):
    project = make_project(path=tmp_path / "proj")
    factory, _ = attach_factory_and_block(project, path=tmp_path / "factory", block_name="users")

    paths = project.emit()
    assert len(paths) == 1
    assert paths[0] == project.get_factory_path(factory.name) / "users.out"
    assert paths[0].read_text() == "emitted"


def test_add_block_rejects_frame_from_unattached_factory(tmp_path):
    project = make_project(path=tmp_path / "proj")
    project.add_factory(make_factory_with_pipelines(path=tmp_path / "factory"))

    orphan = FakeBlock("orphan", "table", frame_id="other-factory:v1.table")
    assert project.add_block(orphan) is False
    assert project.get_block("orphan") is None
    assert project.emit() == []


def test_build_orchestrates_validate_clone_init_emit_build_pipeline(tmp_path):
    project_path = tmp_path / "proj"
    factory_path = tmp_path / "catalog" / "backend-fastapi"
    base_dir = factory_path / "v1" / "base"
    base_dir.mkdir(parents=True)
    (base_dir / "hello.txt.j2").write_text("app={{ app.name }}")

    factory = Factory(
        name="backend-fastapi",
        version="v1",
        data={
            "pipelines": {
                "init": [{"name": "init-step", "cmd": "echo init"}],
                "build": [{"name": "build-step", "cmd": "echo build"}],
            }
        },
        path=factory_path,
    )
    project = make_project(
        path=project_path,
        config={"app": {"name": "Demo"}, "backend-fastapi": {}},
    )
    project.add_factory(factory)
    project.add_block(FakeBlock("users", "table", frame_id="backend-fastapi:v1.table"))

    order = []

    def track_execute(cmd, inputs=None, cwd=None):
        order.append(("shell", cmd, Path(cwd) if cwd else None))
        return 0

    original_emit = project.emit

    def track_emit():
        order.append(("emit",))
        return original_emit()

    with patch("utils.os.execute", side_effect=track_execute):
        project.emit = track_emit
        project.build()

    assert order[0] == ("shell", "echo init", project.get_factory_path("backend-fastapi"))
    assert order[1] == ("emit",)
    assert order[2] == ("shell", "echo build", project.get_factory_path("backend-fastapi"))

    cloned = project.get_factory_path("backend-fastapi") / "hello.txt"
    assert cloned.exists()
    assert cloned.read_text() == "app=Demo"
    assert (project.get_factory_path("backend-fastapi") / "users.out").exists()


def test_build_fails_fast_on_invalid_config(tmp_path):
    project = make_project(path=tmp_path / "proj", config={"app": {}})
    project.add_factory(make_factory_with_pipelines(path=tmp_path / "factory"))

    with patch("utils.os.execute") as execute:
        with pytest.raises(Exception):
            project.build()
        execute.assert_not_called()


def _emit_dockerfile(project, factory_name):
    context_dir = project.get_factory_path(factory_name)
    context_dir.mkdir(parents=True, exist_ok=True)
    (context_dir / "Dockerfile").write_text("FROM scratch")
    return context_dir


def test_package_builds_one_image_per_factory_with_a_dockerfile(tmp_path):
    project = make_project(path=tmp_path / "proj", config={"app": {"name": "My App"}})
    project.add_factory(make_factory_with_pipelines(path=tmp_path / "f", name="backend-fastapi"))
    context_dir = _emit_dockerfile(project, "backend-fastapi")

    with patch("core.Project.ImageBuilder") as Builder:
        Builder.return_value.build.return_value = 0
        tags = project.package()

    assert tags == ["my_app-backend-fastapi:p1"]
    Builder.assert_called_once_with(tool="docker")
    Builder.return_value.build.assert_called_once_with(
        context_dir=context_dir, tag="my_app-backend-fastapi:p1"
    )


def test_package_skips_factories_without_a_dockerfile(tmp_path):
    project = make_project(path=tmp_path / "proj")
    project.add_factory(make_factory_with_pipelines(path=tmp_path / "a", name="backend-fastapi"))
    project.add_factory(make_factory_with_pipelines(path=tmp_path / "b", name="frontend"))
    _emit_dockerfile(project, "backend-fastapi")  # only the backend ships one

    with patch("core.Project.ImageBuilder") as Builder:
        Builder.return_value.build.return_value = 0
        tags = project.package()

    assert tags == ["demo-backend-fastapi:p1"]
    assert Builder.return_value.build.call_count == 1


def test_package_raises_when_a_build_fails(tmp_path):
    project = make_project(path=tmp_path / "proj")
    project.add_factory(make_factory_with_pipelines(path=tmp_path / "f", name="backend-fastapi"))
    _emit_dockerfile(project, "backend-fastapi")

    with patch("core.Project.ImageBuilder") as Builder:
        Builder.return_value.build.return_value = 3
        with pytest.raises(ImageBuildError):
            project.package()


def test_package_uses_the_configured_tool(tmp_path):
    project = make_project(path=tmp_path / "proj")
    project.add_factory(make_factory_with_pipelines(path=tmp_path / "f", name="backend-fastapi"))
    _emit_dockerfile(project, "backend-fastapi")

    with patch("core.Project.ImageBuilder") as Builder:
        Builder.return_value.build.return_value = 0
        project.package(tool="podman")

    Builder.assert_called_once_with(tool="podman")


def test_package_raises_when_app_name_is_missing(tmp_path):
    project = make_project(path=tmp_path / "proj", config={"app": {}})

    with pytest.raises(ImageBuildError):
        project.package()
