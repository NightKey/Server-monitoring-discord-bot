from modules import logger
from os.path import join

def __level__() -> logger.LEVEL:
    with open(join("configs","level"), 'r') as f:
        return logger.LEVEL.from_string(f.read(-1))

def __folder__() -> str:
    with open(join("configs","folder"), 'r') as f:
        return f.read(-1)

log_level = __level__()
log_folder = __folder__()