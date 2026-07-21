import pytest

from base.Schema import Schema, ValidationError, MissingKeyError, UndefinedTypeError
from tests.helpers import FakeType


def make_schema(type_spec):
    return Schema({
        "type": "object",
        "properties": {"x": {"type": type_spec}},
    })


def test_single_custom_type_passes_when_value_matches():
    schema = make_schema("custom.a")
    schema.define_type(FakeType("custom.a", "A"))

    schema.validate({"x": "A"})  # should not raise


def test_single_custom_type_fails_when_value_does_not_match():
    schema = make_schema("custom.a")
    schema.define_type(FakeType("custom.a", "A"))

    with pytest.raises(ValidationError):
        schema.validate({"x": "Z"})


def test_list_of_custom_types_passes_if_any_type_matches():
    schema = make_schema(["custom.a", "custom.b"])
    schema.define_type(FakeType("custom.a", "A"))
    schema.define_type(FakeType("custom.b", "B"))

    schema.validate({"x": "A"})
    schema.validate({"x": "B"})


def test_list_of_custom_types_does_not_crash_and_raises_cleanly():
    """Regression test for the historical `unhashable type: 'list'` crash
    when `type` was a list and every candidate type failed validation."""
    schema = make_schema(["custom.a", "custom.b"])
    schema.define_type(FakeType("custom.a", "A"))
    schema.define_type(FakeType("custom.b", "B"))

    with pytest.raises(ValidationError) as excinfo:
        schema.validate({"x": "Z"})

    message = str(excinfo.value)
    assert "custom.a" in message
    assert "custom.b" in message


def test_missing_required_field_raises_missing_key_error():
    schema = Schema({
        "type": "object",
        "required": ["x"],
        "properties": {"x": {"type": "string"}},
    })

    with pytest.raises(MissingKeyError):
        schema.validate({})


def test_unregistered_single_type_raises_undefined_type_error():
    schema = make_schema("custom.unknown")

    with pytest.raises(UndefinedTypeError):
        schema.validate({"x": "anything"})


def test_primitive_type_still_validates_normally():
    schema = Schema({
        "type": "object",
        "properties": {"x": {"type": "integer"}},
    })

    schema.validate({"x": 1})

    with pytest.raises(ValidationError):
        schema.validate({"x": "not an integer"})


def test_define_type_registers_under_its_name():
    schema = Schema({})
    fake = FakeType("custom.a", "A")
    schema.define_type(fake)

    assert schema.types["custom.a"] is fake


def test_get_and_getitem_resolve_nested_schema_values():
    schema = Schema({
        "type": "object",
        "properties": {
            "columns": {
                "type": "array",
                "items": {"properties": {"type": {"type": "string"}}},
            }
        },
    })

    assert schema.get("properties.columns.items.properties.type.type") == "string"
    assert schema["properties.columns.items.properties.type.type"] == "string"
    assert schema.get("properties.missing.type", "default") == "default"
