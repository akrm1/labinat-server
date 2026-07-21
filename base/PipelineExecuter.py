from utils import os
from pathlib import Path
from typing import Union

class PipelineExecuter:
    def __init__(self, name: str, actions: list[dict] = []):
        self.__name: str = name
        self.update_actions(actions)

    @property
    def name(self):
        return self.__name

    def add_action(self, name: str, cmd: str):
        self.__actions.append({
            "name": name,
            "cmd": cmd
        })

    def update_actions(self, actions: list[dict]):
        self.__actions = []
        for action in actions:
            name = action.get("name", None)
            cmd = action.get("cmd", None)

            if name is not None and cmd is not None:
                self.add_action(name, cmd)

    def __execute(self, cwd: Union[str, Path] = None, **inputs):
        # Imported lazily: `server` transitively imports `core.Workspace` -> `core.Project`,
        # which imports this module at load time, so a top-level import here would be circular.
        import server

        if len(self.__actions) == 0:
            return
        
        title = self.__name.capitalize()
        return_code = 0

        for action in self.__actions:
            name = action["name"]
            cmd = action["cmd"]

            server.log(f"### {name} ...")
            return_code = os.execute(cmd, inputs, cwd=cwd)

            if return_code != 0:
                server.log(f"{title} Failed: issue occurred while executing \"{name}\": \'{cmd}\'", level="error")
                return
            
            server.log(f"------------------------------------------------")
        
        server.log(f"** Successfully Execute \'{title}\' Operator **")

    def parameters(self, index: Union[int, str]) -> dict:
        if isinstance(index, int):
            return os.get_parameters(self.__actions[index]["cmd"])
        elif isinstance(index, str):
            return os.get_parameters(index)
        else:
            raise ValueError(f"Invalid index: {index}")
    
    def __call__(self, cwd: Union[str, Path] = None, **inputs):
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