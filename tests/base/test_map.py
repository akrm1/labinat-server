import pytest

from base.Spec import Spec
from base.types.DataType import DecodingError
from base.types.Map import Map


def test_map_name_is_prefixed():
    m = Map("status", {"active": "ACTIVE"})
    assert m.name == "map.status"


def test_validate_true_for_known_key_false_for_unknown():
    m = Map("status", {"active": "ACTIVE", "inactive": "INACTIVE"})

    assert m.validate("active") is True
    assert m.validate("unknown") is False


def test_decode_returns_mapped_value():
    m = Map("status", {"active": "ACTIVE"})
    assert m.decode("active") == "ACTIVE"


def test_decode_unknown_key_raises_decoding_error():
    m = Map("status", {"active": "ACTIVE"})
    with pytest.raises(DecodingError):
        m.decode("unknown")


def test_add_item_defaults_value_to_key_when_value_is_none():
    m = Map("status", {})
    m.add_item("active")

    assert m["active"] == "active"


def test_invalid_msg_lists_expected_values():
    m = Map("status", {"active": "ACTIVE", "inactive": "INACTIVE"})
    message = m.invalid_msg("x", "bogus", "string")

    assert "active" in message
    assert "inactive" in message
    assert "bogus" in message


def test_map_registers_itself_on_the_schema_it_is_defined_on():
    spec = Spec({})
    spec.define_map("status", {"active": "ACTIVE"})

    assert "map.status" in spec.types


def test_same_named_maps_on_different_specs_do_not_collide():
    """Registration is per-Schema, so one Spec's `map.status` cannot be
    overwritten by a later Spec that happens to define the same name."""
    schema = {"properties": {"state": {"type": "map.status"}}}

    first = Spec({"state": "active"})
    first.define_map("status", {"active": "FIRST"})
    first.validate(schema)

    second = Spec({"state": "active"})
    second.define_map("status", {"active": "SECOND"})
    second.validate(schema)

    assert first.decode()["state"] == "FIRST"
    assert second.decode()["state"] == "SECOND"


def test_dict_like_protocol():
    m = Map("status", {"active": "ACTIVE"})

    assert len(m) == 1
    assert "active" in m
    assert list(iter(m)) == ["active"]

    m["inactive"] = "INACTIVE"
    assert m["inactive"] == "INACTIVE"

    del m["inactive"]
    assert "inactive" not in m
