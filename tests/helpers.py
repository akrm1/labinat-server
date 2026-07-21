from base.types.DataType import DataType, DecodingError


class FakeType(DataType):
    """Minimal concrete DataType used to exercise Schema/Spec in isolation,
    without depending on Map/BindingType internals.
    """

    def __init__(self, name: str, expected_value, decoded_value=None, fail_decode: bool = False):
        super().__init__(name)
        self.expected_value = expected_value
        self.decoded_value = decoded_value
        self.fail_decode = fail_decode

    def validate(self, value) -> bool:
        return value == self.expected_value

    def invalid_msg(self, key: str, value, value_type: str) -> str:
        return f"expected '{self.expected_value}', got '{value_type}' value: {value}"

    def decode(self, value):
        if self.fail_decode:
            raise DecodingError(f"cannot decode '{value}' for type '{self.name}'")
        return self.decoded_value if self.decoded_value is not None else value
