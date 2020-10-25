from . import writer, logger
import socket, select, json
from hashlib import sha256
from sys import getsizeof
from time import sleep, process_time

lg = logger.logger("api_server", folder="logs")

def split(text, error=False, log_only=False, print_only=False):
    """Logs to both stdout and a log file, using both the writer, and the logger module
    """
    if not log_only: writer.write(text)
    if not print_only: lg.log(text, error=error)

writer = writer.writer("API")
print = split   #Changed print to the split function

class server:
    def __init__(self, linking_editor, get_status, send_message, get_user):
        self.clients = {}
        self.run = True
        self.linking_editor = linking_editor
        self.get_status = get_status
        self.send_message = send_message
        self.functions = {}
        self.get_user = get_user
        self._load_settings()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.ip, self.port))
        self.socket_list = [self.socket]

    def change_ip_port(self, ip, port):
        self.ip = ip
        self.port = port
        self.key = self._generate_key()
        self._save_settings()

    def _load_settings(self):
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

    def _generate_key(self):
        return f'{self.ip}{self.port}'

    def _save_settings(self, key="current"):
        from os import path
        settings_path = path.join("data", "server.cfg")
        settings = {}
        if key == "current":
            settings["ip"] = self.ip
            settings["port"] = self.port
            settings["key"] = self.key
        elif key == "default":
            settings["ip"] = '127.0.0.1'
            settings["port"] = 9600
            settings["key"] = '127.0.0.19600'
            self.settings = "default"
        with open(settings_path, "w") as settings_file:
            json.dump(settings, settings_file)


    def get_api_status(self):
        return {"connections":list(self.clients.values()), "commands":list(self.functions.values())}
    
    def start(self):
        """Starts the API server
        """
        self.commands = {
            'Status':self.get_status_command,
            'Send':self.send_command,
            'Create':self.create_command,
            'Remove':self.remove_command,
            'Username':self.return_usrname,
            'Disconnect':self.disconnect
        }
        self.socket.listen()
        print("API Server started")
        self.loop()

    def create_command(self, socket):
        """Creates a command in the discord bot
        """
        data = self.retrive(socket)
        if data is None:
            return
        self.send(self.create_function(self.clients[socket], *data), socket)

    def get_status_command(self, socket):
        """Returns the status to the socket
        """
        status = self.get_status()
        self.send(status, socket)

    def send_command(self, socket):
        """Sends the message retrived from the socket to the bot.
        """
        msg = self.retrive(socket)
        if msg is None:
            return
        self.send(self.send_message(*msg), socket)

    def retrive(self, socket):
        r"""Retrives a message from the socket. Every message is '\n' terminated
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
            print(ex, print_only=True)
            return None
    
    def send(self, msg, socket):
        r"""Sends a message to the socket. Every message is '\n' terminated
        """
        try:
            if isinstance(socket, str):
                for key, value in self.clients.items():
                    if value == socket:
                        socket = key
                        break
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

    def get_api_key_for(self, name):
        """Returns the correct API key for a 'name' named program
        """
        return sha256(f"{self.key}{name}".encode('utf-8')).hexdigest()

    def create_function(self, creator, name, help_text, callback, user_value=0):
        """Creates a function with the given parameters, and stores it in the self.functions dictionary, with the 'name' as key
        user_value: 0 - None, 1 - user_input, 2 - sender name#descriminator, 4 - channel, 3 - 1+2, 5 - 1+4, 6 - 2+4, 7 - 1+2+4
        """
        print(f'Creating function with the name {name}', log_only=True)
        print(f'Creating function with the call back {callback}', log_only=True)
        print(f'Creating function with the creator as {creator}', log_only=True)
        stuff = ''
        stuff += f"self.send(channel, '{creator}')\n    " if user_value in [4, 5, 6, 7] else ''
        stuff += f"self.send(sender, '{creator}')\n    " if user_value in [2, 3, 6, 7] else ''
        stuff += f"self.send(_input, '{creator}')\n    " if user_value in [1,3, 5, 7] else ''
        body = f"""def {name}(self, channel, sender, _input):
    \"\"\"{help_text}\"\"\"
    if _input is None: _input = ""
    self.send('{callback}', '{creator}')
    {stuff}self.send(None, '{creator}')"""
        try:
            exec(body)
        except Exception as ex:
            print(f"\n{body}")
            print(ex)
            return False
        setattr(self, name, locals()[name])
        self.linking_editor([name, getattr(self, name)])
        if creator not in self.functions: self.functions[creator] = []
        self.functions[creator].append(name)
        return True

    def remove_command(self, socket):
        """Removes a function. Removes all functions, if empty message was sent instead of a function name!
        """
        socket.settimeout(2)
        name = self.retrive(socket)
        socket.settimeout(30)
        if not name in self.functions[self.clients[socket]]: name = None
        self.send(self.remove_function(creator=self.clients[socket], name=name), socket)

    def remove_function(self, creator, name=None):
        """Removes a function from the created functions
        """
        try:
            if creator not in self.functions:
                return False
            if name is None:
                for name in self.functions[creator]:
                    delattr(self, name)
                del self.functions[creator]
            else:
                self.linking_editor(name, True)
                delattr(self, name)
                self.functions[creator].remove(name)
            return True
        except Exception as ex:
            print(f"{type(ex)} -> {ex}")

    def return_usrname(self, socket):
        key = self.retrive(socket)
        if key is None:
            return
        self.send(self.get_user(key), socket)

    def loop(self):
        """Handles the clients.
        """
        while self.run:
            read_socket, _, exception_socket = select.select(self.socket_list, [], self.socket_list)
            for notified_socket in read_socket:
                if notified_socket == self.socket:
                    self.new_client()
                else:
                    print(f"Incoming message from {self.clients[notified_socket]}")
                    msg = self.retrive(notified_socket)
                    if msg is None:
                        self.client_lost(notified_socket)
                        continue
                    if msg is not None:
                        self.command_retrived(msg, notified_socket)
                    else:
                        print("Error in retriving message")
            for notified_socket in exception_socket:
                self.client_lost(notified_socket)
        self.socket.close()

    def command_retrived(self, msg, socket):
        """Retrives commands
        """
        if msg not in self.commands:
            self.send('Bad request', socket)
            return
        #print(f'Command: {msg}')
        self.commands[msg](socket)
    
    def disconnect(self, socket):
        reason = self.retrive(socket)
        if reason is not None:
            print(f"{self.clients[socket]} disconnected with the following reason: {reason}")
        else:
            print(f"{self.clients[socket]} disconnected with no reason given.")
        self.client_lost(socket, called=True)

    def client_lost(self, socket, called = False):
        """Handles loosing connections
        """
        if socket not in self.clients: return
        if not called: print(f"{self.clients[socket]} closed connection.")
        if self.remove_function(creator=self.clients[socket]):
            print("Functions removed!", log_only=True)
        del self.clients[socket]
        self.socket_list.remove(socket)
        print("Client removed!", log_only=True)
        if called: socket.close()
        return

    def new_client(self):
        """handles new clinets
        """
        client_socket, client_address = self.socket.accept()
        client_socket.settimeout(30)
        print(f"Incoming connection from {client_address[0]}:{client_address[1]}", log_only=True)
        name = self.retrive(client_socket)
        key = self.retrive(client_socket)
        if key != sha256(f"{self.key}{name}".encode('utf-8')).hexdigest():
            self.send('Denied', client_socket)
            self.send('Bad API Key', client_socket)
            client_socket.close()
            return
        if name in self.clients:
            self.send('Denied', client_socket)
            self.send('Already connected', client_socket)
            client_socket.close()
            return
        self.send('Accepted', client_socket)
        print(f"Adding {name} to the connections", log_only=True)
        self.socket_list.append(client_socket)
        self.clients[client_socket] = name
