"""Catalog frame: schema, concretes, bindings, and optional runtime module."""

from typing import TYPE_CHECKING
from pathlib import Path

from base.CatalogResource import CatalogResource
from utils.RuntimeModule import RuntimeModule
from core.Concrete import Concrete
from base.Template import Template
from utils import logger

if TYPE_CHECKING:
    from core.resources.Block import Block


class Frame(CatalogResource):
    """Reusable component type: properties schema + output file templates.

    On disk under `frames/<name>/`: `module.py`, `concretes/`, `bindings/`.
    `render()` emits concretes; `bind()` evaluates binding snippets with
    `src`/`dest` block contexts (not Jinja's reserved `self`).
    """

    def __init__(self, id: str, name: str, data: dict, path: Path):
        super().__init__(id=id, data=data, path=path)
        self.__name = name
        self.__module = None
        self.__concretes: dict[str, Concrete] = {}
        self.__bindings: dict[str, Template] = {}
        logger.debug("Frame constructed", frame=id, name=name, path=str(path))

    def load(self):
        """Load module, concretes, and bindings from the frame directory."""
        logger.debug("Frame loading from disk", frame=self.id)
        self.load_module()
        self.load_concretes()
        self.load_bindings()
        logger.debug(
            "Frame load finished",
            frame=self.id,
            concretes=len(self.__concretes),
            bindings=len(self.__bindings),
        )

    def reload(self, id: str = None, name: str = None, data: dict = None, path: Path = None):
        """Replace identity/data/path and reload on-disk artifacts."""
        id = id if id else self.id
        name = name if name else self.name
        data = data if data else self.spec.data
        path = path if path else self.path

        logger.debug("Frame reloading", frame=id, previous=self.id)
        super().reload(id, data, path)
        self.__name = name
        self.load()

    def render(self, destination_root: Path, context: dict) -> list[Path]:
        """Resolve concrete destinations and write rendered/copied files."""
        logger.info(
            "Frame render starting",
            frame=self.id,
            destination=str(destination_root),
            concretes=len(self.__concretes),
        )
        self.__load_destinations(destination_root=destination_root, context=context)
        paths = [concrete.render(context=context) for concrete in self.__concretes.values()]
        logger.info("Frame render finished", frame=self.id, files=len(paths))
        return paths

    def bind(self, src_block: "Block", dest_block: "Block"):
        """Render all binding templates for `src_block` into `dest_block` context."""
        logger.debug(
            "Frame bind",
            frame=self.id,
            src=getattr(src_block, "name", None),
            dest=getattr(dest_block, "name", None),
            bindings=len(self.__bindings),
        )
        context = {
            "src": src_block.get_context(),
            "dest": dest_block.get_context()
        }
        output = {binding: template.render(context=context) for binding, template in self.__bindings.items()}
        return output

    def create_binding(self, name: str, content: str):
        """Write a new binding template file under `bindings/<name>.j2`."""
        binding_path = self.path.joinpath("bindings").joinpath(f"{name}.j2")
        binding_path.touch()
        binding_path.write_text(content)
        logger.info("Frame binding created", frame=self.id, binding=name)

    def create_concrete(self, name: str, extension: str, content: str, is_template: bool = True):
        """Create a concrete file under `concretes/` and register it in memory."""
        concretes_dir = self.path.joinpath("concretes")
        concrete = Concrete(
            concretes_path=concretes_dir,
            name=name,
            extension=extension,
            content=content,
            as_template=is_template,
        )

        concrete.src.touch()
        concrete.src.write_text(content)
        self.__concretes[name] = concrete
        logger.info(
            "Frame concrete created",
            frame=self.id,
            concrete=name,
            extension=extension,
            is_template=is_template,
        )

    def load_module(self):
        """Load optional `module.py` as a RuntimeModule."""
        module_name = f"{self.id}.$.module"
        module_path = self.path.joinpath("module.py")
        logger.debug("Frame loading module", frame=self.id, path=str(module_path))
        self.__module = RuntimeModule(module_name, module_path)

    def load_concretes(self):
        """Scan `concretes/` and register each file as a Concrete."""
        concretes_dir: Path = self.path.joinpath("concretes")
        self.__concretes = {}

        for concrete_path in sorted(concretes_dir.iterdir()):
            concrete_file_parts = concrete_path.name.split(".")

            name = concrete_file_parts[0]
            extension = concrete_file_parts[1]
            as_template = concrete_path.suffix == ".j2"
            content = concrete_path.read_text()

            concrete = Concrete(
                concretes_path=concretes_dir,
                name=name,
                extension=extension,
                content=content,
                as_template=as_template,
            )
            self.__concretes[name] = concrete

        logger.debug("Frame concretes loaded", frame=self.id, count=len(self.__concretes))

    def __load_destinations(self, destination_root: Path, context: dict):
        concretes_spec: list[dict] = self.spec.get("concretes", [])
        for spec in concretes_spec:
            name = spec.get("name").split(".")[0]
            concrete: Concrete = self.__concretes.get(name, None)
            if concrete is not None:
                destination = spec.get("destination", None)
                destination = destination_root.joinpath(destination)

                concrete.set_destination(destination, context=context)
            else:
                logger.warning(
                    "Frame concrete spec has no matching file",
                    frame=self.id,
                    concrete=name,
                )

    def load_bindings(self):
        """Scan `bindings/` and register each `.j2` as a Template."""
        bindings_dir: Path = self.path.joinpath("bindings")
        self.__bindings = {
            binding_path.stem: Template.from_file(binding_path)
            for binding_path in sorted(bindings_dir.iterdir())
        }
        logger.debug("Frame bindings loaded", frame=self.id, count=len(self.__bindings))

    @property
    def name(self):
        return self.__name

    @property
    def module(self):
        return self.__module

    @property
    def concretes(self) -> dict[str, Concrete]:
        return self.__concretes
