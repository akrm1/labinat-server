"""Simple `.tar.gz` packaging with MANIFEST.json and safe extract."""

from __future__ import annotations

import tarfile
import tempfile
from pathlib import Path
from typing import Any, Union

from utils import logger
from utils.fs import copy_tree, iter_files, sha256_file
from utils.helpers import load_json, save_json


class PackagerError(Exception):
    """Raised when an archive is invalid, unsafe, or unsupported."""


class Packager:
    """One packaging interface: stage, manifest, pack, unpack."""

    MANIFEST_NAME = "MANIFEST.json"

    def __init__(self, format_version: int = 1, staging_prefix: str = "labinat-pkg-"):
        self.format_version = format_version
        self.staging_prefix = staging_prefix

    def staging_dir(self) -> tempfile.TemporaryDirectory:
        return tempfile.TemporaryDirectory(prefix=self.staging_prefix)

    def copy_tree(self, src: Union[str, Path], dest: Union[str, Path]) -> None:
        copy_tree(Path(src), Path(dest))

    def archive_path(self, dest_path: Union[str, Path], default_name: str) -> Path:
        dest_path = Path(dest_path)
        if dest_path.is_dir() or (not dest_path.exists() and dest_path.suffix == ""):
            dest_path.mkdir(parents=True, exist_ok=True)
            return dest_path / default_name
        if not (str(dest_path).endswith(".tar.gz") or str(dest_path).endswith(".tgz")):
            return Path(f"{dest_path}.tar.gz")
        return dest_path

    def write_manifest(self, staging_root: Path, content_root: Path, **metadata: Any) -> Path:
        staging_root = Path(staging_root)
        content_root = Path(content_root)
        checksums = {
            path.relative_to(staging_root).as_posix(): sha256_file(path)
            for path in iter_files(content_root)
        }
        manifest = {"format_version": self.format_version, "checksums": checksums, **metadata}
        path = staging_root / self.MANIFEST_NAME
        save_json(str(path), manifest)
        return path

    def read_manifest(self, staging_root: Path, *required: str) -> dict:
        path = Path(staging_root) / self.MANIFEST_NAME
        if not path.exists():
            raise PackagerError(f"{self.MANIFEST_NAME} missing from package")
        manifest = load_json(str(path))
        if not isinstance(manifest, dict):
            raise PackagerError(f"{self.MANIFEST_NAME} must be an object")
        if manifest.get("format_version") != self.format_version:
            raise PackagerError(
                f"Unsupported format_version: {manifest.get('format_version')} "
                f"(expected {self.format_version})"
            )
        for key in required:
            if not manifest.get(key):
                raise PackagerError(f"{self.MANIFEST_NAME} requires {key}")
        return manifest

    def pack(self, staging_root: Path, archive_path: Path) -> Path:
        staging_root = Path(staging_root)
        archive_path = Path(archive_path)
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        with tarfile.open(archive_path, "w:gz") as tar:
            for path in iter_files(staging_root):
                tar.add(path, arcname=path.relative_to(staging_root).as_posix())
        logger.info("Package archived", path=str(archive_path))
        return archive_path

    def unpack(self, archive_path: Path, dest: Path) -> Path:
        archive_path = Path(archive_path)
        dest = Path(dest)
        if not archive_path.is_file():
            raise PackagerError(f"Archive not found: {archive_path}")
        dest.mkdir(parents=True, exist_ok=True)
        with tarfile.open(archive_path, "r:gz") as tar:
            for member in tar.getmembers():
                name = member.name
                if (
                    name.startswith("/")
                    or name.startswith("\\")
                    or ".." in Path(name).parts
                    or member.islnk()
                    or member.issym()
                ):
                    raise PackagerError(f"Unsafe archive member: {member.name}")
                try:
                    tar.extract(member, path=dest, filter="data")
                except TypeError:
                    tar.extract(member, path=dest)
        return dest
