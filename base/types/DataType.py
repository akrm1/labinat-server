from abc import ABC, abstractmethod

class DecodingError(Exception):
    def __init__(self, message: str):
        self.__message = message
        super().__init__(self.__message)

    @property
    def message(self) -> str:
        return self.__message

class DataType(ABC):
    DECODERS = {}
    def __init__(self, name: str):
        self.__name = name
        DataType.DECODERS[self.__name] = self.decode

    @property
    def name(self) -> str:
        return self.__name

    @abstractmethod
    def validate(self, value: any) -> bool:
        pass

    @abstractmethod
    def invalid_msg(self, key: str, value: any, value_type: str) -> str:
        pass

    @abstractmethod
    def decode(self, value: any) -> any:
        pass

    def __str__(self) -> str:
        return self.__name

    def __repr__(self) -> str:
        return self.__name
