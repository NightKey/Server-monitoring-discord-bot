from sys import getsizeof
import os, sys, select, socket, json, threading, random
from time import sleep, time

class ValidationError(Exception):
    """Get's raised, when validation failes"""
    def __init__(self, reason):
        self.message=f"Validation failed! Reason: {reason}"

class NotValidatedError(Exception):
    """Get's raised, when trying to communicate with the API server, without validation."""
    def __init__(self):
        self.message="Can't communicate without validation!"

class ActionFailed(Exception):
    """Get's raised, when an action failes"""
    def __init__(self, action):
        self.message = f"'{action}' failed!'"

class Attachment:
    """Message attachment"""
    def from_json(json):
        if json is None: return None
        return Attachment(json["filename"], json["url"], json["size"])
    
    def from_discord_attachment(atch):
        if atch is None: return None
        return Attachment(atch.filename, atch.url, atch.size)

    def __init__(self, filename, url, size):
        if not isinstance(size, int): raise AttributeError(f"{type(size)} is not int type")
        self.url = url
        self.filename = filename
        self.size = size

    def size(self):
        return self.size

    def download(self):
        import requests
        return requests.get(self.url)

    def save(self, path):
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
    
    def to_json(self):
        return {"filename":self.filename, "size":self.size, "url":self.url}

class Message:
    """Message object used by the api"""
    def from_json(json):
        return Message(json["sender"], json["content"], json["channel"], [Attachment.from_json(attachment) for attachment in json["attachments"]] if json["attachments"] is not None else [], json["called"])

    def __init__(self, sender, content, channel, attachments, called):
        self.sender = sender
        self.content = content
        self.channel = channel
        self.attachments = attachments
        self.called = called

    def add_called(self, called):
        self.called = called
        
    def has_attachments(self):
        return len(self.attachments) > 0

    def to_json(self):
        return {"sender":self.sender, "content":self.content, "channel":self.channel, "called":self.called, "attachments":[attachment.to_json() for attachment in self.attachments] if len(self.attachment) > 0 else None}

def blockPrint():
    sys.stdout = open(os.devnull, 'w')

def enablePrint():
    sys.stdout.close()
    sys.stdout = sys.__stdout__

NOTHING = 0
USER_INPUT = 1
SENDER = 2
CHANNEL = 4

class API:
    """API for the 'Server monitoring Discord bot' application."""
    def __init__(self, name, key, ip="127.0.0.1", port=9600, update_function=None):
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

    def _send(self, msg):
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

    def _retrive(self):
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
            print(ex)
            return None
    
    def _re_init_commands(self):
        from copy import deepcopy
        tmp = deepcopy(self.created_function_list)
        for item in tmp:
            self.create_function(*item)
        del tmp

    def validate(self, timeout=-1):
        """Validates with the bot, and starts the listener loop, if validation is finished. Returns false, if validation timed out
        Time out can be set, so it won't halt the program for ever, if no bot is present. (The timeout will only work for the first validation.)
        If the timeout is set to -1, the validation will be in a new thread, and always return true.
        """
        if timeout is not None and timeout == -1:
            tmp = threading.Thread(target=self._validate)
            tmp.name = "Validation"
            tmp.start()
            return True
        else:
            return self._validate(timeout)

    def _validate(self, timeout=None):
        start = time()
        self.sending = True
        while True:
            try:
                self.socket.connect((self.ip, self.port))
                break
            except ConnectionRefusedError: pass
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
                
    def is_admin(self, uid):
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

    def update(self, _):
        """Trys to update the API with PIP, and calls the given update function if there is one avaleable.
        """
        os.system("pip install --user --upgrade smdb_api")
        if self.update_function is not None:
            self.update_function()

    def get_status(self):
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
    
    def get_username(self, key):
        self.sending = True
        self._send({"Command":'Username', "Value":key})
        while self.buffer == []:
            sleep(0.1)
        self.sending = False
        tmp = self.buffer[0]
        self.buffer = []
        return tmp["Data"] if tmp["Response"] == "Success" else "unknown"

    def send_message(self, message, destination=None):
        """Sends a message trough the discord bot.
        """
        if self.valid:
            self.sending = True
            self._send({"Command":"Send", 'Value': [message, destination]})
            while self.buffer == []:
                sleep(0.1)
            tmp = self.buffer[0]
            self.buffer = []
            self.sending = False
            if tmp["Response"] == "Bad request": raise ActionFailed(tmp["Data"])
            elif tmp["Response"] == "Internal error": 
                print(tmp["Data"])
                return False
            return True
        else: raise NotValidatedError

    def _listener(self):
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
                except Exception as ex: print(f"[Listener thread Inner exception]: {type(ex)} -> {ex}")
                sleep(0.2)

            try:
                if self.running: 
                    self._validate()
                    self.connection_alive = True
            except Exception as ex: print(f"[Listener thread Outer exception]: {type(ex)} -> {ex}")

    def close(self, reason=None):
        """Closes the socket, and stops the listener loop.
        """
        self.running = False
        self.valid = False
        self.connection_alive = False
        self.sending = False
        self._send({"Command":"Disconnect", "Value": reason})
        self.socket.close()

    def create_function(self, name, help_text, callback):
        """Creates a function in the connected bot. This function creates a thread so it won't block while it waits for validation from the bot.
        Return order: ChannelID, UserID, UserInput. The returned value depends on the return value, but the order is the same.
        """
        self.create_function_threads.append(threading.Thread(target=self._create_function, args=[name, help_text, callback,]))
        self.create_function_threads[-1].name = f"Create thread for {name}"
        self.create_function_threads[-1].start()

    def _create_function(self, name, help_text, callback):
        """Creates a function in the connected bot when validated.
        """
        while self.sending:
            sleep(random.randrange(1, 3))
        if [name, help_text, callback] not in self.created_function_list:
            self.created_function_list.append([name, help_text, callback])
        if not self.valid: return
        self.sending = True
        self._send({"Command":"Create", "Value": [name, help_text, name]})
        while self.buffer == []:
            sleep(0.1)
        tmp = self.buffer[0]
        self.buffer = []
        self.sending = False
        if tmp["Response"] == "Success":
            self.call_list[name] = callback
        elif tmp["Response"] == "Internal error": print(tmp["Data"])
        else: raise ActionFailed(tmp["Data"])