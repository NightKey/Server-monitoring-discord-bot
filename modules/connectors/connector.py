import inspect
from abc import abstractmethod, ABC
from typing import Callable, Any, Dict, List, Tuple

from smdb_api import Privilege
from smdb_logger import LEVEL

from modules.user import User, Presence
from modules.capability import Capability
from modules.connectors import CallbackType, Status
from modules.commands import WellKnownCommands, Command
from modules.messaging import Message, Channel, Embed


class Connector(ABC):
    # <editor-fold desc="Helpers">
    def __on_ready(self) -> None:
        self.__callbacks[CallbackType.READY](self.name)

    def __on_command(self, command: Command, message: Message) -> Any:
        """
        Calls the core's command callback.

        :parameter command: The command to be called
        :type command: Command
        :parameter message: The message of the user
        :type message: Message
        """
        self.__callbacks[CallbackType.COMMAND](command, message)

    def __on_error(self, error: str) -> None:
        self.__callbacks[CallbackType.FAILED](self.name, error)

    def __on_result(self, user: User, result: Any) -> None:
        self.__callbacks[CallbackType.RESULT](self.name, user, result)

    def __on_presence_update(self, user: User, previous_presence: Presence, new_presence: Presence):
        self.__callbacks[CallbackType.PRESENCE](user, previous_presence, new_presence, self.name)

    def __on_disconnect(self):
        self.__callbacks[CallbackType.DISCONNECTED](self.name)

    def __get_user(self, user_id: str) -> User:
        """
        Returns a user as the core sees it

        :parameter user_id: the user ID for the connector
        :type user_id: str

        :return: A user object saved for the connector
        :type: User
        """
        return self.__callbacks[CallbackType.COMMAND](WellKnownCommands.GetUser, (self.name, user_id))

    def __get_command(self, message: str, key_word: str = "", default_command: Command | None = None) -> Tuple[Command | None, str | None]:
        """
        Returns a core command stored in the commands list.

        :parameter message: should contain the user's message
        :type message: str
        :parameter key_word: should be the key word the user needs to use for the connector to interpret it as a commands.
        :type key_word: str

        :return: A Tuple containing the results. First item can be None if it was not a command, or a Command. Second item can be None if the message only contained a command or the rest of the message
        :type: Tuple[Command | None, str | None]
        """
        components = message.replace(key_word, '').split(' ')
        for command in self.__commands:
            if command.name == components[0] and command.privilege != Privilege.Internal:
                return command, ' '.join(components[1:]) if len(components) > 1 else None
        else:
            return default_command, message

    def __filter_commands(self, commands: List[Command]) -> List[Command]:
        """
        Filters the commands to the capabilities of the connector

        :parameter commands: The command list to be filtered
        :type commands: List[Command]

        :return: A filtered command list the connector can fulfill
        :type: List[Command]
        """
        result: List[Command] = []
        for command in commands:
            if len(command.required) > len(self.capabilities):
                continue
            for requirement in command.required:
                if requirement not in self.capabilities:
                    break
            else:
                result.append(command)
        return result

    def __not_supported_by_connector(self) -> NotImplementedError:
        """
        Returns a not implemented error when a connector does not support the request.
        """
        caller = inspect.getouterframes(inspect.currentframe().f_back)[1].function
        return NotImplementedError(f"{caller} is not supported by {self.name}")
    # </editor-fold>

    # <editor-fold desc="Properties">
    @property
    @abstractmethod
    def name(self) -> str:
        """The name of the connector. Will be used as a key for User's `connector_ids` field."""
        pass

    @property
    @abstractmethod
    def me(self) -> User:
        """The ID of the connector."""
        pass

    @property
    @abstractmethod
    def capabilities(self) -> List[Capability]:
        """The capabilities of the connector"""
        pass

    @property
    @abstractmethod
    def stopped(self) -> bool:
        """Should represent if the connector is safe to disregard"""
        pass

    @property
    @abstractmethod
    def __callbacks(self) -> Dict[CallbackType, Callable]:
        """The callbacks should be saved to here"""
        pass

    @property
    @abstractmethod
    def __commands(self) -> List[Command]:
        """The commands should be saved here"""
        pass

    @property
    @abstractmethod
    def status(self) -> Status:
        """The status of the connector's connection"""
        pass
    # </editor-fold>

    # <editor-fold desc="Required functions">
    @abstractmethod
    def add_command(self, command: Command) -> None:
        """This will be called when new commands will be given from `BotCore` when a new API connection creates a commands."""
        pass

    @abstractmethod
    def remove_command(self, command: Command) -> None:
        """This will be called when a commands were removed by `BotCore` when an API disconnects."""
        pass

    @abstractmethod
    def send_message(self, message: Message) -> bool:
        """
        This will be called when `BotCore` wants to send something to a channel.
        """
        pass

    @abstractmethod
    def send_embed(self, channel: Channel, embed: Embed) -> bool:
        """
        This will be called when `BotCore` wants to send an embed.
        For connectors with supported embeds, it can be transformed to their embed type, otherwise string representation is supported by the Embed class
        """
        pass

    def broadcast_to(self, message: str, channels: List[Channel] | None, users: List[User] | None) -> bool:
        """
        This will be called when a broadcast message is made. One example is when the bot starts up. Either channels or users will be provided.
        This is an optional implementation.
        """
        return False

    @abstractmethod
    def get_local_username(self, channel: Channel, user: User) -> str:
        """
        This will be called when `BotCore` wants to get the users name for the channel or connector
        """
        pass

    @abstractmethod
    def start(self) -> None:
        """This method should start the connector"""
        pass

    @abstractmethod
    def stop(self) -> None:
        """This method should stop the connector"""
        pass

    @abstractmethod
    def on_event(self, event_name: str, callback: Callable[..., None]) -> bool:
        """This will be called to register event handlers on the connector. Return value should be false if event couldn't be created"""
        pass

    @abstractmethod
    def can_user_use_capability(self, user: User, channel: Channel, capability: Capability) -> bool:
        """This will be called to check the user's permission for certain capability. If capability is not supported, this should return false"""
        pass

    @abstractmethod
    def get_channel(self, user: User | None, channel_id: str) -> Channel | None:
        """Returns the channel object for a provided channel ID if it's a valid ID"""
        pass
    # </editor-fold>

    # <editor-fold desc="Not required functions">
    def get_message_history(self, user: User | None, channel: Channel, count: int | None = None) -> List[Message]:
        raise self.__not_supported_by_connector()

    def get_message(self, user: User | None, channel: Channel, message_id: str) -> Message:
        raise self.__not_supported_by_connector()

    def toggle_reaction(self, user: User | None, channel: Channel, message_id: str, reaction: str) -> bool:
        raise self.__not_supported_by_connector()

    def delete_messages(self, user: User | None, channel: Channel, message_ids: List[str]) -> bool:
        raise self.__not_supported_by_connector()

    def ban_users(self, user: User | None, channel: Channel, users: List[str], reason: str) -> Dict[str, bool]:
        raise self.__not_supported_by_connector()
    # </editor-fold>

    @staticmethod
    @abstractmethod
    def create_connector(config_json: str, logger_level: LEVEL, logger_folder: str, callbacks: Dict[CallbackType, Callable], commands: List[Command]) -> 'Connector':
        """
        This will be the method called for creating the connector.
        This method should read a configuration file, prepare the connector and return it.
        """
        pass
