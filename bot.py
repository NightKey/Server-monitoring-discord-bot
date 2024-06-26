import subprocess
import errno
from platform import system
from os import system as run
from os import path, remove, rename
from sys import argv, gettrace, executable
from time import sleep
from modules import log_level, log_folder
from smdb_logger import Logger


def is_debugger():
    return gettrace() is not None


level = "DEBUG" if is_debugger() else "INFO"
if not path.exists(path.join("configs", "level")):
    with open(path.join("configs", "level"), "w") as f:
        f.write(level)
if not path.exists(path.join("configs", "folder")):
    with open(path.join("configs", "folder"), "w") as f:
        f.write("logs")

dnull = "NUL" if system() == 'Windows' else "/dev/null"
restart_counter = 0

logger = Logger("bot_runner.log", log_folder=log_folder, level=log_level,
                log_to_console=True, use_caller_name=True, use_file_names=True)

def main(param):
    """
    Main loop that handdles starting the server, and deciding what to do after an update.
    """
    global restart_counter
    logger.debug(f"Calling the bot with the following params: {param}")
    # Creates a child process with the 'server.py' script
    server = subprocess.Popen([executable, 'bot_core.py', *param])
    while server.poll() is None:  # Works while the child process runs
        try:
            if path.exists('Restart'):  # When the server requires a restart
                remove('Restart')
                server.kill()
                while server.poll() is None:
                    pass
                restart_counter += 1
                logger.info(f"Restarting...")
                if restart_counter > 2:
                    if path.exists("discord.log"):
                        if path.exists("discord.log.last"):
                            remove("discord.log.last")
                        rename("discord.log", "discord.log.last")
                    server = subprocess.Popen(
                        [executable, 'bot_core.py', '--al', *param])
                else:
                    server = subprocess.Popen(
                        [executable, 'bot_core.py', *param])
            if path.exists('Exit'):
                remove('Exit')
                server.kill()
                while server.poll() is None:
                    pass
            sleep(1)
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
            server.kill()
            while server.poll() is None:
                pass
        except Exception as ex:
            logger.error(f"{ex}")
    if server.returncode == errno.EPERM:
        logger.warning("Permission error! Please use the run.bat/run.sh file")


if __name__ == '__main__':
    # Starts the server, while required
    logger.header("Bot runner started")
    while True:
        params = argv[1:]
        if is_debugger():
            logger.info("Debugger mode")
            params.extend(['--nowd', '--api', '--scilent', "--dev", "--telegramm"])
        main(params)
        logger.warning('Bot killed!')
        ansv = str(input('Do you want to restart the bot? ([Y]/N) ') or 'Y')
        if ansv.upper() == 'N':
            break
