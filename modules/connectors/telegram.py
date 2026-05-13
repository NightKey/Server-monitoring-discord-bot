import threading
from json import loads
from operator import truediv
from threading import Event
from typing import Callable, List, Optional, Dict
import telebot
from smdb_api import Privilege
from telebot.apihelper import ApiException
from telebot.types import ReplyKeyboardMarkup, Message, KeyboardButton
from smdb_logger import Logger, LEVEL
from time import time
from logging import CRITICAL, DEBUG

import modules.messaging
from modules import User, Status
from modules.capability import Capability
from modules.connectors import Connector, CallbackType
from modules.commands import Command
from modules.messaging import Channel, Embed


class Telegram(Connector):
    def __init__(self, token: str, logger_level: LEVEL, logger_folder: str) -> None:
        self.telegram_thread = None
        self.telegram_bot_log_level = CRITICAL if logger_level == LEVEL.INFO else DEBUG
        self.telegram_bot = telebot.TeleBot(token=token, threaded=False)
        self.telegram_bot.add_message_handler({"function":self.incoming_message, 'filters':{}})
        self.logger = Logger("telegram.log", log_folder=logger_folder, level=logger_level, use_caller_name=True)
        self.previous_messages: Dict[int, Command] = {}
        self.__stopped: Event = Event()
        self.commands: List[Command] = []
        self.callbacks: Dict[CallbackType, Callable] = {}
        self.__me: User | None = None
        self.__status: Status = Status.OFFLINE
        self.__stopped.set()

    @property
    def name(self) -> str:
        return "Telegram"

    @property
    def me(self) -> User:
        if self.__me is None: self.__me = User(Privilege.Internal, {self.name: str(self.telegram_bot.get_me().id)})
        return self.__me

    @property
    def stopped(self) -> bool:
        return self.__stopped.is_set()

    @property
    def capabilities(self) -> List[Capability]:
        return []

    @property
    def __commands(self) -> List[Command]:
        return self.commands

    @property
    def __callbacks(self) -> Dict[CallbackType, Callable]:
        return self.callbacks

    @property
    def status(self) -> Status:
        return self.__status

    def on_event(self, event_name: str, callback: Callable[..., None]) -> bool:
        return False

    # Basic control
    def start(self):
        self.logger.debug("Telegram start called")
        if self.telegram_thread is not None:
            return
        self.telegram_thread = threading.Thread(
            name="Telegram thread",
            target=self.watchdogged_runner,
            kwargs={"timeout":20}
        )
        self.telegram_thread.start()
        self.logger.info("Telegram bot started")

    def add_command(self, command: Command) -> None:
        if command in self.commands: return
        if self.__filter_commands([command]):
            self.commands.append(command)

    def remove_command(self, command: Command) -> None:
        if command in self.commands:
            self.commands.remove(command)

    def watchdogged_runner(self, timeout: int):
        while not self.__stopped.is_set():
            try:
                if self.__status == Status.OFFLINE:
                    self.__status = Status.OFFLINE
                    self.__on_ready()
                self.logger.trace("Starting Telegram client...")
                self.telegram_bot.get_me()
                while not self.__stopped.is_set():
                    try:
                        self.telegram_bot.polling(timeout=timeout, logger_level=self.telegram_bot_log_level)
                    except Exception as ex:
                        self.logger.error(f"Polling exception", ex)
            except Exception as ex:
                self.logger.error(f"Telegram connection failed", ex)
                self.__on_disconnect()
                self.__status = Status.OFFLINE
                self.__stopped.wait(5)


    def exception_handler(self, ex: Exception) -> bool:
        if isinstance(ex, ApiException):
            self.logger.error(f"Telegram API exception", ex)
            return True
        if isinstance(ex, KeyboardInterrupt):
            self.logger.warning(f"Keyboard Interrupt!")
            return True
        return False

    def stop(self):
        if self.telegram_thread is None:
            return
        self.__stopped.set()
        self.telegram_bot.stop_bot()
        if self.telegram_thread.is_alive():
            self.logger.debug(f"Waiting on thread to stop!")
            self.telegram_thread.join()
        self.logger.debug(f"Bot stopped")

    def __get_previous_chat_for_user(self, chat_id: int) -> Command | None:
        return self.previous_messages.pop(chat_id) if chat_id in self.previous_messages else None

    def can_user_use_capability(self, user: User, channel: Channel, capability: Capability) -> bool:
        return capability in [Capability.HISTORY, Capability.REACT]

    def get_channel(self, user: User | None, channel_id: str) -> Channel | None:
        return None

    # <editor-fold desc="Message reception">
    def incoming_message(self, message: Message) -> None:
        try:
            chat_id = message.chat.id
            previous_message_from_user = self.__get_previous_chat_for_user(chat_id)

            if message.text in ['start', '/start']:
                self.__send_message(chat_id, f"Welcome!\nButtons are enabled.", answer_with_buttons = True)
                return

            if message.text in ["ping", "/ping"]:
                self.__send_message(chat_id, f"{int(time()) - message.date} s")
                return

            if message.text in ["id", "/id"]:
                self.__send_message(chat_id, f"Your Chat ID is {chat_id}")
                return

            (command, arguments) = self.__get_command(message.text, "/", previous_message_from_user)

            if command is None:
                self.__send_message(chat_id, f'Sorry, your messaging "{message.text}" is not supported!')
                return

            if command.needs_argument and arguments is None:
                self.previous_messages[chat_id] = command
                self.__send_message(chat_id, "Please provide the required argument", True)
                return

            user = self.__get_user(str(chat_id))

            self.__on_command(command, modules.messaging.Message.from_telegram_message(message, user, Channel.from_telegram_channel(message.chat, user.privilege == Privilege.Admin), self.name))
        except Exception as ex:
            self.logger.error(f"Exception in incoming_message", ex)
    # </editor-fold>

    # Message sending functions
    def send_message(self, message: modules.messaging.Message) -> bool:
        target_id = int(message.channel.id)
        return self.__send_message(target_id, message.content)

    def send_embed(self, channel: Channel, embed: Embed) -> bool:
        target_id = int(channel.id)
        return self.__send_message(target_id, str(embed))

    def __send_message(self, recipient: int, text: str, remove_markup: Optional[bool] = False, answer_with_buttons: Optional[bool] = False) -> bool:
        if remove_markup:
            self.logger.debug("Disabling reply markup!")
        reply_markup = ReplyKeyboardMarkup(False) if remove_markup else None
        if remove_markup and answer_with_buttons:
            self.logger.error("Send messaging called with both remove_markup and answer_withButtons! Removing markup as default!")
        elif answer_with_buttons:
            reply_markup = self.create_buttons(recipient)
        if len(text) > 30:
            text = f"{text[:25]}[...]"
        self.logger.debug(f"Sending messaging: {text}")
        result = self.telegram_bot.send_message(recipient, text, reply_markup=reply_markup)
        return result is not None

    def send_action_buttons(self, recipient: int, show_all: bool = False) -> None:
        self.logger.debug(f"Reply Markup called")
        markup = self.create_buttons(recipient, show_all)
        self.logger.debug(f"Reply Markup created")
        self.telegram_bot.send_message(recipient, "Your possible options", reply_markup=markup)

    def create_buttons(self, recipient: int, show_all: Optional[bool] = True) -> ReplyKeyboardMarkup:
        user = self.__get_user(str(recipient))
        markup = ReplyKeyboardMarkup()
        for command in self.commands:
            if command.should_show_button(show_all, user.privilege):
                markup.add(KeyboardButton(command.name))
        return markup

    def get_local_username(self, channel: Channel, user: User) -> str:
        return self.telegram_bot.get_chat_member(int(channel.id), int(user.get_connector_id_for_connector(self.name))).user.username

    @staticmethod
    def create_connector(config_json: str, logger_level: LEVEL, logger_folder: str, callbacks: Dict[CallbackType, Callable], commands: List[Command]) -> 'Telegram':
        config = loads(config_json)
        new_connector = Telegram(config['token'], logger_level=logger_level, logger_folder=logger_folder)
        new_connector.commands = new_connector.__filter_commands(commands)
        new_connector.callbacks = callbacks
        return new_connector
