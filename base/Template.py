from pathlib import Path
from typing import Callable, Union
from jinja2 import Environment, Template as JinjaTemplate
from base.filters import FILTERS_REGISTRY


class Template():
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
        cls.__env.filters[name] = filter_func

    @classmethod
    def from_string(cls, text: str) -> 'Template':
        jinja_template = cls.__env.from_string(text)
        template = cls(jinja_template, text)
        return template

    @classmethod
    def from_file(cls, filepath: Union[str, Path]) -> 'Template':
        filepath = Path(filepath)
        text = filepath.read_text(encoding='utf-8')
        jinja_template = cls.__env.from_string(text)

        template = cls(jinja_template, text)
        return template

    def render(self, context: dict = None) -> str:
        return self.__template.render(**(context or {}))

    def render_file(self, filepath: Union[str, Path], context: dict = None) -> str:
        result = self.render(context=context)
        
        filepath = Path(filepath)
        filepath.write_text(result, encoding='utf-8')

    def __str__(self) -> str:
        return self.__text

    def __repr__(self) -> str:
        return self.__text

