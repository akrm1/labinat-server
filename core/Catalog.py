"""Catalog registry: factories and frames on disk + in SQLite."""

from pathlib import Path
import shutil
from typing import Union
from utils.helpers import asjson, load_json, save_json
from utils import logger
from utils.fs import is_python_bytecode
from data.database import get_db
from data.models.FactoryModel import FactoryModel
from data.models.FrameModel import FrameModel
from core.resources.Factory import Factory
from core.resources.Frame import Frame
from base.Template import Template
from base.Spec import Spec
from base.Packager import Packager, PackagerError


class Catalog:
    """Persistent registry of versioned factories and their frames.

    CRUD mutates SQLite and the on-disk tree under `catalog/factories/`.
    Lookups hydrate `Factory`/`Frame` objects and call `frame.load()`.
    Factory package import/export also live here (Specs in DB, artifacts on disk).
    """

    __packager = Packager(format_version=1, staging_prefix="labinat-factory-pkg-")
    __package_root = "factory"

    def __init__(self, catalog_config: dict):
        self.__path: Path = Path(catalog_config['path'])
        logger.debug("Catalog initialized", path=str(self.__path))

    @property
    def path(self) -> Path:
        return self.__path

    def get_context(self, factory: Factory = None, frame: Frame = None) -> dict:
        context = {}
        context["catalog"] = {
            "path": self.__path.absolute()
        }

        if factory is not None:
            context["factory"] = {
                "name": factory.name,
                "version": factory.version,
                "path": factory.path.absolute(),
                "version_path": factory.version_path.absolute()
            }

        if frame is not None:
            context["frame"] = {
                "id": frame.id,
                "name": frame.name,
                "path": frame.path.absolute()
            }

        return context

    def get_factory_path(self, factory_name: str) -> Path:
        return self.__path.joinpath("factories").joinpath(factory_name)

    def get_schema(self, name: str) -> dict:
        return load_json(self.__path.joinpath("schemas").joinpath(f"{name}.json"))

    def get_template(self, filename: str) -> Template:
        filepath = self.__path.joinpath("templates").joinpath(f"{filename}.j2")
        return Template.from_file(filepath)

    def __create_factory_directory_structure(self, factory: Factory):
        # create factory directory structure
        factory.path.mkdir(parents=True, exist_ok=True)

        # create factory version sub-directories
        factory.version_path.mkdir(parents=True, exist_ok=True)

        # create factory version sub-directories
        factory.version_path.joinpath("frames").mkdir(parents=True, exist_ok=True)
        factory.version_path.joinpath("base").mkdir(parents=True, exist_ok=True)

    def __create_frame_directory_structure(self, frame: Frame):
        # create frame directory structure
        frame.path.mkdir(parents=True, exist_ok=True)

        # create frame sub-directories
        frame.path.joinpath("concretes").mkdir(parents=True, exist_ok=True)
        frame.path.joinpath("bindings").mkdir(parents=True, exist_ok=True)

        # create module file
        module_path = frame.path.joinpath("module.py")
        module_path.touch()

        context = self.get_context(frame=frame)
        module_content = self.get_template("frame_module.py").render(context)
        module_path.write_text(module_content)

    def create_factory(self, factory_name: str, factory_version: str, data: dict, frames: list[str]) -> Factory:
        factory_path = self.get_factory_path(factory_name)
        logger.info("Creating factory", factory=factory_name, version=factory_version, frames=frames)
        with get_db() as db:
            factory_record = db.query(FactoryModel).filter_by(name=factory_name, version=factory_version).first()
            if factory_record:
                factory = Factory(name=factory_record.name, version=factory_record.version, data=factory_record.data, path=factory_path)
                
                frame_records = db.query(FrameModel).filter_by(factory=factory.name, factory_version=factory.version).all()
                frame_records_names = [record.name for record in frame_records]
                new_frames = set(frames) - set(frame_records_names)

                for frame_name in new_frames:
                    frame_id = f'{factory.id}.{frame_name}'
                    frame_path = factory.version_path.joinpath("frames").joinpath(frame_name)
                    frame = Frame(id=frame_id, name=frame_name, data={}, path=frame_path)

                    # create frame directory structure
                    self.__create_frame_directory_structure(frame)
                    # load frame components (module, concretes, bindings)
                    frame.load()
                    # add frame to factory
                    factory.add_frame(frame)
                    # insert frame record
                    db.add(FrameModel(factory=factory.name, factory_version=factory.version, name=frame.name, data={}))

                    db.commit()
                    logger.info("Factory already existed; added frames", factory=factory_name, version=factory_version, added=list(new_frames))
                    return factory
                

            factory = Factory(name=factory_name, version=factory_version, data=data, path=factory_path)
            factory.validate(self.get_schema("factory_schema"))

            # create factory directory structure
            self.__create_factory_directory_structure(factory)
            # insert factory record, flushed before the frames whose foreign
            # keys point at it (no relationships exist to order them)
            db.add(FactoryModel(name=factory.name, version=factory.version, data=factory.spec.data))
            db.flush()

            # create and add frames to factory
            for frame_name in frames:
                frame_id = f'{factory.id}.{frame_name}'
                frame_path = factory.version_path.joinpath("frames").joinpath(frame_name)
                frame = Frame(id=frame_id, name=frame_name, data={}, path=frame_path)

                # create frame directory structure
                self.__create_frame_directory_structure(frame)
                # load frame components (module, concretes, bindings)
                frame.load()
                # add frame to factory
                factory.add_frame(frame)
                # insert frame record
                db.add(FrameModel(factory=factory.name, factory_version=factory.version, name=frame.name, data=frame.spec.data))

            db.commit()
            logger.info("Factory created", factory=factory.id, frames=list(factory.frames.keys()))

        return factory

    def create_frame(self, factory_name: str, version: str, frame_name: str, data: dict) -> Union[Frame, None]:
        with get_db() as db:
            factory_record = db.query(FactoryModel).filter_by(name=factory_name, version=version).first()
            if not factory_record:
                logger.warning("Create frame failed: factory not found", factory=factory_name, version=version, frame=frame_name)
                return None

            factory_path = self.get_factory_path(factory_name)
            frame_id = f'{factory_name}:{version}.{frame_name}'
            frame_path = factory_path.joinpath(version).joinpath("frames").joinpath(frame_name)

            frame = Frame(id=frame_id, name=frame_name, data=data, path=frame_path)
            frame.validate(self.get_schema("frame_schema"))

            # create frame directory structure
            self.__create_frame_directory_structure(frame)
            # load frame components (module, concretes, bindings)
            frame.load()
            db.add(FrameModel(factory=factory_name, factory_version=version, name=frame.name, data=frame.spec.data))
            db.commit()
            logger.info("Frame created", frame=frame.id)

            return frame

    def delete_factory_version(self, factory_name: str, version: str) -> bool:
        factory_path = self.get_factory_path(factory_name)
        with get_db() as db:
            factory_record = db.query(FactoryModel).filter_by(name=factory_name, version=version).first()
            if not factory_record:
                logger.warning("Delete factory failed: not found", factory=factory_name, version=version)
                return False

            # delete frame records
            db.query(FrameModel).filter_by(factory=factory_name, factory_version=version).delete()
            db.delete(factory_record)
            db.commit()

            shutil.rmtree(factory_path)
            logger.info("Factory version deleted", factory=factory_name, version=version)
            return True

    def delete_frame(self, factory_name: str, version: str, frame_name: str) -> bool:
        with get_db() as db:
            frame_record = db.query(FrameModel).filter_by(factory=factory_name, factory_version=version, name=frame_name).first()
            if not frame_record:
                logger.warning("Delete frame failed: not found", factory=factory_name, version=version, frame=frame_name)
                return False

            factory_path = self.get_factory_path(factory_name)
            frame_path = factory_path.joinpath(version).joinpath("frames").joinpath(frame_name)

            db.delete(frame_record)
            db.commit()

            shutil.rmtree(frame_path)
            logger.info("Frame deleted", factory=factory_name, version=version, frame=frame_name)
            return True

    def get_factory(self, factory_name: str, version: str) -> Union[Factory, None]:
        """Load a factory and its frames from the database, or None if missing."""
        factory_path = self.get_factory_path(factory_name)
        with get_db() as db:
            factory_record = db.query(FactoryModel).filter_by(name=factory_name, version=version).first()
            if not factory_record:
                logger.warning("Factory not found", factory=factory_name, version=version)
                return None

            frame_records = db.query(FrameModel).filter_by(factory=factory_name, factory_version=version).all()
            
            factory = Factory(name=factory_name, version=version, data=factory_record.data, path=factory_path)
            for record in frame_records:
                frame_id = f'{factory.id}.{record.name}'
                frame_path = factory.version_path.joinpath("frames").joinpath(record.name)

                frame = Frame(id=frame_id, name=record.name, data=record.data, path=frame_path)
                frame.load()
                factory.add_frame(frame)

            logger.debug("Factory loaded", factory=factory.id, frames=len(factory.frames))
            return factory

    def get_all_factories(self) -> dict[str, Factory]:
        """Return all factories keyed by name (last version wins on name collision)."""
        factories = {}

        with get_db() as db:
            factory_records = db.query(FactoryModel).all()
            for factory_record in factory_records:
                factory_path = self.get_factory_path(factory_record.name)
                factory = Factory(name=factory_record.name, version=factory_record.version, data=factory_record.data, path=factory_path)
                
                frame_records = db.query(FrameModel).filter_by(factory=factory.name, factory_version=factory.version).all()
                for frame_record in frame_records:
                    frame_id = f'{factory.id}.{frame_record.name}'
                    frame_path = factory.version_path.joinpath("frames").joinpath(frame_record.name)

                    frame = Frame(id=frame_id, name=frame_record.name, data=frame_record.data, path=frame_path)
                    frame.load()
                    factory.add_frame(frame)

                factories[factory.name] = factory

        logger.debug("All factories loaded", count=len(factories))
        return factories

    def get_frame(self, factory_name: str, version: str, frame_name: str) -> Union[Frame, None]:
        """Load a single frame from the database, or None if missing."""
        factory_path = self.get_factory_path(factory_name)
        with get_db() as db:
            frame_record = db.query(FrameModel).filter_by(factory=factory_name, factory_version=version, name=frame_name).first()
            if not frame_record:
                logger.warning(
                    "Frame not found",
                    factory=factory_name,
                    version=version,
                    frame=frame_name,
                )
                return None

            frame_id = f'{factory_name}:{version}.{frame_name}'
            frame_path = factory_path.joinpath(version).joinpath("frames").joinpath(frame_name)

            frame = Frame(id=frame_id, name=frame_name, data=frame_record.data, path=frame_path)
            frame.load()
            logger.debug("Frame loaded", frame=frame.id)
            return frame

    def update_factory(self, factory_name: str, version: str, data: dict = None) -> bool:
        """Validate and persist factory Spec data. Returns False if not found."""
        factory_path = self.get_factory_path(factory_name)
        with get_db() as db:
            factory_record = db.query(FactoryModel).filter_by(name=factory_name, version=version).first()
            if not factory_record:
                logger.warning("Update factory failed: not found", factory=factory_name, version=version)
                return False

            data = data if data else factory_record.data
            factory = Factory(name=factory_name, version=version, data=data, path=factory_path)
            factory.validate(self.get_schema("factory_schema"))
            factory_record.data = factory.spec.data

            db.commit()
            logger.info("Factory updated", factory=factory.id)
            return True

    def update_frame(self, factory_name: str, version: str, frame_name: str, data: dict = None) -> bool:
        """Validate and persist frame Spec data. Returns False if not found."""
        with get_db() as db:
            frame_record = db.query(FrameModel).filter_by(factory=factory_name, factory_version=version, name=frame_name).first()
            if not frame_record:
                logger.warning(
                    "Update frame failed: not found",
                    factory=factory_name,
                    version=version,
                    frame=frame_name,
                )
                return False

            factory_path = self.get_factory_path(factory_name)
            frame_path = factory_path.joinpath(version).joinpath("frames").joinpath(frame_name)
            frame_id = f'{factory_name}:{version}.{frame_name}'
            
            data = data if data else frame_record.data
            frame = Frame(id=frame_id, name=frame_name, data=data, path=frame_path)
            frame.validate(self.get_schema("frame_schema"))
            frame_record.data = frame.spec.data

            db.commit()
            logger.info("Frame updated", frame=frame.id)
            return True

    def export_factory(self, factory_name: str, version: str, dest_path: Union[str, Path]) -> Path:
        """Pack a registered factory into a `.tar.gz` archive.

        Specs are taken from the database (via `get_factory`); artifacts from
        the on-disk tree. Spec JSON files appear only inside the archive.
        """
        factory = self.get_factory(factory_name, version)
        if factory is None:
            raise PackagerError(f"Factory not found: {factory_name}:{version}")

        packager = self.__packager
        dest_path = packager.archive_path(dest_path, f"{factory.name}-{factory.version}.tar.gz")
        logger.info("Exporting factory", factory=factory.id, dest=str(dest_path))

        with packager.staging_dir() as staging:
            staging_root = Path(staging)
            package_dir = staging_root / self.__package_root / factory.name / factory.version
            package_dir.mkdir(parents=True, exist_ok=True)

            packager.copy_tree(factory.version_path, package_dir)
            Factory.strip_spec_files(package_dir)

            save_json(str(package_dir / "factory.json"), factory.spec.data or {})
            for frame in factory.frames.values():
                frame_dir = package_dir / "frames" / frame.name
                frame_dir.mkdir(parents=True, exist_ok=True)
                save_json(str(frame_dir / "frame.json"), frame.spec.data or {})

            packager.write_manifest(
                staging_root, package_dir, name=factory.name, version=factory.version
            )
            return packager.pack(staging_root, dest_path)

    def import_factory(self, archive_path: Union[str, Path], overwrite: bool = False) -> Factory:
        """Import a factory archive: Specs → DB, artifacts → disk (no Spec JSON on disk)."""
        packager = self.__packager
        archive_path = Path(archive_path)

        with packager.staging_dir() as staging:
            staging_root = Path(staging)
            packager.unpack(archive_path, staging_root)
            manifest = packager.read_manifest(staging_root, "name", "version")
            name, version = manifest["name"], manifest["version"]

            package_dir = staging_root / self.__package_root / name / version
            if not package_dir.is_dir():
                raise PackagerError(
                    f"Package directory missing: {self.__package_root}/{name}/{version}"
                )

            factory_data, frames = self.__read_package_specs(package_dir, name)
            Spec(factory_data).validate(self.get_schema("factory_schema"))
            for frame_data in frames.values():
                Spec(frame_data).validate(self.get_schema("frame_schema"))

            version_path = self.get_factory_path(name) / version

            with get_db() as db:
                existing = db.query(FactoryModel).filter_by(name=name, version=version).first()
                if existing and not overwrite:
                    raise PackagerError(
                        f"Factory already exists: {name}:{version} (pass overwrite=True)"
                    )

                if version_path.exists():
                    if not overwrite:
                        raise PackagerError(
                            f"On-disk factory path already exists: {version_path}"
                        )
                    shutil.rmtree(version_path)

                version_path.parent.mkdir(parents=True, exist_ok=True)
                packager.copy_tree(package_dir, version_path)
                Factory.strip_spec_files(version_path)

                if existing:
                    existing.data = factory_data
                else:
                    db.add(FactoryModel(name=name, version=version, data=factory_data))
                # Flushed so the factory row exists before its frames are
                # inserted against it.
                db.flush()

                for frame_name, frame_data in frames.items():
                    frame_record = db.query(FrameModel).filter_by(
                        factory=name, factory_version=version, name=frame_name
                    ).first()
                    if frame_record:
                        frame_record.data = frame_data
                    else:
                        db.add(FrameModel(
                            factory=name,
                            factory_version=version,
                            name=frame_name,
                            data=frame_data,
                        ))

                db.commit()

        factory = self.get_factory(name, version)
        logger.info("Factory imported", factory=f"{name}:{version}", frames=len(frames))
        return factory

    def __read_package_specs(
        self, package_dir: Path, name: str
    ) -> tuple[dict, dict[str, dict]]:
        """Read Spec JSON from an unpacked package (transport only, not catalog disk)."""
        factory_json = package_dir / "factory.json"
        if not factory_json.exists():
            raise PackagerError("factory.json missing from package")
        factory_data = load_json(str(factory_json))
        if not isinstance(factory_data, dict):
            raise PackagerError("factory.json must be an object")

        frames: dict[str, dict] = {}
        frames_root = package_dir / "frames"
        if frames_root.is_dir():
            for frame_dir in sorted(frames_root.iterdir()):
                if not frame_dir.is_dir() or is_python_bytecode(frame_dir):
                    continue
                frame_json = frame_dir / "frame.json"
                if not frame_json.exists():
                    raise PackagerError(f"frame.json missing for frame '{frame_dir.name}'")
                data = load_json(str(frame_json))
                if not isinstance(data, dict):
                    raise PackagerError(f"frame.json for '{frame_dir.name}' must be an object")
                data.setdefault("name", frame_dir.name)
                data.setdefault("factory", name)
                frames[frame_dir.name] = data

        return factory_data, frames

    def summary(self):
        factories = self.get_all_factories()

        print("### Catalog Summary ###")
        print("=" * 52)
        for factory in factories.values():
            print(f"  {factory.name}:{factory.version}")
            print(f"    frames : {list(factory.frames.keys())}")
            print(f"    maps   : {list(factory.maps.keys())}")
            print()

        print("=" * 52)

    @property
    def info(self):
        return asjson({"path": self.__path.absolute()})

    def __str__(self):
        return self.info

    def __repr__(self):
        return self.info
