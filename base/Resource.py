from abc import ABC
from base.Spec import Spec
from utils.helpers import asjson, asyaml
from typing import Dict, Any


class Resource(ABC):
    def __init__(self, id: str, data: dict):
        self.__id: str   = id
        self.__spec: Spec = Spec(data)

    def reload(self, id: str, data: dict):
        self.__id: str = id
        self.__spec: Spec = Spec(data)

    def validate(self, jsonschema: dict):
        self.__spec.validate(jsonschema)

    def define_enum(self, name: str, items: Dict[str, Any]):
        self.__spec.define_enum(name, items)

    @property
    def id(self):
        return self.__id

    @property
    def spec(self):
        return self.__spec

    @property
    def info(self):
        return asjson({
            "id": self.__id,
            "spec": self.__spec.data
        })

    @property
    def info_as_yaml(self):
        return asyaml({
            "id": self.__id,
            "spec": self.__spec.data
        })

    def asjson(self):
        return asjson(self.__spec.data)

    def asyaml(self):
        return asyaml(self.__spec.data)

    def __str__(self):
        return f"{self.info}"

    def __repr__(self):
        return str(self.__id)
