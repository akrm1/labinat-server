from base.Template import Template
import shutil
from pathlib import Path

class Concrete:
    def __init__(self, concretes_path: Path, name: str, extension: str, content: str, as_template: bool = True):
        self.__name: str = name
        self.__extension: str = extension.removeprefix(".")
        self.__content: str = content
        self.__is_template: bool = as_template

        j2 = ".j2" if self.__is_template else ""
        filename: str = f"{name}.{extension}{j2}"
        self.__src: Path = concretes_path.joinpath(filename)
        self.__destination: Path = None

    @property
    def name(self) -> str:
        return self.__name

    @property
    def extension(self) -> str:
        return self.__extension

    @property
    def content(self) -> str:
        return self.__content

    @property
    def is_template(self) -> bool:
        return self.__is_template

    @property
    def src(self) -> Path:
        return self.__src

    @property
    def destination(self) -> Path:
        return self.__destination

    def set_destination(self, destination: Path, context: dict = None):
        rendered_destination = Template.from_string(str(destination)).render(context=context)
        self.__destination = Path(rendered_destination)

    def render(self, context: dict) -> Path:
        if self.__destination is None:
            raise RuntimeError("Destination path is not set")

        self.__destination.parent.mkdir(parents=True, exist_ok=True)

        if self.__is_template:
            Template.from_file(self.__src).render_file(filepath=self.__destination, context=context)
        else:
            shutil.copy2(self.__src, self.__destination)     

        return self.__destination

    def __str__(self) -> str:
        return self.__content

    def __repr__(self) -> str:
        return self.__content