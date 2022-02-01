import subprocess, errno
from platform import system
from os import system as run
from os import path, remove, rename
from sys import argv, gettrace
from time import sleep

def set_log_level():
    level = "DEBUG" if is_debugger() else "INFO"
    with open(path.join("modules", "level"), "w") as f:
        f.write(level)

from modules.logger import logger_class, LEVEL

interpreter = 'python' if system() == 'Windows' else 'python3'
dnull = "NUL" if system() == 'Windows' else "/dev/null"
restart_counter = 0

def is_debugger():
    return gettrace() is not None

logger = logger_class("logs/bot_runner.log", level=LEVEL.DEBUG if is_debugger() else LEVEL.INFO, log_to_console=True, use_caller_name=True, use_file_names=True)

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
    set_log_level()
    param = []
    param.extend(argv[1:])
    if is_debugger(): param.extend(['--nowd', '--api', '--scilent'])
    logger.debug(f"Calling the bot with the following params: {param}")
    server = subprocess.Popen([interpreter, 'bot_core.py', *param])  #Creates a child process with the 'server.py' script
    while server.poll() is None:    #Works while the child process runs
        try:
            if path.exists('Restart'):  #When the server requires a restart
                remove('Restart')
                server.kill()
                while server.poll() is None:
                    pass
                restart_counter += 1
                logger.info(f"Restarting...")
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
            logger.error(f"{ex}")
        finally:
            sleep(1)
    if server.returncode == errno.EPERM:
        logger.warning("Permission error! If this occures more than once, please try to run the program in administrator/root mode")
        logger.info("Installing dependencies...")
        if install_dependencies() == 0:
            logger.info("Dependencies installed!")
        else:
            logger.error("Error in installing dependecies, please install them manually!")

if __name__ == '__main__':
    #Starts the server, while required
    logger.header("Bot runner started")
    while True:
        main()
        logger.warning('Bot killed!')
        ansv = str(input('Do you want to restart the bot? ([Y]/N) ') or 'Y')
        if ansv.upper() == 'N':
            break