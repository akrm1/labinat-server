from pathlib import Path
from datetime import datetime
from typing import Union, TYPE_CHECKING
import shutil
from utils.helpers import asjson, asyaml
from base.Spec import Spec
from base.DirectoryTemplate import DirectoryTemplate
from base.PipelineExecuter import PipelineExecuter

if TYPE_CHECKING:
    from core.resources.Factory import Factory
    from core.resources.Block import Block

class Project():
    def __init__(self, id: str, name: str, path: Path, created_at: datetime, description: str = "", config: dict = {}):
        self.__name = name
        self.__id = id
        self.__path = path
        self.__description = description
        self.__config = Spec(config)
        self.__created_at = created_at

        self.__factories : dict[str, dict] = {}
        self.__blocks : dict[str, "Block"] = {}

    def validate_config(self):
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "app": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "name": { "type": "string" }
                    },
                    "required": ["name"]
                }
            },
            "required": ["app"]
        }

        for factory_name, factory in self.factories.items():
            schema["properties"][factory_name] = {
                "type": "object",
                "additionalProperties": False,
                "properties": factory.config.get('properties', {}),
                "required": factory.config.get('required', [])
            }
            schema["required"].append(factory_name)
        
        self.__config.validate(schema)

    def add_factory(self, factory: "Factory"):
        self.__factories[factory.name] = {"version": factory.version, "factory": factory}

    def get_factory(self, factory_name: str) -> Union["Factory", None]:
        return self.__factories.get(factory_name, {"factory": None})["factory"]

    def add_block(self, block: "Block"):
        self.__blocks[block.name] = block

    def get_block(self, block_name: str) -> "Block":
        return self.__blocks.get(block_name, None)

    def get_block_type(self, block_name: str) -> str:
        block = self.__blocks.get(block_name, None)
        if block:
            return block.frame.name
        return None

    def __str__(self):
        return self.info

    def __repr__(self):
        return self.info

    @property
    def name(self) -> str:
        return self.__name

    @property
    def id(self) -> str:
        return self.__id

    @property
    def path(self) -> Path:
        return self.__path

    @property
    def src(self) -> Path:
        return self.__path.joinpath("src")

    @property
    def description(self) -> str:
        return self.__description

    @property
    def config(self) -> dict:
        return self.__config.data

    @property
    def created_at(self) -> datetime:
        return self.__created_at

    @property
    def factories(self) -> dict[str, "Factory"]:
        return {factory_name: factory_dict.get("factory", None) for factory_name, factory_dict in self.__factories.items()}

    @property
    def blocks(self) -> dict[str, "Block"]:
        return self.__blocks

    @property
    def info(self) -> dict:
        return asjson({
            "name": self.__name,
            "id": self.__id,
            "path": self.__path,
            "description": self.__description,
            "config": self.__config,
            "created_at": self.__created_at.isoformat()
        })

    @property
    def info_as_yaml(self) -> str:
        return asyaml({
            "name": self.__name,
            "id": self.__id,
            "path": self.__path,
            "description": self.__description,
            "config": self.__config,
            "created_at": self.__created_at.isoformat()
        })

    def get_factory_path(self, factory_name: str) -> Path:
        return self.src.joinpath(factory_name)

    def get_context(self, factory: "Factory") -> dict:
        project = {
            "name": self.__name,
            "id": self.__id,
            "path": self.__path,
            "description": self.__description,
            "config": self.__config.data,
            "created_at": self.__created_at.isoformat()
        }

        factory_object = {
            "id": factory.id,
            "name": factory.name,
            "version": factory.version,
            "path": factory.path,
            "version_path": factory.version_path,
            "spec": factory.spec.data,
            "config": self.__config.data.get(factory.name, {})
        }

        return {
            "app": self.__config.data.get("app", {}),
            "project": project,
            "factory": factory_object,
            "config": self.__config.data
        }

    def clone(self):
        for factory_name, factory_dict in self.__factories.items():
            factory: "Factory" = factory_dict.get("factory", None)
            if not factory:
                continue

            base_path = factory.version_path.joinpath("base")
            if not base_path.exists():
                continue

            destination = self.get_factory_path(factory_name)
            if destination.exists():
                shutil.rmtree(destination)
            destination.mkdir(parents=True, exist_ok=True)

            DirectoryTemplate(base_path).render(destination, self.get_context(factory))

    def __execute_pipeline(self, pipeline_name: str, **inputs):
        for factory_name, factory_dict in self.__factories.items():
            factory: "Factory" = factory_dict.get("factory", None)
            if not factory:
                continue

            executer_name = f"{factory_name}.{pipeline_name}"
            actions = factory.lifecycle.get(pipeline_name, [])

            executer = PipelineExecuter(name=executer_name, actions=actions)

            context = self.get_context(factory)
            executer(**context, **inputs)

    def build(self):
        self.__execute_pipeline(pipeline_name="build")