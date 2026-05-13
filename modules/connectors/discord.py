import logging
from os.path import join
from json import loads
from threading import Event
from time import sleep, time
from typing import Dict, Callable, List, Any, Coroutine

from discord import Intents, Client
from discord.abc import Snowflake, GuildChannel, PrivateChannel
from discord.threads import Thread
from discord.message import Message
from smdb_api import Privilege
from smdb_logger import LEVEL, Logger

import asyncio

import modules.messaging
from modules import User, Channel, TODO, Status
from modules.utility import chunk
from modules.capability import Capability, all_messaging_capabilities, all_reaction_capabilities, all_user_capabilities
from modules.connectors import Connector, CallbackType
from modules.commands import Command

class DiscordSnowflake(Snowflake):
    def __init__(self, _id: int):
        self.id = _id

class Discord(Connector):
    def __init__(self, token: str, me: int, trusted_channels: List[str], logger_level: LEVEL, logger_folder: str, event_loop: asyncio.AbstractEventLoop):
        self.logger = Logger("telegram.log", log_folder=logger_folder, level=logger_level, use_caller_name=True)
        self.client: Client | None = None
        self.event_loop = event_loop
        self.callbacks: Dict[CallbackType, Callable] = {}
        self.commands: List[Command] = []
        self.trusted_channels = trusted_channels
        self.__status: Status = Status.OFFLINE
        self.__stopped: Event = Event()
        self.__token = token
        self.__me: User | None = None
        self.__id = me
        self.__capabilities = all_messaging_capabilities.copy()
        self.__capabilities.extend(all_user_capabilities)
        self.__capabilities.extend(all_reaction_capabilities)
        self.__last_disconnected: float | None = None
        self.__prepare_client()

    # <editor-fold desc="Internal">
    def __add_event(self, coro: Callable[..., Coroutine[Any, Any, Any]]) -> None:
        self.client.event(coro)

    def __prepare_client(self) -> None:
        intents = Intents.default()
        intents.members = True
        intents.voice_states = True
        intents.message_content = True
        intents.presences = True
        self.client = Client(heartbeat_timeout=120, intents=intents)
        self.__add_event(self.on_ready)
        self.__add_event(self.on_error)
        self.__add_event(self.on_message)
        self.__add_event(self.on_disconnect)
        self.__stopped.set()

    def create_internal_message(self, message: Message) -> modules.messaging.message.Message:
        return modules.messaging.message.Message.from_discord_message(message, self.__get_user(str(message.author.id)), modules.messaging.Channel.from_discord_channel(message.channel, str(message.channel.id) in self.trusted_channels), self.name)

    def __get_discord_channel(self, channel: modules.messaging.Channel) -> GuildChannel | PrivateChannel | Thread:
        return self.event_loop.run_until_complete(self.client.fetch_channel(int(channel.id)))
    # </editor-fold>

    # <editor-fold desc="Properties">
    @property
    def name(self) -> str:
        return "Discord"

    @property
    def me(self) -> User:
        if self.__me is None: self.__me = User(Privilege.Internal, {self.name: str(self.__id)})
        return self.__me

    @property
    def capabilities(self) -> List[Capability]:
        return self.__capabilities

    @property
    def stopped(self) -> bool:
        return self.__stopped.is_set()

    @property
    def __commands(self) -> List[Command]:
        return self.commands

    @property
    def __callbacks(self) -> Dict[CallbackType, Callable]:
        return self.callbacks

    @property
    def status(self) -> Status:
        return self.__status
    # </editor-fold>

    # <editor-fold desc="Required">
    async def on_ready(self):
        if self.__last_disconnected is not None:
            offline_time = time() - self.__last_disconnected
            self.__last_disconnected = None
            for channel_id in self.trusted_channels:
                await self.client.get_channel(int(channel_id)).send(f"{self.name} connector reconnected after {offline_time} s")
        self.__status = Status.ONLINE
        self.__on_ready()

    async def on_error(self, error: str, /, *args, **kwargs):
        self.__on_error(error=error)

    async def on_disconnect(self):
        self.__status = Status.OFFLINE
        self.__last_disconnected = time()
        self.__on_disconnect()

    async def on_message(self, message: modules.messaging.Message) -> None:
        TODO("Not Implemented")

    def send_message(self, message: Message) -> bool:
        TODO("Not Implemented")

    def send_embed(self, channel: modules.messaging.Channel, embed: modules.messaging.Embed) -> bool:
        TODO("Not Implemented")

    def broadcast_to(self, message: str, channels: List[Channel] | None, users: List[User] | None) -> bool:
        TODO("Not Implemented")

    def remove_command(self, command: Command) -> None:
        if command in self.commands:
            self.commands.remove(command)

    def add_command(self, command: Command) -> None:
        if command in self.commands: return
        if self.__filter_commands([command]):
            self.commands.append(command)

    def on_event(self, event_name: str, callback: Callable[..., None]) -> bool:
        async def tmp():
            callback()
        tmp.__name__ = event_name
        self.__add_event(tmp)
        return True

    def get_local_username(self, channel: modules.messaging.Channel, user: modules.User) -> str:
        local_user = self.event_loop.run_until_complete(self.__get_discord_channel(channel).guild.fetch_member(int(user.connector_ids[self.name])))
        return local_user.name

    def can_user_use_capability(self, user: User, channel: modules.messaging.Channel, capability: Capability) -> bool:
        discord_channel = self.__get_discord_channel(channel)
        discord_user = self.event_loop.run_until_complete(discord_channel.guild.fetch_member(int(user.connector_ids[self.name])))

        if discord_user.guild_permissions.administrator:
            return True

        if not discord_channel.permissions_for(discord_user).view_channel: return False

        if capability in [Capability.HISTORY, Capability.REACT]:
            return discord_channel.permissions_for(discord_user).read_message_history
        if capability in [Capability.MODIFY, Capability.DELETE]:
            return isinstance(discord_channel, (GuildChannel, Thread)) and discord_channel.permissions_for(discord_user).manage_messages
        if capability in [Capability.BAN]:
            return isinstance(discord_channel, (GuildChannel, Thread)) and discord_user.guild_permissions.ban_members
        # Should not be reachable
        return False

    def get_channel(self, user: User | None, channel_id: str) -> Channel | None:
        tmp_channel = modules.messaging.channel.Channel(channel_id, None, False)
        if user is not None and not self.can_user_use_capability(user, tmp_channel, Capability.HISTORY):
            raise PermissionError(f"User can't access messages on this channel!")
        discord_channel = self.__get_discord_channel(tmp_channel)
        return modules.messaging.Channel.from_discord_channel(discord_channel, str(discord_channel.id) in self.trusted_channels)

    # </editor-fold>

    # <editor-fold desc="Control flow">
    def start(self) -> None:
        self.__stopped.clear()
        self.event_loop.create_task(coro=self.client.start(token=self.__token), name="Discord")
        self.event_loop.run_forever()

    def stop(self) -> None:
        self.client.close()
        while not self.client.is_closed():
            sleep(1)
        self.__stopped.set()
    # </editor-fold>

    # <editor-fold desc="Supported optionals">
    async def __get_message_history(self, channel: modules.messaging.Channel, limit: int | None) -> List[Message]:
        return [x async for x in self.__get_discord_channel(channel).history(limit=limit)]

    def get_message_history(self, user: User | None, channel: modules.messaging.Channel, count: int | None = None) -> List[modules.messaging.Message]:
        if user is not None and not self.can_user_use_capability(user, channel, Capability.HISTORY):
            raise PermissionError(f"User does not have a permission to get message history!")
        history = self.event_loop.run_until_complete(self.__get_message_history(channel, count))
        return [self.create_internal_message(x) for x in history]

    def get_message(self, user: User | None, channel: modules.messaging.Channel, message_id: str) -> Message:
        if user is not None and not self.can_user_use_capability(user, channel, Capability.HISTORY):
            raise PermissionError(f"User does not have a permission to get message history!")
        return self.create_internal_message(self.event_loop.run_until_complete(self.client.get_channel(int(channel.id)).fetch_message(int(message_id))))

    def toggle_reaction(self, user: User | None, channel: modules.messaging.Channel, message_id: str, reaction: str) -> bool:
        if user is not None and not self.can_user_use_capability(user, channel, Capability.REACT):
            raise PermissionError(f"User does not have a permission to react on messages!")
        message = self.event_loop.run_until_complete(self.client.get_channel(int(channel.id)).fetch_message(int(message_id)))
        add = True
        for reaction in message.reactions:
            if reaction.emoji == reaction and reaction.me:
                add = False
                break
        if add:
            message.add_reaction(reaction)
        else:
            message.remove_reaction(reaction, DiscordSnowflake(int(self.me)))
        return True

    def delete_messages(self, user: User | None, channel: modules.messaging.Channel, message_ids: List[str]) -> bool:
        if user is not None and not self.can_user_use_capability(user, channel, Capability.DELETE):
            raise PermissionError(f"User does not have a permission to delete messages!")
        discord_channel = self.__get_discord_channel(channel)
        if isinstance(discord_channel, PrivateChannel):
            raise TypeError(f"Channel type {discord_channel.__class__} does not support deleting messages!")
        snowflake_list = list(chunk(message_ids, 99, lambda x: DiscordSnowflake(x)))
        try:
            [self.event_loop.run_until_complete(discord_channel.delete_messages(x)) for x in snowflake_list]
            return True
        except:
            return False

    def ban_users(self, user: User | None, channel: modules.messaging.Channel, users: List[str], reason: str) -> Dict[str, bool]:
        if user is not None and not self.can_user_use_capability(user, channel, Capability.BAN):
            raise PermissionError(f"User does not have a permission to ban users!")
        discord_channel = self.__get_discord_channel(channel)
        if isinstance(discord_channel, PrivateChannel):
            raise TypeError(f"Channel type {discord_channel.__class__} does not support banning users!")
        results = self.event_loop.run_until_complete(discord_channel.guild.bulk_ban([DiscordSnowflake(int(x)) for x in users], reason=reason))
        actual_result = {}
        for banned in results.banned:
            actual_result[str(banned.id)] = True
        for failed in results.failed:
            actual_result[str(failed.id)] = False
        return actual_result
    # </editor-fold>

    @staticmethod
    def create_connector(config_json: str, logger_level: LEVEL, logger_folder: str, callbacks: Dict[CallbackType, Callable], commands: List[Command]) -> 'Discord':
        config = loads(config_json)
        event_loop = asyncio.get_event_loop()
        new_connector = Discord(config["token"], int(config["id"]), logger_level=logger_level, logger_folder=logger_folder, event_loop=event_loop, trusted_channels=config["trusted_channels"])
        new_connector.commands = new_connector.__filter_commands(commands)
        new_connector.callbacks = callbacks
        return new_connector

    def enable_debug_logger(self):
        _logger = logging.getLogger('discord')
        _logger.setLevel(logging.DEBUG)
        handler = logging.FileHandler(filename=join('logs', 'discord.log'), encoding='utf-8', mode='w')
        handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(messaging)s'))
        _logger.addHandler(handler)