import pytest
from base.types.DataType import DataType


@pytest.fixture(autouse=True)
def _isolate_data_type_decoders():
    """`DataType.DECODERS` is a class-level dict shared by every DataType
    subclass instance. Snapshot/restore it around each test so that types
    registered in one test (Map, BindingType, FakeType, ...) never leak
    into another test's decode lookups.
    """
    original = dict(DataType.DECODERS)
    try:
        yield
    finally:
        DataType.DECODERS.clear()
        DataType.DECODERS.update(original)
