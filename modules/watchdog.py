import discord, psutil, os, json
from . import writer, logger, status
from .scanner import scann
from time import sleep

def split(text, error=False):
    """Logs to both stdout and a log file, using both the writer, and the logger module
    """
    writer.write(text)
    lg = logger.logger("watchdog", folder="logs")
    lg.log(text, error=error)

writer = writer.writer("Watchdog")
print = split   #Changed print to the split function

class watchdog():
    def __init__(self, loop, client, process_list=None):
        self.process_list = process_list
        self.error = ""
        self.battery_warning = False
        self.client = client
        self.loop = loop
        self._ready = False

    def update_process_list(self, new_process_list):
        """Updates the process list to the given argument's value.
        """
        self.process_list = new_process_list

    def ready(self):
        self._ready = True

    def not_ready(self):
        self._ready = False

    def run_watchdog(self, channels):
        """This method scanns the system for runing processes, and if no process found, sends a mention message to all of the valid channels.
        This scan runs every 10 secound. And every 50 Secound, the program scanns for updates in the process list.
        """
        while not self._ready: pass
        channel = None
        for channel in self.client.get_all_channels():
            if str(channel) in channels:
                break
        print("started")
        n = 5
        while True:
            self.process_list = scann(self.process_list, psutil.process_iter())
            if n % 2 == 0:
                _, _, battery = status.get_pc_status()
                if battery != None:
                    if not battery["power_plugged"]:
                        if not self.battery_warning:
                            if self._ready:
                                print('Power Disconnected!')
                                self.loop.create_task(channel.send(f"@here The Battery is not plugged in!"))
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
                    self.loop.create_task(channel.send(f"@here\n{self.error}"))
                    self.error = ""