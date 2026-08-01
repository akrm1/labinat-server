"""Render a directory tree of Jinja templates (and static files) to a destination."""

from pathlib import Path
from typing import Union
from app.base.Template import Template
from utils import logger
import os
import shutil


class DirectoryTemplate():
    """Recursively render a source directory into `dest_path` using Jinja.

    File and directory names may themselves be Jinja templates. Files ending
    in `.j2` are rendered; other files are copied as-is.
    """

    def __init__(self, path: Union[str, Path]):
        self.__path: Path = Path(path)

    @property
    def path(self) -> Path:
        return self.__path

    def render(self, dest_path: Union[str, Path], context: dict = None) -> list[Path]:
        """Render this template tree into `dest_path` and return written paths."""
        context = context if context is not None else {}
        src_path = self.__path
        dest_path = Path(dest_path)
        logger.info("DirectoryTemplate render starting", src=str(src_path), dest=str(dest_path))

        if src_path.is_file():
            output_paths = [self.__render_file(src_filepath=src_path, dest_path=dest_path, context=context)]
        else:
            output_paths = self.__render_dir(src_path=src_path, dest_path=dest_path, context=context)

        logger.info("DirectoryTemplate render finished", files=len(output_paths), dest=str(dest_path))
        return output_paths

    def __render_file(self, src_filepath: Path, dest_path: Path, context: dict = None) -> Path:
        dest_path.mkdir(parents=True, exist_ok=True)

        if src_filepath.suffix == ".j2":
            rendered_name = Template.from_string(text=src_filepath.name).render(context=context)
            filename = Path(rendered_name).stem
            dest_filepath = dest_path.joinpath(filename)
            Template.from_file(filepath=src_filepath).render_file(filepath=dest_filepath, context=context)
            logger.debug("Rendered template file", src=str(src_filepath), dest=str(dest_filepath))
        else:
            dest_filepath = dest_path.joinpath(src_filepath.name)
            shutil.copy2(src_filepath, dest_filepath)
            logger.debug("Copied static file", src=str(src_filepath), dest=str(dest_filepath))

        return dest_filepath

    def __render_dir(self, src_path: Path, dest_path: Path, context: dict = None) -> list[Path]:
        output_paths = []

        with os.scandir(src_path) as it:
            entries = sorted(it, key=lambda entry: entry.name)

        for entry in entries:
            child_path = Path(entry.path)
            if entry.is_dir(follow_symlinks=False):
                dirname = Template.from_string(text=entry.name).render(context=context)
                result_paths = self.__render_dir(src_path=child_path, dest_path=dest_path.joinpath(dirname), context=context)
                output_paths.extend(result_paths)
            else:
                result_path = self.__render_file(src_filepath=child_path, dest_path=dest_path, context=context)
                output_paths.append(result_path)

        return output_paths
