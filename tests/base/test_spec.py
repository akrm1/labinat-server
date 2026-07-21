import pytest

from base.Spec import Spec, Attribute
from base.types.DataType import DecodingError
from base.Schema import Schema
from tests.helpers import FakeType


def test_validate_noop_when_schema_is_empty():
    spec = Spec({"x": 1})
    spec.validate({})  # no schema to validate against -> should not raise


def test_validate_still_runs_when_data_is_empty():
    """Empty data must still be checked against the schema -- previously
    `Spec.validate` returned early whenever `self.__data` was falsy, which
    silently skipped `required`-field checks for an empty object."""
    spec = Spec({})
    spec.validate({"type": "object"})  # no required fields -> passes trivially


def test_validate_raises_for_empty_data_missing_required_field():
    spec = Spec({})

    with pytest.raises(Exception):
        spec.validate({"type": "object", "required": ["name"], "properties": {"name": {"type": "string"}}})


def test_validate_delegates_to_schema_and_raises_on_mismatch():
    spec = Spec({"x": "not-an-int"})
    jsonschema = {"type": "object", "properties": {"x": {"type": "integer"}}}

    with pytest.raises(Exception):
        spec.validate(jsonschema)


def test_define_map_registers_map_type_on_schema():
    spec = Spec({"x": "active"})
    spec.define_map("status", {"active": "ACTIVE"})

    assert "map.status" in spec.types


def test_decode_uses_registered_decoder_for_matching_type():
    spec = Spec({"x": "A"})
    spec.schema.define_type(FakeType("custom.a", "A", decoded_value="DECODED"))

    # simulate a validated schema so Attribute.from_schema_path can resolve "type"
    spec.validate({"type": "object", "properties": {"x": {"type": "custom.a"}}})

    decoded = spec.decode()
    assert decoded["x"] == "DECODED"


def test_decode_passes_through_value_when_no_decoder_registered():
    spec = Spec({"x": "A"})
    spec.validate({"type": "object", "properties": {"x": {"type": "string"}}})

    decoded = spec.decode()
    assert decoded["x"] == "A"


def test_decode_raises_aggregated_error_when_all_list_decoders_fail():
    """Regression test: previously, decode() silently returned the original
    value if every candidate decoder in a list-typed attribute failed."""
    spec = Spec({"x": "A"})  # matches custom.a so validation passes; decode still fails for both
    spec.schema.define_type(FakeType("custom.a", "A", fail_decode=True))
    spec.schema.define_type(FakeType("custom.b", "B", fail_decode=True))

    spec.validate({"type": "object", "properties": {"x": {"type": ["custom.a", "custom.b"]}}})

    with pytest.raises(DecodingError) as excinfo:
        spec.decode()

    message = str(excinfo.value)
    assert "custom.a" in message
    assert "custom.b" in message


def test_decode_recurses_through_nested_dict():
    spec = Spec({"parent": {"x": "A"}})
    spec.schema.define_type(FakeType("custom.a", "A", decoded_value="DECODED"))
    spec.validate({
        "type": "object",
        "properties": {
            "parent": {
                "type": "object",
                "properties": {"x": {"type": "custom.a"}},
            }
        },
    })

    decoded = spec.decode()
    assert decoded["parent"]["x"] == "DECODED"


def test_decode_recurses_through_list_items():
    spec = Spec({"items": ["A", "A"]})
    spec.schema.define_type(FakeType("custom.a", "A", decoded_value="DECODED"))
    spec.validate({
        "type": "object",
        "properties": {
            "items": {"type": "array", "items": {"type": "custom.a"}}
        },
    })

    decoded = spec.decode()
    assert decoded["items"] == ["DECODED", "DECODED"]


def test_attribute_from_schema_path_falls_back_to_jsonpath_when_flat_get_misses():
    """Regression test for KeyError raised when the schema didn't declare a
    `type` for a nested `columns.items.properties.type` shape."""
    schema = Schema({
        "type": "object",
        "properties": {
            "columns": {
                "type": "array",
                "items": {
                    "properties": {"type": {"type": "string"}}
                },
            }
        },
    })

    attribute = Attribute.from_schema_path(
        key="type",
        value="text",
        schema=schema,
        path="columns[0].type",
        schema_path="properties.columns.items.properties.type",
    )

    assert attribute.type == "string"


def test_attribute_asdict_converts_no_default_sentinel_to_none():
    attribute = Attribute(path="x", schema_path="properties.x", key="x", value=1, type="integer")
    result = attribute.asdict()

    assert result["default"] is None


def test_spec_dict_like_protocol():
    spec = Spec({"a": 1, "b": 2})

    assert spec["a"] == 1
    assert spec.get("missing", "default") == "default"
    assert "a" in spec
    assert len(spec) == 2
    assert set(spec.keys()) == {"a", "b"}

    del spec["a"]
    assert "a" not in spec
