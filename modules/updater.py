from platform import system
from subprocess import Popen, DEVNULL
from time import sleep


def main():
    cmd = []
    cmd.append("update.bat" if system() == "Windows" else "update.sh")
    updater = Popen(cmd, stdout=DEVNULL)
    while updater.poll() is None:
        sleep(.1)
    if updater.returncode == 1: return True
    return False
