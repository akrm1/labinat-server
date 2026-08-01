"""JSON Schema validation with Labinat custom DataType checkers."""

from typing import Type, Union
from jsonschema.validators import extend
import jsonschema as schema_engine
from jsonschema.exceptions import UnknownType
from app.base.types.DataType import DataType
from utils.helpers import flatten_dict, jsonpath
from utils import logger

PRIMITIVE_TYPE_MAP = {
    int: "integer",
    float: "number",
    bool: "boolean",
    str: "string",
    list: "array",
    dict: "object",
    type(None): "null"
}

class FailureError(Exception):
    """Base class for schema validation failures raised by Schema.validate."""

    def __init__(self, message: str):
        super().__init__(message)

    def get_jsonpath(self, path_deque):
        if not path_deque:
            return "$"
        parts = ["$"]
        for p in path_deque:
            if isinstance(p, int):
                parts.append(f"[{p}]")
            else:
                # dot notation for simple keys, bracket notation otherwise
                if isinstance(p, str) and p.isidentifier():
                    parts.append(f".{p}")
                else:
                    parts.append(f"['{p}']")
        return "".join(parts)


class UndefinedTypeError(FailureError):
    """Raised when a schema references a type name that was never registered."""

    def __init__(self, type: str):
        super().__init__(f"Type \'{type}\'is not defined")

class ValidationError(FailureError):
    """Raised when a value does not match its declared schema type(s)."""

    def __init__(self, key: str, value: any, expected_type: Union[DataType, str, list[DataType]], path: str, is_primitive: bool = False):
        jsonpath = self.get_jsonpath(path)
        message = f"Invalid value for '{jsonpath}'\n  "

        value_type = PRIMITIVE_TYPE_MAP[type(value)]
        if isinstance(expected_type, list):
            types_names = [str(data_type) for data_type in expected_type]
            message += f"expected one of '{types_names}' types, but got '{value_type}' value: {value}"
            message += "\n    Expected Types Validation Failures:"

            for data_type in expected_type:
                if isinstance(data_type, DataType):
                    message += f"\n      - {data_type.name}: {data_type.invalid_msg(key, value, value_type)}"
                else:
                    message += f"\n      - {data_type}: unknown"
        elif is_primitive:
            message += f"expected '{expected_type}' type, but got '{value_type}' value: {value}"
        else:
            message += expected_type.invalid_msg(key, value, value_type)

        super().__init__(message)


class MissingKeyError(FailureError):
    """Raised when a required field is absent from the validated document."""

    def __init__(self, key: str, path: str):
        jsonpath = self.get_jsonpath(path)
        super().__init__(f"Missing required field \'{key}\' at {jsonpath}")

class Schema:
    """JSON Schema validator with Labinat custom DataType checkers plugged in."""

    def __init__(self, jsonschema: dict):
        self.__types: dict[str, DataType] = {}
        self.set_jsonschema(jsonschema)

    @property
    def types(self):
        return self.__types
        
    @property
    def flatten(self):
        return self.__flat

    def set_jsonschema(self, jsonschema: dict):
        """Replace the underlying JSON Schema document and rebuild the flat index."""
        self.__jsonschema = jsonschema
        self.__flat = flatten_dict(jsonschema) if jsonschema else {}

    def define_type(self, new_type: DataType):
        """Register a custom DataType (e.g. map.status, binding.table)."""
        self.__types[new_type.name] = new_type
        logger.debug("Schema type registered", type=new_type.name)

    def __new_type_checker(self, type: DataType):
        def checker(checker, instance):
            return type.validate(instance)
        
        return checker

    def __extend(self):
        types_checkers = {name: self.__new_type_checker(type) for name, type in self.__types.items()}
        custom_checker = schema_engine.Draft7Validator.TYPE_CHECKER.redefine_many(types_checkers)

        validator = extend(schema_engine.Draft7Validator, type_checker=custom_checker)
        return validator

    def validate(self, data: dict):
        """Validate `data` against the configured JSON Schema.

        Raises MissingKeyError / ValidationError / UndefinedTypeError on failure.
        """
        logger.debug("Schema validating", custom_types=list(self.__types.keys()))
        validator = self.__extend()
            
        try:
            validator(self.__jsonschema).validate(data)
        except schema_engine.ValidationError as e:
            key = e.validator

            if key == "required":
                missing_field = e.message.split("'")[1]
                err = MissingKeyError(missing_field, e.absolute_path)
                logger.warning("Schema missing required field", field=missing_field)
                raise err from None
            
            expected_type_value = e.validator_value
            value = e.instance

            if isinstance(expected_type_value, list):
                expected_types = [self.__types.get(type_name, type_name) for type_name in expected_type_value]
                err = ValidationError(key, value, expected_types, e.absolute_path)
                logger.warning("Schema type validation failed", expected=expected_type_value)
                raise err from None

            expected_type = self.__types.get(expected_type_value, None)            
            if expected_type is None:
                err = ValidationError(key, value, expected_type_value, e.absolute_path, is_primitive=True)
                logger.warning("Schema primitive type validation failed", expected=expected_type_value)
                raise err from None
            
            err = ValidationError(key, value, expected_type, e.absolute_path)
            logger.warning("Schema custom type validation failed", expected=expected_type_value)
            raise err from None
        except UnknownType as e:
            logger.error("Schema undefined type", type=e.type)
            raise UndefinedTypeError(e.type) from None

        logger.debug("Schema validation passed")


    def jsonpath(self, path: str):
        return jsonpath(self.__jsonschema, path)

    def get(self, key: str, default: any = None):
        return self.__flat.get(key, default)

    def __getitem__(self, key: str):
        return self.__flat[key]

    def __str__(self) -> str:
        return str(self.__jsonschema)

    def __repr__(self) -> str:
        return repr(self.__jsonschema)

    def asdict(self) -> dict:
        return self.__jsonschema

    @staticmethod
    def primitive_type_map(type: Type) -> str:
        return PRIMITIVE_TYPE_MAP[type]