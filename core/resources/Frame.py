from typing import TYPE_CHECKING
from base.CatalogResource import CatalogResource
from pathlib import Path
from utils.RuntimeModule import RuntimeModule
from core.Concrete import Concrete
from base.Template import Template

if TYPE_CHECKING:
    from core.resources.Block import Block

class Frame(CatalogResource):
    def __init__(self, id: str, name: str, data: dict, path: Path):
        super().__init__(id=id, data=data, path=path)
        self.__name = name
        self.__module = None
        self.__concretes: dict[str, Concrete] = {}
        self.__bindings: dict[str, Template] = {}

    def load(self):
        self.load_module()
        self.load_concretes()
        self.load_bindings()

    def reload(self, id: str = None, name: str = None, data: dict = None, path: Path = None):
        id = id if id else self.id
        name = name if name else self.name
        data = data if data else self.spec.data
        path = path if path else self.path

        super().reload(id, data, path)
        self.__name = name
        self.load()
        

    def render(self, destination_root: Path, context: dict) -> list[Path]:
        self.__load_destinations(destination_root=destination_root, context=context)
        return [concrete.render(context=context) for concrete in self.__concretes.values()]

    def bind(self, src_block: "Block", dest_block: "Block"):
        context = {
            "src": src_block.get_context(),
            "dest": dest_block.get_context()
        }
        output = {binding: template.render(context=context) for binding, template in self.__bindings.items()}
        return output

    def create_binding(self, name: str, content: str):
        binding_path = self.path.joinpath("bindings").joinpath(f"{name}.j2")
        binding_path.touch()
        binding_path.write_text(content)

    def create_concrete(self, name: str, extension: str, content: str, is_template: bool = True):
        concretes_dir= self.path.joinpath("concretes")
        concrete = Concrete(concretes_path=concretes_dir, name=name, extension=extension, content=content, is_template=is_template)

        concrete.path.touch()
        concrete.path.write_text(content)
        self.__concretes[name] = concrete
    
    def load_module(self):
        module_name = f"{self.id}.$.module"
        module_path = self.path.joinpath("module.py")
        self.__module = RuntimeModule(module_name, module_path)

    def load_concretes(self):
        concretes_dir: Path = self.path.joinpath("concretes")

        for concrete_path in sorted(concretes_dir.iterdir()):
            concrete_file_parts = concrete_path.name.split(".")

            name = concrete_file_parts[0]
            extension = concrete_file_parts[1]
            as_template = concrete_path.suffix == ".j2"
            content = concrete_path.read_text()

            concrete = Concrete(concretes_path=concretes_dir, name=name, extension=extension, content=content, as_template=as_template)
            self.__concretes[name] = concrete

    def __load_destinations(self, destination_root: Path, context: dict):
        concretes_spec: list[dict] = self.spec.get("concretes", [])
        for spec in concretes_spec:
            name = spec.get("name").split(".")[0]
            concrete: Concrete = self.__concretes.get(name, None)
            if concrete is not None:
                destination = spec.get("destination", None)
                destination = destination_root.joinpath(destination)

                concrete.set_destination(destination, context=context)

    def load_bindings(self):
        bindings_dir: Path = self.path.joinpath("bindings")
        self.__bindings = {binding_path.stem: Template.from_file(binding_path) for binding_path in sorted(bindings_dir.iterdir())}



    @property
    def name(self):
        return self.__name

    @property
    def module(self):
        return self.__module

    @property
    def concretes(self) -> dict[str, Concrete]:
        return self.__concretes