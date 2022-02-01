from modules import logger
from os.path import join

def __level__() -> logger.LEVEL:
    with open(join("modules","level"), 'r') as f:
        return logger.LEVEL.from_string(f.read(-1))

log_level = __level__()