from base.Resource import Resource
from core.resources.Factory import Factory
from core.resources.Frame import Frame

class Block(Resource):
    def __init__(self, factory: Factory, frame: Frame, name: str, data: dict):
        super().__init__(id=f'{frame.id}.{name}', data=data)
        self.__name = name
        self.__frame = frame

        for enum_name, enum_items in factory.enums.items():
            self.define_enum(enum_name, enum_items)

    @property
    def name(self) -> str:
        return self.__name

    @property
    def frame(self) -> Frame:
        return self.__frame

    def validate(self):
        block_schema = {
            "type": "object",
            "properties": self.__frame.spec.get('properties', {}),
            "required": self.__frame.spec.get('required', [])
        }

        self.spec.validate(block_schema)
