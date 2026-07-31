"""In-memory project: factories, blocks, config, clone, and named pipelines."""

from pathlib import Path
from datetime import datetime
from typing import Union, TYPE_CHECKING
import shutil
from utils.helpers import asjson, asyaml
from utils import logger
from base.Spec import Spec
from base.DirectoryTemplate import DirectoryTemplate
from base.PipelineExecuter import PipelineExecuter, PipelineError
from base.ImageBuilder import ImageBuilder, ImageBuildError
from base.filters import snake

if TYPE_CHECKING:
    from core.resources.Factory import Factory
    from core.resources.Block import Block


class Project():
    """Workspace project instance: attached factories, blocks, and config Spec.

    Disk layout lives under `workspace/projects/<id>/`. `clone()` renders each
    factory's `base/` templates into `src/<factory>/`. `build()` orchestrates
    validate → clone → init → emit blocks → build pipeline. Other pipeline
    methods (`init`, `run`, `debug`) run optional shell sequences with cwd set
    to `src/<factory>`. `package()` builds a container image per factory.
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

    def add_block(self, block: "Block") -> bool:
        """Register a block under this project (keyed by block name).

        Returns False unless the block's frame belongs to an already-attached
        factory (`frame.id` = `{factory.id}.{frame_name}`).
        """
        factory = self.__factory_from_frame(block.frame)
        if factory is None:
            logger.warning(
                "Failed to add block: factory not found",
                project_id=self.__id,
                block=getattr(block, "id", getattr(block, "name", None)),
                frame=block.frame.id,
            )
            return False

        self.__blocks[block.name] = block
        logger.debug(
            "Project adding block",
            project_id=self.__id,
            block=getattr(block, "id", getattr(block, "name", None)),
            factory=factory.id,
        )
        return True

    def remove_block(self, block_name: str) -> bool:
        """Unregister a block by name. Returns True if it was present."""
        removed = self.__blocks.pop(block_name, None)
        if removed is None:
            logger.debug("Project remove_block: not found", project_id=self.__id, block=block_name)
            return False
        logger.debug("Project block removed", project_id=self.__id, block=block_name)
        return True

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

    def get_block_factory(self, block_name: str) -> Union["Factory", None]:
        """Return the attached factory that owns this block's frame, or None."""
        block = self.__blocks.get(block_name, None)
        if block is None:
            return None
        return self.__factory_from_frame(block.frame)

    def __factory_from_frame(self, frame) -> Union["Factory", None]:
        """Resolve an attached factory from `frame.id` (`{name}:{version}.{frame}`)."""
        factory_id = frame.id.rsplit(".", 1)[0]
        factory_name = factory_id.split(":", 1)[0]
        entry = self.__factories.get(factory_name)
        if not entry:
            return None
        factory = entry.get("factory")
        if factory is None or factory.id != factory_id:
            return None
        return factory

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
        """Render each factory's `base/` templates into `src/<factory>/`."""
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

    def emit(self) -> list[Path]:
        """Decode and render every block into its factory's `src/<factory>/` tree."""
        logger.info("Emitting project blocks", project_id=self.__id, blocks=len(self.__blocks))
        written: list[Path] = []

        for block in self.__blocks.values():
            factory = self.get_block_factory(block.name)
            if factory is None:
                logger.warning(
                    "Emit skipped: block's factory not found",
                    project_id=self.__id,
                    block=block.id,
                    frame=block.frame.id,
                )
                continue

            destination_root = self.get_factory_path(factory.name)
            written.extend(block.build(destination_root))

        logger.info("Emit finished", project_id=self.__id, files=len(written))
        return written

    def __execute_pipeline(self, pipeline_name: str, **inputs):
        """Run a named pipeline for each attached factory with cwd=`src/<factory>`.

        Raises `PipelineError` on the first factory whose pipeline fails, so a
        broken step stops the build instead of letting later stages run
        against a half-built tree.
        """
        logger.info("Running project pipeline", project_id=self.__id, pipeline=pipeline_name)
        for factory_name, factory_dict in self.__factories.items():
            factory: "Factory" = factory_dict.get("factory", None)
            if not factory:
                continue

            executer_name = f"{factory_name}.{pipeline_name}"
            actions = factory.pipelines.get(pipeline_name, [])

            executer = PipelineExecuter(name=executer_name, actions=actions)
            cwd = self.get_factory_path(factory_name)

            context = self.get_context(factory)
            return_code = executer(cwd=cwd, **context, **inputs)

            if return_code != 0:
                logger.error(
                    "Project pipeline failed",
                    project_id=self.__id,
                    pipeline=pipeline_name,
                    factory=factory_name,
                    return_code=return_code,
                )
                raise PipelineError(
                    f"Pipeline '{executer_name}' failed with return code {return_code}"
                )

    def init(self):
        """Run the optional `init` pipeline (after clone, before block emit)."""
        logger.info("Running init pipeline", project_id=self.__id, name=self.__name)
        self.__execute_pipeline(pipeline_name="init")
        logger.info("Init finished", project_id=self.__id)

    def build(self):
        """Full build: validate → clone → init → emit blocks → build pipeline."""
        logger.info("Building project", project_id=self.__id, name=self.__name)
        self.validate_config()
        self.clone()
        self.init()
        self.emit()
        self.__execute_pipeline(pipeline_name="build")
        logger.info("Build finished", project_id=self.__id)

    def run(self):
        """Run the optional `run` pipeline (experience / testing)."""
        logger.info("Running project", project_id=self.__id, name=self.__name)
        self.__execute_pipeline(pipeline_name="run")

    def debug(self):
        """Run the optional `debug` pipeline."""
        logger.info("Debugging project", project_id=self.__id, name=self.__name)
        self.__execute_pipeline(pipeline_name="debug")

    def package(self, tool: str = "docker") -> list[str]:
        """Build a container image for each attached factory that emitted a Dockerfile.

        Meant to run after `build()`: a factory's `base/Dockerfile.j2` renders
        into `src/<factory>/Dockerfile` during clone, and this builds that tree
        into a locally-tagged image (`<app>-<factory>:<short-id>`). Factories
        without a Dockerfile are skipped. Raises `ImageBuildError` on the first
        failed build so a broken image stops the run.
        """
        app_name = self.__config.data.get("app", {}).get("name")
        if not app_name:
            raise ImageBuildError("Cannot tag images: project config has no 'app.name'")

        logger.info("Packaging project into images", project_id=self.__id, tool=tool)
        builder = ImageBuilder(tool=tool)
        tags: list[str] = []

        for factory_name in self.__factories:
            context_dir = self.get_factory_path(factory_name)
            if not context_dir.joinpath("Dockerfile").exists():
                logger.debug("Factory has no Dockerfile; skipping image build", factory=factory_name)
                continue

            tag = f"{snake(app_name)}-{factory_name}:{self.__id[:8]}"
            return_code = builder.build(context_dir=context_dir, tag=tag)
            if return_code != 0:
                logger.error(
                    "Project packaging failed",
                    project_id=self.__id,
                    factory=factory_name,
                    tag=tag,
                    return_code=return_code,
                )
                raise ImageBuildError(
                    f"Image build for factory '{factory_name}' failed with return code {return_code}"
                )
            tags.append(tag)

        logger.info("Packaging finished", project_id=self.__id, images=tags)
        return tags
