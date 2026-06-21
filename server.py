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

    logger_config = config['logger']
    logger.init(logger_config['name'], logger_config['level'], logger_config['handlers'])

    database.init_db(config['database'])
    controller.init(config['catalog'], config['workspace'])

def log(message: str, level: str = "info"):
    logger.log(message, level)



