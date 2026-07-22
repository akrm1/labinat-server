"""Execute a named sequence of shell lifecycle actions for a factory."""

from utils import os
from utils import logger
from pathlib import Path
from typing import Union


class PipelineExecuter:
    """Runs factory lifecycle steps (`build`, `rebuild`, …) as shell commands.

    Each action is `{name, cmd}`; `cmd` may be a Jinja template filled from
    the project/factory context passed into `__call__`.
    """

    def __init__(self, name: str, actions: list[dict] = []):
        self.__name: str = name
        self.update_actions(actions)

    @property
    def name(self):
        return self.__name

    def add_action(self, name: str, cmd: str):
        """Append one named shell action to this pipeline."""
        self.__actions.append({
            "name": name,
            "cmd": cmd
        })

    def update_actions(self, actions: list[dict]):
        """Replace the action list, keeping only entries with both name and cmd."""
        self.__actions = []
        for action in actions:
            name = action.get("name", None)
            cmd = action.get("cmd", None)

            if name is not None and cmd is not None:
                self.add_action(name, cmd)

    def __execute(self, cwd: Union[str, Path] = None, **inputs):
        if len(self.__actions) == 0:
            logger.debug("Pipeline has no actions; skipping", pipeline=self.__name)
            return
        
        title = self.__name.capitalize()
        logger.info(
            "Pipeline starting",
            pipeline=self.__name,
            actions=len(self.__actions),
            cwd=str(cwd) if cwd else None,
        )

        for action in self.__actions:
            name = action["name"]
            cmd = action["cmd"]

            logger.info("Pipeline action starting", pipeline=self.__name, action=name)
            return_code = os.execute(cmd, inputs, cwd=cwd)

            if return_code != 0:
                logger.error(
                    "Pipeline action failed",
                    pipeline=self.__name,
                    action=name,
                    cmd=cmd,
                    return_code=return_code,
                )
                return
            
            logger.debug("Pipeline action finished", pipeline=self.__name, action=name)
        
        logger.info("Pipeline completed successfully", pipeline=title)

    def parameters(self, index: Union[int, str]) -> dict:
        """Return Jinja parameter names referenced by an action cmd."""
        if isinstance(index, int):
            return os.get_parameters(self.__actions[index]["cmd"])
        elif isinstance(index, str):
            return os.get_parameters(index)
        else:
            raise ValueError(f"Invalid index: {index}")
    
    def __call__(self, cwd: Union[str, Path] = None, **inputs):
        """Execute the pipeline with optional working directory and Jinja inputs."""
        return self.__execute(cwd=cwd, **inputs)

    def __str__(self):
        string = ""
        for action in self.__actions:
            name = action["name"]
            cmd = action["cmd"]

            string += f"- {cmd}  ## {name}\n"
            
        return f"### \'{self.__name.capitalize()}\' Operator ###\n{string}\n"

    def __repr__(self):
        return self.__str__()
