from app.base.Binding import Binding


def test_binding_delegates_to_injected_callables():
    calls = {}

    def type_fetcher(value):
        calls["type"] = value
        return "table"

    def object_fetcher(value):
        calls["object"] = value
        return "SRC_OBJ"

    def binder(src, dest):
        calls["bind"] = (src, dest)
        return "RESULT"

    binding = Binding(
        binding_object="block",
        type_fetcher=type_fetcher,
        object_fetcher=object_fetcher,
        binder=binder,
    )

    assert binding.binding_object == "block"

    assert binding.get_type("users") == "table"
    assert calls["type"] == "users"

    assert binding.fetch("users") == "SRC_OBJ"
    assert calls["object"] == "users"

    assert binding.bind("SRC", "DEST") == "RESULT"
    assert calls["bind"] == ("SRC", "DEST")
