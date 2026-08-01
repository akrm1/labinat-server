import pytest

from app.core.resources.Frame import Frame
from app.core.resources.Block import Block


class FakeFactory:
    def __init__(self, maps=None, frames=None):
        self.maps = maps or {}
        self.frames = frames or {}


class FakeProject:
    def __init__(self):
        self._blocks = {}

    def add_block(self, block):
        self._blocks[block.name] = block

    def get_block(self, name):
        return self._blocks.get(name)

    def get_block_type(self, name):
        block = self._blocks.get(name)
        return block.frame.name if block else None


@pytest.fixture
def frame_dirs(tmp_path):
    def _make(name):
        path = tmp_path / name
        (path / "bindings").mkdir(parents=True)
        (path / "concretes").mkdir(parents=True)
        return path

    return _make


def make_frame(path, name, data=None):
    return Frame(id=f"factory:v1.{name}", name=name, data=data or {}, path=path)


def test_load_registers_maps_and_bindings(frame_dirs):
    screen_frame = make_frame(frame_dirs("screen"), "screen")
    table_frame = make_frame(frame_dirs("table"), "table")

    block = Block(frame=screen_frame, name="myscreen", data={})
    factory = FakeFactory(
        maps={"status": {"active": "ACTIVE"}},
        frames={"table": table_frame},
    )
    project = FakeProject()

    block.load(project, factory)

    assert "map.status" in block.spec.types
    assert "binding.table" in block.spec.types


def test_validate_uses_frame_properties_and_required(frame_dirs):
    frame = make_frame(frame_dirs("table"), "table", data={
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
    })

    good_block = Block(frame=frame, name="users", data={"name": "Users"})
    good_block.validate()  # should not raise

    bad_block = Block(frame=frame, name="users2", data={"name": 123})  # wrong type
    with pytest.raises(Exception):
        bad_block.validate()


def test_validate_raises_when_block_data_is_empty_but_field_is_required(frame_dirs):
    """Regression test: `Spec.validate` used to return early whenever its
    data was empty/falsy, silently skipping `required`-field checks for an
    empty block. It must now raise just like any other missing-field case."""
    frame = make_frame(frame_dirs("table"), "table", data={
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
    })

    empty_block = Block(frame=frame, name="users3", data={})
    with pytest.raises(Exception):
        empty_block.validate()


def test_get_context_shape(frame_dirs):
    frame = make_frame(frame_dirs("table"), "table", data={"properties": {"name": {"type": "string"}}})
    block = Block(frame=frame, name="users", data={"name": "Users"})

    context = block.get_context()

    assert context["block"]["id"] == block.id
    assert context["block"]["name"] == "users"
    assert context["block"]["spec"] == {"name": "Users"}
    assert context["frame"]["name"] == "table"
    assert context["frame"]["id"] == frame.id


def test_binding_end_to_end_validate_and_decode(frame_dirs):
    """Full binding flow: a `screen` block references a `table` block via
    `@block.<name>`, validates against the registered BindingType, and
    decode() resolves it to the referenced frame's rendered binding output."""
    table_frame = make_frame(frame_dirs("table"), "table", data={
        "properties": {"name": {"type": "string"}},
    })
    (table_frame.path / "bindings" / "var.j2").write_text("TABLE:{{ src.block.name }}")
    table_frame.load_bindings()

    screen_frame = make_frame(frame_dirs("screen"), "screen", data={
        "properties": {"main": {"type": "binding.table"}},
    })

    project = FakeProject()
    factory = FakeFactory(frames={"table": table_frame})

    table_block = Block(frame=table_frame, name="users_table", data={"name": "Users"})
    table_block.load(project, factory)
    project.add_block(table_block)

    screen_block = Block(frame=screen_frame, name="home_screen", data={"main": "@block.users_table"})
    screen_block.load(project, factory)
    project.add_block(screen_block)

    screen_block.validate()  # "@block.users_table" resolves to type "table" -> matches binding.table

    decoded = screen_block.spec.decode()
    assert decoded["main"] == {"var": "TABLE:users_table"}


def test_binding_validate_fails_for_wrong_referenced_type(frame_dirs):
    table_frame = make_frame(frame_dirs("table"), "table")
    other_frame = make_frame(frame_dirs("other"), "other")

    screen_frame = make_frame(frame_dirs("screen"), "screen", data={
        "properties": {"main": {"type": "binding.table"}},
    })

    project = FakeProject()
    factory = FakeFactory(frames={"table": table_frame})

    other_block = Block(frame=other_frame, name="something", data={})
    other_block.load(project, factory)
    project.add_block(other_block)

    screen_block = Block(frame=screen_frame, name="home_screen", data={"main": "@block.something"})
    screen_block.load(project, factory)

    with pytest.raises(Exception):
        screen_block.validate()
