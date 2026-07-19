from typing import TYPE_CHECKING
from pathlib import Path
from base.Resource import Resource
from base.Binding import Binding
from base.Spec import Spec

if TYPE_CHECKING:
    from core.resources.Factory import Factory
    from core.resources.Frame import Frame
    from core.Project import Project

class Block(Resource):
    def __init__(self, frame: "Frame", name: str, data: dict):
        super().__init__(id=f'{frame.id}.{name}', data=data)
        self.__name: str = name
        self.__frame: "Frame" = frame

    def load(self, project: "Project", factory: "Factory"):
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

    @property
    def name(self) -> str:
        return self.__name

    @property
    def frame(self) -> "Frame":
        return self.__frame

    def validate(self):
        block_schema = {
            "type": "object",
            "properties": self.__frame.spec.get('properties', {}),
            "required": self.__frame.spec.get('required', [])
        }

        self.spec.validate(block_schema)

    def get_context(self, decode: bool = False) -> dict:
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
        context: dict = self.get_context(decode=True)
        return self.__frame.render(destination_root=destination_root, context=context)
