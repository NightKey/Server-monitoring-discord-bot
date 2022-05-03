from datetime import datetime
from requests.models import Response
from typing import Any, Callable, Dict, List, Union
from .logger import Logger
from .response import response
from . import log_level, log_folder
from .voice_connection import VCRequest, VCStatus
import socket, select, json, discord
from hashlib import sha256
import os

logger = Logger("api_server.log", log_folder=log_folder, level=log_level, log_to_console=True, use_caller_name=True, use_file_names=True)

class Attachment:
    """Message attachment"""
    def from_json(json: dict) -> "Attachment":
        if json is None: return None
        return Attachment(json["filename"], json["url"], json["size"])
    
    def from_discord_attachment(atch: discord.Attachment) -> "Attachment":
        if atch is None: return None
        return Attachment(atch.filename, atch.url, atch.size)

    def __init__(self, filename: str, url: str, size: int) -> None:
        if not isinstance(size, int): raise AttributeError(f"{type(size)} is not int type")
        self.url = url
        self.filename = filename
        self.size = size

    def size(self) -> int:
        return self.size

    def download(self) -> Response:
        import requests
        return requests.get(self.url)

    def save(self, path: str) -> str:
        if not os.path.exists(path): return ""
        tmp = self.filename
        n = 1
        while os.path.exists(os.path.join(path, tmp)):
            tmp = "".join((".".join(self.filename.split(".")[:-1]), f"({n}).", self.filename.split(".")[-1]))
            n += 1
        self.filename = tmp
        file = self.download()
        with open(os.path.join(path, self.filename), "wb") as f:
            f.write(file.content)
        return os.path.join(path, self.filename)
    
    def to_json(self) -> dict:
        return {"filename":self.filename, "size":self.size, "url":self.url}

class Message:
    """Message object used by the api"""
    def from_json(json) -> "Message":
        msg = Message(json["sender"], json["content"], json["channel"], [Attachment.from_json(attachment) for attachment in json["attachments"]] if json["attachments"] is not None else [], json["called"])
        if "random_id" in json:
            msg.random_id = json["random_id"]
        return msg

    def create_message(sender: str, content: str, channel: str, attachments: List[Attachment], called: str) -> "Message":
        return Message(sender, content if content is not None else "", channel, attachments, called)

    def __init__(self, sender: str, content: str, channel: str, attachments: List[Attachment], called: str) -> None:
        self.sender = sender
        self.content = content
        self.channel = channel
        self.attachments = attachments
        self.called = called
        self.random_id = sha256(f"{sender}{content}{channel}{called}{datetime.now()}".encode("utf-8")).hexdigest()

    def add_called(self, called: str) -> None:
        self.called = called
        
    def has_attachments(self) -> bool:
        return len(self.attachments) > 0

    def to_json(self) -> dict:
        return {"sender":self.sender, "content":self.content, "channel":self.channel, "called":self.called, "attachments":[attachment.to_json() for attachment in self.attachments] if len(self.attachments) > 0 else None, "random_id": self.random_id}

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Message): return False
        return self.sender == other.sender and self.content == other.content and self.channel

class server:
    def __init__(
        self, 
        linking_editor: Callable[[Any, bool], None], 
        get_status: Callable[[], dict],
        send_message: Callable[[Message], bool], 
        get_user: Callable[[str], response], 
        is_admin: Callable[[str], bool], 
        voice_connection_controll: Callable[[VCRequest, Union[str, None], Union[str, None]], Union[response, bool, List[str]]]
    ) -> None:
        self.clients = {}
        self.run = True
        self.linking_editor = linking_editor
        self.get_status = get_status
        self.send_message = send_message
        self.functions = {}
        self.get_user = get_user
        self.is_admin = is_admin
        self._load_settings()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.ip, self.port))
        self.socket_list = [self.socket]
        self.bad_request = response("Bad request", None)
        self.voice_connection_controll = voice_connection_controll
        self.track_finished_socket = None
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
        if not path.exists(settings_path):
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
        return {"connections":list(self.clients.values()), "commands":list(self.functions.values())}
    
    def request_all_update(self) -> None:
        """Requests an update from the all connected clients. This update should request the application used to update itself and the API
        """
        for target in self.socket_list:
            if target == self.socket: continue
            self.send_update_request(target)

    def send_update_request(self, target) -> None:
        """Requests an update from the target. This update should request the application used to update itself and the API
        """
        self.send(Message("0000000000", "", "0000000000", [], "update").to_json(), target)

    def start(self) -> None:
        """Starts the API server
        """
        self.commands = {
            'Status':self.get_status_command,
            'Send':self.send_command,
            'Create':self.create_command,
            'Remove':self.remove_command,
            'Username':self.return_usrname,
            'Disconnect':self.disconnect,
            'Is Admin':self.admin_check,
            'Connect To User': self.connect_to_user,
            'Disconnect From Voice':self.disconnect_from_voice,
            'Play Audio File': self.play_file,
            'Add Audio File': self.add_file,
            'Pause Currently Playing': self.pause_playing,
            'Resume Paused': self.resume_paused,
            'Skip Currently Playing': self.skip_playing,
            'Stop Currently Playing': self.stop_playing,
            'List Queue': self.list_queue,
            'Set As Track Finished': self.set_track_finished_target
        }
        self.socket.listen()
        logger.info("API Server started")
        self.loop()
    
    def _start_for_test(self) -> None:
        self.commands = {
            'Status':self.get_status_command,
            'Send':self.send_command,
            'Create':self.create_command,
            'Remove':self.remove_command,
            'Username':self.return_usrname,
            'Disconnect':self.disconnect,
            'Is Admin':self.admin_check,
            'Connect To User': self.connect_to_user,
            'Disconnect From Voice':self.disconnect_from_voice,
            'Play Audio File': self.play_file,
            'Add Audio File': self.add_file,
            'Pause Currently Playing': self.pause_playing,
            'Resume Paused': self.resume_paused,
            'Skip Currently Playing': self.skip_playing,
            'Stop Currently Playing': self.stop_playing,
            'List Queue': self.list_queue
        }
        self.socket.listen()

    def connect_to_user(self, socket: socket, user: str) -> None:
        self.send(self.voice_connection_controll(VCRequest.connect, user_id=user), socket)
    
    def disconnect_from_voice(self, socket: socket, _) -> None:
        self.send(self.voice_connection_controll(VCRequest.disconnect), socket)
    
    def play_file(self, socket: socket, data: Dict[str, str]) -> None:
        self.send(self.voice_connection_controll(VCRequest.play, user_id=data["User"], path=data["Path"]), socket)
    
    def add_file(self, socket: socket, path: str) -> None:
        self.send(self.voice_connection_controll(VCRequest.add, path=path), socket)

    def pause_playing(self, socket: socket, user: str) -> None:
        self.send(self.voice_connection_controll(VCRequest.pause, user_id=user), socket)
    
    def resume_paused(self, socket: socket, user: str) -> None:
        self.send(self.voice_connection_controll(VCRequest.resume, user_id=user), socket)

    def stop_playing(self, socket: socket, user: str) -> None:
        self.send(self.voice_connection_controll(VCRequest.stop, user_id=user), socket)
    
    def skip_playing(self, socket: socket, user: str) -> None:
        logger.debug("Skip requested")
        self.send(self.voice_connection_controll(VCRequest.skip, user_id=user), socket)
    
    def list_queue(self, socket: socket, _) -> None:
        self.send(self.voice_connection_controll(VCRequest.queue), socket)

    def set_track_finished_target(self, socket: socket, _) -> None:
        self.track_finished_socket = socket
        self.send(response("Accepted"), socket)

    def track_finished(self, track: str) -> None:
        if self.track_finished_socket is not None:
            self.send(Message("Bot", track, None, [], "Track Finished").to_json(), self.track_finished_socket)

    def create_command(self, socket: socket, data: dict) -> None:
        """Creates a command in the discord bot
        """
        if data is None:
            self.send(self.bad_request.create_altered(Data="No data given"), socket)
            return
        self.send(self.create_function(self.clients[socket], *data), socket)

    def get_status_command(self, socket: socket, _) -> None:
        """Returns the status to the socket
        """
        self.send(self.get_status(), socket)

    def send_command(self, socket: socket, msg: str) -> None:
        """Sends the message retrived from the socket to the bot.
        """
        if msg is None:
            self.send(self.bad_request.create_altered(Data="Empty message"), socket)
            return
        message = Message.from_json(msg)
        self.send(self.send_message(message), socket)

    def retrive(self, socket: socket) -> dict:
        r"""Retrives a message from the socket. Every message is '\n' terminated (terminator not included)
        """
        ret = ""
        try:
            while True: 
                size = socket.recv(1).decode('utf-8')
                try: size = int(size)
                except:
                    self.client_lost(socket)
                    return None
                data = socket.recv(size).decode(encoding="utf-8")
                if data == '\n':
                    break
                if data == None:
                    return None
                ret += data
            return json.loads(ret)
        except Exception as ex:
            logger.error(ex)
            return None
    
    def send(self, msg: str, socket: socket) -> None:
        r"""Sends a message to the socket. Every message is '\n' terminated (terminator does not required)
        """
        try:
            if isinstance(socket, str):
                for key, value in self.clients.items():
                    if value == socket:
                        socket = key
                        break
            if isinstance(msg, response):
                msg = json.dumps(msg.__dict__)
            else:
                msg = json.dumps(msg)
            while True:
                tmp = ''
                if len(msg) > 9:
                    tmp = msg[9:]
                    msg = msg[:9]
                socket.send(str(len(msg)).encode(encoding='utf-8'))
                socket.send(msg.encode(encoding="utf-8"))
                if tmp == '': tmp = '\n'
                if msg == '\n': break
                msg = tmp
        except ConnectionError:
            self.client_lost(socket)

    def get_api_key_for(self, name: str) -> str:
        """Returns the correct API key for a 'name' named program
        """
        return sha256(f"{self.key}{name}".encode('utf-8')).hexdigest()

    def admin_check(self, socket: socket, uid: str) -> None:
        if uid is None:
            self.send(self.bad_request.create_altered(Data="No UID was given"), socket)
            return
        self.send(self.is_admin(uid), socket)

    def create_function(self, creator: str, name: str, help_text: str, callback: str) -> response:
        """Creates a function with the given parameters, and stores it in the self.functions dictionary, with the 'name' as key
        """
        logger.debug(f'Creating function with the name {name}')
        logger.debug(f'Creating function with the call back {callback}')
        logger.debug(f'Creating function with the creator as {creator}')
        body = f"""def {name}(self, message):
    \"\"\"{help_text}\"\"\"
    message.add_called('{name}')
    self.send(message.to_json(), '{creator}')"""
        try:
            exec(body)
        except Exception as ex:
            logger.error(f"{body}")
            logger.error(ex)
            return response("Internal error", ex)
        setattr(self, name, locals()[name])
        self.linking_editor([name, getattr(self, name)])
        if creator not in self.functions: self.functions[creator] = []
        self.functions[creator].append(name)
        return response("Success")

    def remove_command(self, socket: socket, name) -> None:
        """Removes a function. Removes all functions, if empty message was sent instead of a function name!
        """
        if not name in self.functions[self.clients[socket]]: name = None
        self.send(self.remove_function(creator=self.clients[socket], name=name), socket)

    def remove_function(self, creator: str, name: str = None) -> response:
        """Removes a function from the created functions
        """
        try:
            if creator not in self.functions:
                return response("Internal error", "Function not found")
            if name is None:
                for name in self.functions[creator]:
                    self.linking_editor(name, True)
                    delattr(self, name)
                del self.functions[creator]
            else:
                self.linking_editor(name, True)
                delattr(self, name)
                self.functions[creator].remove(name)
            return response("Success")
        except Exception as ex:
            logger.error(f"{ex}")
            return response("Internal error", ex)

    def return_usrname(self, socket: socket, uid: str) -> None:
        if uid is None:
            self.send(self.bad_request.create_altered(Data="No UID was given"), socket)
            return
        self.send(self.get_user(uid), socket)

    def stop(self) -> None:
        self.run = False

    def loop(self) -> None:
        """Handles the clients.
        """
        while self.run:
            try:
                read_socket, _, exception_socket = select.select(self.socket_list, [], self.socket_list, 30)
                for notified_socket in read_socket:
                    if notified_socket == self.socket:
                        self.new_client()
                    else:
                        logger.debug(f"Incoming message from {self.clients[notified_socket]}")
                        msg = self.retrive(notified_socket)
                        if msg is None:
                            self.client_lost(notified_socket)
                            continue
                        else:
                            self.command_retrieved(msg, notified_socket)
                for notified_socket in exception_socket:
                    self.client_lost(notified_socket)
            except socket.error: pass
            except Exception as ex: logger.error(f"{ex}")
        self.socket.close()

    def command_retrieved(self, msg: Message, socket: socket) -> None:
        """Retrives commands
        """
        if msg["Command"] not in self.commands or "Value" not in msg.keys():
            self.send(self.bad_request.create_altered(Data="Command is not a valid command" if msg["Command"] not in self.commands else "Value is not present!"), socket)
            return
        #logger.debug(f'Command: {msg}')
        self.commands[msg["Command"]](socket, msg["Value"])
    
    def disconnect(self, socket: socket, reason: str) -> None:
        if reason is not None:
            logger.info(f"{self.clients[socket]} disconnected with the following reason: {reason}")
        else:
            logger.info(f"{self.clients[socket]} disconnected with no reason given.")
        self.client_lost(socket, called=True)

    def client_lost(self, socket: socket, called: str = False) -> None:
        """Handles loosing connections
        """
        if socket not in self.clients: return
        if not called: logger.warning(f"{self.clients[socket]} closed connection.")
        if self.remove_function(creator=self.clients[socket]):
            logger.debug("Functions removed!")
        del self.clients[socket]
        self.socket_list.remove(socket)
        logger.info("Client removed!")
        if called: socket.close()
        return

    def new_client(self) -> None:
        """handles new clinets
        """
        client_socket, client_address = self.socket.accept()
        client_socket.settimeout(30)
        logger.info(f"Incoming connection from {client_address[0]}:{client_address[1]}")
        retrived = self.retrive(client_socket)
        try:
            name, key = retrived['Command'], retrived['Value']
        except:
            self.send(self.bad_request.create_altered(Response="Denied", Data="Bad API protocoll was used!"), client_socket)
            client_socket.close()
            return
        if key != sha256(f"{self.key}{name}".encode('utf-8')).hexdigest():
            self.send(self.bad_request.create_altered(Response="Denied", Data="Bad API Key"), client_socket)
            client_socket.close()
            return
        if name in self.clients:
            self.send(self.bad_request.create_altered(Response="Denied", Data="Already connected"), client_socket)
            client_socket.close()
            return
        self.send(self.bad_request.create_altered(Response="Success"), client_socket)
        logger.debug(f"Adding {name} to the connections")
        self.socket_list.append(client_socket)
        self.clients[client_socket] = name
