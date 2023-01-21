from datetime import timedelta, datetime
from time import time
import inspect
from typing import Callable, List
from enum import Enum
from os import path, walk, remove, mkdir
from sys import stdout
from shutil import move


class LEVEL(Enum):
    WARNING = "WARNING"
    INFO = "INFO"
    ERROR = "ERROR"
    DEBUG = "DEBUG"
    HEADER = "HEADER"

    def from_string(string: str) -> 'LEVEL':
        for lvl in [LEVEL.DEBUG, LEVEL.INFO, LEVEL.WARNING, LEVEL.ERROR, LEVEL.HEADER]:
            if lvl.value.lower() == string.lower():
                return lvl
        return None

    def get_hierarchy(selected: 'LEVEL') -> List['LEVEL']:
        tmp = [LEVEL.DEBUG, LEVEL.INFO,
               LEVEL.WARNING, LEVEL.ERROR, LEVEL.HEADER]
        if isinstance(selected, str):
            selected = LEVEL.from_string(selected)
        return tmp[tmp.index(selected):]


class COLOR(Enum):
    INFO = "\033[92m"
    ERROR = "\033[91m"
    WARNING = "\033[93m"
    HEADER = "\033[94m"
    DEBUG = "\033[95m"
    END = "\033[0m"

    def from_level(level: LEVEL) -> "COLOR":
        return getattr(COLOR, level.value)


class Logger:
    __slots__ = "log_file", "allowed", "log_to_console", "storage_life_extender_mode", "stored_logs", "max_logfile_size", "max_logfile_lifetime", "__print", "use_caller_name", "use_file_names", "header_used", "log_folder", "level_only_valid_for_console"

    def __init__(
        self,
        log_file: str,
        log_folder: str = ".",
        clear: bool = False,
        level: LEVEL = LEVEL.INFO,
        log_to_console: bool = False,
        storage_life_extender_mode: bool = False,
        max_logfile_size: int = -1,
        max_logfile_lifetime: int = -1,
        __print: Callable = stdout.write,
        use_caller_name: bool = False,
        use_file_names: bool = True,
        level_only_valid_for_console: bool = False
    ) -> None:
        """
        Creates a logger with specific functions needed for server monitoring discord bot.
        log_file: Log file name
        log_folder: Absoluth path to the log file's location
        clear (False): Clear the (last used) log file from it's contents
        level (LEVEL.INFO): Sets the level of the logging done
        log_to_console (False): Allows the logger to show logs in the console window if exists
        storage_life_extender_mode (False): Stores the logs in memory instead of on storage media and only saves sometimes to preserve it's lifetime
        max_logfile_size (-1): Sets the maximum allowed log file size in MiB. By default it's set to -1 meaning no limit.
        max_logfile_lifetime (-1): Sets the maximum allowed log file life time in Days. By default it's set to -1 meaning no limit.
        __print (stdout.write): The function to use to log to console.
        use_caller_name (False): Allows the logger to use the caller functions name (with full call path) instead of the level. It only concerns logging to console.
        use_file_names (True): Sets if the file name should be added to the begining of the caller name. It only concerns logging to console.
        level_only_valid_for_console (False): Sets if the level set is only concerns the logging to console, or to file as well.
        """
        self.log_file = log_file
        self.validate_folder(log_folder)
        self.log_folder = log_folder
        self.allowed = LEVEL.get_hierarchy(level)
        self.log_to_console = log_to_console
        self.storage_life_extender_mode = storage_life_extender_mode
        self.stored_logs = []
        self.max_logfile_size = max_logfile_size
        self.max_logfile_lifetime = max_logfile_lifetime
        self.__print = __print
        self.use_caller_name = use_caller_name
        self.use_file_names = use_file_names
        self.header_used = False
        self.level_only_valid_for_console = level_only_valid_for_console
        if clear:
            with open(path.join(log_folder, log_file), "w"):
                pass

    def get_date(self, timestamp: float = None, format_string: str = r"%Y.%m.%d-%I:%M:%S") -> datetime:
        if timestamp is None:
            timestamp = time()
        return datetime.fromtimestamp(timestamp).strftime(format_string)

    def __check_logfile(self) -> None:
        if self.max_logfile_size != -1 and path.exists(path.join(self.log_folder, self.log_file)) and (path.getsize(path.join(self.log_folder, self.log_file)) / (1024 ^ 2)) > self.max_logfile_size:
            tmp = self.log_file.split(".")
            tmp[0] += str(self.get_date(format_string=r"%y.%m.%d-%I"))
            new_name = ".".join(tmp)
            move(path.join(self.log_folder, self.log_file),
                 path.join(self.log_folder, new_name))

        if self.max_logfile_lifetime != -1:
            names = self.__get_all_logfile_names()
            for name in names:
                if name != self.log_file and self.get_date() - self.get_date(path.getctime(name)) > timedelta(days=self.max_logfile_lifetime):
                    remove(name)

    def __get_all_logfile_names(self) -> List[str]:
        for dir_path, _, filenames in walk(self.log_folder):
            return [path.join(dir_path, fname) for fname in filenames if self.log_file.split(".")[-1] in fname]

    def __log_to_file(self, log_msg: str, flush: bool = False) -> None:
        if self.storage_life_extender_mode:
            self.stored_logs.append(log_msg)
        else:
            with open(path.join(self.log_folder, self.log_file), "a", encoding="UTF-8") as f:
                f.write(log_msg)
                f.write("\n")
        if len(self.stored_logs) > 500 or flush:
            if log_msg == "":
                del self.stored_logs[-1]
            with open(path.join(self.log_folder, self.log_file), "a", encoding="UTF-8") as f:
                f.write("\n".join(self.stored_logs))
                self.stored_logs = []
        self.__check_logfile()

    def __get_caller_name(self):
        frames = inspect.getouterframes(
            inspect.currentframe().f_back.f_back, 2)
        caller = f"{frames[1].function if frames[1].function != 'log' else frames[2].function}"
        start = 3 if frames[1].function == "log" else 2
        previous_filename = path.basename(frames[start-1].filename)
        if caller == "<module>":
            return previous_filename
        for frame in frames[start:]:
            if frame.function in ["<module>", "_run_event", "_run_once", "_bootstrap_inner"] or path.basename(frame.filename) in ["threading.py"]:
                break
            if path.basename(frame.filename) != previous_filename and self.use_file_names:
                caller = f"{frame.function}->{previous_filename}->{caller}"
                previous_filename = path.basename(frame.filename)
            else:
                caller = f"{frame.function}->{caller}"
        return f"{previous_filename}->{caller}" if self.use_file_names else caller

    def __log(self, level: LEVEL, data: str, counter: str, end: str) -> None:
        if (counter is None):
            counter = str(self.get_date())
        log_msg = f"[{counter}] [{level.value}]: {data}"
        if self.header_used and level != LEVEL.HEADER:
            log_msg = f"\t{log_msg}"
        if self.level_only_valid_for_console or level in self.allowed:
            self.__log_to_file(log_msg)
        if self.log_to_console and level in self.allowed:
            if self.use_caller_name:
                caller = self.__get_caller_name()
                log_msg = f"[{counter}] [{caller}]: {data}"
            self.__print(
                f"{COLOR.from_level(level).value}{log_msg}{COLOR.END.value}{end}")

    def get_buffer(self) -> List[str]:
        return self.stored_logs if self.storage_life_extender_mode else []

    def flush_buffer(self):
        if self.storage_life_extender_mode:
            self.__log_to_file("", True)

    def set_level(self, level: LEVEL) -> None:
        self.allowed = LEVEL.get_hierarchy(level)

    def set_folder(self, folder: str) -> None:
        self.validate_folder(folder)
        self.log_folder = folder

    def validate_folder(self, log_folder: str) -> None:
        if not path.exists(log_folder):
            if "/" not in log_folder or "\\" not in log_folder:
                log_folder = path.join(path.curdir, log_folder)
            mkdir(log_folder)
        elif not path.isdir(log_folder):
            raise IOError(
                "Argument `log_folder` can only reffer to a directory!")

    def log(self, level: LEVEL, data: str, counter: str = None, end: str = "\n") -> None:
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

    def header(self, data: str, counter: str = None, end: str = "\n") -> None:
        decor = list("="*40)
        decor.insert(int(20-len(data) / 2), data)
        final_decor = decor[0:int(20-len(data) / 2) + 1]
        final_decor.extend(decor[int((20-len(data) / 2) + len(data)):])
        self.__log(LEVEL.HEADER, "".join(final_decor), counter, end)
        self.header_used = True

    def debug(self, data: str, counter: str = None, end: str = "\n") -> None:
        self.__log(LEVEL.DEBUG, data, counter, end)

    def warning(self, data: str, counter: str = None, end: str = "\n") -> None:
        self.__log(LEVEL.WARNING, data, counter, end)

    def info(self, data: str, counter: str = None, end: str = "\n") -> None:
        self.__log(LEVEL.INFO, data, counter, end)

    def error(self, data: str, counter: str = None, end: str = "\n") -> None:
        self.__log(LEVEL.ERROR, data, counter, end)
