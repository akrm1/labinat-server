"""Abstract custom schema types used by Schema and Spec."""

from abc import ABC, abstractmethod

from utils import logger


class DecodingError(Exception):
    """Raised when a custom type cannot decode a validated value."""

    def __init__(self, message: str):
        self.__message = message
        super().__init__(self.__message)

    @property
    def message(self) -> str:
        return self.__message


class DataType(ABC):
    """Base for platform custom types (`map.*`, `binding.*`, …).

    Instances are registered per `Schema` via `Schema.define_type`, which is
    what `Spec` consults to validate and decode. Types are deliberately not
    tracked process-wide: the same name means different things to different
    Specs.
    """

    def __init__(self, name: str):
        self.__name = name
        logger.debug("Custom type registered", type=self.__name)

    @property
    def name(self) -> str:
        return self.__name

    @abstractmethod
    def validate(self, value: any) -> bool:
        """Return True if `value` is acceptable for this type."""
        pass

    @abstractmethod
    def invalid_msg(self, key: str, value: any, value_type: str) -> str:
        """Human-readable validation failure message for a field."""
        pass

    @abstractmethod
    def decode(self, value: any) -> any:
        """Convert a validated raw value into its runtime form."""
        pass

    def __str__(self) -> str:
        return self.__name

    def __repr__(self) -> str:
        return self.__name
