"""Emitted output file produced by a frame concrete template or static copy."""

from pathlib import Path
import shutil

from app.base.Template import Template
from utils import logger


class Concrete:
    """One named output artifact belonging to a frame.

    Template concretes live as `<name>.<ext>.j2` under `concretes/`; static
    files omit `.j2` and are copied verbatim on render.
    """

    def __init__(
        self,
        concretes_path: Path,
        name: str,
        extension: str,
        content: str,
        as_template: bool = True,
    ):
        self.__name: str = name
        self.__extension: str = extension.removeprefix(".")
        self.__content: str = content
        self.__is_template: bool = as_template

        j2 = ".j2" if self.__is_template else ""
        filename: str = f"{name}.{self.__extension}{j2}"
        self.__src: Path = concretes_path.joinpath(filename)
        self.__destination: Path = None
        logger.debug(
            "Concrete constructed",
            concrete=name,
            extension=self.__extension,
            is_template=as_template,
            src=str(self.__src),
        )

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
        """Jinja-render the destination path and store it for later `render()`."""
        rendered_destination = Template.from_string(str(destination)).render(context=context)
        self.__destination = Path(rendered_destination)
        logger.debug(
            "Concrete destination set",
            concrete=self.__name,
            destination=str(self.__destination),
        )

    def render(self, context: dict) -> Path:
        """Write this concrete to `destination` (render Jinja or copy static)."""
        if self.__destination is None:
            logger.error("Concrete render failed: destination not set", concrete=self.__name)
            raise RuntimeError("Destination path is not set")

        self.__destination.parent.mkdir(parents=True, exist_ok=True)

        if self.__is_template:
            Template.from_file(self.__src).render_file(filepath=self.__destination, context=context)
            logger.debug(
                "Concrete template rendered",
                concrete=self.__name,
                destination=str(self.__destination),
            )
        else:
            shutil.copy2(self.__src, self.__destination)
            logger.debug(
                "Concrete file copied",
                concrete=self.__name,
                destination=str(self.__destination),
            )

        return self.__destination

    def __str__(self) -> str:
        return self.__content

    def __repr__(self) -> str:
        return self.__content
