from typing import Callable, Any

class Binding:
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
        return self.__binding_object

    def get_type(self, binding_value: str) -> str:
        return self.__type_fetcher(binding_value)

    def fetch(self, binding_value: str) -> Any:
        return self.__object_fetcher(binding_value)

    def bind(self, src_object: Any, dest_object: Any) -> Any:
        return self.__binder(src_object, dest_object)