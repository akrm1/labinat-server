import pytest

from core.resources.Frame import Frame


@pytest.fixture
def frame_dirs(tmp_path):
    path = tmp_path / "frame"
    (path / "bindings").mkdir(parents=True)
    (path / "concretes").mkdir(parents=True)
    return path


class FakeBlock:
    def __init__(self, name):
        self._name = name

    def get_context(self, decode: bool = False):
        return {"block": {"name": self._name}}


def make_frame(path, name="table", data=None):
    return Frame(id=f"factory:v1.{name}", name=name, data=data or {}, path=path)


def test_load_bindings_reads_j2_templates_keyed_by_stem(frame_dirs):
    (frame_dirs / "bindings" / "var.j2").write_text("{{ src.block.name }}")
    (frame_dirs / "bindings" / "literal.j2").write_text("literal text")

    frame = make_frame(frame_dirs)
    frame.load_bindings()

    result = frame.bind(FakeBlock("users"), FakeBlock("screen1"))
    assert set(result.keys()) == {"var", "literal"}
    assert result["literal"] == "literal text"


def test_bind_renders_with_src_and_dest_context_keys(frame_dirs):
    """Regression test for the historical `self`-key Jinja crash: `bind()`
    must expose the two blocks as `src`/`dest`, not `self`/`other`."""
    (frame_dirs / "bindings" / "var.j2").write_text("{{ src.block.name }}-{{ dest.block.name }}")

    frame = make_frame(frame_dirs)
    frame.load_bindings()

    result = frame.bind(FakeBlock("users_table"), FakeBlock("home_screen"))
    assert result == {"var": "users_table-home_screen"}


def test_create_binding_writes_template_file_to_disk(frame_dirs):
    frame = make_frame(frame_dirs)
    frame.create_binding("var", "{{ src.block.name }}")

    created = frame_dirs / "bindings" / "var.j2"
    assert created.exists()
    assert created.read_text() == "{{ src.block.name }}"


def test_create_concrete_writes_file_and_registers_it(frame_dirs):
    frame = make_frame(frame_dirs)
    frame.create_concrete("model", "py", "class {{ block.name }}: pass")

    created = frame_dirs / "concretes" / "model.py.j2"
    assert created.exists()
    assert "model" in frame.concretes


def test_load_concretes_reads_files_from_disk(frame_dirs):
    (frame_dirs / "concretes" / "model.py.j2").write_text("class {{ block.name }}: pass")

    frame = make_frame(frame_dirs)
    frame.load_concretes()

    assert "model" in frame.concretes
    concrete = frame.concretes["model"]
    assert concrete.extension == "py"
    assert concrete.is_template is True


def test_render_writes_rendered_concrete_to_destination(frame_dirs):
    (frame_dirs / "concretes" / "model.py.j2").write_text("class {{ block.name }}: pass")

    frame = make_frame(frame_dirs, data={
        "concretes": [{"name": "model.py", "destination": "{{ block.name }}_model.py"}]
    })
    frame.load_concretes()

    destination_root = frame_dirs.parent / "out"
    context = {"block": {"name": "Users"}}

    rendered_paths = frame.render(destination_root=destination_root, context=context)

    assert len(rendered_paths) == 1
    output_file = destination_root / "Users_model.py"
    assert output_file.exists()
    assert output_file.read_text() == "class Users: pass"


def test_reload_reloads_module_concretes_and_bindings(frame_dirs):
    (frame_dirs / "module.py").write_text("VALUE = 1\n")

    frame = make_frame(frame_dirs)
    frame.load()
    assert frame.module["VALUE"] == 1

    (frame_dirs / "module.py").write_text("VALUE = 2\n")
    frame.reload()
    assert frame.module["VALUE"] == 2
