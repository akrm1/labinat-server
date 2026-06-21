from base.CatalogResource import CatalogResource
from pathlib import Path
from utils.RuntimeModule import RuntimeModule

class Frame(CatalogResource):
    __MODULE_TEMPLATE: str = """
    # {comment}
    # {functions}
    """

    def __init__(self, id: str, name: str, data: dict, path: Path):
        super().__init__(id=id, data=data, path=path)
        self.__name = name
        self.__module = None

    def reload(self, id: str = None, name: str = None, data: dict = None, path: Path = None):
        id = id if id else self.id
        name = name if name else self.name
        data = data if data else self.spec.data
        path = path if path else self.path

        super().reload(id, data, path)
        self.__name = name

    def get_module_template_content(self):
        functions = '''
def example_function():
    return "Hello, World!"
        '''
        return self.__MODULE_TEMPLATE.format(comment=f"Module for {self.id}", functions=functions)

    def load_module(self):
        module_name = f"{self.id}.$.module"
        module_path = self.path.joinpath("module.py")
        self.__module = RuntimeModule(module_name, module_path)

    def create_concrete(self, name: str, content: str):
        concrete_path = self.path.joinpath("concretes").joinpath(f"{name}.j2")
        concrete_path.touch()
        concrete_path.write_text(content)

    def __create_binding(self, name: str, content: str):
        binding_path = self.path.joinpath("bindings").joinpath(f"{name}.j2")
        binding_path.touch()
        binding_path.write_text(content)

    @property
    def name(self):
        return self.__name

    @property
    def module(self):
        return self.__module
