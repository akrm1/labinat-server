"""Base resource types that wrap a Spec of JSON data."""

from abc import ABC
from app.base.Spec import Spec
from utils.helpers import asjson, asyaml
from utils import logger
from typing import Dict, Any, List
from app.base.Binding import Binding


class Resource(ABC):
    """Abstract domain object identified by `id` and backed by a Spec.

    Factories, frames, and blocks all inherit from this so they share
    validation and custom-type registration (`map.*`, `binding.*`).
    """

    def __init__(self, id: str, data: dict):
        self.__id: str = id
        self.__spec: Spec = Spec(data)
        logger.debug("Resource created", resource_id=id)

    def reload(self, id: str, data: dict):
        """Replace identity and Spec data in place."""
        logger.debug("Resource reloading", resource_id=id, previous_id=self.__id)
        self.__id: str = id
        self.__spec: Spec = Spec(data)

    def validate(self, jsonschema: dict):
        """Validate this resource's Spec against a JSON Schema document."""
        logger.debug("Resource validating", resource_id=self.__id)
        try:
            self.__spec.validate(jsonschema)
        except Exception:
            logger.error("Resource validation failed", resource_id=self.__id)
            raise
        logger.debug("Resource validation passed", resource_id=self.__id)

    def define_map(self, name: str, items: Dict[str, Any]):
        """Register a `map.<name>` custom type on this resource's Spec."""
        logger.debug("Resource defining map", resource_id=self.__id, map=name)
        self.__spec.define_map(name, items)

    def define_binding(self, dest_object: Any, name: str, bindings: List[Binding]):
        """Register a `binding.<name>` custom type on this resource's Spec."""
        logger.debug("Resource defining binding", resource_id=self.__id, binding=name)
        self.__spec.define_binding(dest_object, name, bindings)

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
