import select
import socket
import json
import threading
import discord
import re
import pickle
from os import path, devnull, system, remove
from sys import stdout, __stdout__
from time import sleep, time
from datetime import datetime
from typing import Any, Callable, Dict, List, Union, Optional
from hashlib import sha256
from enum import Enum
from abc import ABC, abstractclassmethod

from requests.models import Response

class JsonSerializable(ABC):
    @staticmethod
    def from_json(json_string: str) -> "JsonSerializable":
        pass

    @abstractclassmethod
    def to_json(self) -> str:
        pass


class ValidationError(Exception):
    """Get's raised, when validation failes"""

    def __init__(self, reason: str) -> None:
        self.message = f"Validation failed! Reason: {reason}"


class NotValidatedError(Exception):
    """Get's raised, when trying to communicate with the API server, without validation."""

    def __init__(self) -> None:
        self.message = "Can't communicate without validation!"


class ActionFailed(Exception):
    """Get's raised, when an action failes"""

    def __init__(self, action: str) -> None:
        self.message = f"'{action}' failed!'"


class Attachment(JsonSerializable):
    """Message attachment"""
    @staticmethod
    def from_json(json_string: str):
        data = json.loads(json_string)
        if data is None:
            return None
        return Attachment(data["filename"], data["url"], data["size"])

    def from_discord_attachment(atch: discord.Attachment):
        if atch is None:
            return None
        return Attachment(atch.filename, atch.url, atch.size)

    def __init__(self, filename: str, url: str, size: int) -> None:
        if not isinstance(size, int):
            raise AttributeError(f"{type(size)} is not int type")
        self.url = url
        self.filename = filename
        self.size = size

    def size(self) -> int:
        return self.size

    def download(self) -> Response:
        import requests
        return requests.get(self.url)

    def save(self, save_path: str) -> str:
        if not path.exists(save_path):
            return ""
        tmp = self.filename
        n = 1
        while path.exists(path.join(save_path, tmp)):
            tmp = "".join((".".join(self.filename.split(
                ".")[:-1]), f"({n}).", self.filename.split(".")[-1]))
            n += 1
        self.filename = tmp
        file = self.download()
        with open(path.join(save_path, self.filename), "wb") as f:
            f.write(file.content)
        return path.join(save_path, self.filename)

    def to_json(self) -> Dict:
        return json.dumps({"filename": self.filename, "size": self.size, "url": self.url})


class Interface(Enum):
    Discord = 0
    Telegramm = 1


class Message(JsonSerializable):
    """Message object used by the api"""
    USER_REGX = r"(<@![0-9]+>){1}"

    @staticmethod
    def from_json(json_string: str) -> "Message":
        data = json.loads(json_string)
        msg = Message(data["sender"], data["content"], data["channel"], [Attachment.from_json(attachment)
                      for attachment in data["attachments"]] if data["attachments"] is not None else [], data["called"], Interface(data["interface"]) if data["interface"] is not None else Interface.Discord)
        if "random_id" in data:
            msg.random_id = data["random_id"]
        return msg

    def create_message(sender: str, content: str, channel: str, attachments: List[Attachment], called: str, interface: Interface) -> "Message":
        return Message(sender, content if content is not None else "", channel, attachments, called, interface)

    def __init__(self, sender: str, content: str, channel: str, attachments: List[Attachment], called: str, interface: Interface = None) -> None:
        self.sender = sender
        self.content = content
        self.channel = channel
        self.attachments = attachments
        self.called = called
        self.interface = interface
        self.random_id = sha256(
            f"{sender}{content}{channel}{called}{datetime.now()}".encode("utf-8")).hexdigest()

    def add_called(self, called: str) -> None:
        self.called = called

    def contains_user(self) -> bool:
        return len(re.findall(Message.USER_REGX, self.content)) > 0

    def get_contained_user_id(self) -> str:
        if not self.contains_user():
            return ""
        if " " in self.content:
            content = self.content.split(' ')
            for item in content:
                if "<@" in item:
                    return item.replace("<@!", "").replace(">", "")

    def has_attachments(self) -> bool:
        return len(self.attachments) > 0

    def to_json(self) -> str:
        return json.dumps({
            "sender": self.sender,
            "content": self.content,
            "channel": self.channel,
            "called": self.called,
            "attachments": [attachment.to_json() for attachment in self.attachments] if len(self.attachments) > 0 else None,
            "interface": self.interface.value if self.interface is not None else None,
            "random_id": self.random_id
        })

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Message):
            return False
        return self.sender == other.sender and self.content == other.content and self.channel == other.channel and self.random_id == other.random_id


class ResponseCode(Enum):
    Success = 0
    BadRequest = 1
    InternalError = 2
    Denied = 3
    Accepted = 4
    Failed = 5
    NotFound = 6

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self):
        return str(self.value)

    def __eq__(self, __o: object) -> bool:
        return str(__o) == str(self.value)


class Response(JsonSerializable):

    def __init__(self, response: ResponseCode, Data=None, __bool: bool = None):
        """Possible Responses: Bad request, Success, Internal error
        """
        self.response_code = response
        self.data = Data
        self.bool = __bool if __bool is not None else response in [
            ResponseCode.Success, ResponseCode.Accepted]

    def create_altered(self, response=None, Data=None):
        return Response(response or self.response_code, Data or self.data)

    def __bool__(self):
        return self.bool

    def __str__(self):
        return str(self.__dict__)
    
    def __eq__(self, __value: object) -> bool:
        if (isinstance(__value, Response)):
            return self.response_code == __value.response_code
        if (isinstance(__value, ResponseCode)):
            return self.response_code == __value
        return False

    def to_json(self) -> Dict:
        tmp = self.__dict__
        tmp["response_code"] = self.response_code.__repr__()
        return json.dumps(tmp)

    @staticmethod
    def from_json(json_string: str) -> "Response":
        data = json.loads(json_string)
        return Response(ResponseCode(int(data["response_code"])), data["data"], data["__bool"] if "__bool" in data else None)

class Events(Enum):
    presence_update = 0
    activity = 1

class UserEventRequest(JsonSerializable):
    uid: str
    event: Events

    @staticmethod
    def from_json(json_string: Dict) -> "UserEventRequest":
        data = json.loads(json_string)
        return UserEventRequest(data["uid"], Events(data["event"]))

    def __init__(self, uid: str, event: Events) -> None:
        self.uid = uid
        self.event = event
    
    def to_json(self) -> str:
        tmp = self.__dict__
        tmp["event"] = self.event.value
        return json.dumps(tmp)
        
class Privilege(Enum):
    Anyone = 0
    OnlyAdmin = 1
    OnlyUnknown = 2

def blockPrint() -> None:
    global stdout
    stdout = open(devnull, 'w')


def enablePrint() -> None:
    global stdout
    stdout.close()
    stdout = __stdout__


NOTHING = 0
USER_INPUT = 1
SENDER = 2
CHANNEL = 4


class API:
    """API for the 'Server monitoring Discord bot' application."""

    @staticmethod
    def from_config(file_name: str, update_function: Callable[[], None] = None) -> "API":
        data = None
        with open(file_name, "rb") as f:
            data = pickle.load(f)
        return API(data["name"], data["key"], data["ip"], int(data["port"]), update_function)

    @staticmethod
    def create_config(name: str, key: str, ip: str, port: int, file_name: str = "api_config.conf") -> None:
        with open(file_name, "wb") as f:
            pickle.dump({"name": name, "key": key, "ip": ip, "port": port}, f)

    def __init__(self, name: str, key: str, ip: str = "127.0.0.1", port: int = 9600, update_function: Callable[[], None] = None) -> None:
        """Initialises an API that connects to the 'ip' ip and to the 'port' port with the 'name' name and the 'key' api key.
        The update_function should be a vfunction to call, when the bot calls for update (usually when the bot is updated). The function should not require input data.
        """
        self.ip = ip
        self.port = port
        self.name = name
        self.key = key
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.valid = False
        self.call_list = {"UPDATE": self.update,
                          "TRACK FINISHED": self.__track_hoock, "EVENT": self.__event_callback}
        self.buffer = []
        self.sending = False
        self.running = True
        self.connection_alive = True
        self.initial = True
        self.socket_list: List[socket.socket] = []
        self.created_function_list: List[List[str]] = []
        self.create_function_threads: List[threading.Thread] = []
        self.update_function = update_function
        self.communicateLock = threading.Lock()
        self.track_hook: Callable[[Message], None] = None
        self.last_message: Message = None
        self.subscriber_threads: List[threading.Thread] = []
        self.subscriber_callbacks: Dict[Events,
                                        Callable[[str, str, int], None]] = {}

    def __send(self, msg: JsonSerializable) -> None:
        """Sends a socket message
        """
        msg_json = msg.to_json()
        while True:
            tmp = ''
            if len(msg_json) > 9:
                tmp = msg_json[9:]
                msg_json = msg_json[:9]
            self.socket.send(str(len(msg_json)).encode(encoding='utf-8'))
            self.socket.send(msg_json.encode(encoding="utf-8"))
            if tmp == '':
                tmp = '\x00'
            if msg_json == "\x00":
                break
            msg_json = tmp

    def __retrive(self) -> str:
        """Retrives a socket message
        """
        ret = ""
        try:
            while True:
                blockPrint()
                size = int(self.socket.recv(1).decode('utf-8'))
                data = self.socket.recv(size).decode('utf-8')
                enablePrint()
                if data == '\x00':
                    break
                ret += data
            return ret
        except Exception as ex:
            enablePrint()
            print(f"[_retrive exception]: {ex}")
            return None

    def __listener(self) -> None:
        """Listens for incoming messages, and stops when the program stops running
        """
        while self.running:
            while self.valid and self.connection_alive:
                try:
                    read_socket, _, exception_socket = select.select(
                        self.socket_list, [], self.socket_list)

                    if exception_socket != []:
                        self.__close_connection

                    elif read_socket != []:
                        msg = self.__retrive()
                        if msg is None:
                            self.connection_alive = False
                            self.socket.close()
                            self.socket = socket.socket(
                                socket.AF_INET, socket.SOCK_STREAM)
                            self.socket_list = []
                            if self.sending:
                                self.buffer.append(
                                    {"response": ResponseCode.InternalError, "data": "Connection closed"})
                        elif self.sending:
                            self.buffer.append(msg)
                            self.last_message = msg
                        elif not self.sending:
                            if "response_code" in msg:
                                response = Response.from_json(msg)
                                if not response:
                                    print(response.data)
                                continue
                            message = Message.from_json(msg)
                            if self.last_message is not None and self.last_message == message:
                                continue
                            self.last_message = message
                            if message.called is not None and message.called in self.call_list:
                                call = threading.Thread(
                                    target=self.call_list[message.called], args=[message, ])
                                call.name = message.called
                                call.start()
                except Exception as ex:
                    print(f"[Listener thread Inner exception] <{ex.__qualname__}>: {ex}")
                sleep(0.2)

            try:
                if self.running:
                    self.__validate()
                    self.connection_alive = True
            except Exception as ex:
                print(f"[Listener thread Outer exception] <{ex.__qualname__}>: {ex}")

    def __close_connection(self):
        self.connection_alive = False
        self.socket.close()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_list = []
        if self.sending:
            self.buffer.append(
                {"response": ResponseCode.InternalError, "data": "Connection closed"})

    def __get_copy_function_list(self):
        ret = []
        for item in self.created_function_list:
            ret.append(item)
        return ret

    def __re_init_commands(self) -> None:
        tmp = self.__get_copy_function_list()
        for item in tmp:
            self.create_function(*item)
        del tmp

    def validate(self, timeout: int = -1) -> bool:
        """Validates with the bot, and starts the listener loop, if validation is finished. Returns false, if validation timed out
        Timeout can be set, so it won't halt the program for ever, if no bot is present. (The timeout will only work for the first validation.)
        If the timeout is set to -1, the validation will be in a new thread, and always return true.
        """
        if timeout is not None and timeout == -1:
            tmp = threading.Thread(target=self.__validate)
            tmp.name = "Validation"
            tmp.start()
            return True
        else:
            return self.__validate(timeout)

    def __validate(self, timeout: int = None) -> bool:
        start = time()
        self.communicateLock.acquire()
        self.sending = True
        try:
            while True:
                try:
                    self.socket.connect((self.ip, self.port))
                    break
                except:
                    pass
                if (timeout is not None and timeout > 0 and time() - start > timeout) or not self.running:
                    return False
            self.__send(Message(self.name, self.key, None, [], self.name))
            ansvear = self.__retrive()
            response = Response.from_json(ansvear)
            if not response.bool:
                raise ValidationError(response.data)
            else:
                self.valid = True
                self.socket_list.append(self.socket)
                if self.created_function_list != []:
                    self.connection_alive = True
                    self.__re_init_commands()
                if self.subscriber_callbacks != {}:
                    self.connection_alive = True
                    self.__re_subscribe()
                if self.initial:
                    self.initial = False
                    self.th = threading.Thread(target=self.__listener)
                    self.th.name = "Listener Thread"
                    self.th.start()
            self.sending = False
        except Exception as ex:
            raise ex
        finally:
            self.sending = False
            self.communicateLock.release()
        return True

    def is_admin(self, uid: str) -> bool:
        if self.valid:
            self.sending = True
            self.__send(Message(self.name, uid, None, [], "Is Admin"))
            tmp = self.__wait_for_response()
            if tmp.response_code == ResponseCode.Success:
                return tmp.data
            print(f"{tmp.response_code.name}: {tmp.data}")
            return False
        else:
            NotValidatedError()

    def get_user_status(self, uid: str, __type: Events = Events.activity) -> str:
        if self.valid:
            self.sending = True
            self.__send(Message(self.name, UserEventRequest(uid, __type).to_json(), None, [], "Get User Status"))
            tmp = self.__wait_for_response()
            if tmp.response_code == ResponseCode.Success:
                return tmp.data
            print(f"{tmp.response_code.name}: {tmp.data}")
            return ""
        else:
            NotValidatedError()

    def update(self, _) -> None:
        """Trys to update the API with PIP, and calls the given update function if there is one avaleable.
        """
        system("pip install --user --upgrade smdb_api > pip.txt")
        remove("pip.txt")
        if self.update_function is not None:
            self.update_function()

    def get_status(self) -> dict:
        """Gets the bot's status
        """
        if self.valid:
            self.sending = True
            self.__send(Message(self.name, None, None, [], "Status"))
            tmp = self.__wait_for_response()
            return tmp.data
        else:
            raise NotValidatedError()

    def get_username(self, key: str) -> str:
        self.sending = True
        self.__send(Message(self.name, key, None, [], "Username"))
        tmp = self.__wait_for_response()
        return tmp.data if tmp.response_code == ResponseCode.Success else "unknown"

    def send_message(self, message: str, interface: Interface, destination: str = None, file_path: str = None) -> bool:
        """Sends a message trough the discord bot.
        """
        msg = Message("API", message, destination, [Attachment(file_path.split(
            "/")[-1], file_path, path.getsize(file_path))] if file_path is not None else [], "API", interface)
        if self.valid:
            self.sending = True
            self.__send(Message(self.name, msg.to_json(), None, [], "Send"))
            tmp = self.__wait_for_response()
            if tmp.response_code == ResponseCode.BadRequest:
                raise ActionFailed(tmp.data)
            elif tmp.response_code == ResponseCode.InternalError:
                print(
                    f"[Message sending exception] Internal error: {tmp.data}")
                return False
            return True
        else:
            raise NotValidatedError

    def close(self, reason: str = None) -> None:
        """Closes the socket, and stops the listener loop.
        """
        if self.valid and self.connection_alive:
            self.__send(Message(self.name, reason, None, [], "Disconnect"))
        self.running = False
        self.valid = False
        self.connection_alive = False
        self.sending = False
        self.socket.close()

    def create_function(self, name: str, help_text: str, callback: Callable[[Message], None], privilege: Privilege = None, show_button: bool = False, needs_arguments: bool = False) -> None:
        """Creates a function in the connected bot. This function creates a thread so it won't block while it waits for validation from the bot.
        Returns a Message object. The returned value depends on the return value, but the order is the same.
        """
        self.create_function_threads.append(threading.Thread(
            target=self.__create_function, args=[name, help_text, callback, privilege, show_button, needs_arguments, ]))
        self.create_function_threads[-1].name = f"Create thread for {name}"
        self.create_function_threads[-1].start()

    def __create_function(self, name: str, help_text: str, callback: Callable[[Message], None], privilege: Privilege = None, show_button: bool = False, needs_arguments: bool = False) -> None:
        """Creates a function in the connected bot when validated.
        """
        self.communicateLock.acquire()
        self.sending = True
        try:
            if [name, help_text, callback, privilege, show_button, needs_arguments] not in self.created_function_list:
                self.created_function_list.append([name, help_text, callback, privilege, show_button, needs_arguments])
            if not self.valid:
                return
            self.__send(Message(self.name, json.dumps({"name": name, "help":help_text, "privilege":privilege, "show_button": show_button, "needs_arguments":needs_arguments}), None, [], "Create"))
            tmp = self.__wait_for_response()
            self.sending = False
            if tmp.response_code == ResponseCode.Success:
                self.call_list[name] = callback
            elif tmp.response_code == ResponseCode.InternalError:
                print(
                    f"[_create_function exception] Internal error: {tmp.data}")
            else:
                raise ActionFailed(tmp["data"])
        except Exception as ex:
            raise ex
        finally:
            self.sending = False
            self.communicateLock.release()

    def __wait_for_response(self) -> Response:
        while self.buffer == []:
            sleep(0.1)
        self.sending = False
        tmp = Response.from_json(self.buffer[0])
        self.buffer = []
        return tmp

    def connect_to_voice(self, user_id: str) -> bool:
        self.sending = True
        self.__send(Message(self.name, user_id, None, [], "Connect To User"))

        return self.__wait_for_response().bool

    def disconnect_from_voice(self) -> bool:
        self.sending = True
        self.__send(Message(self.name, None, None, [], "Disconnect From Voice"))

        return self.__wait_for_response().bool

    def play_file(self, path: str, user_id: str) -> bool:
        self.sending = True
        self.__send(Message(self.name, json.dumps({"Path": path, "User": user_id}), None, [], "Play Audio File"))

        return self.__wait_for_response().bool

    def add_file(self, path: str) -> bool:
        self.sending = True
        self.__send(Message(self.name, path, None, [], "Add Audio File"))
        return self.__wait_for_response().bool

    def pause_currently_playing(self, user_id: str) -> bool:
        self.sending = True
        self.__send(Message(self.name, user_id, None, [], "Pause Currently Playing"))
        return self.__wait_for_response().bool

    def resume_paused(self, user_id: str) -> bool:
        self.sending = True
        self.__send(Message(self.name, user_id, None, [], "Resume Paused"))
        return self.__wait_for_response().bool

    def skip_currently_playing(self, user_id: str) -> bool:
        self.sending = True
        self.__send(Message(self.name, user_id, None, [], "Skip Currently Playing"))
        return self.__wait_for_response().bool

    def stop_currently_playing(self, user_id: str) -> bool:
        self.sending = True
        self.__send(Message(self.name, user_id, None, [], "Stop Currently Playing"))
        return self.__wait_for_response().bool

    def get_queue(self) -> Union[List[str], None]:
        self.sending = True
        self.__send(Message(self.name, None, None, [], "List Queue"))
        return self.__wait_for_response().data

    def set_as_hook_for_track_finished(self, callable: Callable[[Message], None]) -> None:
        thread = threading.Thread(
            target=self.__set_as_hook_for_track_finished, args=[callable, ])
        thread.name = "Hook thread"
        thread.start()

    def __set_as_hook_for_track_finished(self, callable: Callable[[Message], None]) -> None:
        self.communicateLock.acquire()
        try:
            self.sending = True
            self.__send(Message(self.name, None, None, [], "Set As Track Finished"))
            if self.__wait_for_response().bool:
                self.track_hook = callable
        finally:
            self.communicateLock.release()

    def __track_hoock(self, message: Message) -> None:
        if self.track_hook != None:
            self.track_hook(message)

    def __re_subscribe(self) -> None:
        for key, value in self.subscriber_callbacks.items():
            self.subscribe_to_event(key, value)

    def subscribe_to_event(self, event: Events, callable: Callable[[str, str, Message], None]) -> bool:
        self.subscriber_threads.append(threading.Thread(
            target=self.__subscribe_to_event, args=[event, callable, ]))
        self.subscriber_threads[-1].name = f"Subscribe to {event.name}"
        self.subscriber_threads[-1].start()

    def __subscribe_to_event(self, event: Events, callable: Callable[[str, str, Message], None]) -> bool:
        self.communicateLock.acquire()
        self.sending = True
        try:
            if (not self.valid):
                return
            self.__send(
                {"Command": "Subscribe To Event", "Value": event.value})
            tmp = self.__wait_for_response()
            self.sending = False
            if tmp.response_code == ResponseCode.Success:
                if event not in self.subscriber_callbacks:
                    self.subscriber_callbacks[event] = callable
                return True
            elif tmp.response_code == ResponseCode.InternalError:
                print(
                    f"[__subscribe_to_event exception] Internal error: {tmp['Data']}")
                return False
            else:
                raise ActionFailed(tmp["data"])
        finally:
            self.sending = False
            self.communicateLock.release()

    def reply_to_message(self, reply: str, message: Message) -> bool:
        return self.send_message(reply, message.interface, message.sender)

    def __event_callback(self, message: Message) -> None:
        event, before, after = message.content.split('|')
        self.subscriber_callbacks[Events(int(event))](
            before, after, message)
