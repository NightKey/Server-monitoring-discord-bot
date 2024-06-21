from dataclasses import dataclass, field
from enum import Enum
from os import path
import sys
from typing import Any, Callable, Dict, List, Optional, Union, overload
from smdb_logger import Logger
from smdb_api import Message, Response, ResponseCode, Events, Interface, UserEventRequest

from . import log_level, log_folder
from .voice_connection import VCRequest
from hashlib import sha256
import socket
import select
import json


logger = Logger("api_server.log", log_folder=log_folder, level=log_level,
                log_to_console=True, use_caller_name=True, use_file_names=True)

class Privilege(Enum):
    Anyone = 0
    OnlyAdmin = 1
    OnlyUnknown = 2

@dataclass()
class LinkingEditorData:
    name: str
    callback: Callable[..., Any] = field(default_factory=None)
    add_to_telegramm: bool = False
    add_button: bool = False
    privilage: Privilege = field(default=Privilege.OnlyAdmin)
    needs_input: bool = False


class Server:
    def __init__(self) -> None:
        self.clients = {}
        self.run = True
        self.functions = {}
        self._load_settings()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.ip, self.port))
        self.socket_list = [self.socket]
        self.track_finished_socket = None
        self.subscribers_for_event: Dict[Events, List[socket.socket]] = {
            Events.presence_update: [],
            Events.activity: []
        }
        self.callbacks: Dict[str, Callable[..., Any]] = {}
        logger.header("Service initialized")

    def change_ip_port(self, ip: str, port: int) -> None:
        self.ip = ip
        self.port = port
        self.key = self._generate_key()
        self._save_settings()

    def _load_settings(self) -> None:
        from os import path
        settings_path = path.join("data", "server.cfg")
        if path.exists(settings_path):
            try:
                with open(settings_path, "r") as settings_file:
                    settings = json.load(settings_file)
                self.ip = settings["ip"]
                self.port = settings["port"]
                self.key = settings["key"]
                self.settings = "custom"
            except:
                self._save_settings("default")
        else:
            self._save_settings("default")

    def _generate_key(self) -> str:
        return f'{self.ip}{self.port}'

    def _save_settings(self, key: str = "current") -> None:
        from os import path, mkdir
        settings_path = path.join("data", "server.cfg")
        if not path.exists("data"):
            mkdir("data")
        settings = {}
        if key == "current":
            settings["ip"] = self.ip
            settings["port"] = self.port
            settings["key"] = self.key
        elif key == "default":
            settings["ip"] = '127.0.0.1'
            self.ip = '127.0.0.1'
            settings["port"] = 9600
            self.port = 9600
            settings["key"] = '127.0.0.19600'
            self.key = '127.0.0.19600'
            self.settings = "default"
        with open(settings_path, "w") as settings_file:
            json.dump(settings, settings_file)

    def get_api_status(self) -> dict:
        return {"connections": list(self.clients.values()), "commands": list(self.functions.values())}

    def request_all_update(self) -> None:
        """Requests an update from the all connected clients. This update should request the application used to update itself and the API
        """
        for target in self.socket_list:
            if target == self.socket:
                continue
            self.send_update_request(target)

    def send_update_request(self, target) -> None:
        """Requests an update from the target. This update should request the application used to update itself and the API
        """
        self.send(Message("0000000000", "", "0000000000",
                  [], "UPDATE"), target)

    def start(self) -> None:
        """Starts the API server
        """
        self.commands = {
            'Status': self.get_status_command,
            'Send': self.send_command,
            'Create': self.create_command,
            'Remove': self.remove_command,
            'Username': self.return_usrname,
            'Disconnect': self.disconnect,
            'Is Admin': self.admin_check,
            'Connect To User': self.connect_to_user,
            'Disconnect From Voice': self.disconnect_from_voice,
            'Play Audio File': self.play_file,
            'Add Audio File': self.add_file,
            'Pause Currently Playing': self.pause_playing,
            'Resume Paused': self.resume_paused,
            'Skip Currently Playing': self.skip_playing,
            'Stop Currently Playing': self.stop_playing,
            'List Queue': self.list_queue,
            'Set As Track Finished': self.set_track_finished_target,
            'Subscribe To Event': self.subscribe_to_event,
            'Get User Status': self.get_user_status
        }
        self.socket.listen()
        logger.info("API Server started")
        self.loop()

    def _start_for_test(self) -> None:
        self.commands = {
            'Status': self.get_status_command,
            'Send': self.send_command,
            'Create': self.create_command,
            'Remove': self.remove_command,
            'Username': self.return_usrname,
            'Disconnect': self.disconnect,
            'Is Admin': self.admin_check,
            'Connect To User': self.connect_to_user,
            'Disconnect From Voice': self.disconnect_from_voice,
            'Play Audio File': self.play_file,
            'Add Audio File': self.add_file,
            'Pause Currently Playing': self.pause_playing,
            'Resume Paused': self.resume_paused,
            'Skip Currently Playing': self.skip_playing,
            'Stop Currently Playing': self.stop_playing,
            'List Queue': self.list_queue,
            'Get User Status': self.get_user_status
        }
        logger.log_to_console = False
        self.socket.listen()

    # region MUSIC
    def connect_to_user(self, socket: socket, user: str) -> None:
        self.send(self.use_callback("voice_connection_controll", 
            VCRequest.connect, user_id=user), socket)

    def disconnect_from_voice(self, socket: socket, _) -> None:
        self.send(self.use_callback("voice_connection_controll", VCRequest.disconnect), socket)

    def play_file(self, socket: socket, data: str) -> None:
        data = json.loads(data)
        self.send(self.use_callback("voice_connection_controll", VCRequest.play, user_id=data["User"], path=data["Path"]), socket)

    def add_file(self, socket: socket, path: str) -> None:
        self.send(self.use_callback("voice_connection_controll", VCRequest.add, path=path), socket)

    def pause_playing(self, socket: socket, user: str) -> None:
        self.send(self.use_callback("voice_connection_controll", VCRequest.pause, user_id=user), socket)

    def resume_paused(self, socket: socket, user: str) -> None:
        self.send(self.use_callback("voice_connection_controll", VCRequest.resume, user_id=user), socket)

    def stop_playing(self, socket: socket, user: str) -> None:
        self.send(self.use_callback("voice_connection_controll", VCRequest.stop, user_id=user), socket)

    def skip_playing(self, socket: socket, user: str) -> None:
        logger.debug("Skip requested")
        self.send(self.use_callback("voice_connection_controll", VCRequest.skip, user_id=user), socket)

    def list_queue(self, socket: socket, _) -> None:
        self.send(self.use_callback("voice_connection_controll", VCRequest.queue), socket)

    def set_track_finished_target(self, socket: socket, _) -> None:
        self.track_finished_socket = socket
        self.send(Response(ResponseCode.Accepted), socket)

    def track_finished(self, track: str) -> None:
        if self.track_finished_socket is not None:
            self.send(Message("Bot", track, None, [],
                      "TRACK FINISHED", Interface.Discord), self.track_finished_socket)
    # endregion

    def create_command(self, socket: socket, data: dict) -> None:
        """Creates a command in the discord bot
        """
        if data is None:
            self.send(Response(ResponseCode.BadRequest, "No data given"), socket)
            return
        data = json.loads(data)
        self.send(self.create_function(self.clients[socket], **data), socket)

    def get_status_command(self, socket: socket, _) -> None:
        """Returns the status to the socket
        """
        self.send(self.use_callback("get_status", ), socket)

    def send_command(self, socket: socket, msg: str) -> None:
        """Sends the message retrived from the socket to the bot.
        """
        if msg is None:
            self.send(Response(ResponseCode.BadRequest, "Empty message"), socket)
            return
        message = Message.from_json(msg)
        self.send(self.use_callback("send_message", message), socket)

    def retrive(self, socket: socket) -> str:
        r"""Retrives a message from the socket. Every message is '\x00' terminated (terminator not included)
        """
        ret = ""
        try:
            while True:
                size = socket.recv(1).decode('utf-8')
                try:
                    size = int(size)
                except:
                    logger.debug(f"Retrived NoN Int data for size: {size}")
                    self.client_lost(socket)
                    return None
                data = socket.recv(size).decode(encoding="utf-8")
                if data == '\x00':
                    break
                ret += data
            return ret
        except Exception as ex:
            _, _, exc_tb = sys.exc_info()
            logger.error(f"{ex} on line {exc_tb.tb_lineno}")
            return None

    def send(self, msg: Union[Message, Response], socket: Union[socket.socket, str]) -> bool:
        r"""Sends a message to the socket. Every message is '\x00' terminated (terminator does not required)
        """
        try:
            logger.debug(f"Sending total message: {msg}")
            if isinstance(socket, str):
                for key, value in self.clients.items():
                    if value == socket:
                        socket = key
                        break
            msg_json = msg.to_json()
            while True:
                tmp = ''
                if len(msg_json) > 9:
                    tmp = msg_json[9:]
                    msg_json = msg_json[:9]
                length = str(len(msg_json)).encode(encoding='utf-8')
                # logger.debug(f"Sending legth: {length}")
                socket.send(length)
                chunk = msg_json.encode(encoding="utf-8")
                # logger.debug(f"Sending chunk: {chunk}")
                socket.send(chunk)
                if tmp == '':
                    tmp = '\x00'
                if msg_json == "\x00":
                    break
                msg_json = tmp
            return True
        except ConnectionError:
            self.client_lost(socket)
            return False

    def get_api_key_for(self, name: str) -> str:
        """Returns the correct API key for a 'name' named program
        """
        return sha256(f"{self.key}{name}".encode('utf-8')).hexdigest()

    def admin_check(self, socket: socket, uid: str) -> None:
        if uid is None:
            self.send(Response(ResponseCode.BadRequest, "No UID was given"), socket)
            return
        self.send(self.use_callback("is_admin", uid), socket)

    def __read_template__(self, name: str, creator: str, help_text: str) -> str:
        with open(path.join("templates", "service_command_template.template"), 'r') as f:
            data = f.read(-1)
        return data.replace(r'{help_text}', help_text).replace(
            r'{name}', name).replace(r'{creator}', creator)

    def event_trigger(self, event: Events, before: str, after: str, channel: int) -> None:
        for recepient in self.subscribers_for_event[event]:
            self.send(Message("Bot", f"{event.value}|{before}|{after}",
                      str(channel), [], "EVENT", Interface.Discord), recepient)

    def subscribe_to_event(self, socket: socket, msg: str) -> None:
        self.subscribers_for_event[Events(int(msg))].append(socket)
        self.send(Response(ResponseCode.Success), socket)

    def create_function(self, creator: str, name: str, help: str, privilege: Union[Privilege, None], show_button: bool, needs_arguments: bool) -> Response:
        """Creates a function with the given parameters, and stores it in the self.functions dictionary, with the 'name' as key
        """
        logger.debug(f'Creating function with the name {name}')
        logger.debug(f'Creating function with the creator as {creator}')
        logger.debug(f'Telegram options: {privilege}, {show_button}, {needs_arguments}')
        add_to_telegramm = privilege is not None
        if privilege is None: privilege = Privilege.OnlyAdmin
        body = self.__read_template__(name, creator, help)
        try:
            exec(body)
        except Exception as ex:
            logger.error(f"{body}")
            logger.error(ex)
            return Response(ResponseCode.InternalError, ex)
        setattr(self, name, locals()[name])
        self.use_callback("linking_editor", LinkingEditorData(name, getattr(self, name), add_to_telegramm=add_to_telegramm, privilage=privilege, needs_input=needs_arguments))
        if creator not in self.functions:
            self.functions[creator] = []
        self.functions[creator].append(name)
        return Response(ResponseCode.Success)

    def remove_command(self, socket: socket, name) -> None:
        """Removes a function. Removes all functions, if empty message was sent instead of a function name!
        """
        if not name in self.functions[self.clients[socket]]:
            name = None
        self.send(self.remove_function(
            creator=self.clients[socket], name=name), socket)

    def remove_function(self, creator: str, name: str = None) -> Response:
        """Removes a function from the created functions
        """
        try:
            if creator not in self.functions:
                return Response(ResponseCode.InternalError, "Function not found")
            if name is None:
                for name in self.functions[creator]:
                    self.use_callback("linking_editor", name, True)
                    delattr(self, name)
                del self.functions[creator]
            else:
                self.use_callback("linking_editor", LinkingEditorData(name), True)
                delattr(self, name)
                self.functions[creator].remove(name)
            return Response(ResponseCode.Success)
        except Exception as ex:
            logger.error(f"{ex}")
            return Response(ResponseCode.InternalError, ex)

    def return_usrname(self, socket: socket, uid: str) -> None:
        if uid is None:
            self.send(Response(ResponseCode.BadRequest, "No UID was given"), socket)
            return
        self.send(self.use_callback("get_user", uid), socket)

    def get_user_status(self, socket: socket, data: Dict[str, Any]) -> None:
        user_event = UserEventRequest.from_json(data)
        if user_event.uid is None or user_event.event is None:
            self.send(Response(ResponseCode.BadRequest, "No User or Type were provided."), socket)
        self.send(self.use_callback("get_user_status", user_event.uid, user_event.event), socket)

    def stop(self) -> None:
        self.run = False

    def loop(self) -> None:
        """Handles the clients.
        """
        while self.run:
            try:
                read_socket, _, exception_socket = select.select(
                    self.socket_list, [], self.socket_list, 1)
                for notified_socket in read_socket:
                    if notified_socket == self.socket:
                        self.new_client()
                    else:
                        logger.debug(
                            f"Incoming message from {self.clients[notified_socket]}")
                        msg = self.retrive(notified_socket)
                        if msg is None:
                            logger.debug("None message retrived")
                            self.client_lost(notified_socket)
                            continue
                        else:
                            self.command_retrieved(Message.from_json(msg), notified_socket)
                for notified_socket in exception_socket:
                    self.client_lost(notified_socket)
            except socket.error as er:
                logger.error(f"{er}")
            except Exception as ex:
                _, _, exc_tb = sys.exc_info()
                logger.error(f"{ex} on line {exc_tb.tb_lineno}")
        self.socket.close()

    def command_retrieved(self, msg: Message, socket: socket) -> None:
        """Retrives commands
        """
        if msg.called not in self.commands:
            self.send(Response(ResponseCode.BadRequest, Data="Command is not a valid command"), socket)
            return
        self.commands[msg.called](socket, msg.content)

    def disconnect(self, socket: socket, reason: str) -> None:
        if reason is not None:
            logger.info(
                f"{self.clients[socket]} disconnected with the following reason: {reason}")
        else:
            logger.info(
                f"{self.clients[socket]} disconnected with no reason given.")
        self.client_lost(socket, called=True)

    def client_lost(self, socket: socket, called: bool = False) -> None:
        """Handles loosing connections
        """
        if socket not in self.clients:
            return
        if not called:
            logger.warning(f"{self.clients[socket]} closed connection.")
        if self.remove_function(creator=self.clients[socket]):
            logger.debug("Functions removed!")
        del self.clients[socket]
        self.socket_list.remove(socket)
        logger.info("Client removed!")
        if called:
            socket.close()
        return

    def new_client(self) -> None:
        """handles new clinets
        """
        client_socket, client_address = self.socket.accept()
        client_socket.settimeout(30)
        logger.info(
            f"Incoming connection from {client_address[0]}:{client_address[1]}")
        retrived = Message.from_json(self.retrive(client_socket))
        try:
            name, key = retrived.called, retrived.content
        except:
            self.send(Response(ResponseCode.Denied, "Bad API protocoll was used!"), client_socket)
            client_socket.close()
            return
        if key != sha256(f"{self.key}{name}".encode('utf-8')).hexdigest():
            self.send(Response(ResponseCode.Denied, "Bad API Key"), client_socket)
            client_socket.close()
            return
        if name in self.clients:
            self.send(Response(ResponseCode.Success, "Already connected"), client_socket)
            client_socket.close()
            return
        self.send(Response(ResponseCode.Success), client_socket)
        logger.debug(f"Adding {name} to the connections")
        self.socket_list.append(client_socket)
        self.clients[client_socket] = name

    def register_callback(self, callback: Callable[..., Any], name: Optional[str] = None):
        """Registers a callback to the service.
        The following callbacks needed:
        - linking_editor: Callable[[Any, bool], None],
        - get_status: Callable[[], dict],
        - send_message: Callable[[Message], Response],
        - get_user: Callable[[str], Response],
        - is_admin: Callable[[str], Response],
        - voice_connection_controll: Callable[[
            VCRequest, Union[str, None], Union[str, None]], Union[Response, bool, List[str]]],
        - get_user_status: Callable[[str, Events], Response]
        """
        final_name = name if name is not None else callback.__name__
        self.callbacks[final_name] = callback
        logger.debug(
            f"Callback registered with the name \"{final_name}\"")
    
    def callback(self, name: Optional[str] = None):
        """Registers a callback to the service.
        The following callbacks needed:
        - linking_editor: Callable[[Any, bool], None],
        - get_status: Callable[[], dict],
        - send_message: Callable[[Message], Response],
        - get_user: Callable[[str], Response],
        - is_admin: Callable[[str], Response],
        - voice_connection_controll: Callable[[
            VCRequest, Union[str, None], Union[str, None]], Union[Response, bool, List[str]]],
        - get_user_status: Callable[[str, Events], Response]
        """
        def decorator(callback: Callable[..., Any]) -> None:
            self.register_callback(callback, name)
        
        return decorator

    def use_callback(self, name: str, *args, **kwargs) -> Any:
        if (name not in self.callbacks):
            message = f"The following callback was not registered '{name}'"
            logger.error(message)
            raise SyntaxError(message)
        return self.callbacks[name](*args, **kwargs)
