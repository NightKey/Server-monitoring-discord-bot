from typing import Dict, List, Tuple, Union
from data_structures import Command
from fuzzywuzzy import fuzz
from smdb_logger import Logger, LEVEL
from threading import Thread, Event

from .. import log_folder, log_level

class Connector:
    name: str = "Connector"
    commands: Dict[str, Command] = {}
    token: str = ""
    logger: Logger = None
    stop_flag: Event = Event()

    def __init__(self, token: str, log_enabled: bool) -> None:
        self.token = token
        self.logger = Logger(f"{self.name}.log", log_folder=log_folder, level=log_level, use_caller_name=True, log_disabled=(not log_enabled), use_log_name=True)
        self.__setup__()

    def __setup__(self) -> None:
        pass

    def __add_command(self, command: Command) -> None:
        self.commands[command.name] = command
    
    def __add_commands(self, commands: List[Command]) -> None:
        for command in commands:
            self.commands[command.name] = command

    def __get_command(self, name: str) -> Union[Command, None]:
        return self.commands[name]

    def __get_correct_key(self, name: str, max_deviance: int = 70) -> Union[Tuple[str, int], Tuple[None, None]]:
        best_ratio = 0
        best_key = ''
        for key in self.commands.keys():
            tmp = fuzz.ratio(name, key)
            if tmp > best_ratio:
                best_ratio = tmp
                best_key = key
        if best_ratio < max_deviance:
            return (None, None)
        return (best_key, best_ratio)
    
    def __remove_command(self, name: str) -> bool:
        del self.commands[name]

    def start(self) -> None:
        self.stop_flag.clear()
        self.__start()

    def __start(self) -> None:
        pass

    def is_alive(self) -> bool:
        pass
    
    def stop(self) -> None:
        self.stop_flag.set()
        self.__clean_up()

    def __clean_up(self) -> None:
        pass