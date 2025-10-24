from typing import Dict, Callable, Optional, Any, List, Union, Tuple
from enum import Enum
from smdb_api import Message, Attachment, Interface
from smdb_logger import Logger
from command import CommandPrivilege, Command
from user import User
from threading import Event
from . import Server
from .. import log_level, log_folder

class Error(Enum):
    Key = 0
    Argument = 1
    Privilage = 2

class VoiceStatus:
    connected: bool = False
    target: Union[str, None] = None

    def change_status(self, connected: bool, target: Union[str, None]):
        self.connected = connected
        self.target = target

class Connector:
    callbacks: Dict[str, Callable[[Server, Message], None]]
    voice_status: Union[VoiceStatus, None]
    commands: Dict[str, Command]
    interface: Interface
    stop_event: Event
    logger: Logger
    server: Server

    def __init__(self, server: Server, interface: Interface, *args, **kwargs) -> None:
        self.logger = Logger(f"{interface.name}.log", log_folder=log_folder, log_level=log_level, use_caller_name=True)
        self.server = server
        self.callbacks = {}
        self.commands = {}
        self.interface = interface
        self.voice_status = None
        self.stop_event = Event()

    def handle_message(self, user: User, called: str, argument: Union[str, None], attachments: Optional[List[Attachment]] = []) -> Tuple[bool, Union[Error, None]]:
        command = self.commands.get(called.lower(), None)
        if (command is None): return (False, Error.Key)
        if (command.needs_argument and argument is None): return (False, Error.Argument)
        if (command.privilege == CommandPrivilege.OnlyAdmin and not user.isAdmin): return (False, Error.Argument)
        self.callbacks[called[0]](self.server, Message(user, argument, user, attachments, called, self.interface))
        return (True, None)

    def start(self, *args, **kwargs) -> None:
        pass

    def stop(self, *args, **kwargs) -> None:
        pass

    #region Callback registers
    def register_callback(
            self, 
            callback: Callable[[Server, Message], None], 
            name: Optional[str] = None,
            needs_argument: bool = False, 
            show_button: bool = False, 
            privilege: CommandPrivilege = CommandPrivilege.Anyone,
            accessable_to_user = True
        ) -> None:
        """Registers a callback to an internal function that will be called later.

        The needed functions are the following:
            - is_admin(int) -> bool
            - add_admin(int) -> bool
            - check_admin_password(str) -> bool
            - send_status() -> str
            
        If no name is provided, the callback function's name will be used instead. The names should be the exact names specified above.
        """
        final_name = name if name is not None else callback.__name__
        self.callbacks[final_name] = callback
        if (final_name not in self.commands and accessable_to_user):
            self.commands[final_name] = Command(final_name, privilege, False, show_button, needs_argument)
        self.logger.debug(f"Callback registered with the name \"{final_name}\"")

    def callback(
            self, 
            name: Optional[str] = None,
            needs_argument: bool = False, 
            show_button: bool = False, 
            privilege: CommandPrivilege = CommandPrivilege.Anyone, 
            accessable_to_user = True
        ):
        """Registers a callback to an internal function that will be called later.
        
        The needed functions are the following:
            - is_admin(int) -> bool
            - add_admin(int) -> bool
            - check_admin_password(str) -> bool
            - send_status() -> str
        
        If no name is provided, the callback function's name will be used instead. The names should be the exact names specified above.
        """
        def decorator(callback: Callable[[Server, Message], None]):
            self.register_callback(callback, name, needs_argument, show_button, privilege, accessable_to_user)
        return decorator
    #endregion

    #region Voice    
    def isVoiceCapable(self) -> bool:
        return self.voice_status is not None

    def __connect_to_user(self, user: User) -> None:
        pass

    def __connect_to_channel(self, channel: str) -> None:
        pass

    def connect(self, target: Union[User, str]) -> None:
        if (target is User): self.__connect_to_user(target)
        if (target is str): self.__connect_to_channel(target)
    #endregion
