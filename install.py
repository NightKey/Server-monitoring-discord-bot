try:
    import bot_core
except:
    print("Installation failed, please install dependencies.txt")
    exit(-1)
from os import getcwdb
import subprocess

try:
    with open("smdb.service.template", 'r') as f:
        service = f.read(-1)
    service = service.replace(
        "<file_path>", f'{getcwdb().decode("utf-8")}/service.py')
    with open("/etc/systemd/system/smdb.service", "w") as f:
        f.write(service)
    subprocess.call(["sudo", "systemctl", "daemon-reload"])
    subprocess.call(["sudo", "systemctl", "enable", "smdb.service"])
    subprocess.call(["sudo", "systemctl", "start", "smdb.service"])
except Exception as ex:
    print("Service creation failed, please try starting this with sudo!")
