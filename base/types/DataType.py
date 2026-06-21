from abc import ABC, abstractmethod

class DataType(ABC):
    DECODERS = {}
    def __init__(self, name: str):
        self.__name = name
        DataType.DECODERS[self.__name] = self.decode

    @property
    def name(self):
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