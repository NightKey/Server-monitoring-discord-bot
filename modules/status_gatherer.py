import socket, json
from os import path

ip_range = []
start_ip = '192.168.0'
port = 1286

def init():
    global ip_range
    if not path.exists(path.join("data", "gatherer.cfg")):
        init_range()
        save()
    else: load()

def save():
    with open(path.join("data", "gatherer.cfg"), "wb") as f:
        json.dump([ip_range, start_ip], f)

def load():
    global ip_range
    global start_ip
    with open(path.join("data", "gatherer.cfg"), "rb") as f:
        [ip_range, start_ip] = json.load(f)

def _retrive(socket):
    """Retrives a socket message
    """
    ret = ""
    try:
        while True: 
            size = int(socket.recv(1).decode('utf-8'))
            data = socket.recv(size).decode('utf-8')
            if data == '\n': break
            ret += data
        return json.loads(ret)
    except Exception as ex:
        print(ex)
        return None

def init_range():
    global ip_range
    ip_range = [f'{start_ip}.{last}' for last in range(254)]
    for ip in reversed(ip_range):
        try:
            _socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            _socket.connect((ip, port))
            data = _retrive(_socket)
            if data is None: ip_range.remove(ip)
        except: ip_range.remove(ip)

def gather_status():
    data = {}
    for ip in reversed(ip_range):
        try:
            _socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            _socket.connect((ip, port))
            ret = _retrive(_socket)
            if ret is None: ip_range.remove(ip)
            else: data.update(ret)
        except: ip_range.remove(ip)
    return data