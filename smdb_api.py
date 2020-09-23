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

class API:
    """API for the 'Server monitoring Discord bot' application."""
    def __init__(self, name, key, ip="127.0.0.1", port=9600):
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
        self.last_hearth_beat = None

    def send(self, msg):
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

    def retrive(self):
        """Retrives a socket message
        """
        ret = ""
        try:
            blockPrint()
            while True: 
                size = int(self.socket.recv(1).decode('utf-8'))
                data = self.socket.recv(size).decode('utf-8')
                if data == '\n':
                    break
                ret += data
            enablePrint()
            return json.loads(ret)
        except Exception as ex:
            print(ex)
            return None
    
    def validate(self):
        """Validates with the bot, and starts the listener loop, if validation is finished
        """
        while True:
            try:
                self.socket.connect((self.ip, self.port))
                break
            except ConnectionRefusedError: pass
        self.send(self.name)
        self.send(self.key)
        ansvear = self.retrive()
        if ansvear == 'Denied':
            reason = self.retrive()
            raise ValidationError(reason)
        elif ansvear == None:
            raise ValueError("Bad value retrived from socket.")
        else:
            self.socket.setblocking(False)
            self.socket.settimeout(2)
            self.last_hearth_beat = process_time()
            self.valid = True
            self.th = threading.Thread(target=self.listener)
            self.th.name = "Listener Thread"
            self.th.start()

    def get_status(self):
        """Gets the bot's status
        """
        if self.valid:
            self.sending = True
            self.send("Status")
            while self.buffer == []:
                sleep(0.1)
            tmp = self.buffer[0]
            self.buffer = []
            self.sending = False
            return tmp
        else: raise NotValidatedError()
    
    def send_message(self, message, user=None):
        """Sends a message trough the discord bot
        """
        if self.valid:
            self.sending = True
            self.send("Send")
            self.send([message, user])
            while self.buffer == []:
                sleep(0.1)
            tmp = self.buffer[0]
            self.buffer = []
            self.sending = False
            if not tmp: raise ActionFailed("Send message")
        else: raise NotValidatedError()

    def listener(self):
        """Listens for incoming messages, and stops when the program stops running
        """
        while self.running:
            while self.valid and process_time() - self.last_hearth_beat < 0.12:
                if not self.running: break
                msg = self.retrive()
                #print(msg)
                if msg == None: 
                    sleep(0.01)
                    continue
                if msg == "hearth beat":
                    self.last_hearth_beat = process_time()
                if self.sending:
                    self.buffer.append(msg)
                    continue
                if not self.running: break
                msg2 = self.retrive()
                #print(msg2)
                if not self.running or self.sending: break
                if msg in self.call_list:
                    if msg2 == "":
                        self.call_list[msg]()
                    else:
                        self.call_list[msg](msg2)

            if process_time() - self.last_hearth_beat > 0.11:
                self.connection_alive = False
                self.valid = False
                raise ConnectionError("The hearth beat stopped!")

    def close(self):
        """Closes the socket, and stops the listener loop.
        """
        self.socket.close()
        self.running = False

    def create_function(self, name, help_text, call_back, user_value=False):
        """Creates a function in the connected bot.
        """
        if self.valid:
            self.sending = True
            self.send("Create")
            self.send([name, help_text, name, user_value])
            while self.buffer == []:
                sleep(0.1)
            tmp = self.buffer[0]
            self.buffer = []
            self.sending = False
            if tmp:
                self.call_list[name] = call_back
            else: raise ActionFailed("Create")
        else: raise NotValidatedError()

if __name__ == "__main__":
    api = API("Test", "80716cbfd9f90428cd308acc193b4b58519a4f10a7440b97aaffecf75e63ecec")
    input("Press return to start...")
    api.validate()
    print('Validation finished')
    print(api.get_status())
    print('Status finished')
    api.send_message("Test", user="Night Key#7326")
    print('Message finished')
    def sst(msg):
        print(msg)
    api.create_function("SuperSecretTest",
    "It's a super secret test option!\nUsage: &SuperSecretTest <You can say aaaanything>\nCategory: SOFTWARE",
    sst, True)
    print('Function created')
    input("Press return to exit")
    api.close()
