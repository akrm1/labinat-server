"""Workspace block: a project-owned instance of a catalog frame."""

from typing import TYPE_CHECKING
from pathlib import Path

from base.Resource import Resource
from base.Binding import Binding
from base.Spec import Spec
from utils import logger

if TYPE_CHECKING:
    from core.resources.Factory import Factory
    from core.resources.Frame import Frame
    from core.Project import Project


class Block(Resource):
    """One validated instance of a `Frame` inside a `Project`.

    Identity is `frame.id.block_name`. Data is validated against the frame's
    property schema. `load()` registers factory maps and cross-frame bindings
    so `@block.*` expressions can resolve during decode/emit.
    """

    def __init__(self, frame: "Frame", name: str, data: dict):
        super().__init__(id=f'{frame.id}.{name}', data=data)
        self.__name: str = name
        self.__frame: "Frame" = frame
        logger.debug(
            "Block constructed",
            block=self.id,
            frame=frame.id,
            name=name,
        )

    def load(self, project: "Project", factory: "Factory"):
        """Register factory maps and frame bindings onto this block's Spec."""
        logger.debug(
            "Block loading maps and bindings",
            block=self.id,
            factory=factory.id if hasattr(factory, "id") else None,
            maps=len(factory.maps),
            frames=len(factory.frames),
        )
        for map_name, map_items in factory.maps.items():
            self.define_map(map_name, map_items)

        for frame in factory.frames.values():
            self.define_binding(self, frame.name, [
                Binding(
                    binding_object="block",
                    type_fetcher=project.get_block_type,
                    object_fetcher=project.get_block,
                    binder=frame.bind
                )
            ])
        logger.debug("Block load finished", block=self.id)

    @property
    def name(self) -> str:
        return self.__name

    @property
    def frame(self) -> "Frame":
        return self.__frame

    def validate(self):
        """Validate block data against the frame's properties/required schema."""
        logger.debug("Block validating", block=self.id, frame=self.__frame.id)
        block_schema = {
            "type": "object",
            "properties": self.__frame.spec.get('properties', {}),
            "required": self.__frame.spec.get('required', [])
        }

        try:
            self.spec.validate(block_schema)
        except Exception:
            logger.warning("Block validation failed", block=self.id)
            raise
        logger.debug("Block validation passed", block=self.id)

    def get_context(self, decode: bool = False) -> dict:
        """Jinja/context payload for this block (optionally with decoded Spec)."""
        spec: Spec = self.spec.decode() if decode else self.spec
        return {
            "block": {
                "id": self.id,
                "name": self.name,
                "spec": spec.data
            },
            "frame": {
                "id": self.__frame.id,
                "name": self.__frame.name,
                "path": self.__frame.path
            }
        }

    def build(self, destination_root: Path) -> list[Path]:
        """Decode bindings/maps and render this block's frame concretes to disk."""
        logger.info(
            "Block build starting",
            block=self.id,
            destination=str(destination_root),
        )
        context: dict = self.get_context(decode=True)
        paths = self.__frame.render(destination_root=destination_root, context=context)
        logger.info(
            "Block build finished",
            block=self.id,
            files=len(paths),
        )
        return paths
