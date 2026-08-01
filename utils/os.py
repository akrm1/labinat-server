import subprocess
from pathlib import Path
from typing import Union
from jinja2 import Template
import re
from utils import logger
from utils.cancellation import guard_process


def execute(cmd: str, inputs: dict = None, cwd: Union[str, Path] = None):
    if inputs:
        cmd = Template(cmd).render(**inputs)

    logger.info("Shell execute", cmd=cmd, cwd=str(cwd) if cwd else None)
    logger.debug("Shell output start")
    # start_new_session puts the child in its own process group so a cancelled
    # streamed operation can terminate it (and anything it spawned) as a unit.
    proc = subprocess.Popen(cmd, cwd=cwd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, start_new_session=True)
    guard_process(proc)
    for line in iter(proc.stdout.readline, ""):
        logger.debug(line.rstrip())
    proc.wait()
    if proc.returncode != 0:
        logger.error("Shell command failed", cmd=cmd, return_code=proc.returncode)
    else:
        logger.debug("Shell command succeeded", return_code=proc.returncode)
    return proc.returncode

def get_parameters(cmd: str) -> dict:
    pattern = r'\{[\{%#]\s*(.*?)\s*[\}%#]\}'
    parameters = re.findall(pattern, cmd)      
    return parameters
