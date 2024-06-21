from smdb_logger import LEVEL
from .coordinates import Coordinates, get_coordinates
from os.path import join
from typing import Union
from os import path


def __level__() -> LEVEL:
    with open(join("configs", "level"), 'r') as f:
        return LEVEL.from_string(f.read(-1))


def __folder__() -> str:
    with open(join("configs", "folder"), 'r') as f:
        return f.read(-1)


log_level = __level__()
log_folder = __folder__()
__location_cache: Union[Coordinates, None] = None

def __coordinates__() -> None:
    global __location_cache
    if (__location_cache is not None):
        return __location_cache
    address_path = path.join("data", "address.cfg")
    if path.exists(address_path):
        with open(address_path, "r", encoding="utf-8") as fp:
            __location_cache = get_coordinates(fp.read(-1))
            return __location_cache
    return None

server_coordinates: Union[Coordinates, None] = __coordinates__()
