import pytest

from base.types.DataType import DataType
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


def test_decode_unknown_key_raises_key_error():
    m = Map("status", {"active": "ACTIVE"})
    with pytest.raises(KeyError):
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


def test_map_registers_itself_in_data_type_decoders():
    Map("status", {"active": "ACTIVE"})
    assert "map.status" in DataType.DECODERS


def test_dict_like_protocol():
    m = Map("status", {"active": "ACTIVE"})

    assert len(m) == 1
    assert "active" in m
    assert list(iter(m)) == ["active"]

    m["inactive"] = "INACTIVE"
    assert m["inactive"] == "INACTIVE"

    del m["inactive"]
    assert "inactive" not in m
