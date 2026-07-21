import pytest

from base.Binding import Binding
from base.types.BindingType import BindingType, BindingException


class DummyDest:
    pass


def make_binding(binding_object="block", type_map=None, objects=None, bind_result="RENDERED"):
    type_map = type_map or {}
    objects = objects or {}

    return Binding(
        binding_object=binding_object,
        type_fetcher=lambda value: type_map.get(value),
        object_fetcher=lambda value: objects.get(value),
        binder=lambda src, dest: bind_result,
    )


def test_name_and_expected_type_derived_from_binding_type():
    bt = BindingType(DummyDest(), "table", [make_binding()])
    assert bt.name == "binding.table"
    assert bt.expected_type == "table"


def test_validate_true_when_type_matches():
    binding = make_binding(type_map={"users": "table"})
    bt = BindingType(DummyDest(), "table", [binding])

    assert bt.validate("@block.users") is True


def test_validate_false_for_non_string_value():
    bt = BindingType(DummyDest(), "table", [make_binding()])
    assert bt.validate(123) is False


def test_validate_false_when_missing_at_prefix():
    bt = BindingType(DummyDest(), "table", [make_binding()])
    assert bt.validate("block.users") is False


def test_validate_false_for_malformed_binding_string():
    bt = BindingType(DummyDest(), "table", [make_binding()])
    assert bt.validate("@block.users.extra") is False
    assert bt.validate("@blockonly") is False


def test_validate_false_for_unknown_binding_object():
    binding = make_binding(binding_object="block", type_map={"users": "table"})
    bt = BindingType(DummyDest(), "table", [binding])

    assert bt.validate("@unknown.users") is False


def test_validate_false_for_type_mismatch():
    binding = make_binding(type_map={"users": "screen"})
    bt = BindingType(DummyDest(), "table", [binding])

    assert bt.validate("@block.users") is False


def test_decode_happy_path_returns_binder_result():
    dest = DummyDest()
    binding = make_binding(type_map={"users": "table"}, objects={"users": "SRC_OBJ"}, bind_result="RENDERED")
    bt = BindingType(dest, "table", [binding])

    assert bt.decode("@block.users") == "RENDERED"


def test_decode_raises_for_unknown_binding_object():
    binding = make_binding(type_map={"users": "table"})
    bt = BindingType(DummyDest(), "table", [binding])

    with pytest.raises(BindingException):
        bt.decode("@unknown.users")


def test_decode_raises_for_type_mismatch_consistent_with_validate():
    """Regression test: decode() must reject the same type mismatch that
    validate() rejects, instead of silently binding through the wrong type."""
    binding = make_binding(type_map={"users": "screen"})
    bt = BindingType(DummyDest(), "table", [binding])

    with pytest.raises(BindingException):
        bt.decode("@block.users")


def test_decode_raises_when_resource_not_found():
    binding = make_binding(type_map={"users": "table"}, objects={})
    bt = BindingType(DummyDest(), "table", [binding])

    with pytest.raises(BindingException):
        bt.decode("@block.users")


def test_invalid_msg_for_non_string_value():
    bt = BindingType(DummyDest(), "table", [make_binding()])
    message = bt.invalid_msg("x", 123, "integer")
    assert "binding.table" in message


def test_invalid_msg_for_missing_at_prefix():
    bt = BindingType(DummyDest(), "table", [make_binding()])
    message = bt.invalid_msg("x", "block.users", "string")
    assert "must start with" in message


def test_invalid_msg_for_malformed_shape():
    bt = BindingType(DummyDest(), "table", [make_binding()])
    message = bt.invalid_msg("x", "@block.users.extra", "string")
    assert "pattern" in message


def test_invalid_msg_for_unknown_binding_object():
    binding = make_binding(binding_object="block", type_map={"users": "table"})
    bt = BindingType(DummyDest(), "table", [binding])

    message = bt.invalid_msg("x", "@unknown.users", "string")
    assert "unknown" in message


def test_invalid_msg_for_type_mismatch():
    binding = make_binding(binding_object="block", type_map={"users": "screen"})
    bt = BindingType(DummyDest(), "table", [binding])

    message = bt.invalid_msg("x", "@block.users", "string")
    assert "expected 'table'" in message
    assert "screen" in message


def test_invalid_msg_for_resource_not_found():
    binding = make_binding(binding_object="block", type_map={"users": "table"})
    bt = BindingType(DummyDest(), "table", [binding])

    message = bt.invalid_msg("x", "@block.users", "string")
    assert "not found" in message
