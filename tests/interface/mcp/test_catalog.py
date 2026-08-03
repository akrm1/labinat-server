"""Catalog tools against an empty catalog."""

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from tests.interface.mcp.conftest import call


def test_list_factories_is_empty_on_a_fresh_catalog(server):
    assert call(server, "list_factories") == []


def test_get_missing_factory_raises_a_clean_error(server):
    with pytest.raises(ToolError) as exc:
        call(server, "get_factory", name="nope", version="1")
    assert "Factory not found: nope:1" in str(exc.value)


def test_get_missing_frame_raises_a_clean_error(server):
    with pytest.raises(ToolError) as exc:
        call(server, "get_frame", name="nope", version="1", frame="f")
    assert "Frame not found" in str(exc.value)
