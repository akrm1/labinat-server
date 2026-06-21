from base.CatalogResource import CatalogResource
from pathlib import Path
from typing import Union
from core.resources.Frame import Frame

class Factory(CatalogResource):
    def __init__(self, name: str, version: str, data: dict, path: Path):
        super().__init__(id=f'{name}:{version}', data=data, path=path)
        self.__name = name
        self.__version = version
        self.__frames = {}

    def reload(self, name: str = None, version: str = None, data: dict = None, path: Path = None):
        name = name if name else self.name
        version = version if version else self.version
        data = data if data else self.spec.data
        path = path if path else self.path

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
    def frames(self) -> dict[str, Frame]:
        return self.__frames

    @property
    def enums(self) -> dict[str, list[str]]:
        return self.spec.get('enums', {})

    @property
    def config(self) -> dict:
        return self.spec.get('config', {})

    @property
    def lifecycle(self) -> dict:
        return self.spec.get('lifecycle', {})

    def add_frame(self, frame: Frame):
        self.__frames[frame.name] = frame

    def get_frame(self, frame_name: str) -> Union[Frame, None]:
        return self.__frames.get(frame_name, None)