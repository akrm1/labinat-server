"""Build a container image from an emitted factory source tree."""

import subprocess
from pathlib import Path
from typing import Union

from utils import logger


class ImageBuildError(Exception):
    """Raised when a container image build exits non-zero."""


class ImageBuilder:
    """Wraps a container build tool (`docker` by default) for one image build.

    The build command is assembled as an argument list and run without a
    shell, so a project-derived tag or path can never be interpreted as shell
    syntax. `build` returns the tool's exit code; callers decide whether a
    non-zero result should abort.
    """

    def __init__(self, tool: str = "docker"):
        self.__tool = tool

    @property
    def tool(self) -> str:
        return self.__tool

    def build(self, context_dir: Union[str, Path], tag: str, dockerfile: str = "Dockerfile") -> int:
        """Build `context_dir` into an image tagged `tag`; return the exit code."""
        context_dir = Path(context_dir)
        command = [
            self.__tool, "build",
            "-t", tag,
            "-f", str(context_dir.joinpath(dockerfile)),
            str(context_dir),
        ]

        logger.info("Image build starting", tool=self.__tool, tag=tag, context=str(context_dir))
        logger.debug("Image build output start")

        try:
            proc = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except FileNotFoundError as error:
            logger.error("Image build tool not found", tool=self.__tool)
            raise ImageBuildError(
                f"Container build tool '{self.__tool}' is not installed or not on PATH"
            ) from error

        for line in iter(proc.stdout.readline, ""):
            logger.debug(line.rstrip())
        proc.wait()

        if proc.returncode != 0:
            logger.error("Image build failed", tag=tag, return_code=proc.returncode)
        else:
            logger.info("Image build finished", tag=tag)

        return proc.returncode
