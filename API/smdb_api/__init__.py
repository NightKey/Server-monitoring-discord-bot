import select, socket, json, threading, random, discord, re
from os import path, devnull, system, remove
from sys import stdout, __stdout__
from time import sleep, time
from typing import Callable

from requests.models import Response

class ValidationError(Exception):
    """Get's raised, when validation failes"""
    def __init__(self, reason: str) -> None:
        self.message=f"Validation failed! Reason: {reason}"

class NotValidatedError(Exception):
    """Get's raised, when trying to communicate with the API server, without validation."""
    def __init__(self) -> None:
        self.message="Can't communicate without validation!"

class ActionFailed(Exception):
    """Get's raised, when an action failes"""
    def __init__(self, action: str) -> None:
        self.message = f"'{action}' failed!'"

class Attachment:
    """Message attachment"""
    def from_json(json: dict):
        if json is None: return None
        return Attachment(json["filename"], json["url"], json["size"])
    
    def from_discord_attachment(atch: discord.Attachment):
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
        if not path.exists(path): return ""
        tmp = self.filename
        n = 1
        while path.exists(path.join(path, tmp)):
            tmp = "".join((".".join(self.filename.split(".")[:-1]), f"({n}).", self.filename.split(".")[-1]))
            n += 1
        self.filename = tmp
        file = self.download()
        with open(path.join(path, self.filename), "wb") as f:
            f.write(file.content)
        return path.join(path, self.filename)
    
    def to_json(self) -> dict:
        return {"filename":self.filename, "size":self.size, "url":self.url}

class Message:
    """Message object used by the api"""
    USER_REGX = r"(<@![0-9]+>){1}"
    def from_json(json):
        return Message(json["sender"], json["content"], json["channel"], [Attachment.from_json(attachment) for attachment in json["attachments"]] if json["attachments"] is not None else [], json["called"])

    def __init__(self, sender: str, content: str, channel: str, attachments: list, called: str) -> None:
        self.sender = sender
        self.content = content
        self.channel = channel
        self.attachments = attachments
        self.called = called

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
        return len(self.attachments) == 1

    def to_json(self) -> dict:
        return {"sender":self.sender, "content":self.content, "channel":self.channel, "called":self.called, "attachments":[attachment.to_json() for attachment in self.attachments] if len(self.attachments) > 0 else None}

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
    def __init__(self, name: str, key: str, ip: str = "127.0.0.1", port: int = 9600, update_function: Callable[[], None] = None) -> None:
        """Initialises an API that connects to the 'ip' ip and to the 'port' port with the 'name' name and the 'key' api key.
        The update_function should be a vfunction to call, when the bot calls for update (usually when the bot is updated). The function should not require input data.
        """
        self.ip = ip
        self.port = port
        self.name = name
        self.key =  key
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.valid = False
        self.call_list = {"update": self.update}
        self.buffer = []
        self.sending = False
        self.running = True
        self.connection_alive = True
        self.initial = True
        self.socket_list = []
        self.created_function_list=[]
        self.create_function_threads = []
        self.update_function = update_function

    def _send(self, msg: str) -> None:
        """Sends a socket message
        """
        msg = json.dumps(msg)
        while True:
            tmp = ''
            if len(msg) > 9:
                tmp = msg[9:]
                msg = msg[:9]
            self.socket.send(str(len(msg)).encode(encoding='utf-8'))
            self.socket.send(msg.encode(encoding="utf-8"))
            if tmp == '': tmp = '\n'
            if msg == '\n': break
            msg = tmp

    def _retrive(self) -> dict:
        """Retrives a socket message
        """
        ret = ""
        try:
            while True: 
                blockPrint()
                size = int(self.socket.recv(1).decode('utf-8'))
                data = self.socket.recv(size).decode('utf-8')
                enablePrint()
                if data == '\n': break
                ret += data
            return json.loads(ret)
        except Exception as ex:
            enablePrint()
            print(f"[_retrive exception]: {ex}")
            return None
    
    def _get_copy_function_list(self):
        ret = []
        for item in self.created_function_list:
            ret.append(item)
        return ret

    def _re_init_commands(self) -> None:
        tmp = self._get_copy_function_list()
        for item in tmp:
            self.create_function(*item)
        del tmp

    def validate(self, timeout: int = -1) -> bool:
        """Validates with the bot, and starts the listener loop, if validation is finished. Returns false, if validation timed out
        Timeout can be set, so it won't halt the program for ever, if no bot is present. (The timeout will only work for the first validation.)
        If the timeout is set to -1, the validation will be in a new thread, and always return true.
        """
        if timeout is not None and timeout == -1:
            tmp = threading.Thread(target=self._validate)
            tmp.name = "Validation"
            tmp.start()
            return True
        else:
            return self._validate(timeout)

    def _validate(self, timeout: int = None) -> bool:
        start = time()
        self.sending = True
        while True:
            try:
                self.socket.connect((self.ip, self.port))
                break
            except: pass
            if (timeout is not None and timeout > 0 and time() - start > timeout) or not self.running:
                return False
        self._send({"Command":self.name, "Value": self.key})
        ansvear = self._retrive()
        if not isinstance(ansvear, dict):
            raise ValueError("Bad value retrived from socket.")
        elif ansvear["Response"] == 'Denied':
            raise ValidationError(ansvear["Data"])
        else:            
            self.valid = True
            self.socket_list.append(self.socket)
            if self.created_function_list != []:
                self.connection_alive = True
                self._re_init_commands()
            if self.initial:
                self.initial = False
                self.th = threading.Thread(target=self._listener)
                self.th.name = "Listener Thread"
                self.th.start()
        self.sending = False
        return True
                
    def is_admin(self, uid: str) -> bool:
        if self.valid:
            self.sending = True
            self._send({"Command":"Is Admin", "Value":uid})
            while self.buffer == []:
                sleep(0.1)
            self.sending = False
            tmp = self.buffer[0]
            self.buffer = []
            if tmp["Response"] == "Success":
                return tmp["Data"]
        else: NotValidatedError()

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
            self._send({"Command":"Status", "Value":None})
            while self.buffer == []:
                sleep(0.1)
            tmp = self.buffer[0]
            self.buffer = []
            self.sending = False
            return tmp
        else: raise NotValidatedError()
    
    def get_username(self, key: str) -> str:
        self.sending = True
        self._send({"Command":'Username', "Value":key})
        while self.buffer == []:
            sleep(0.1)
        self.sending = False
        tmp = self.buffer[0]
        self.buffer = []
        return tmp["Data"] if tmp["Response"] == "Success" else "unknown"

    def send_message(self, message: str, destination: str = None, file_path: str = None) -> bool:
        """Sends a message trough the discord bot.
        """
        msg = Message("API", message, destination, [Attachment(file_path.split("/")[-1], file_path, path.getsize(file_path))] if file_path is not None else [], "API")
        if self.valid:
            self.sending = True
            self._send({"Command":"Send", 'Value': msg.to_json()})
            while self.buffer == []:
                sleep(0.1)
            tmp = self.buffer[0]
            self.buffer = []
            self.sending = False
            if tmp["Response"] == "Bad request": raise ActionFailed(tmp["Data"])
            elif tmp["Response"] == "Internal error": 
                print(f"[Message sending exception] Internal error: {tmp['Data']}")
                return False
            return True
        else: raise NotValidatedError

    def _listener(self) -> None:
        """Listens for incoming messages, and stops when the program stops running
        """
        while self.running:
            while self.valid and self.connection_alive:
                try:
                    read_socket, _, exception_socket = select.select(self.socket_list, [], self.socket_list)
                    if read_socket != []:
                        msg = self._retrive()
                        if msg is None:
                            self.connection_alive = False
                            self.socket.close()
                            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            self.socket_list = []
                            if self.sending:
                                self.buffer.append({"Response":"Internal error", "Data": "Connection closed"})
                        elif self.sending:
                            self.buffer.append(msg)
                        elif not self.sending:
                            message = Message.from_json(msg)
                            if message.called is not None and message.called in self.call_list:
                                call = threading.Thread(target=self.call_list[message.called], args=[message, ])
                                call.name = message.called
                                call.start()
                    if exception_socket != []:
                        self.connection_alive = False
                        self.socket.close()
                        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        self.socket_list = []
                except Exception as ex: print(f"[Listener thread Inner exception]: {ex}")
                sleep(0.2)

            try:
                if self.running: 
                    self._validate()
                    self.connection_alive = True
            except Exception as ex: print(f"[Listener thread Outer exception]: {ex}")

    def close(self, reason: str = None) -> None:
        """Closes the socket, and stops the listener loop.
        """
        if self.valid and self.connection_alive: self._send({"Command":"Disconnect", "Value": reason})
        self.running = False
        self.valid = False
        self.connection_alive = False
        self.sending = False
        self.socket.close()

    def create_function(self, name: str, help_text: str, callback: Callable[[Message], None]) -> None:
        """Creates a function in the connected bot. This function creates a thread so it won't block while it waits for validation from the bot.
        Return order: ChannelID, UserID, UserInput. The returned value depends on the return value, but the order is the same.
        """
        self.create_function_threads.append(threading.Thread(target=self._create_function, args=[name, help_text, callback,]))
        self.create_function_threads[-1].name = f"Create thread for {name}"
        self.create_function_threads[-1].start()

    def _create_function(self, name: str, help_text: str, callback: Callable[[Message], None]) -> None:
        """Creates a function in the connected bot when validated.
        """
        while self.sending:
            sleep(random.randrange(0, 5))
        self.sending = True
        if [name, help_text, callback] not in self.created_function_list:
            self.created_function_list.append([name, help_text, callback])
        if not self.valid: return
        self._send({"Command":"Create", "Value": [name, help_text, name]})
        while self.buffer == []:
            sleep(0.1)
        tmp = self.buffer[0]
        self.buffer = []
        self.sending = False
        if tmp["Response"] == "Success":
            self.call_list[name] = callback
        elif tmp["Response"] == "Internal error": print(f"[_create_function exception] Internal error: {tmp['Data']}")
        else: raise ActionFailed(tmp["Data"])