"""Catalog-backed resources that also live on disk under a Path."""

from abc import ABC
from pathlib import Path
from base.Resource import Resource
from utils import logger


class CatalogResource(Resource, ABC):
    """A Resource that has an on-disk directory (factory/frame layout)."""

    def __init__(self, id: str, data: dict, path: Path):
        super().__init__(id, data)
        self.__path: Path = path
        logger.debug("CatalogResource created", resource_id=id, path=str(path))

    def reload(self, id: str, data: dict, path: Path):
        """Replace identity, Spec data, and on-disk path."""
        logger.debug("CatalogResource reloading", resource_id=id, path=str(path))
        super().reload(id, data)
        self.__path: Path = path

    @property
    def path(self):
        """Absolute/relative filesystem path for this catalog resource."""
        return self.__path
