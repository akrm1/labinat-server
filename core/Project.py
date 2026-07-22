"""In-memory project: factories, blocks, config, clone, and lifecycle pipelines."""

from pathlib import Path
from datetime import datetime
from typing import Union, TYPE_CHECKING
import shutil
from utils.helpers import asjson, asyaml
from utils import logger
from base.Spec import Spec
from base.DirectoryTemplate import DirectoryTemplate
from base.PipelineExecuter import PipelineExecuter

if TYPE_CHECKING:
    from core.resources.Factory import Factory
    from core.resources.Block import Block


class Project():
    """Workspace project instance: attached factories, blocks, and config Spec.

    Disk layout lives under `workspace/projects/<id>/`. `clone()` renders each
    factory's `base/` templates into `src/<factory>/`; `build()` runs lifecycle
    pipelines declared on attached factories.
    """

    def __init__(self, id: str, name: str, path: Path, created_at: datetime, description: str = "", config: dict = {}):
        self.__name = name
        self.__id = id
        self.__path = path
        self.__description = description
        self.__config = Spec(config)
        self.__created_at = created_at

        self.__factories : dict[str, dict] = {}
        self.__blocks : dict[str, "Block"] = {}
        logger.debug("Project constructed", project_id=id, name=name, path=str(path))

    def validate_config(self):
        """Validate project config against app + per-factory config schemas."""
        logger.debug("Project validating config", project_id=self.__id)
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
        
        try:
            self.__config.validate(schema)
        except Exception:
            logger.warning("Project config validation failed", project_id=self.__id)
            raise
        logger.debug("Project config validation passed", project_id=self.__id)

    def add_factory(self, factory: "Factory"):
        """Attach a catalog factory to this project (keyed by factory name)."""
        logger.debug("Project adding factory", project_id=self.__id, factory=factory.id)
        self.__factories[factory.name] = {"version": factory.version, "factory": factory}

    def get_factory(self, factory_name: str) -> Union["Factory", None]:
        """Return an attached factory by name, or None."""
        factory = self.__factories.get(factory_name, {"factory": None})["factory"]
        if factory is None:
            logger.debug("Project factory not found", project_id=self.__id, factory=factory_name)
        return factory

    def add_block(self, block: "Block"):
        """Register a block under this project (keyed by block name)."""
        logger.debug(
            "Project adding block",
            project_id=self.__id,
            block=getattr(block, "id", getattr(block, "name", None)),
        )
        self.__blocks[block.name] = block

    def get_block(self, block_name: str) -> "Block":
        """Return a block by name, or None."""
        block = self.__blocks.get(block_name, None)
        if block is None:
            logger.debug("Project block not found", project_id=self.__id, block=block_name)
        return block

    def get_block_type(self, block_name: str) -> str:
        """Return the frame name for a block, or None if the block is missing."""
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
        logger.info("Cloning project base templates", project_id=self.__id, factories=list(self.__factories.keys()))
        for factory_name, factory_dict in self.__factories.items():
            factory: "Factory" = factory_dict.get("factory", None)
            if not factory:
                continue

            base_path = factory.version_path.joinpath("base")
            if not base_path.exists():
                logger.debug("Factory has no base templates; skipping clone", factory=factory_name)
                continue

            destination = self.get_factory_path(factory_name)
            if destination.exists():
                shutil.rmtree(destination)
            destination.mkdir(parents=True, exist_ok=True)

            DirectoryTemplate(base_path).render(destination, self.get_context(factory))
            logger.info("Factory base cloned", project_id=self.__id, factory=factory_name, destination=str(destination))

    def __execute_pipeline(self, pipeline_name: str, **inputs):
        logger.info("Running project pipeline", project_id=self.__id, pipeline=pipeline_name)
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
        logger.info("Building project", project_id=self.__id, name=self.__name)
        self.__execute_pipeline(pipeline_name="build")
        logger.info("Build finished", project_id=self.__id)