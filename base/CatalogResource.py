from abc import ABC
from pathlib import Path
from base.Resource import Resource


class CatalogResource(Resource, ABC):
    def __init__(self, id: str, data: dict, path: Path):
        super().__init__(id, data)
        self.__path: Path = path

    def reload(self, id: str, data: dict, path: Path):
        super().reload(id, data)
        self.__path: Path = path

    @property
    def path(self):
        return self.__path
