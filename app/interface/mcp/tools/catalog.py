"""Catalog tools: browse and author factories and frames."""

from typing import List, Optional

from app.interface.mcp.auth import authorize
from app.interface.mcp.tools._common import ToolError, catalog
from app.interface.permissions import CATALOG_READ as READ, CATALOG_WRITE as WRITE
from app.interface.serializers import factory_to_dict, frame_to_dict


def register(mcp) -> None:
    @mcp.tool()
    def list_factories() -> list:
        """List every factory (and version) in the catalog."""
        authorize(READ)
        return [factory_to_dict(factory) for factory in catalog().get_all_factories().values()]

    @mcp.tool()
    def get_factory(name: str, version: str) -> dict:
        """Get one factory version, including its frames, config, and pipelines."""
        authorize(READ)
        factory = catalog().get_factory(name, version)
        if factory is None:
            raise ToolError(f"Factory not found: {name}:{version}")
        return factory_to_dict(factory)

    @mcp.tool()
    def create_factory(
        name: str,
        version: str,
        data: Optional[dict] = None,
        frames: Optional[List[str]] = None,
    ) -> dict:
        """Create a factory version. `data` is the factory spec; `frames` names the
        frames to scaffold inside it. Names must not contain dots."""
        authorize(WRITE)
        factory = catalog().create_factory(name, version, data or {}, frames or [])
        return factory_to_dict(factory)

    @mcp.tool()
    def get_frame(name: str, version: str, frame: str) -> dict:
        """Get one frame from a factory version, with its spec and concretes."""
        authorize(READ)
        result = catalog().get_frame(name, version, frame)
        if result is None:
            raise ToolError(f"Frame not found: {name}:{version}.{frame}")
        return frame_to_dict(result)

    @mcp.tool()
    def create_frame(name: str, version: str, frame_name: str, data: Optional[dict] = None) -> dict:
        """Add a frame to a factory version. Fails if the frame exists or the
        factory is missing. The frame name must not contain dots."""
        authorize(WRITE)
        frame = catalog().create_frame(name, version, frame_name, data or {})
        if frame is None:
            raise ToolError("Frame already exists or factory not found")
        return frame_to_dict(frame)
