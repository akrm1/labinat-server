from typing import Dict, Any
from base.types.DataType import DataType


class Enum(DataType):
    def __init__(self, name: str, items: Dict[str, Any] = {}):
        super().__init__(name)
        self.__items: Dict[str, Any] = {}

        for key, value in items.items():
            self.add_item(key, value)

    def validate(self, value: any):
        return value in self.__items.keys()

    def invalid_msg(self, key: str, value: any, value_type: str) -> str:
        values = list(self.__items.keys())
        return f"expected one of '{self.name}' values: {values}, but got \'{value_type}\' value: {value}"
    
    def decode(self, value: any) -> any:
        return self.__items[value]


    def add_item(self, key: str, value: str = None):
        self.__items[key] = value if value is not None else key

    def keys(self):
        return list(self.__items.keys())

    def values(self):
        return list(self.__items.values())

    def items(self):
        return self.__items

    def __str__(self):
        return str(list(self.__items.keys()))

    def __repr__(self):
        return repr(list(self.__items.keys()))

    def __len__(self):
        return len(self.__items)

    def __contains__(self, key: str):
        return key in self.__items.keys()

    def __getitem__(self, key: str):
        return self.__items[key]

    def __setitem__(self, key: str, value: str):
        self.__items[key] = value

    def __delitem__(self, key: str):
        del self.__items[key]

    def __iter__(self):
        return iter(self.__items)

    def __next__(self):
        return next(self.__items)

    