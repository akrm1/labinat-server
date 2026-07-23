"""Filesystem helpers used across packaging and tree copies."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Callable, Iterator, Optional


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()

def is_python_bytecode(path: Path) -> bool:
    return path.name == "__pycache__" or path.name.endswith(".pyc")

def iter_files(root: Path, *, skip: Optional[Callable[[Path], bool]] = None) -> Iterator[Path]:
    """Yield files under `root`, skipping entries matched by `skip`."""
    root = Path(root)
    if not root.exists():
        return
    skip = skip or is_python_bytecode

    def walk(directory: Path) -> Iterator[Path]:
        for item in sorted(directory.iterdir()):
            if skip(item):
                continue
            if item.is_dir():
                yield from walk(item)
            elif item.is_file():
                yield item

    yield from walk(root)


def copy_tree(src: Path, dest: Path, *, skip: Optional[Callable[[Path], bool]] = None) -> None:
    """Copy a directory tree, skipping paths matched by `skip` (default: bytecode)."""
    src = Path(src)
    dest = Path(dest)
    if not src.exists():
        return

    skip = skip or is_python_bytecode
    dest.mkdir(parents=True, exist_ok=True)
    
    for item in sorted(src.iterdir()):
        if skip(item):
            continue

        target = dest.joinpath(item.name)
        if item.is_dir():
            copy_tree(item, target, skip=skip)
        else:
            shutil.copy2(item, target)
