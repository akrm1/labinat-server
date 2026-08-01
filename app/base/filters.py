import re
from typing import Any, Callable

FILTERS_REGISTRY = {}

def jinja_filter(func: Callable) -> Callable:
    FILTERS_REGISTRY[func.__name__] = func
    return func

def _to_words(value: Any) -> list[str]:
    text = str(value)
    text = re.sub(r"[\s\-]+", "_", text)
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", text)
    return [word for word in text.split("_") if word]


@jinja_filter
def snake(value: Any) -> str:
    return "_".join(word.lower() for word in _to_words(value))

@jinja_filter
def pascal(value: Any) -> str:
    return "".join(word[:1].upper() + word[1:] for word in _to_words(value))

@jinja_filter
def camel(value: Any) -> str:
    result = pascal(value)
    return result[:1].lower() + result[1:] if result else result
