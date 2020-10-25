import discord, psutil, os, json
from copy import deepcopy
from . import writer, logger, status
from .scanner import scann
from time import sleep

lg = logger.logger("watchdog", folder="logs")
def split(text, error=False, log_only=False, print_only=False):
    """Logs to both stdout and a log file, using both the writer, and the logger module
    """
    if not log_only: writer.write(text)
    if not print_only: lg.log(text, error=error)

writer = writer.writer("Watchdog")
print = split   #Changed print to the split function

class watchdog():
    def __init__(self, loop, client, process_list=None):
        self.process_list = deepcopy(process_list)
        self.error = ""
        self.battery_warning = False
        self.client = client
        self.loop = loop
        self._ready = False
        self.run = True

    def was_restarted(self):
        """Updates the restarted state
        """
        self.from_tmp()

    def stop(self):
        self.run = False

    def update_process_list(self, process_list):
        """Updates the process list to the given argument's value.
        """
        tmp = deepcopy(process_list)
        for key, value in tmp.items():
            if key not in self.process_list:
                self.process_list[key] = value
        for key in self.process_list.values():
            if key not in tmp:
                del self.process_list[key]

    def is_ready(self):
        return self._ready

    def ready(self):
        self._ready = True

    def not_ready(self):
        self._ready = False

    async def check_connection(self, call_back):
        try:
            await self.channel.pins()
            call_back(True)
        except discord.HTTPException: call_back(False)

    async def send_msg(self, msg):
        try: await self.channel.send(msg)
        except: print(f"Failed sending message '{msg}'")

    def from_tmp(self):
        """Reads the process list from a file. (Used to handle restarts)
        """
        with open("data/wd_list.json", "r") as f:
            tmp = json.load(f)
        for key, value in tmp.items():
            if key in self.process_list:
                self.process_list[key] = value
        os.remove("data/wd_list.json")

    def create_tmp(self):
        """Saves the process list to a file (Used to handle restarts)
        """
        self.run = False
        with open("data/wd_list.json", "w") as f:
            json.dump(self.process_list, f)

    def run_watchdog(self, channels):
        """This method scanns the system for runing processes, and if no process found, sends a mention message to all of the valid channels.
        This scan runs every 10 secound. And every 50 Secound, the program scanns for updates in the process list.
        """
        while not self._ready: pass
        channel = None
        for channel in self.client.get_all_channels():
            if str(channel) in channels:
                break
        self.channel = channel
        print("started")
        n = 5
        while self.run:
            self.process_list = scann(self.process_list, psutil.process_iter())
            if n % 2 == 0:
                _, _, battery = status.get_pc_status()
                if battery != None:
                    if not battery["power_plugged"]:
                        if not self.battery_warning:
                            if self._ready:
                                print('Power Disconnected!', log_only=True)
                                self.loop.create_task(channel.send(f"@everyone The Battery is not plugged in!"))
                                self.battery_warning = True
                    elif self.battery_warning:
                        self.battery_warning = False
            if n >= 5:
                n = 0
            else:
                n += 1
            for key, value in self.process_list.items():
                if not value[1] and not value[0]:
                    self.error += f"{key} stopped working!\n"    #Adds the process name, to the message
                    self.process_list[key] = [False, True]       #Don't want to send the same process more than once every time it stops
                else:
                    self.process_list[key] = [False, value[1]]
            if self.error != "":
                print(self.error)
                if self._ready:
                    self.loop.create_task(channel.send(f"@everyone\n{self.error}"))
                    self.error = ""