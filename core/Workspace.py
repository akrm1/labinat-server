"""Workspace registry: projects and blocks on disk + in SQLite."""

from pathlib import Path
from typing import Union
import uuid
import shutil
from datetime import datetime, timezone
from utils.helpers import asjson
from utils import logger
from core.Catalog import Catalog
from core.Project import Project
from core.resources.Factory import Factory
from core.resources.Frame import Frame
from core.resources.Block import Block
from data.database import get_db
from sqlalchemy import and_
from data.models.ProjectModel import ProjectModel
from data.models.ProjectFactoryModel import ProjectFactoryModel
from data.models.FactoryModel import FactoryModel
from data.models.FrameModel import FrameModel
from data.models.BlockModel import BlockModel


class Workspace:
    """Persistent registry of projects and their blocks.

    CRUD mutates SQLite and the on-disk tree under `workspace/projects/`.
    Lookups hydrate `Project` objects with attached factories and blocks.
    """

    def __init__(self, workspace_config: dict):
        self.__path = Path(workspace_config['path'])
        logger.debug("Workspace initialized", path=str(self.__path))

    @property
    def path(self):
        return self.__path

    @property
    def info(self):
        info = {
            "path": self.__path.absolute(),
        }

        return asjson(info)

    def get_project_path(self, project_id: str) -> Path:
        return self.path.joinpath("projects").joinpath(project_id)

    def __load_factory(self, db, catalog: Catalog, factory_record: FactoryModel) -> Factory:
        factory_path = catalog.get_factory_path(factory_record.name)
        factory = Factory(name=factory_record.name, version=factory_record.version, data=factory_record.data, path=factory_path)

        frame_records = db.query(FrameModel).filter_by(factory=factory_record.name, factory_version=factory_record.version).all()
        for frame_record in frame_records:
            frame_id = f'{factory.id}.{frame_record.name}'
            frame_path = factory.version_path.joinpath("frames").joinpath(frame_record.name)

            frame = Frame(id=frame_id, name=frame_record.name, data=frame_record.data, path=frame_path)
            frame.load()
            factory.add_frame(frame)

        return factory

    def create_project(self, name: str, description: str = "", config: dict = {}, factories: list[Factory] = []) -> Project:
        project_id = str(uuid.uuid4())
        project_path = self.get_project_path(project_id)
        created_at = datetime.now(timezone.utc)

        with get_db() as db:
            while db.query(ProjectModel).filter_by(id=project_id).first():
                project_id = str(uuid.uuid4())  # regenerate if collision
        
            project = Project(id=project_id, name=name, path=project_path, created_at=created_at, description=description, config=config)
            
            # create project directories
            project.path.mkdir(parents=True, exist_ok=True) # create project directory
            project.src.mkdir(parents=True, exist_ok=True) # create src directory

            project_record = ProjectModel(id=project_id, name=name, description=description, config=config, created_at=created_at)
            db.add(project_record)

            for factory in factories:
                project.get_factory_path(factory.name).mkdir(parents=True, exist_ok=True)

                project_factory_record = ProjectFactoryModel(project_id=project.id, factory=factory.name, factory_version=factory.version)
                db.add(project_factory_record)

                project.add_factory(factory)
            
            db.commit()
            logger.info(
                "Project created",
                project_id=project.id,
                name=name,
                factories=[f.name for f in factories],
            )
            return project

    def add_factory_to_project(self, project_id: str, factory: Factory) -> bool:
        with get_db() as db:
            project_record = db.query(ProjectModel).filter_by(id=project_id).first()
            if not project_record:
                logger.warning("Add factory failed: project not found", project_id=project_id)
                return False
            
            project_path = self.get_project_path(project_id)
            project = Project(id=project_record.id, name=project_record.name, path=project_path, created_at=project_record.created_at, description=project_record.description, config=project_record.config)
            
            project.get_factory_path(factory.name).mkdir(parents=True, exist_ok=True)
            project_factory_record = ProjectFactoryModel(project_id=project.id, factory=factory.name, factory_version=factory.version)
            db.add(project_factory_record)
            project.add_factory(factory)

            db.commit()
            logger.info("Factory added to project", project_id=project_id, factory=factory.id)

            return True

    def delete_project(self, project_id: str) -> bool:
        with get_db() as db:
            project_record = db.query(ProjectModel).filter_by(id=project_id).first()
            if not project_record:
                logger.warning("Delete project failed: not found", project_id=project_id)
                return False
            
            project_path = self.get_project_path(project_id)
            shutil.rmtree(project_path)

            db.query(BlockModel).filter_by(project_id=project_id).delete()
            db.query(ProjectFactoryModel).filter_by(project_id=project_id).delete()
            db.delete(project_record)
            db.commit()
            logger.info("Project deleted", project_id=project_id)
            
            return True

    def delete_all_projects(self) -> bool:
        """Delete every project record and on-disk tree."""
        with get_db() as db:
            projects_records = db.query(ProjectModel).all()
            count = len(projects_records)
            for project_record in projects_records:
                project_path = self.get_project_path(project_record.id)
                shutil.rmtree(project_path)
                
                db.query(BlockModel).filter_by(project_id=project_record.id).delete()
                db.query(ProjectFactoryModel).filter_by(project_id=project_record.id).delete()
                db.delete(project_record)
            
            db.commit()

        logger.info("All projects deleted", count=count)
        return True

    def get_project(self, project_id: str, catalog: Catalog) -> Union[Project, None]:
        """Hydrate a project with factories and blocks, or None if missing."""
        with get_db() as db:
            project_record = db.query(ProjectModel).filter_by(id=project_id).first()
            if not project_record:
                logger.warning("Project not found", project_id=project_id)
                return None
            
            project_path = self.get_project_path(project_id)
            project = Project(id=project_record.id, name=project_record.name, path=project_path, created_at=project_record.created_at, description=project_record.description, config=project_record.config)

            factories_records = db.query(FactoryModel).join(ProjectFactoryModel, and_(FactoryModel.name == ProjectFactoryModel.factory, FactoryModel.version == ProjectFactoryModel.factory_version)).filter(ProjectFactoryModel.project_id == project_id).all()
            for factory_record in factories_records:
                factory = self.__load_factory(db, catalog, factory_record)
                project.add_factory(factory)

            blocks_records = db.query(BlockModel).filter_by(project_id=project_id).all()
            for block_record in blocks_records:
                factory = project.get_factory(block_record.factory)
                frame = factory.get_frame(block_record.frame)
                block = Block(frame=frame, name=block_record.name, data=block_record.data)
                block.load(project, factory)
                project.add_block(block)
            
            logger.debug(
                "Project loaded",
                project_id=project.id,
                factories=len(project.factories),
                blocks=len(project.blocks),
            )
            return project

    def get_all_projects(self, catalog: Catalog) -> dict[str, Project]:
        """Return all projects keyed by id, each fully hydrated."""
        projects = {}

        with get_db() as db:
            projects_records = db.query(ProjectModel).all()
            for project_record in projects_records:
                project_path = self.get_project_path(project_record.id)
                project = Project(id=project_record.id, name=project_record.name, path=project_path, created_at=project_record.created_at, description=project_record.description, config=project_record.config)

                factories_records = db.query(FactoryModel).join(ProjectFactoryModel, and_(FactoryModel.name == ProjectFactoryModel.factory, FactoryModel.version == ProjectFactoryModel.factory_version)).filter(ProjectFactoryModel.project_id == project.id).all()
                for factory_record in factories_records:
                    factory = self.__load_factory(db, catalog, factory_record)
                    project.add_factory(factory)

                blocks_records = db.query(BlockModel).filter_by(project_id=project.id).all()
                for block_record in blocks_records:
                    factory = project.get_factory(block_record.factory)
                    frame = factory.get_frame(block_record.frame)
                    block = Block(frame=frame, name=block_record.name, data=block_record.data)
                    block.load(project, factory)
                    project.add_block(block)
                
                projects[project_record.id] = project

            logger.debug("All projects loaded", count=len(projects))
            return projects

    def create_block(self, project: Project, frame_id: str, block_name: str, data: dict) -> Union[Block, None]:
        """Create a block in the DB and register it on the project.

        The factory named in `frame_id` (`{factory}.{frame}`) must already be
        attached to `project`; registration goes through `Project.add_block`.
        """
        factory_name, frame_name = frame_id.split(".")
        factory = project.get_factory(factory_name)
        if not factory:
            logger.warning("Create block failed: factory not found", project_id=project.id, frame_id=frame_id)
            return None

        frame = factory.get_frame(frame_name)
        if not frame:
            logger.warning("Create block failed: frame not found", project_id=project.id, frame_id=frame_id)
            return None

        block = Block(frame=frame, name=block_name, data=data)
        block.load(project, factory)
        block.validate()

        if not project.add_block(block):
            return None

        with get_db() as db:
            block_record = BlockModel(
                project_id=project.id,
                factory=factory.name,
                factory_version=factory.version,
                frame=frame_name,
                name=block_name,
                data=data,
            )
            db.add(block_record)
            db.commit()

        logger.info("Block created", project_id=project.id, block=block.id, frame=frame_id)
        return block

    def delete_blocks(self, project: Project, blocks_names: list[str]) -> bool:
        """Delete blocks from the DB and unregister them from the project."""
        with get_db() as db:
            db.query(BlockModel).filter(BlockModel.project_id == project.id, BlockModel.name.in_(blocks_names)).delete()
            db.commit()

        for name in blocks_names:
            project.remove_block(name)

        logger.info("Blocks deleted", project_id=project.id, blocks=blocks_names)
        return True

    def get_blocks(self, project: Project, blocks_names: list[str]) -> dict[str, Block]:
        """Load named blocks from the DB and register them on the project."""
        blocks = {}

        with get_db() as db:
            block_records = db.query(BlockModel).filter(
                BlockModel.project_id == project.id,
                BlockModel.name.in_(blocks_names),
            ).all()
            for block_record in block_records:
                factory = project.get_factory(block_record.factory)
                if not factory:
                    continue
                frame = factory.get_frame(block_record.frame)
                if not frame:
                    continue

                block = Block(frame=frame, name=block_record.name, data=block_record.data)
                block.load(project, factory)
                if not project.add_block(block):
                    continue
                blocks[block_record.name] = block

        return blocks



    def summary(self, catalog: Catalog):
        projects = self.get_all_projects(catalog)

        print("### Workspace Summary ###")
        print("=" * 52)
        for project in projects.values():
            print(f"  {project.name} ({project.id})")
            print(f"    factories : {list(project.factories.keys())}")
            print(f"    blocks    : {len(project.blocks)}")
            print()

        print("=" * 52)

    def __str__(self):
        return self.info

    def __repr__(self):
        return self.info