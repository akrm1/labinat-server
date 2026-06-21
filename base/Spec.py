from base.Schema import Schema
from base.types.Enum import Enum
from base.types.DataType import DataType
from typing import Callable, Dict, Any, Union
from utils.helpers import asjson, asyaml, jsonpath, save_json, save_yaml, load_json, load_yaml

class Attribute:
    NO_DEFAULT = object()

    def __init__(self, path: Union[str, None], schema_path: Union[str, None], key: str, value: any, type: str, default: any = NO_DEFAULT):
        self.__path = path
        self.__schema_path = schema_path
        
        self.key = key
        self.value = value
        self.type = type
        self.default = default

    @property
    def path(self):
        return self.__path

    @property
    def schema_path(self):
        return self.__schema_path

    def asdict(self):
        return {
            "path": self.__path,
            "schema_path": self.__schema_path,
            "key": self.key,
            "value": self.value,
            "type": self.type,
            "default": self.default
        }

    def __str__(self):
        return f'{self.key}: {self.type} = {self.value}'

    def __repr__(self):
        return f'{self.key}: {self.type} = {self.value}'

class Spec:
    def __init__(self, data: Union[dict, list]):
        self.__data = data
        self.__schema = Schema(None)

    @property
    def types(self):
        return self.__schema.types

    def validate(self, jsonschema: dict):
        if not self.__data or not jsonschema:
            return
        
        self.__schema.set_jsonschema(jsonschema)
        self.__schema.validate(self.__data)

    def validate_from_json(self, filepath: str):
        jsonschema = load_json(filepath)
        self.validate(jsonschema)

    def validate_from_yaml(self, filepath: str):
        jsonschema = load_yaml(filepath)
        self.validate(jsonschema)

    def define_enum(self, name: str, items: Dict[str, Any] = {}):
        self.__schema.define_type(Enum(f"enum.{name}", items))

    def jsonpath(self, attribute_path: str):
        return jsonpath(self.__data, attribute_path)

    def __apply(self, attribute: Any, func: Callable[[Attribute], Any]):
        if isinstance(attribute.value, dict):
            result = {}
            for key, value in attribute.value.items():
                child_path = f'{attribute.path}.{key}'
                child_schema_path = f'{attribute.schema_path}.properties.{key}'
                child_type = self.__schema[f'{child_schema_path}.type']
                child_default = self.__schema.get(f'{child_schema_path}.default', Attribute.NO_DEFAULT)

                child_attribute = Attribute(path=child_path, schema_path=child_schema_path, key=key, value=value, type=child_type, default=child_default)

                result[key] = self.__apply(child_attribute, func)

            return result
        elif isinstance(attribute.value, list):
            result = []
            for index, item in enumerate(attribute.value):
                child_path = f'{attribute.path}[{index}]'
                child_schema_path = f'{attribute.schema_path}.items'
                child_type = self.__schema[f'{child_schema_path}.type']
                child_default = self.__schema.get(f'{child_schema_path}.default', Attribute.NO_DEFAULT)

                child_attribute = Attribute(path=child_path, schema_path=child_schema_path, key=item, value=item, type=child_type, default=child_default)

                result.append(self.__apply(child_attribute, func))

            return result
        else:
            return func(attribute)

    def apply(self, func: Callable[[Attribute], Any]):
        result = {} if isinstance(self.__data, dict) else []
        root = self.__data
        if isinstance(root, dict):
            for key, value in root.items():
                child_path = f'{key}'
                child_schema_path = f'properties.{key}'
                child_type = self.__schema[f'{child_schema_path}.type']
                child_default = self.__schema.get(f'{child_schema_path}.default', Attribute.NO_DEFAULT)

                child_attribute = Attribute(path=child_path, schema_path=child_schema_path, key=key, value=value, type=child_type, default=child_default)

                result[key] = self.__apply(child_attribute, func)
        elif isinstance(root, list):
            for index, item in enumerate(root):
                child_path = f'[{index}]'
                child_schema_path = 'items'
                child_type = self.__schema[f'{child_schema_path}.type']
                child_default = self.__schema.get(f'{child_schema_path}.default', Attribute.NO_DEFAULT)
                
                child_attribute = Attribute(path=child_path, schema_path=child_schema_path, key=item, value=item, type=child_type, default=child_default)

                result.append(self.__apply(child_attribute, func))

        self.__data = result
        return self.__data

    def decode(self):
        def type_decode(attribute):
            decoder = DataType.DECODERS.get(attribute.type, None)
            new_value = decoder(attribute.value) if decoder is not None else attribute.value
            return new_value
        
        self.apply(type_decode)
        return self.__data

    def asjson(self):
        return asjson(self.__data)

    def asyaml(self):
        return asyaml(self.__data)

    def load_from_json(self, filepath: str):
        data = load_json(filepath)
        self.__data = data

    def load_from_yaml(self, filepath: str):
        data = load_yaml(filepath)
        self.__data = data

    def save_as_json(self, filepath: str):
        save_json(filepath, self.__data)

    def save_as_yaml(self, filepath: str):
        save_yaml(filepath, self.__data)

    @property
    def data(self):
        return self.__data

    @property
    def schema(self):
        return self.__schema

    def __getitem__(self, key: str):
        return self.__data[key]

    def get(self, key: str, default: any = None):
        return self.__data.get(key, default)

    def __delitem__(self, key: str):
        del self.__data[key]

    def __iter__(self):
        return iter(self.__data)

    def __len__(self):
        return len(self.__data)

    def __contains__(self, key: str):
        return key in self.__data

    def keys(self):
        return self.__data.keys()

    def values(self):
        return self.__data.values()

    def items(self):
        return self.__data.items()

    def __str__(self):
        return str(self.__data)

    def __repr__(self):
        return repr(self.__data)