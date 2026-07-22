import subprocess
from pathlib import Path
from typing import Union
from jinja2 import Template
import re
import os
from utils import logger


def execute(cmd: str, inputs: dict = None, cwd: Union[str, Path] = None):
    if inputs:
        cmd = Template(cmd).render(**inputs)

    logger.info("Shell execute", cmd=cmd, cwd=str(cwd) if cwd else None)
    logger.debug("Shell output start")
    proc = subprocess.Popen(cmd, cwd=cwd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
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
