from smdb_logger import LEVEL
from os.path import join


def __level__() -> LEVEL:
    with open(join("configs", "level"), 'r') as f:
        return LEVEL.from_string(f.read(-1))


def __folder__() -> str:
    with open(join("configs", "folder"), 'r') as f:
        return f.read(-1)


log_level = __level__()
log_folder = __folder__()
