"""Serializer guards: block/frame responses must read the real Spec accessor.

These use a real `Spec` (whose data accessor is `.data`, not `.asdict()`), so a
wrong method name here fails loudly instead of only surfacing as a live 500.
"""

from types import SimpleNamespace

from app.base.Spec import Spec
from app.api.serializers import block_to_dict, frame_to_dict


def test_block_to_dict_uses_spec_data():
    spec = Spec({"name": "users", "columns": [{"name": "id"}]})
    block = SimpleNamespace(
        id="backend:v1.table.users",
        name="users",
        frame=SimpleNamespace(name="table"),
        spec=spec,
    )

    assert block_to_dict(block) == {
        "id": "backend:v1.table.users",
        "name": "users",
        "frame": "table",
        "data": {"name": "users", "columns": [{"name": "id"}]},
    }


def test_frame_to_dict_uses_spec_data():
    spec = Spec({"module": "table", "concretes": {}})
    frame = SimpleNamespace(
        id="backend:v1.table",
        name="table",
        spec=spec,
        concretes={"model": object(), "schema": object()},
    )

    result = frame_to_dict(frame)
    assert result["id"] == "backend:v1.table"
    assert result["spec"] == {"module": "table", "concretes": {}}
    assert sorted(result["concretes"]) == ["model", "schema"]
