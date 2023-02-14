import inspect
import threading
from typing import Any, Callable, List, Optional, Union
import telebot
from telebot.types import ReplyKeyboardMarkup, ReplyKeyboardRemove, Message, KeyboardButton
from smdb_logger import Logger, LEVEL
from time import time
from enum import Enum


class CommandPrivilege(Enum):
    Anyone = 0
    OnlyAdmin = 1
    OnlyUnknown = 2

    def should_show(privilege: 'CommandPrivilege', is_admin: bool) -> bool:
        if (is_admin):
            return privilege.value < 2
        else:
            return privilege.value != 1


class Telegramm():
    def __init__(self, token: str, logger_level: LEVEL, logger_folder: str) -> None:
        self.commands = {'wake': CommandPrivilege.OnlyAdmin, 'shutdown': CommandPrivilege.OnlyAdmin, "ping": CommandPrivilege.Anyone,
                         'status': CommandPrivilege.Anyone, 'id': CommandPrivilege.Anyone, 'register': CommandPrivilege.OnlyUnknown}
        self.Telegramm_thread = None
        self.Telegramm_bot = telebot.TeleBot(token)
        self.Telegramm_bot.register_message_handler(self.incoming_message)
        self.logger = Logger(
            "telegramm.log", log_folder=logger_folder, level=logger_level, log_to_console=True)
        self.callbacks = {}
        self.previous_messages = {}

    # Basic controll
    def start(self):
        if (self.Telegramm_thread != None):
            return
        self.Telegramm_thread = threading.Thread(
            target=self.Telegramm_bot.infinity_polling)
        self.Telegramm_thread.name = "Telegram thread"
        self.Telegramm_thread.start()
        self.logger.debug(f"Bot thread started")
        self.Telegramm_bot.get_me()

    def stop(self):
        if (self.Telegramm_thread == None):
            return
        self.Telegramm_bot.stop_bot()
        if (self.Telegramm_thread.is_alive()):
            self.logger.debug(f"Waiting on thread to stop!")
            self.Telegramm_thread.join()
        self.logger.debug(f"Bot finished")

    # Mesage reception
    def incoming_message(self, message: Message) -> None:
        split_message = message.text.split(' ')
        chat_id = message.chat.id
        previous_message_from_user = self.previous_messages[
            chat_id] if chat_id in self.previous_messages else None
        if (message.text.lower() in ['start', 'help', '/start', '/help']):
            self.send_message(
                chat_id, f"Welcome!\nI will send you your possible commands in a second.")
            self.send_default_action_buttons(chat_id)
            return
        if (split_message[0].lower() not in self.commands and previous_message_from_user is None):
            self.send_message(
                chat_id, f'Sorry, your message "{message.text}" is not supported!')
            return
        if (message.text.lower() == "ping"):
            self.send_message(chat_id, f"{int(time()) - message.date} s")
        elif (message.text.lower() == "id"):
            self.send_message(
                chat_id, f"Your Chat ID is {chat_id}")
        elif (split_message[0].lower() == 'register' or previous_message_from_user == 'register'):
            self.previous_messages[chat_id] = self.__register_admin__(
                chat_id, split_message, previous_message_from_user)
        elif (split_message[0].lower() == "status"):
            self.__send_status__(chat_id)
        elif (split_message[0].lower() == "wake"):
            self.__wake__(chat_id)
        elif (split_message[0].lower() == "shutdown"):
            self.__shutdown__(chat_id, split_message[1] if len(
                split_message) > 1 else None)
        else:
            self.logger.debug(f"Incoming message: {message.text}")

    # Internal logic functions
    def __register_admin__(self, chat_id: int, split_message: List[str], previous_message: Union[str, None]) -> Union[str, None]:
        password_correct = None
        if (len(split_message) > 1 or previous_message is not None):
            password_correct = self.__check_admin_password__(
                chat_id, split_message[-1])

        if (password_correct == True):
            self.__add_admin__(chat_id)
            self.send_default_action_buttons(chat_id)
            return None
        elif (password_correct is not None):
            self.send_message(
                chat_id, "The provided password was incorrect!")
            self.send_default_action_buttons(chat_id)
            return None
        else:
            self.send_message(
                chat_id, "Please provide the admin password", True)
            return split_message[0].lower()

    # Message sending functions
    def send_message(self, recepient: int, text: str, remove_markup: Optional[bool] = False) -> None:
        if (remove_markup):
            self.logger.debug("Disabling reply markup!")
        self.Telegramm_bot.send_message(
            recepient, text, reply_markup=ReplyKeyboardRemove(False) if remove_markup else None)
        if (len(text) > 30):
            text = f"{text[:25]}[...]"
        self.logger.debug(f"Sending message: {text}")

    def send_default_action_buttons(self, recepient: int) -> None:
        self.logger.debug(f"Reply Markup called")
        caller_is_admin = self.__is_admin__(recepient)
        markup = ReplyKeyboardMarkup()
        items = [KeyboardButton(action)
                 for action, privilege in self.commands.items() if (CommandPrivilege.should_show(privilege, caller_is_admin))]
        markup.add(*items)
        self.logger.debug(f"Reply Markup created")
        self.Telegramm_bot.send_message(
            recepient, "Your possible options", reply_markup=markup)

    # Callback registers
    def register_callback(self, callback: Callable[..., Any], name: Optional[str] = None) -> None:
        """Registers a callback to an internal function that will be called later.
        The needed functions are the following:
            - is_admin(int) -> bool
            - add_admin(int) -> bool
            - check_admin_password(str) -> bool
            - send_status() -> str
            - wake(int) -> None
            - shutdown(int, str|None) -> None
        If no name is provided, the callback function's name will be used instead. The names should be the exact names specified above.
        """
        final_name = name if name is not None else callback.__name__
        self.callbacks[final_name] = callback
        self.logger.debug(
            f"Callback registered with the name \"{final_name}\"")

    def callback(self, name: Optional[str] = None):
        """Registers a callback to an internal function that will be called later.
        The needed functions are the following:
            - is_admin(int) -> bool
            - add_admin(int) -> bool
            - check_admin_password(str) -> bool
            - send_status() -> str
            - wake(int) -> None
            - shutdown(int, str|None) -> None
        If no name is provided, the callback function's name will be used instead. The names should be the exact names specified above.
        """
        def decorator(callback: Callable[..., Any]):
            final_name = name if name is not None else callback.__name__
            self.callbacks[final_name] = callback
            self.logger.debug(
                f"Callback registered with the name \"{final_name}\"")
        return decorator

    # Callback user functions
    def __add_admin__(self, chat_id: int) -> None:
        function_name = inspect.stack()[0][3].strip('__')
        if (function_name in self.callbacks):
            if (self.callbacks[function_name](chat_id)):
                self.send_message(
                    chat_id, "You were added to admins successfully!")
            else:
                self.send_message(
                    chat_id, "Something happaned when adding you to the admins!\nPlease try again later.")
        else:
            self.logger.warning("AddAdmin callback is not found!")
            self.send_message(chat_id, "Can't add a new admin at the moment!")

    def __check_admin_password__(self, chat_id: int, provided_password: str) -> bool:
        function_name = inspect.stack()[0][3].strip('__')
        if (function_name in self.callbacks):
            return self.callbacks[function_name](provided_password)
        else:
            self.logger.warning("CheckAdminPassword callback is not found!")
            self.Telegramm_bot.send_message(
                chat_id, "The password validation is not possible at this moment!")
            return False

    def __is_admin__(self, chat_id: int) -> bool:
        function_name = inspect.stack()[0][3].strip('__')
        if (function_name in self.callbacks):
            return self.callbacks[function_name](chat_id)
        else:
            self.logger.warning("IsAdmin callback is not found!")
            self.Telegramm_bot.send_message(
                chat_id, "The admin validation is not possible at this moment!")
            return False

    def __send_status__(self, chat_id: int) -> None:
        function_name = inspect.stack()[0][3].strip('__')
        if (function_name in self.callbacks):
            status = self.callbacks[function_name]()
            self.send_message(chat_id, status)
        else:
            self.logger.warning("SendStatus callback is not found!")
            self.send_message(
                chat_id, "The status is not available at the moment!")

    def __wake__(self, chat_id: int) -> None:
        function_name = inspect.stack()[0][3].strip('__')
        if (function_name in self.callbacks):
            self.callbacks[function_name](chat_id)
        else:
            self.logger.warning("Wake callback is not found!")
            self.send_message(
                chat_id, "Waking is not available at the moment!")

    def __shutdown__(self, chat_id: int, time: Union[str, None]) -> None:
        function_name = inspect.stack()[0][3].strip('__')
        if (function_name in self.callbacks):
            self.callbacks[function_name](chat_id, time)
        else:
            self.logger.warning("Shutdown callback is not found!")
            self.send_message(
                chat_id, "Shutdown is not available at the moment!")


if __name__ == "__main__":
    print("Starting Telegramm bot")
    bot = Telegramm(
        "5738974434:AAFhpRt_qdN6-B7GWf230JPUoekBPirACbA", LEVEL.DEBUG, "logs")
    bot.start()
    admins = []

    @bot.callback()
    def is_admin(id: int) -> bool:
        bot.logger.debug("Outside IsAdmin called")
        return id in admins

    @bot.callback()
    def check_admin_password(psw: str) -> bool:
        bot.logger.debug("Outside CheckAmdinPassword called")
        return psw == "ASD"

    @bot.callback()
    def add_admin(id: int) -> None:
        bot.logger.debug("Outside AddAdmin called")
        admins.append(id)
        return True

    bot.send_default_action_buttons(5965064964)
    input("Waiting on return to stop")
    bot.stop()
