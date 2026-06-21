from typing import Type, Union
from jsonschema.validators import extend
import jsonschema as schema_engine
from jsonschema.exceptions import UnknownType
from base.types.DataType import DataType
from utils.helpers import flatten_dict

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
    def __init__(self, type: str):
        super().__init__(f"Type \'{type}\'is not defined")

class ValidationError(FailureError):
    def __init__(self, key: str, value: any, expected_type: Union[DataType, str], path: str, is_primitive: bool = False):
        jsonpath = self.get_jsonpath(path)
        message = f"Invalid value for '{jsonpath}'\n  "

        value_type = PRIMITIVE_TYPE_MAP[type(value)]
        if is_primitive:
            message += f"expected '{expected_type}' type, but got '{value_type}' value: {value}"
        else:
            message += expected_type.invalid_msg(key, value, value_type)

        super().__init__(message)


class MissingKeyError(FailureError):
    def __init__(self, key: str, path: str):
        jsonpath = self.get_jsonpath(path)
        super().__init__(f"Missing required field \'{key}\' at {jsonpath}")

class Schema:
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
        self.__jsonschema = jsonschema
        self.__flat = flatten_dict(jsonschema)

    def define_type(self, new_type: DataType):
        self.__types[new_type.name] = new_type

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
        validator = self.__extend()
            
        try:
            validator(self.__jsonschema).validate(data)
        except schema_engine.ValidationError as e:
            key = e.validator

            if key == "required":
                missing_field = e.message.split("'")[1]
                raise MissingKeyError(missing_field, e.absolute_path) from None
            
            expected_type_name = e.validator_value
            expected_type = self.__types.get(expected_type_name, None)
            value = e.instance
            if expected_type is None:
                raise ValidationError(key, value, expected_type_name, e.absolute_path, is_primitive=True) from None
            
            raise ValidationError(key, value, expected_type, e.absolute_path) from None
        except UnknownType as e:
            raise UndefinedTypeError(e.type) from None

    def get(self, key: str, default: any = None):
        return self.__flat.get(key, default)

    def __getitem__(self, key: str):
        return self.__flat[key]

    def __str__(self):
        return str(self.__jsonschema)

    def __repr__(self):
        return repr(self.__jsonschema)

    @staticmethod
    def primitive_type_map(type: Type) -> str:
        return PRIMITIVE_TYPE_MAP[type]