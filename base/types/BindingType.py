"""Schema type for `@object.attr` binding expressions (`binding.<type>`)."""

from typing import Callable, Any, Dict, List
from base.types.DataType import DataType, DecodingError
from base.Binding import Binding


class BindingException(DecodingError):
    """Raised when a binding expression cannot be resolved."""

    def __init__(self, message: str):
        super().__init__(message)


class BindingType(DataType):
    """Validates and decodes `@binding_object.attr` strings against registered bindings.

    Registered as `binding.<binding_type>` so frames can declare fields that
    resolve to callables/values on a destination object (e.g. a project).
    """

    def __init__(self, dest_object: Any, binding_type: str, bindings: List[Binding]):
        name = f"binding.{binding_type}"
        super().__init__(name)
        self.__dest_object = dest_object
        self.__bindings: Dict[str, Binding] = {binding.binding_object: binding for binding in bindings}

    @property
    def expected_type(self) -> str:
        return self.name.split(".")[1]

    def get_binding(self, binding_object: str) -> Callable[[str], Any]:
        return self.__bindings.get(binding_object, None)

    def validate(self, value: any):
        if isinstance(value, str):
            if value.startswith("@"):
                binding_string: str = value[1:].split(".")
                if len(binding_string) != 2:
                    return False
            
                binding_object = binding_string[0]
                binding_value = binding_string[1]

                binding = self.get_binding(binding_object)
                if binding:
                    value_type: str = binding.get_type(binding_value)
                    if value_type == self.expected_type:
                        return True
        
        return False

    def invalid_msg(self, key: str, value: any, value_type: str) -> str:
        if not isinstance(value, str):
            return f"expected '{self.name}', but got \'{value_type}\' value: {value}"
        if not value.startswith("@"):
            return f"the value of binding must start with '@', but got \'{value}\'"
        
        binding_string: str = value[1:].split(".")
        if len(binding_string) != 2:
            return f"the binding value must follow this pattern: '@<binding_object>.<binding_value>', but got \'{value}\'"
        
        binding_object = binding_string[0]
        binding_value = binding_string[1]

        expected_binding_objects = list(self.__bindings.keys())
        if binding_object not in  expected_binding_objects:
            return f"binding object '{binding_object}' is unknown, expected one of the following binding objects: {expected_binding_objects}"
        
        binding = self.get_binding(binding_object)
        binding_value_type = binding.get_type(binding_value)
        if binding_value_type != self.expected_type:
            return f"expected '{self.expected_type}' type, but got '{binding_value_type}' type"
        
        return f"the binding resource '{value}' is not found"

        
    def decode(self, value: any) -> any:
        binding_object, binding_value = value[1:].split(".")

        binding: Binding = self.get_binding(binding_object)
        if not binding:
            raise BindingException(f"the binding object '{binding_object}' is not defined")

        value_type = binding.get_type(binding_value)
        if value_type != self.expected_type:
            raise BindingException(f"expected '{self.expected_type}' type, but got '{value_type}' type")

        src_object =  binding.fetch(binding_value)
        if not src_object:
            raise BindingException(f"the binding resource '{binding_value}' is not found")

        return binding.bind(src_object, self.__dest_object)
