import subprocess, errno
from platform import system
from os import system as run
from os import path, remove, rename
from sys import argv, gettrace
from time import sleep

interpreter = 'python' if system() == 'Windows' else 'python3'
dnull = "NUL" if system() == 'Windows' else "/dev/null"
restart_counter = 0

def is_debugger():
    return gettrace() is not None

def install_dependencies():
    pre = "sudo " if system() == 'Linux' else ""
    post = " --user" if system() == 'Windows' else ""
    resp = run(f"{pre}{interpreter} -m pip install{post} -r dependencies.txt")
    return resp

def main():
    """
    Main loop that handdles starting the server, and deciding what to do after an update.
    """
    global restart_counter
    param = []
    param .extend(argv[1:])
    if is_debugger(): param.extend(['--nowd', '--api', '--scilent'])
    server = subprocess.Popen([interpreter, 'bot_core.py', *param])  #Creates a child process with the 'server.py' script
    while server.poll() is None:    #Works while the child process runs
        try:
            if path.exists('Restart'):  #When the server requires a restart
                remove('Restart')
                server.kill()
                while server.poll() is None:
                    pass
                restart_counter += 1
                print(f"Restarting...")
                if restart_counter > 2:
                    if path.exists("discord.log"):
                        if path.exists("discord.log.last"): remove("discord.log.last")
                        rename("discord.log", "discord.log.last")
                    server = subprocess.Popen([interpreter, 'bot_core.py', '--al', *param])
                else:
                    server = subprocess.Popen([interpreter, 'bot_core.py', *param])
            if path.exists('Exit'):
                remove('Exit')
                server.kill()
                while server.poll() is None:
                    pass
        except Exception as ex:
            print(f"{type(ex)} -> {ex}")
        finally:
            sleep(0.2)
    if server.returncode == errno.EPERM:
        print("Permission error! If this occures more than once, please try to run the program in administrator/root mode")
        print("Installing dependencies...")
        if install_dependencies() == 0:
            print("Dependencies installed!")
        else:
            print("Error in installing dependecies, please install them manually!")

if __name__ == '__main__':
    #Starts the server, while required
    while True:
        main()
        print('Bot killed!')
        ansv = str(input('Do you want to restart the bot? ([Y]/N) ') or 'Y')
        if ansv.upper() == 'N':
            break