from pathlib import Path
import shutil
from typing import Union
from utils.helpers import asjson, load_json
from data.database import get_db
from data.models.FactoryModel import FactoryModel
from data.models.FrameModel import FrameModel
from core.resources.Factory import Factory
from core.resources.Frame import Frame
from base.Template import Template


class Catalog:
    def __init__(self, catalog_config: dict):
        self.__path: Path = Path(catalog_config['path'])

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
                    return factory
                

            factory = Factory(name=factory_name, version=factory_version, data=data, path=factory_path)
            factory.validate(self.get_schema("factory_schema"))

            # create factory directory structure
            self.__create_factory_directory_structure(factory)
            # insert factory record
            db.add(FactoryModel(name=factory.name, version=factory.version, data=factory.spec.data))

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

        return factory

    def create_frame(self, factory_name: str, version: str, frame_name: str, data: dict) -> Union[Frame, None]:
        with get_db() as db:
            factory_record = db.query(FactoryModel).filter_by(name=factory_name, version=version).first()
            if not factory_record:
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

            return frame

    def delete_factory_version(self, factory_name: str, version: str) -> bool:
        factory_path = self.get_factory_path(factory_name)
        with get_db() as db:
            factory_record = db.query(FactoryModel).filter_by(name=factory_name, version=version).first()
            if not factory_record:
                return False

            # delete frame records
            db.query(FrameModel).filter_by(factory=factory_name, factory_version=version).delete()
            db.delete(factory_record)
            db.commit()

            shutil.rmtree(factory_path)
            return True

    def delete_frame(self, factory_name: str, version: str, frame_name: str) -> bool:
        with get_db() as db:
            frame_record = db.query(FrameModel).filter_by(factory=factory_name, factory_version=version, name=frame_name).first()
            if not frame_record:
                return False

            factory_path = self.get_factory_path(factory_name)
            frame_path = factory_path.joinpath(version).joinpath("frames").joinpath(frame_name)

            db.delete(frame_record)
            db.commit()

            shutil.rmtree(frame_path)
            return True

    def get_factory(self, factory_name: str, version: str) -> Union[Factory, None]:
        factory_path = self.get_factory_path(factory_name)
        with get_db() as db:
            factory_record = db.query(FactoryModel).filter_by(name=factory_name, version=version).first()
            if not factory_record:
                return None

            frame_records = db.query(FrameModel).filter_by(factory=factory_name, factory_version=version).all()
            
            factory = Factory(name=factory_name, version=version, data=factory_record.data, path=factory_path)
            for record in frame_records:
                frame_id = f'{factory.id}.{record.name}'
                frame_path = factory.version_path.joinpath("frames").joinpath(record.name)

                frame = Frame(id=frame_id, name=record.name, data=record.data, path=frame_path)
                frame.load()
                factory.add_frame(frame)

            return factory

    def get_all_factories(self) -> dict[str, Factory]:
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

        return factories

    def get_frame(self, factory_name: str, version: str, frame_name: str) -> Union[Frame, None]:
        factory_path = self.get_factory_path(factory_name)
        with get_db() as db:
            frame_record = db.query(FrameModel).filter_by(factory=factory_name, factory_version=version, name=frame_name).first()
            if not frame_record:
                return None

            frame_id = f'{factory_name}:{version}.{frame_name}'
            frame_path = factory_path.joinpath(version).joinpath("frames").joinpath(frame_name)

            frame = Frame(id=frame_id, name=frame_name, data=frame_record.data, path=frame_path)
            frame.load()
            return frame

    def update_factory(self, factory_name: str, version: str, data: dict = None) -> bool:
        factory_path = self.get_factory_path(factory_name)
        with get_db() as db:
            factory_record = db.query(FactoryModel).filter_by(name=factory_name, version=version).first()
            if not factory_record:
                return False

            data = data if data else factory_record.data
            factory = Factory(name=factory_name, version=version, data=data, path=factory_path)
            factory.validate(self.get_schema("factory_schema"))
            factory_record.data = factory.spec.data

            db.commit()
            return True

    def update_frame(self, factory_name: str, version: str, frame_name: str, data: dict = None) -> bool:
        with get_db() as db:
            frame_record = db.query(FrameModel).filter_by(factory=factory_name, factory_version=version, name=frame_name).first()
            if not frame_record:
                return False

            factory_path = self.get_factory_path(factory_name)
            frame_path = factory_path.joinpath(version).joinpath("frames").joinpath(frame_name)
            frame_id = f'{factory_name}:{version}.{frame_name}'
            
            data = data if data else frame_record.data
            frame = Frame(id=frame_id, name=frame_name, data=data, path=frame_path)
            frame.validate(self.get_schema("frame_schema"))
            frame_record.data = frame.spec.data

            db.commit()
            return True


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
