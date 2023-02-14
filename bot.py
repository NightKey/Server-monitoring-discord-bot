import subprocess
import errno
from platform import system
from os import system as run
from os import path, remove, rename
from sys import argv, gettrace
from time import sleep
try:
    from modules import log_level, log_folder
    from smdb_logger import Logger
except:
    run("pip install -r dependencies.txt > remove")
    remove("remove")
    from modules import log_level, log_folder
    from smdb_logger import Logger


def is_debugger():
    return gettrace() is not None


level = "DEBUG" if is_debugger() else "INFO"
with open(path.join("configs", "level"), "w") as f:
    f.write(level)

with open(path.join("configs", "folder"), "w") as f:
    f.write("logs")


interpreter = 'python' if system() == 'Windows' else 'python3'
dnull = "NUL" if system() == 'Windows' else "/dev/null"
restart_counter = 0

logger = Logger("bot_runner.log", log_folder=log_folder, level=log_level,
                log_to_console=True, use_caller_name=True, use_file_names=True)


def install_dependencies(sudo: bool):
    post = " --user" if system() == 'Windows' and sudo else ""
    logger.debug(f"System: {system()}")
    if sudo:
        logger.info("Upgrading pip...")
        run(f"{interpreter} -m pip install{post} --upgrade pip > remove")
    logger.info("Upgrading dependencies...")
    resp = run(
        f"{interpreter} -m pip install{post} --upgrade -r dependencies.txt > remove")
    remove("remove")
    if resp == 0:
        logger.info("Dependencies installed!")
    else:
        logger.error(
            f"Error in installing dependecies, please install them manually!\nUse the following command: {interpreter} -m pip install{post} --upgrade -r dependencies.txt")
    return resp


def main(param):
    """
    Main loop that handdles starting the server, and deciding what to do after an update.
    """
    global restart_counter
    logger.debug(f"Calling the bot with the following params: {param}")
    # Creates a child process with the 'server.py' script
    server = subprocess.Popen([interpreter, 'bot_core.py', *param])
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
                        [interpreter, 'bot_core.py', '--al', *param])
                else:
                    server = subprocess.Popen(
                        [interpreter, 'bot_core.py', *param])
            if path.exists('Exit'):
                remove('Exit')
                server.kill()
                while server.poll() is None:
                    pass
            if path.exists('Update'):
                remove('Update')
                install_dependencies(False)
            sleep(1)
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
            server.kill()
            while server.poll() is None:
                pass
        except Exception as ex:
            logger.error(f"{ex}")
    if server.returncode == errno.EPERM:
        logger.warning(
            "Permission error! If this occures more than once, please try to run the program in administrator/root mode")
        logger.info("Installing dependencies...")
        install_dependencies(True)


if __name__ == '__main__':
    # Starts the server, while required
    logger.header("Bot runner started")
    while True:
        params = argv[1:]
        if is_debugger():
            params.extend(['--nowd', '--api', '--scilent', '--telegramm'])
        main(params)
        logger.warning('Bot killed!')
        ansv = str(input('Do you want to restart the bot? ([Y]/N) ') or 'Y')
        if ansv.upper() == 'N':
            break
