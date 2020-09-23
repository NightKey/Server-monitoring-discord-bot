import socket, select
from . import writer, logger
from hashlib import sha256
from sys import getsizeof
import json
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
    def __init__(self, linking_editor, get_status, send_message, ip='127.0.0.1', port=9600):
        self.ip = ip
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.ip, self.port))
        self.socket_list = [self.socket]
        self.clients = {}
        self.key = f"{self.ip}{self.port}"
        self.run = True
        self.linking_editor = linking_editor
        self.get_status = get_status
        self.send_message = send_message
        self.functions = {}
    
    def start(self):
        self.commands = {
            'Status':self.get_status_command,
            'Send':self.send_command,
            'Create':self.create_command
        }
        self.socket.listen()
        print("API Server started")
        self.loop()

    def create_command(self, socket):
        data = self.retrive(socket)
        self.send(self.create_function(self.clients[socket], *data), socket)

    def get_status_command(self, socket):
        status = self.get_status()
        self.send(status, socket)

    def send_command(self, socket):
        msg = self.retrive(socket)
        self.send(self.send_message(*msg), socket)

    def retrive(self, socket):
        ret = ""
        try:
            while True: 
                size = int(socket.recv(1).decode('utf-8'))
                data = socket.recv(size).decode(encoding="utf-8")
                if data == '\n':
                    break
                ret += data
            return json.loads(ret)
        except Exception as ex:
            print(ex, print_only=True)
            return None
    
    def send(self, msg, socket):
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
                if tmp == '': break
                msg = tmp
            msg = '\n'
            socket.send(str(len(msg)).encode(encoding='utf-8'))
            socket.send(msg.encode(encoding="utf-8"))
        except ConnectionError:
            self.client_lost(socket)

    def get_api_key_for(self, name):
        return sha256(f"{self.key}{name}".encode('utf-8')).hexdigest()

    def create_function(self, creator, name, help_text, call_back, user_value=False):
        """Creates a function with the given parameters, and stores it in the self.functions dictionary, with the 'name' as key
        """
        print(f'Creating function with the name {name}')
        print(f'Creating function with the call back {call_back}')
        print(f'Creating function with the creator as {creator}')
        uv=f"self.send(_input, '{creator}')" if user_value else ''
        body = f"""def {name}(self, _input=None):
    \"\"\"{help_text}\"\"\"
    self.send('{call_back}', '{creator}')
    {uv}"""
        try:
            exec(body)
        except Exception as ex:
            print(ex)
            return False
        setattr(self, name, locals()[name])
        self.linking_editor([name, getattr(self, name)])
        if creator not in self.functions: self.functions[creator] = []
        self.functions[creator].append(name)
        return True

    def remove_function(self, creator, name=None):
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

    def hearth_beat(self):
        while self.run:
            start = process_time()
            for client in self.clients:
                self.send('hearth beat', client)
            finish = process_time()
            sleep(10-(finish-start))            

    def loop(self):
        """Handles the clients.
        """
        while self.run:
            read_socket, _, exceptio_socket = select.select(self.socket_list, [], self.socket_list)
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
            for notified_socket in exceptio_socket:
                self.client_lost(notified_socket)
        self.socket.close()

    def command_retrived(self, msg, socket):
        if msg not in self.commands:
            self.send('Bad request', socket)
            return
        print(f'Command: {msg}')
        self.commands[msg](socket)
    
    def client_lost(self, socket):
        print("Connection closed")
        if self.remove_function(self.clients[socket]):
            print("Functions removed!", log_only=True)
        del self.clients[socket]
        self.socket_list.remove(socket)
        return

    def new_client(self):
        client_socket, client_address = self.socket.accept()
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
        print(f"Adding {name} to the connections")
        self.socket_list.append(client_socket)
        self.clients[client_socket] = name