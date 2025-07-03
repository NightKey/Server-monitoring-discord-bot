import inspect
import threading
from typing import Any, Callable, List, Optional, Union
import telebot
from telebot.apihelper import ApiException
from telebot.types import ReplyKeyboardMarkup, Message, KeyboardButton
from smdb_logger import Logger, LEVEL
from smdb_api import Message as APIMessage
from smdb_api import Interface
from time import time
from .data_structures import CommandPrivilege, Command
from logging import CRITICAL, DEBUG

class Telegramm():
    def __init__(self, token: str, logger_level: LEVEL, logger_folder: str) -> None:
        self.commands = {
            'status': Command('status', CommandPrivilege.Anyone, True, True),
            "register": Command("register", CommandPrivilege.OnlyUnknown, True, True, True),
            "id": Command("id", CommandPrivilege.Anyone, True, True),
            "ping": Command("ping", CommandPrivilege.Anyone, True, True)
        }
        self.Telegramm_thread = None
        self.telegramm_bot_log_level = CRITICAL if logger_level == LEVEL.INFO else DEBUG
        self.Telegramm_bot = telebot.TeleBot(token=token, threaded=False)
        self.Telegramm_bot.add_message_handler({"function":self.incoming_message, 'filters':{}})
        self.logger = Logger("telegramm.log", log_folder=logger_folder, level=logger_level, use_caller_name=True)
        self.callbacks = {}
        self.previous_messages = {}
        self.stop_flag = False
        self.register_callback(self.__status__, "status", accessable_to_user=False)

    # Basic controll
    def start(self):
        if (self.Telegramm_thread != None):
            return
        self.Telegramm_thread = threading.Thread(
            target=self.watchdogged_runner,
            kwargs={"timeout":20}
        )
        self.Telegramm_thread.name = "Telegram thread"
        self.Telegramm_thread.start()
        self.logger.debug(f"Bot thread started")
        self.Telegramm_bot.get_me()

    def watchdogged_runner(self, timeout: int):
        while not self.stop_flag:
            try:
                self.logger.trace("Starting Telegramm client...")
                while not self.stop_flag:
                    try:
                        self.Telegramm_bot.polling(timeout=timeout, logger_level=self.telegramm_bot_log_level)
                    except Exception as ex:
                        self.logger.warning(f"Polling exception: {ex}")
            except Exception as ex:
                self.logger.warning(f"Telegramm connection failed: {ex}")

    def remove_command(self, name: str) -> None:
        if (name in self.commands):
            del self.commands[name]
        if (name in self.callbacks):
            del self.callbacks[name]

    def exception_handler(self, ex: Exception) -> bool:
        if isinstance(ex, ApiException):
            self.logger.error(f"Api exception: {ex}")
            return True
        if isinstance(ex, KeyboardInterrupt):
            self.logger.warning(f"Keyboard Interrupt!")
            return True
        return False

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
        try:
            split_message = message.text.split(' ')
            chat_id = message.chat.id
            previous_message_from_user = self.previous_messages[
                chat_id] if chat_id in self.previous_messages else None
            if (previous_message_from_user is not None):
                del self.previous_messages[chat_id]
            if (message.text in ['start', 'help', '/start', '/help']):
                self.send_message(
                    chat_id, f"Welcome!\nI will send you your possible commands in a second.", answer_with_buttons=True)
                return
            commandName = split_message[0]
            if (commandName not in [name for name in self.commands.keys()] and previous_message_from_user is None):
                self.send_message(
                    chat_id, f'Sorry, your message "{message.text}" is not supported!')
                return
            if (message.text == "ping"):
                self.send_message(chat_id, f"{int(time()) - message.date} s")
                return
            elif (message.text == "id"):
                self.send_message(
                    chat_id, f"Your Chat ID is {chat_id}")
                return
            elif (commandName == 'register' or previous_message_from_user == 'register'):
                self.previous_messages[chat_id] = self.__register__(
                    chat_id, split_message, previous_message_from_user)
                return
            
            command = self.commands[commandName] if commandName in self.commands else self.commands[previous_message_from_user] if previous_message_from_user in self.commands else None
            if (command is None):
                return
            argument = split_message[1] if len(split_message) > 1 else None
            if (command.needs_argument and argument is None):
                if (commandName == command.name):
                    self.previous_messages[chat_id] = commandName
                    self.send_message(chat_id, "Please provide the required argument", True)
                    return
                argument = message.text
            self.__call_command__(chat_id, command, argument)
        except Exception as ex:
            self.logger.error(f"Exception in incoming_message: {ex}")

    # Internal logic functions
    def __register__(self, chat_id: int, split_message: List[str], previous_message: Union[str, None]) -> Union[str, None]:
        password_correct = None
        if (len(split_message) > 1 or previous_message is not None):
            password_correct = self.__check_admin_password__(
                chat_id, split_message[-1])

        if (password_correct == True):
            self.__add_admin__(chat_id)
            self.send_action_buttons(chat_id, True)
            return None
        elif (password_correct is not None):
            self.send_message(
                chat_id, "The provided password was incorrect!")
            self.send_action_buttons(chat_id, True)
            return None
        else:
            self.send_message(
                chat_id, "Please provide the admin password", True)
            return split_message[0].lower()

    # Message sending functions
    def send_message(self, recepient: int, text: str, remove_markup: Optional[bool] = False, answer_with_buttons: Optional[bool] = False) -> None:
        if (remove_markup):
            self.logger.debug("Disabling reply markup!")
        reply_markup = ReplyKeyboardMarkup(False) if remove_markup else None
        if (remove_markup and answer_with_buttons):
            self.logger.error("Send message called with both remove_markup and answer_withButtons! Removing markup as default!")
        elif (answer_with_buttons):
            reply_markup = self.create_buttons(recepient)
        self.Telegramm_bot.send_message(
            recepient, text, reply_markup=reply_markup)
        if (len(text) > 30):
            text = f"{text[:25]}[...]"
        self.logger.debug(f"Sending message: {text}")

    def send_action_buttons(self, recepient: int, show_all: bool = False) -> None:
        self.logger.debug(f"Reply Markup called")
        markup = self.create_buttons(recepient, show_all)
        self.logger.debug(f"Reply Markup created")
        self.Telegramm_bot.send_message(
            recepient, "Your possible options", reply_markup=markup)

    def create_buttons(self, recepient: int, show_all: Optional[bool] = True) -> ReplyKeyboardMarkup:
        caller_is_admin = self.__is_admin__(recepient)
        markup = ReplyKeyboardMarkup()
        items = [KeyboardButton(command.name)
                 for command in self.commands.values() if ((command.is_default or show_all) and CommandPrivilege.should_show(command.privilege, caller_is_admin))]
        markup.add(*items)
        return markup

    # Callback registers
    def register_callback(
            self, 
            callback: Callable[..., Any], 
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

        Optional, predefined:
            - wake(int) -> None
            - shutdown(int, str|None) -> None
            
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
        
        Optional, predefined:
            - wake(int) -> None
            - shutdown(int, str|None) -> None
        
        If no name is provided, the callback function's name will be used instead. The names should be the exact names specified above.
        """
        def decorator(callback: Callable[..., Any]):
            self.register_callback(callback, name, needs_argument, show_button, privilege, accessable_to_user)
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

    def __status__(self, chat_id: int, _) -> None:
        function_name = "send_status"
        if (function_name in self.callbacks):
            status = self.callbacks[function_name]()
            self.send_message(chat_id, status)
        else:
            self.logger.warning("SendStatus callback is not found!")
            self.send_message(
                chat_id, "The status is not available at the moment!")

    def __call_command__(self, chat_id: int, command: Command, argument: str = None) -> None:
        if (command.name not in self.callbacks):
            self.logger.warning(f"Command '{command.name}' not in callbacks!")
            self.send_message(chat_id, "Command not available at the moment!", answer_with_buttons=True)
            return
        self.callbacks[command.name](command.name, APIMessage.create_message(str(chat_id), argument, str(chat_id), [], None, Interface.Telegramm))

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
