from smdb_logger import LEVEL
from os.path import join
from .bar import Bar
from .scanner import scann
from .services import LinkingEditorData, Server
from .status import get_battery_status, get_disk_status, get_graphical, get_memory_status, get_pc_status, get_temp
from .updater import main
from .user import UserException, User, UserContainer, create_code
from .watchdog import Watchdog
import connectors

def __level__() -> LEVEL:
    with open(join("configs", "level"), 'r') as f:
        return LEVEL.from_string(f.read(-1))


def __folder__() -> str:
    with open(join("configs", "folder"), 'r') as f:
        return f.read(-1)


log_level = __level__()
log_folder = __folder__()
