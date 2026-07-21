import subprocess
from pathlib import Path
from typing import Union
from jinja2 import Template
import re
import os


def execute(cmd: str, inputs: dict = None, cwd: Union[str, Path] = None):
    # Imported lazily: `server` transitively imports `core.Workspace` -> `core.Project`
    # -> `base.PipelineExecuter` -> here, so a top-level import here would be circular.
    import server

    if inputs:
        cmd = Template(cmd).render(**inputs)

    server.log(f"EXECUTE: {cmd}")
    server.log(f"<***** START *****>")
    proc = subprocess.Popen(cmd, cwd=cwd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    for line in iter(proc.stdout.readline, ""):
        server.log(line.rstrip())
    proc.wait()
    if proc.returncode != 0:
        server.log(f"Error: {cmd}", level="error")
    
    server.log(f"Return Code: {proc.returncode}")
    server.log(f"<***** END *****>")
    return proc.returncode

def get_parameters(cmd: str) -> dict:
    pattern = r'\{[\{%#]\s*(.*?)\s*[\}%#]\}'
    parameters = re.findall(pattern, cmd)      
    return parameters
