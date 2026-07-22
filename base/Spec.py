"""Spec: validated JSON documents with custom type registration and decode."""

from base.Schema import Schema, FailureError
from base.types.Map import Map
from base.types.BindingType import BindingType
from base.Binding import Binding
from base.types.DataType import DataType, DecodingError
from typing import Callable, Dict, Any, Union, List
from utils.helpers import asjson, asyaml, jsonpath, save_json, save_yaml, load_json, load_yaml
from utils import logger


class Attribute:
    """One leaf (or container node) discovered while walking Spec data against a schema."""

    NO_DEFAULT = object()

    def __init__(self, path: Union[str, None], schema_path: Union[str, None], key: str, value: any, type: str, default: any = NO_DEFAULT):
        self.__path = path
        self.__schema_path = schema_path
        
        self.key: str = key
        self.value: any = value
        self.type: str = type
        self.default: any = default

    @classmethod
    def from_schema_path(cls, key: str, value: any, schema: Schema, path: Union[str, None], schema_path: str):
        """Build an Attribute by resolving `type`/`default` from the schema path."""
        _type = schema.get(f'{schema_path}.type', None)
        _default = schema.get(f'{schema_path}.default', Attribute.NO_DEFAULT)

        if _type is None:
            try:
                _type = schema.jsonpath(f'{schema_path}.type')
            except Exception:
                pass

        return cls(path=path, schema_path=schema_path, key=key, value=value, type=_type, default=_default)


    @property
    def path(self) -> Union[str, None]:
        return self.__path

    @property
    def schema_path(self) -> Union[str, None]:
        return self.__schema_path

    def asdict(self) -> dict:
        return {
            "path": self.__path,
            "schema_path": self.__schema_path,
            "key": self.key,
            "value": self.value,
            "type": self.type,
            "default": self.default if self.default is not Attribute.NO_DEFAULT else None
        }

    def __str__(self) -> str:
        return f'{self.key}: {self.type} = {self.value}'

    def __repr__(self) -> str:
        return f'{self.key}: {self.type} = {self.value}'


class Spec:
    """Validated, decodable JSON document with optional custom DataTypes.

    Used as the data backbone for every Resource (factory/frame/block/config).
    """

    def __init__(self, data: Union[dict, list]):
        self.__data = data
        self.__schema = Schema(None)

    @property
    def types(self):
        return self.__schema.types

    def validate(self, jsonschema: dict):
        """Validate `self.data` against `jsonschema`. No-ops if schema is empty."""
        if not jsonschema:
            logger.debug("Spec.validate skipped: empty schema")
            return

        logger.debug("Spec validating")
        self.__schema.set_jsonschema(jsonschema)
        try:
            self.__schema.validate(self.__data)
        except FailureError as e:
            logger.warning("Spec validation failed", error=str(e))
            raise
        logger.debug("Spec validation passed")

    def validate_from_json(self, filepath: str):
        """Load a JSON schema file and validate against it."""
        jsonschema = load_json(filepath)
        self.validate(jsonschema)

    def validate_from_yaml(self, filepath: str):
        """Load a YAML schema file and validate against it."""
        jsonschema = load_yaml(filepath)
        self.validate(jsonschema)

    def define_map(self, name: str, items: Dict[str, Any] = {}):
        """Register a Map data type as `map.<name>`."""
        logger.debug("Spec defining map", map=name)
        self.__schema.define_type(Map(name, items))

    def define_binding(self, dest_object: Any, name: str, bindings: List[Binding]):
        """Register a BindingType as `binding.<name>` for `dest_object`."""
        logger.debug("Spec defining binding", binding=name)
        self.__schema.define_type(BindingType(dest_object, name, bindings))

    def jsonpath(self, attribute_path: str):
        return jsonpath(self.__data, attribute_path)

    def __apply(self, attribute: Any, func: Callable[[Attribute], Any]) -> dict | list:
        if isinstance(attribute.value, dict):
            result = {}
            for key, value in attribute.value.items():
                child_path = f'{attribute.path}.{key}'
                child_schema_path = f'{attribute.schema_path}.properties.{key}'
                child_attribute = Attribute.from_schema_path(key, value, self.__schema, child_path, child_schema_path)
                
                result[key] = self.__apply(child_attribute, func)

            return result
        elif isinstance(attribute.value, list):
            result = []
            for index, item in enumerate(attribute.value):
                child_path = f'{attribute.path}[{index}]'
                child_schema_path = f'{attribute.schema_path}.items'
                child_attribute = Attribute.from_schema_path(item, item, self.__schema, child_path, child_schema_path)

                result.append(self.__apply(child_attribute, func))

            return result
        else:
            return func(attribute)

    def apply(self, func: Callable[[Attribute], Any]) -> dict | list:
        """Walk the data tree and apply `func` to every leaf Attribute."""
        result = {} if isinstance(self.__data, dict) else []
        root = self.__data
        if isinstance(root, dict):
            for key, value in root.items():
                child_path = f'{key}'
                child_schema_path = f'properties.{key}'
                child_attribute = Attribute.from_schema_path(key, value, self.__schema, child_path, child_schema_path)

                result[key] = self.__apply(child_attribute, func)
        elif isinstance(root, list):
            for index, item in enumerate(root):
                child_path = f'[{index}]'
                child_schema_path = 'items'
                child_attribute = Attribute.from_schema_path(item, item, self.__schema, child_path, child_schema_path)

                result.append(self.__apply(child_attribute, func))

        return result

    def decode(self) -> "Spec":
        """Return a new Spec with custom types decoded (maps, bindings, etc.)."""
        logger.debug("Spec decoding")

        def type_decode(attribute):
            types: list[str] = attribute.type if isinstance(attribute.type, list) else [attribute.type]
            tried: bool = False
            errors: list[str] = []

            for _type in types:
                decoder = DataType.DECODERS.get(_type, None)
                if not decoder:
                    continue

                tried = True
                try:
                    return decoder(attribute.value)
                except DecodingError as e:
                    errors.append(f"decoding failed for type '{_type}': {e.message}")
            
            
            if tried:
                error_message = "\n    - " + "\n    - ".join(errors) if len(errors) > 1 else errors[0]
                logger.error("Spec decode failed", path=attribute.path, error=error_message)
                raise DecodingError(error_message)     
            return attribute.value
           
        decoded = Spec(self.apply(type_decode))
        logger.debug("Spec decode finished")
        return decoded

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