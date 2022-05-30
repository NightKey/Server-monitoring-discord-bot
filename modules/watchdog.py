import discord, psutil, os, json
from copy import deepcopy
from smdb_logger import Logger
from .scanner import scann
from . import status, log_level, log_folder
from time import sleep

logger = Logger("watchdog.log", log_folder=log_folder, level=log_level, log_to_console=True, use_caller_name=True, use_file_names=True)

class Watchdog():
    def __init__(self, loop, client, process_list=None):
        self.process_list = deepcopy(process_list)
        self.error = ""
        self.battery_warning = False
        self.temp_warning = False
        self.client = client
        self.loop = loop
        self._ready = False
        self.run = True
        self.high_temp = 80.0
        self.disks = {}
        self.memory = {}
        logger.header("Watchdog initialized")

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
        except: logger.error(f"Failed sending message '{msg}'")

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

    def send_message(self, channel, message):
        self.loop.create_task(channel.send(message))

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
        logger.info("started")
        battery_warning_number = 0
        temp_warning_number = 0
        n = 5
        while self.run:
            self.process_list = scann(self.process_list, psutil.process_iter())
            if n % 2 == 0:
                battery = status.get_battery_status()
                if battery != None:
                    if not battery["power_plugged"] and battery_warning_number >= 300:
                        if not self.battery_warning:
                            if self._ready:
                                logger.debug('Power Disconnected!')
                                self.send_message(channel, f"@everyone The Battery is not plugged in!")
                                self.battery_warning = True
                    elif not battery["power_plugged"]:
                        battery_warning_number += 1
                    elif self.battery_warning:
                        self.battery_warning = False
                    elif battery_warning_number != 0:
                        battery_warning_number = 0
                temp = status.get_temp()
                if temp != None:
                    if not self.temp_warning:
                        if temp > self.high_temp:
                            logger.warning(f'{temp}°C CPU temp detected!')
                            self.send_message(channel, f"@everyone CPU is running hot @ {temp}°C!")
                            self.temp_warning = True
                    else:
                        if temp > self.high_temp:
                            temp_warning_number += 1
                        else:
                            temp_warning_number = 0
                            self.temp_warning = False
                        if temp_warning_number % 150 == 0:
                            logger.warning('CPU temp constantly high!')
                            self.loop.create_task(channel.send(f"@everyone CPU is running hot @ {temp}°C for more than 5 minutes! The server will be hut down in 5 minutes!"))
                if n % 5 == 0:
                    disks = status.get_disk_status()
                    for key, disk in disks.items():
                        percentage = round(disk["percent"], 1)
                        if key in self.disks:
                            if percentage > 99 and percentage > (self.disks[key] + 3):
                                self.send_message(channel, f"@everyone The disk '{key}' is full ({percentage}%)!")
                            elif percentage > 95 and percentage > (self.disks[key] + 3):
                                self.send_message(channel, f"@everyone The disk '{key}' is nearly filled ({percentage}%)!")
                            elif percentage > 90 and percentage > (self.disks[key] + 3):
                                self.send_message(channel, f"@everyone The disk '{key}' is {percentage}% filled!")
                        self.disks[key] = percentage
                    memory = status.get_memory_status()
                    for key, data in memory.items():
                        percentage = round(data["percent"], 1)
                        if key in self.memory:
                            if percentage > 90 and percentage > (self.memory[key] + 3):
                                self.send_message(channel, f"@everyone The {key} is going to be filled! Current status: {percentage}%")
                            if percentage > 85 and percentage > (self.memory[key] + 3):
                                self.send_message(channel, f"@everyone The {key} is {percentage}% filled!")
                        self.memory[key] = percentage
            if n >= 20:
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
                logger.error(self.error)
                if self._ready:
                    self.send_message(channel, f"@everyone\n{self.error}")
                    self.error = ""
            sleep(1)