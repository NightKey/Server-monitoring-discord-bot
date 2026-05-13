from os.path import join

from smdb_logger import LEVEL


def __level__() -> LEVEL:
    with open(join("configs", "level"), 'r') as f:
        return LEVEL.from_string(f.read(-1))


def __folder__() -> str:
    with open(join("configs", "folder"), 'r') as f:
        return f.read(-1)
