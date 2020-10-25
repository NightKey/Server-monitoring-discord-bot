from sys import getsizeof
import os, sys, select, socket, json, threading
from time import sleep, process_time

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

def blockPrint():
    sys.stdout = open(os.devnull, 'w')

def enablePrint():
    sys.stdout = sys.__stdout__

NOTHING = 0
USER_INPUT = 1
SENDER = 2
CHANNEL = 4

class API:
    """API for the 'Server monitoring Discord bot' application."""
    def __init__(self, name, key, ip="127.0.0.1", port=9600, max_delay = 1):
        """Initialises an API that connects to the 'ip' ip and to the 'port' port with the 'name' name and the 'key' api key
        """
        self.ip = ip
        self.port = port
        self.name = name
        self.key =  key
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.valid = False
        self.call_list = {}
        self.buffer = []
        self.sending = False
        self.running = True
        self.connection_alive = True
        self.max_delay = max_delay
        self.socket_list = []
        self.created_function_list=[]

    def _send(self, msg):
        """Sends a socket message
        """
        msg = json.dumps(msg)
        while True:
            tmp = ''
            if len(msg) > 9:
                tmp = msg[9:]
                msg = msg[:9]
            self.socket._send(str(len(msg)).encode(encoding='utf-8'))
            self.socket._send(msg.encode(encoding="utf-8"))
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
        while not self.connection_alive:
            pass
        from copy import deepcopy
        tmp = deepcopy(self.created_function_list)
        for item in tmp:
            self.create_function(*item)
        del self.tmp
        del tmp

    def validate(self, timeout=None):
        """Validates with the bot, and starts the listener loop, if validation is finished.
        Time out can be set, so it won't halt the program for ever, if no bot is present. (The timeout will only work for the first validation.)
        """
        start = process_time()
        while True:
            try:
                self.socket.connect((self.ip, self.port))
                break
            except ConnectionRefusedError: pass
            if timeout is not None and process_time() - start > timeout:
                return False
        self._send(self.name)
        self._send(self.key)
        ansvear = self._retrive()
        if ansvear == 'Denied':
            reason = self._retrive()
            raise ValidationError(reason)
        elif ansvear == None:
            raise ValueError("Bad value retrived from socket.")
        else:
            self.valid = True
            self.socket_list.append(self.socket)
            if self.connection_alive:
                self.th = threading.Thread(target=self._listener)
                self.th.name = "Listener Thread"
                self.th.start()
            if not self.connection_alive:
                self.tmp = threading.Thread(target=self._re_init_commands)
                self.tmp.start()
                

    def get_status(self):
        """Gets the bot's status
        """
        if self.valid:
            self.sending = True
            self._send("Status")
            while self.buffer == []:
                sleep(0.1)
            tmp = self.buffer[0]
            self.buffer = []
            self.sending = False
            return tmp
        else: raise NotValidatedError()
    
    def get_username(self, key):
        self.sending = True
        self._send('Username')
        self._send(key)
        while self.buffer == []:
            sleep(0.1)
        self.sending = False
        tmp = self.buffer[0]
        self.buffer = []
        return tmp if tmp is not None else "unknown"

    def send_message(self, message, destination=None):
        """Sends a message trough the discord bot.
        """
        if self.valid:
            self.sending = True
            self._send("Send")
            self._send([message, destination])
            while self.buffer == []:
                sleep(0.1)
            tmp = self.buffer[0]
            self.buffer = []
            self.sending = False
            if not tmp: raise ActionFailed("Send message")
        else: raise NotValidatedError()

    def _listener(self):
        """Listens for incoming messages, and stops when the program stops running
        """
        retrived_call=[]
        while self.running:
            while self.valid and self.connection_alive:
                try:
                    read_socket, _, exception_socket = select.select(self.socket_list, [], self.socket_list)
                    if read_socket != []:
                        msg = self._retrive()
                        if self.sending:
                            self.buffer.append(msg)
                        elif msg in self.call_list:
                            retrived_call.append(msg)
                        elif msg is None and retrived_call != []:
                            call = threading.Thread(target=self.call_list[retrived_call[0]], args=[*retrived_call[1:], ])
                            call.name = self.call_list[retrived_call[0]]
                            retrived_call = []
                            call.start()
                        elif retrived_call != []:
                            retrived_call.append(msg)
                        elif msg is None:
                            self.connection_alive = False
                            self.socket.close()
                            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            self.socket_list = []
                    if exception_socket != []:
                        self.connection_alive = False
                        self.socket.close()
                        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        self.socket_list = []
                except: pass

            try:
                if self.running: 
                    self.validate()
                    self.connection_alive = True
            except Exception as ex: print(f"{type(ex)} -> {ex}")

    def close(self, reason=None):
        """Closes the socket, and stops the listener loop.
        """
        self.running = False
        self.valid = False
        self.connection_alive = False
        self._send("Disconnect")
        self._send(reason)
        self.socket.close()

    def create_function(self, name, help_text, callback, return_value=[NOTHING]):
        """Creates a function in the connected bot.
        Return order: ChannelID, UserID, UserInput. The returned value depends on the return value, but the order is the same.
        """
        if self.valid:
            if isinstance(return_value, (tuple, list)):
                self.created_function_list.append([name, help_text, callback, sum(return_value)])
                return_value = sum(return_value)
            self.sending = True
            self._send("Create")
            self._send([name, help_text, name, return_value])
            while self.buffer == []:
                sleep(0.1)
            tmp = self.buffer[0]
            self.buffer = []
            self.sending = False
            if tmp:
                self.call_list[name] = callback
            else: raise ActionFailed("Create")
        else: raise NotValidatedError()

if __name__ == "__main__":
    api = API("Test", "80716cbfd9f90428cd308acc193b4b58519a4f10a7440b97aaffecf75e63ecec")
    input("Press return to start...")
    api.validate()
    print('Validation finished')
    print(api.get_status())
    print('Status finished')
    api.send_message("Test", destination="165892968283242497")
    print('Message finished')
    def sst(usr, msg):
        print(api.get_username(usr))
        print(msg)
        if msg == "": msg = "Empty message"
        api.send_message(msg, usr)
    api.create_function("SuperSecretTest",
    "It's a super secret test option!\nUsage: &SuperSecretTest <You can say aaaanything>\nCategory: SOFTWARE",
    sst, [USER_INPUT, SENDER])
    print('Function created')
    input("Press return to exit")
    api.close("it's the end of the word!")
