from dataclasses import dataclass, field
from typing import List

import discord.message
import telebot.types

from bot_core import connectors
from modules.user import User
from modules.messaging import Attachment, Reaction, Channel
from datetime import datetime


@dataclass
class Message:
    """
    Represents a message as the core can see it.

    id: str - The ID of the original message. When response is created, this will contain the original message's ID.
    sender: User - The sender of the message
    content: str - The message the user sent
    reactions: List[Reaction] - A list of reactions on the message.
    attachments: List[Attachment] - A list of attachments contained in the message.
    channel: Channel - The source channel the message was received on.
    created_at: datetime - The timestamp the message was created
    connector: str - The connector used for communication
    is_response: bool - If the message should be a response to a specific message. If true, the 'id' will be the message responded to
    """
    id: str
    sender: User
    content: str
    reactions: List[Reaction]
    attachments: List[Attachment]
    channel: Channel
    created_at: datetime
    connector: str
    is_response: bool = field(default=False)

    def get_arguments(self) -> str | None:
        """Removes the command portion of the message (first word as all commands must be one word)"""
        args = self.content.split(' ')[1:]
        return ' '.join(args) if len(args) > 0 else None

    def respond_to(self, *, /, sender: User, content: str, reactions: List[Reaction] | None = None, attachments: List[Attachment] | None = None, tag_response: bool = False) -> "Message":
        return Message(
            id=self.id,
            sender=sender,
            content=content,
            reactions=reactions or [],
            attachments=attachments or [],
            channel=self.channel,
            created_at=datetime.now(),
            connector=self.connector,
            is_response=tag_response
        )

    @staticmethod
    def from_discord_message(message: discord.message.Message, user: User, channel: Channel, connector: str) -> "Message":
        return Message(
            id=str(message.id),
            sender=user,
            content=message.content,
            reactions=[Reaction(x.me, str(x.emoji)) for x in message.reactions],
            attachments=[Attachment(x.filename, x.url, x.size) for x in message.attachments],
            channel=channel,
            created_at=message.created_at,
            connector=connector
        )

    @staticmethod
    def from_telegram_message(message: telebot.types.Message, user: User, channel: Channel, connector: str) -> "Message":
        return Message(
            id=str(message.id),
            sender=user,
            content=message.text,
            reactions=[],
            attachments=[],
            channel=channel,
            created_at=datetime.fromtimestamp(message.date),
            connector=connector
        )
