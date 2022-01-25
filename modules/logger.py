from datetime import datetime, timedelta
from typing import Callable, List
from enum import Enum
from os import path, walk, remove
from sys import stdout
from shutil import copy

class LEVEL(Enum):
    WARNING = "WARNING"
    INFO = "INFO"
    ERROR = "ERROR"
    DEBUG = "DEBUG"
    HEADER = "HEADER"

    def get_hierarchy(selected: 'LEVEL') -> List['LEVEL']:
        tmp = [LEVEL.DEBUG, LEVEL.INFO, LEVEL.WARNING, LEVEL.ERROR, LEVEL.HEADER]
        return tmp[tmp.index(selected):]
        
class COLOR(Enum):
    INFO = "\033[92m"
    ERROR = "\033[91m"
    WARNING = "\033[93m"
    HEADER = "\033[94m"
    DEBUG="\033[95m"
    END = "\033[0m"

    def from_level(level: LEVEL) -> "COLOR":
        return getattr(COLOR, level.value)

class logger_class:
    __slots__ = "log_file", "allowed", "log_to_console", "storage_life_extender_mode", "stored_logs", "max_logfile_size", "max_logfile_lifetime", "__print", "use_name"

    def __init__(
        self, 
        log_file: str, 
        clear: bool = False, 
        level: LEVEL = LEVEL.INFO, 
        log_to_console: bool = False, 
        storage_life_extender_mode: bool = False, 
        max_logfile_size: int = -1, 
        max_logfile_lifetime: int = -1,
        __print: Callable = stdout.write,
        use_name: bool = False
    ) -> None:
        self.log_file = log_file
        self.allowed = LEVEL.get_hierarchy(level)
        self.log_to_console = log_to_console
        self.storage_life_extender_mode = storage_life_extender_mode
        self.stored_logs = []
        self.max_logfile_size = max_logfile_size
        self.max_logfile_lifetime = max_logfile_lifetime
        self.__print = __print
        self.use_name = use_name
        if clear:
            with open(log_file, "w"): pass

    def __check_logfile(self) -> None:
        if self.max_logfile_size != -1 and (path.getsize(self.log_file) / 1024^2) > self.max_logfile_size:
            tmp = self.log_file.split(".")
            tmp[0] += str(datetime.now())
            new_name = ".".join(tmp)
            copy(self.log_file, new_name)

        if self.max_logfile_lifetime != -1:
            names = self.__get_all_logfile_names()
            for name in names:
                if datetime.now() - datetime.fromtimestamp(path.getctime(name)) > timedelta(days=self.max_logfile_lifetime):
                    remove(name)

    def __get_all_logfile_names(self) -> List[str]:
        for dir_path, _, filenames in walk(path.dirname(self.log_file)):
            return [path.join(dir_path, fname) for fname in filenames if self.log_file.split(".")[-1] in fname]

    def __log_to_file(self, log_msg: str) -> None:
        if self.storage_life_extender_mode:
            self.stored_logs.append(log_msg)
        else:
            with open(self.log_file, "a") as f:
                f.write(log_msg)
                f.write("\n")
        if len(self.stored_logs) > 500:
            with open(self.log_file, "a") as f:
                f.write("\n".join(self.stored_logs))
                self.stored_logs = []
        self.__check_logfile()

    def __log(self, level: LEVEL, data: str, counter: str, end: str) -> None:
        log_msg = f"[{counter}] [{level.value}]: {data}"
        self.__log_to_file(log_msg)
        if self.log_to_console and level in self.allowed:
            if self.use_name:
                log_msg = f"[{counter}] [{path.splitext(self.log_file.split(path.sep)[-1])[0]}]: {data}"
            self.__print(f"{COLOR.from_level(level).value}{log_msg}{COLOR.END.value}{end}")
    
    def log(self, level: LEVEL, data: str, counter: str = str(datetime.now()), end: str = "\n") -> None:
        if level == LEVEL.INFO:
            self.info(data, counter, end)
        elif level == LEVEL.WARNING:
            self.warning(data, counter, end)
        elif level == LEVEL.ERROR:
            self.error(data, counter, end)
        elif level == LEVEL.HEADER:
            self.header(data, counter, end)
        else:
            self.debug(data, counter, end)

    def header(self, data: str, counter: str = str(datetime.now()), end: str = "\n") -> None:
        decor = list("="*40)
        decor.insert(int(20-len(data) / 2), data)
        final_decor = decor[0:int(20-len(data) / 2) + 1]
        final_decor.extend(decor[int((20-len(data) / 2) + len(data)):])
        self.__log(LEVEL.HEADER, "".join(final_decor), counter, end)

    def debug(self, data: str, counter: str = str(datetime.now()), end: str = "\n") -> None:
        self.__log(LEVEL.DEBUG, data, counter, end)

    def warning(self, data: str, counter: str = str(datetime.now()), end: str = "\n") -> None:
        self.__log(LEVEL.WARNING, data, counter, end)

    def info(self, data: str, counter: str = str(datetime.now()), end: str = "\n") -> None:
        self.__log(LEVEL.INFO, data, counter, end)

    def error(self, data: str, counter: str = str(datetime.now()), end: str = "\n") -> None:
        self.__log(LEVEL.ERROR, data, counter, end)
