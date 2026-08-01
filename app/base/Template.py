"""Jinja2 template wrapper shared by bindings, concretes, and directory trees."""

from pathlib import Path
from typing import Callable, Union
from jinja2 import Environment, Template as JinjaTemplate
from app.base.filters import FILTERS_REGISTRY
from utils import logger


class Template():
    """Thin wrapper around a Jinja2 template with Labinat filters registered."""

    # Jinja filters/functions shared by every render call. This is the lightweight,
    # growable home for the "functions/actions" available inside templates.
    __env = Environment()
    __env.filters.update(FILTERS_REGISTRY)

    def __init__(self, jinja_template: JinjaTemplate, text: str):
        self.__template: JinjaTemplate = jinja_template
        self.__text: str = text

    @property
    def filters(self) -> dict:
        return self.__env.filters

    @property
    def text(self) -> str:
        return self.__text

    @classmethod
    def register_filter(cls, name: str, filter_func: Callable) -> None:
        """Register a custom Jinja filter available to all templates."""
        cls.__env.filters[name] = filter_func
        logger.debug("Jinja filter registered", filter=name)

    @classmethod
    def from_string(cls, text: str) -> 'Template':
        """Build a Template from an in-memory string."""
        jinja_template = cls.__env.from_string(text)
        return cls(jinja_template, text)

    @classmethod
    def from_file(cls, filepath: Union[str, Path]) -> 'Template':
        """Load a Template from a UTF-8 text file on disk."""
        filepath = Path(filepath)
        text = filepath.read_text(encoding='utf-8')
        jinja_template = cls.__env.from_string(text)
        logger.debug("Template loaded from file", path=str(filepath))
        return cls(jinja_template, text)

    def render(self, context: dict = None) -> str:
        """Render this template with the given context dict."""
        return self.__template.render(**(context or {}))

    def render_file(self, filepath: Union[str, Path], context: dict = None) -> str:
        """Render to a string and write it to `filepath`."""
        result = self.render(context=context)
        filepath = Path(filepath)
        filepath.write_text(result, encoding='utf-8')
        logger.debug("Template written to file", path=str(filepath))
        return result

    def __str__(self) -> str:
        return self.__text

    def __repr__(self) -> str:
        return self.__text
