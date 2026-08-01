"""Binding wiring: how a referenced object is typed, fetched, and rendered."""

from typing import Callable, Any


class Binding:
    """Callables that resolve a binding reference such as `@block.users`.

    - `type_fetcher`: name -> frame/type name (e.g. `"table"`)
    - `object_fetcher`: name -> source object (e.g. a Block)
    - `binder`: (src, dest) -> rendered binding payload
    """

    def __init__(
        self,
        binding_object: str,
        type_fetcher: Callable[[str], str],
        object_fetcher: Callable[[str], Any],
        binder: Callable[[Any, Any], Any]
        ):
        self.__binding_object = binding_object
        self.__type_fetcher = type_fetcher
        self.__object_fetcher = object_fetcher
        self.__binder = binder

    @property
    def binding_object(self) -> str:
        """Object namespace in the binding string (e.g. `block` in `@block.users`)."""
        return self.__binding_object

    def get_type(self, binding_value: str) -> str:
        """Return the expected frame/type name for `binding_value`."""
        return self.__type_fetcher(binding_value)

    def fetch(self, binding_value: str) -> Any:
        """Return the live source object for `binding_value`."""
        return self.__object_fetcher(binding_value)

    def bind(self, src_object: Any, dest_object: Any) -> Any:
        """Render this binding for `src_object` into `dest_object`'s context."""
        return self.__binder(src_object, dest_object)
