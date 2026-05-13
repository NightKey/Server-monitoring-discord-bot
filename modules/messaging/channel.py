from dataclasses import dataclass

from discord.abc import GuildChannel, PrivateChannel
from discord.threads import Thread

from telebot.types import Chat

@dataclass
class Channel:
    """
    Represents a channel as the core sees it

    id: str - The Channels ID for the connector
    name: str - Name of the channel
    is_admin: str - If the connector trusts this channel as an admin only channel
    """
    id: str
    name: str | None
    is_admin: bool

    @staticmethod
    def from_discord_channel(original_channel: GuildChannel | PrivateChannel | Thread, is_trusted: bool) -> Channel:
        if isinstance(original_channel, GuildChannel):
            return Channel(id=str(original_channel.id), name=original_channel.name, is_admin=is_trusted)
        if isinstance(original_channel, PrivateChannel):
            return Channel(id=str(original_channel.id), name="Private Channel", is_admin=is_trusted)
        else:
            return Channel(id=str(original_channel.id), name=original_channel.name, is_admin=is_trusted)

    @staticmethod
    def from_telegram_channel(original_channel: Chat, is_trusted: bool) -> Channel:
        return Channel(id=str(original_channel.id), name="Private Chat", is_admin=is_trusted)
