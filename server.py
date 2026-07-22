import yaml
from utils import logger
from data import database
import controller


config : dict = None

def load_config():
    global config
    with open("config.yaml", "r") as file:
        config = yaml.safe_load(file)

def init():
    load_config()
    global config

    logger.init(config['logger'])
    logger.info("Server initializing")

    database.init_db(config['database'])
    logger.info("Database initialized", url=config['database'].get('url'))

    controller.init(config['catalog'], config['workspace'])
    logger.info(
        "Controller ready",
        catalog=config['catalog'].get('path'),
        workspace=config['workspace'].get('path'),
    )


def log(message: str, level: str = "info", **extra):
    """Thin re-export of the centralized logger for legacy call sites."""
    logger.log(message, level=level, **extra)



