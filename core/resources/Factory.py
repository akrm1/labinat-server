"""Catalog factory: versioned stack profile holding frames and pipelines."""

from base.CatalogResource import CatalogResource
from pathlib import Path
from typing import Union, TYPE_CHECKING

from utils import logger

if TYPE_CHECKING:
    from core.resources.Frame import Frame


class Factory(CatalogResource):
    """Versioned catalog package: maps, config schema, pipelines, and frames.

    Identity is `name:version`. On-disk path is the factory root; frames live
    under `version_path/frames/`. Spec data holds `maps`, `config`, `pipelines`.
    """

    def __init__(self, name: str, version: str, data: dict, path: Path):
        super().__init__(id=f'{name}:{version}', data=data, path=path)
        self.__name = name
        self.__version = version
        self.__frames = {}
        logger.debug("Factory constructed", factory=self.id, path=str(path))

    def reload(self, name: str = None, version: str = None, data: dict = None, path: Path = None):
        """Replace identity/data/path and clear the in-memory frame registry."""
        name = name if name else self.name
        version = version if version else self.version
        data = data if data else self.spec.data
        path = path if path else self.path

        logger.debug(
            "Factory reloading",
            factory=f"{name}:{version}",
            previous=self.id,
        )
        super().reload(id=f'{name}:{version}', data=data, path=path)
        self.__name = name
        self.__version = version
        self.__frames = {}

    @property
    def name(self) -> str:
        return self.__name

    @property
    def version(self) -> str:
        return self.__version

    @property
    def version_path(self) -> Path:
        return self.path.joinpath(self.__version)

    @property
    def description(self) -> str:
        return self.spec.get('description', '')

    @property
    def frames(self) -> dict[str, "Frame"]:
        return self.__frames

    @property
    def maps(self) -> dict[str, list[str]]:
        return self.spec.get('maps', {})

    @property
    def config(self) -> dict:
        return self.spec.get('config', {})

    @property
    def pipelines(self) -> dict:
        """Optional named shell pipelines (`init`, `build`, `run`, `debug`, `release`)."""
        return self.spec.get('pipelines', {})

    def add_frame(self, frame: "Frame"):
        """Register a frame under this factory (keyed by frame name)."""
        logger.debug("Factory adding frame", factory=self.id, frame=frame.name)
        self.__frames[frame.name] = frame

    def get_frame(self, frame_name: str) -> Union["Frame", None]:
        """Return a frame by name, or None if it is not registered."""
        frame = self.__frames.get(frame_name, None)
        if frame is None:
            logger.debug("Factory frame not found", factory=self.id, frame=frame_name)
        return frame
