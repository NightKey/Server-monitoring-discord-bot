from modules import log_folder, log_level
from smdb_logger import Logger
from os import path, chdir
from os import system as run
from platform import system
from sys import argv
from bot import main as runner_main

self_path = path.dirname(path.realpath(__file__))
chdir(self_path)

with open(path.join(self_path, "configs", "level"), "w") as f:
    f.write("INFO")

with open(path.join(self_path, "configs", "folder"), "w") as f:
    f.write("Logs" if system() == 'Windows' else "/var/log/smdb")

logger = Logger("service.log", log_folder=log_folder,
                level=log_level, log_to_console=False)


def get_params():
    with open(path.join(self_path, "configs", "params"), "r") as f:
        all = f.read(-1).split('\n')
    param_list = []

    for item in all:
        if item == "" or item[0] == '#':
            continue
        param_value = ""
        for param in item.split(' '):
            if param[0] == "#":
                break
            param_value += f" {param}"
        param_list.append(param_value.strip(" "))

    return param_list


def main():
    logger.info("Starting bot")
    runner_main(get_params())


if __name__ == "__main__":
    main()
