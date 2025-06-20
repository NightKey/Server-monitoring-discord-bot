from argparse import ArgumentError
import sys
from typing import List, Optional, Union, Dict
from modules import status, log_level, log_folder
from modules.watchdog import Watchdog
from smdb_logger import Logger
from smdb_api import Message, Attachment, Interface, Response, ResponseCode, Events
from platform import node
from modules.services import LinkingEditorData, Server
from modules.scanner import scann
from modules.voice_connection import VCRequest, VoiceConnection
from threading import Thread
from time import sleep, process_time
import datetime
import psutil
import os
import json
import webbrowser
import asyncio
import logging
import discord
from fuzzywuzzy import fuzz
from connectors import CommandPrivilege, Telegramm

trys = 0
discord_token = ""
reset_time = 2  # hours
process_list = {}
ptime = 0
was_online = False
id = None
logger = Logger("bot.log", log_folder=log_folder, level=log_level,
                log_to_console=True, use_caller_name=True, use_file_names=True)
dc_time = None
bar_size = 18
connections = []
channels = ["commands"]
is_running = True
errors = {}
threads = {}
admins: Dict[str, list] = {}
telegramm_bot: Telegramm = None
telegramm_token: str = ""
loop: asyncio.AbstractEventLoop = None
watchdog: Watchdog = None
server: Server = None
admin_key = None
me: discord.User = None
dev_mode: bool = False


class signals:
    exit = "Exit"
    restart = "Restart"


intents = discord.Intents.default()
intents.members = True
intents.voice_states = True
intents.message_content = True
intents.presences = True
# Creates a client instance using the discord  module
client = discord.Client(heartbeat_timeout=120, intents=intents)
voice_connection: VoiceConnection = None


def play(link):
    """Opens an URL in the default browser
Category: SERVER
    """
    logger.info(f"The url was {link}")
    return webbrowser.open(link)


def signal(what):
    """
    Sends a signal to the runner. It is used to stop the API if it exists.
    """
    try:
        server.run = False
    except:
        pass
    with open(what, 'w') as _:
        pass


def enable_debug_logger():
    _logger = logging.getLogger('discord')
    _logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler(filename=os.path.join(
        'logs', 'discord.log'), encoding='utf-8', mode='w')
    handler.setFormatter(logging.Formatter(
        '%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
    _logger.addHandler(handler)


async def updater(message, _=None):
    """Updates the bot, and restarts it after a successfull update.
Category: BOT
    """
    if message is None or str(message.channel) in channels or str(message.author.id) in admins["discord"]:
        from modules import updater
        os.system("pip3 install --upgrade smdb_api > update.lg")
        os.system("pip3 install --upgrade smdb_logger > update.lg")
        with open("update.lg", "r") as f:
            tmp = f.read(-1).split("\n")
        os.remove("update.lg")
        if len(tmp) > 2 and message is not None:
            await message.channel.send("API updated!")
        if server is not None and message is not None:
            server.request_all_update()
        if updater.main():
            if message is not None:
                await message.channel.send("Restarting...")
            try:
                await client.logout()
            except:
                pass
            signal(signals.restart)
        else:
            if message is not None:
                await message.channel.send('Nothing was updated!')


async def processes(message):
    text = 'Currently running processes:\n'
    text += f"{(chr(96) * 3)}\n"
    for process in psutil.process_iter():
        try:
            if os.path.exists(process.cmdline()[-1]):
                name = os.path.basename(process.cmdline()[-1])
            else:
                name = os.path.basename(process.cmdline()[0])
            if name == "":
                continue
            text += f"{name}\n"
        except:
            pass
        if len(text) > 1900:
            await message.channel.send(f"{text}{chr(96)*3}")
            text = f"{(chr(96) * 3)}\n"
    await message.channel.send(f'{text}{chr(96)*3}')


def get_passcode():
    from hashlib import sha256
    from random import randint
    passcode = ""
    for _ in range(60):
        passcode += chr(randint(33, 126))
    key = sha256(passcode.encode(encoding="utf-8")).hexdigest()
    print(f"Your key is {key}")
    return key


def save_cfg():
    tmp = {"tokens": {"discord": discord_token, "telegramm": telegramm_token}, "id": id, 'connections': connections,
           "admins": admins, "admin key": admin_key}
    with open(os.path.join("data", "bot.cfg"), 'w') as f:
        json.dump(tmp, f)


def load():
    """This function loads in the data, and sets up the program variables.
    In the case of a missing, or corrupt cfg file, this function requests the data's input through console inpt.
    The data is stored in a json like cfg file with the following format:
    {"token":"BOT-TOKEN-HERE", "id":{"bot":BOT-ID-HERE}, [...]}
    """
    if not os.path.exists("data"):
        os.mkdir("data")
    global discord_token  # The discord bot's login tocken
    global id  # The discord bots' ID
    global connections
    global admins
    global admin_key
    global telegramm_token
    logger.debug("Loading data...")
    if os.path.exists(os.path.join("data", "bot.cfg")):
        try:
            should_save = False
            with open(os.path.join("data", "bot.cfg"), "r") as f:
                tmp = json.load(f)
            if ("tokens" not in tmp):
                should_save = True
                discord_token = tmp["token"]
                try:
                    telegramm_token = tmp['telegramm']
                except:
                    telegramm_token = ""
                    logger.warning(
                        "No Telegramm token found, please add a Telegramm token, if you wish to use Telegramm as well.")
                    should_save = True
            else:
                tokens = tmp["tokens"]
                discord_token = tokens["discord"]
                telegramm_token = tokens["telegramm"]
            id = tmp["id"]
            try:
                connections = tmp['connections']
            except:
                connections = []
            admins = tmp["admins"]
            if (isinstance(admins, (list))):
                admins = {"discord": admins, "telegramm": []}
                should_save = True
            try:
                admin_key = tmp['admin key']
            except:
                admin_key = get_passcode()
                should_save = True
            logger.info("Data loading finished!")
            if (should_save):
                logger.info(
                    "Some config data was not found, re-creating the config files")
                save_cfg()
            del tmp
        except Exception as ex:  # incase there is an error, the program deletes the file, and restarts
            from datetime import datetime
            with open("Loading_error", 'a') as f:
                f.write(f"[{datetime.now()}]: {ex}")
            os.remove(os.path.join("data", "bot.cfg"))
            logger.error("Error in cfg file... Restarting")
            signal(signals.restart)
            exit(0)
    else:
        logger.warning("Data not found!")
        discord_token = input("Type in the token: ")
        me = int(input("Type in this bot's user id: "))
        admins = {
            "discord":
            str(input("Type in the admin user's Discord ID, separated by a coma (,): ")).split(
                ','),
            "telegramm":
            str(input(
                "Type in the admin user's Telegramm chat ID, separated by a coma (,): ")).split(',')
        }
        id = me
        save_cfg()
    check_process_list()


def runner(loop: asyncio.AbstractEventLoop) -> None:
    """Runs the needed things in a way, the watchdog can access the bot client."""
    if '--nodcc' not in os.sys.argv and "--remote" not in os.sys.argv:
        start_thread("Disconnect checker")
    if '--nowd' not in os.sys.argv:
        start_thread("Watchdog")
    if "--api" in os.sys.argv and "--remote" not in os.sys.argv:
        start_thread("API Server")
    if "--remote" not in os.sys.argv:
        loop.create_task(start_discord_client(0))
        loop.run_forever()
    else:
        logger.debug("Started in remote mode...")
        logger.debug("Gathering IP and Authentication code")
        ip = port = auth = name = None
        try:
            ip = os.sys.argv[os.sys.argv.index('--ip') + 1]
            port = int(os.sys.argv[os.sys.argv.index('--port') + 1])
            auth = os.sys.argv[os.sys.argv.index('--auth') + 1]
            name = os.sys.argv[os.sys.argv.index('--name') + 1]
            if ip is None or port is None or auth is None or name is None:
                raise ArgumentError(
                    "Ip, Port, Auth and Name is needed for remote mode!")
            from smdb_api import API
            _api = API(name, auth, ip, port)
            _api.validate(10)
            if not _api.valid:
                logger.debug("Validation failed!")
                signal(signals.exit)
            _api.create_function(
                "status", "Scanns the system for the running applications, and creates a message depending on the resoults.\nUsage: &status <long if you want to see the API status too>\nCategory: SOFTWARE")
        except Exception as ex:
            logger.error(f"Exception: {ex}")
            logger.error(f"IP: {ip} Port: {port} Auth: {auth} Name: {name}")
            logger.error("IP and Authentication code needed in remote mode!")
            stop()
            signal(signals.exit)


def stop():
    global is_running
    if voice_connection is not None and voice_connection.is_connected:
        loop.create_task(voice_connection.disconnect(True))
    if was_online:
        logger.info("Sending stop signal to discord...")
        loop.create_task(client.logout())
        loop.create_task(client.close())
        logger.debug("Waiting for discord to close...")
        while not client.is_closed():
            pass
    if watchdog is not None:
        logger.info("Stopping watchdogs")
        watchdog.create_tmp()
        watchdog.stop()
    logger.info("Stopping disconnect checker")
    is_running = False
    if server is not None and server.run:
        server.stop()
    if loop is not None:
        loop.stop()
    if telegramm_bot is not None:
        telegramm_bot.stop()
    signal(signals.exit)


def send_message(msg: Message) -> Response:
    """Callback function to the services.py.
    """
    if msg.channel is None:
        loop.create_task(watchdog.send_msg(msg.content))
        return Response(ResponseCode.Success)
    if (msg.interface == Interface.Discord):
        response = send_discord_message(msg)
    elif (msg.interface == Interface.Telegramm and telegramm_bot is not None):
        response = send_telegramm_message(msg)
    if (response == ResponseCode.Success):
        return Response(ResponseCode.Success)
    elif (response == ResponseCode.NotFound):
        return Response(ResponseCode.BadRequest, response.message)
    elif (response == ResponseCode.Failed):
        return Response(ResponseCode.InternalError, f"{response.message}")


# region DISCORD
def check_process_list():
    """Looks for update in the process list. To lighten the load, it uses the last modified date.
    As a side effect, too frequent updates are not possible.
    """
    if not os.path.exists(os.path.join("data", "process_list.json")):
        with open(os.path.join("data", "process_list.json"), "w") as f:
            f.write("{}")
    mtime = os.path.getmtime(os.path.join("data", "process_list.json"))
    global ptime
    if ptime < mtime:
        global process_list
        logger.debug("Process list update detected!")
        with open(os.path.join("data", "process_list.json"), "r") as f:
            process_list = json.load(f)
        ptime = mtime


def get_status():
    """Callback function for services.py. Returns the bot's inner status"""
    status = {}
    status['Network'] = "Available" if is_running else "Unavailable"
    status["SupportingFunctions"] = {
        name: ("Active" if thread.is_alive() else "Inactive") for name, thread in threads.items()
    }
    try:
        status["Ping"] = int(client.latency*1000)
    except:
        status["Ping"] = 'Nan'
    return status


async def status_check(message: discord.Message, stype="short"):
    """Scanns the system for the running applications, and creates a message depending on the resoults.
Usage: &status <full if you want to see the API status too or module name for specific module status [bot, watchdog, api, host/pc_name]>
Category: SOFTWARE
    """
    color = 0x14f9a2 if not dev_mode else 0x3273e3
    global process_list
    if stype is None:
        stype = "short"
    try:
        channel = message.channel
    except:
        channel = message
    if str(channel) not in channels and isinstance(message, discord.Message) and str(message.author.id) not in admins["discord"]:
        await echo(message)
        return
    if stype.lower() in ["short", "full", "bot"]:
        bot_status = discord.Embed(title="Bot status", color=color)
        bot_status.add_field(name=f"Reconnectoins in the past {reset_time} hours", value=len(
            connections), inline=False)
        for name, thread in threads.items():
            bot_status.add_field(name=name, value=(
                "Active" if thread.is_alive() else "Inactive"))
        bot_status.set_author(name="Night Key", url="https://github.com/NightKey",
                              icon_url="https://avatars.githubusercontent.com/u/8132508?s=400&v=4")

    if stype.lower() in ["short", "full", "watchdog"]:
        process_list = scann(process_list, psutil.process_iter())
        watchdog_status = discord.Embed(
            title="Watched processes' status", color=color)
        for key, value in process_list.items():
            watchdog_status.add_field(name=key, value=(
                "running" if value[0] else "stopped"), inline=True)
            process_list[key] = [False, False]

    if stype.lower() in ["full", "api"]:
        api_server_status = discord.Embed(title="API Status", color=color)
        api_status = server.get_api_status() if server is not None else {
            "API": "Offline"}
        for key, values in api_status.items():
            if values == []:
                continue
            api_server_status.add_field(name=key, value="\u200B", inline=False)
            for item in list(values):
                api_server_status.add_field(
                    value="\u200B", name=item, inline=True)

    pc_name = node()
    if stype.lower() in ["short", "full", "host", pc_name.lower()]:
        host_status = discord.Embed(
            title=f"{pc_name}'s status", color=color)
        host_status.set_footer(text="Created by Night Key @ https://github.com/NightKey",
                               icon_url="https://avatars.githubusercontent.com/u/8132508?s=400&v=4")
        stts = status.get_graphical(bar_size, True)
        # Battery
        battery_values = stts["Battery"]
        if len(battery_values) > 1:
            host_status.add_field(name="Battery", value="Status", inline=False)
            host_status.add_field(name="Battery life", value=battery_values[0])
            host_status.add_field(name="Power status", value=battery_values[1])
            host_status.add_field(name="Status", value=battery_values[2])
        # Memory
        for key in ["RAM", "SWAP"]:
            memory_values = stts[key]
            host_status.add_field(name=key, value="Status", inline=False)
            host_status.add_field(name="Max", value=memory_values[0])
            host_status.add_field(name="Used", value=memory_values[1])
            host_status.add_field(name="Status", value=memory_values[2])
        temp = status.get_temp()
        host_status.add_field(name="Temperature", value=(
            f"{temp}°C" if temp is not None else "Not detected!"))
        # Disks
        disk_status = discord.Embed(
            title=f"{pc_name}'s disk status", color=color)
        for key, value in stts.items():
            if len(value) > 1 and key not in ["Battery", "RAM", "SWAP"]:
                disk_status.add_field(name=key, value="Status", inline=False)
                disk_status.add_field(name="Max", value=value[0])
                disk_status.add_field(name="Free", value=value[1])
                disk_status.add_field(name="Status", value=value[2])

    if stype.lower() in ["short", "full", "bot"]:
        await channel.send(embed=bot_status)

    if stype.lower() in ["short", "full", "watchdog"]:
        await channel.send(embed=watchdog_status)

    if stype.lower() in ["full", "api"] and api_server_status.fields != []:
        await channel.send(embed=api_server_status)

    if stype.lower() in ["short", "full", "host", pc_name.lower()]:
        await channel.send(embed=disk_status)
        await channel.send(embed=host_status)


async def add_process(message, name):
    """Adds a process to the watchlist. The watchdog automaticalli gets updated with the new list.
Usage: &add <existing process name>
Category: BOT
    """
    if str(message.channel) in channels or str(message.author.id) in admins["discord"]:
        global process_list
        process_list[name] = [False, False]
        with open(os.path.join("data", "process_list.json"), "w") as f:
            json.dump(process_list, f)
        await message.channel.send('Process added')


async def remove(message: discord.Message, name):
    """Removes the given program from the watchlist
Usage: &remove <watched process name>
Category: BOT
    """
    if str(message.channel) in channels or str(message.author.id) in admins["discord"]:
        global process_list
        try:
            del process_list[name]
        except:
            await message.channel.send(f"Couldn't delete the '{name}' item.")
        with open(os.path.join("data", "process_list.json"), "w") as f:
            json.dump(process_list, f)

async def decide(message: discord.Message, original: str):
    """Decides between options separated by a coma (,)
Usage: &decide option1,option2,[...]
Category: SERVER
"""
    import random
    options = original.split(',')
    selected = random.choice(options)
    selected.strip(" ")
    tag = "@"
    try:
        await message.delete()
    except discord.Forbidden:
        pass
    await message.channel.send(f"{tag}{message.author.name} choose `{selected.strip(' ')}` from the following: `[{', '.join((option.strip(' ') for option in options))}]`")

async def roll(message, original):
    """Rolls the dice specifyed.
Usage: &roll <(# of dices)d(# of sides) or default 1d20>
Category: SERVER
    """
    import random
    if original is None:
        original = '1d20'
    value = original.split('d')
    if '+' in original:
        value[-1] = value[-1].split('+')[0]
        value.append(original.split('+')[-1])
    num = int(value[0]) if value[0] != "" else 1
    sides = int(value[1])
    addition = int(value[2]) if (len(value) > 2) else None
    if num > 1000 or sides > 10000:
        await message.channel.send("A maximum of 1000 dice with a maximum of 10000 sides are allowed!")
        return
    res = []
    for _ in range(num):
        n = random.randint(1, sides)
        res.append(n)
    tag = ""
    try:
        await message.delete()
        tag = "@"
    except discord.Forbidden:
        pass
    # Add a preferrence setting option for more costumisable bot
    get_addition = f' + {addition}' if addition is not None else ''
    await message.channel.send(f"{tag}{message.author.name}`[{num}d{sides}{get_addition}]` rolled [{'+'.join([str(n) for n in res])}]{get_addition}: {sum(res)+(addition if addition is not None else 0)}")


@client.event
async def on_presence_update(before: discord.Member, after: discord.Member):
    if (before.activity != after.activity):
        server.event_trigger(Events.activity,
                             before.activity.name if before.activity is not None else "None",
                             after.activity.name if after.activity is not None else "None",
                             before.id)
    if (before.status != after.status):
        server.event_trigger(Events.presence_update,
                             before.status.name if before.status is not None else "None",
                             after.status.name if after.status is not None else "None",
                             before.id)


@client.event
async def on_message_edit(before, after):
    await on_message(after)


def offline(online):
    if not online:
        logger.info("Connection lost!")
        global dc_time
        dc_time = datetime.datetime.now()
        watchdog.not_ready()


@client.event
async def on_disconnect():
    try:
        await watchdog.check_connection(offline)
    except Exception as ex:
        errors[datetime.datetime.now(
        )] = f"Exception occured during disconnect event {ex}"


@client.event
async def on_ready():
    """When the client is all set up, this sectio get's called, and runs once.
It does a system scann for the running programs.
    """
    global connections
    connections.append(datetime.datetime.now().timestamp())
    logger.debug('Startup check started')
    start = process_time()
    global was_online
    global me
    me = client.get_user(id)
    # Sets the channel to the first valid channel, and runs a scann.
    for channel in client.get_all_channels():
        if str(channel) not in channels: continue
        if os.path.exists("Offline"):
            with open("Offline", 'r') as f:
                td = f.read(-1)
            os.remove("Offline")
            check_process_list()
            watchdog.was_restarted()
            if '--scilent' not in os.sys.argv:
                difference = datetime.datetime.now() - datetime.datetime.fromtimestamp(float(td))
                await channel.send(f"Bot restarted after being offline for {str(difference).split('.')[0]}")
            was_online = True
        elif not was_online:
            if '--scilent' not in os.sys.argv:
                await channel.send("Bot started")
                check_process_list()
                await status_check(channel)
            was_online = True
        else:
            now = datetime.datetime.now()
            if dc_time is None:
                break
            if (now - dc_time) > datetime.timedelta(seconds=2) and '--scilent' not in os.sys.argv:
                await channel.send("Back online!")
                await channel.send(f"Was offline for {now - dc_time}")
        break
    finish = process_time()
    logger.info('Startup check finished')
    logger.debug(f"Startup check took {finish-start} s")
    watchdog.ready()
    global trys
    trys = 0
    # The bot totally started up, and ready.
    logger.info("Bot started up correctly!")


async def echo(message, _):
    """Responds with 'ping' and shows the current latency, and the PID if the user was an admin
Category: SERVER
    """
    await message.channel.send(f'ping: {int(client.latency*1000)} ms{ f" PID: {os.getpid()}" if str(message.author.id) in admins["discord"] else ""}{" DEV" if dev_mode else ""}')


async def send_link(message, _):
    """Responds with the currently running bot's invite link
Category: SERVER
    """
    try:
        embed = discord.Embed()
        embed.add_field(name="Server monitoring Discord bot",
                        value=f"You can invite this bot to your server on [this](https://discord.com/api/oauth2/authorize?client_id={id}&permissions=3615744&scope=bot) link!")
        embed.add_field(
            name="Warning!", value="This bot only monitors the server it runs on. If you want it to monitor a server you own, visit [this](https://github.com/NightKey/Server-monitoring-discord-bot) link instead!")
        embed.color = 0xFF00F3
        await message.channel.send(embed=embed)
    except Exception as ex:
        errors[datetime.datetime.now(
        )] = f"Exception occured during link sending {ex}"


async def stop_bot(message, _):
    """Stops the bot. To use this command, you need to be an admin, or need to call it from a selected channel!
Category: BOT
    """
    global is_running
    if str(message.channel) in channels or str(message.author.id) in admins["discord"]:
        await message.channel.send("Exiting")
        stop()


class clear_helper:
    def __init__(self, number, user) -> None:
        self.finished = False
        self.number = number
        self.user = user
        self.count = 0
        self.lock = discord.Reaction(
            message=None, data={"count": 1, "me": None}, emoji=str("🔒"))
        self.stop = discord.Reaction(
            message=None, data={"count": 1, "me": None}, emoji=str("🛑"))
        self.bulk = []

    def check(self, message: discord.Message):
        skip = False
        if self.lock in message.reactions:
            skip = True
        if self.stop in message.reactions:
            self.finished = True
        if self.user is not None and message.author != self.user:
            skip = True
        if self.number != None and self.count == self.number:
            self.finished = True
        if not skip and not self.finished:
            self.count += 1
        return not skip and not self.finished

    def add_to_bulk(self, message):
        if len(self.bulk) >= 99:
            self.trigger_bulk(message.channel)
        self.bulk.append(message)

    def trigger_bulk(self, channel: discord.TextChannel):
        if len(self.bulk) == 0:
            return
        loop.create_task(channel.delete_messages(self.bulk))
        self.bulk = []

    def is_finished(self):
        return self.finished or (self.number is not None and self.count == self.number)


async def clear(message: discord.Message, data: None) -> None:
    """Clears all messages from this channel.
Usage: &clear [optionally the number of messages or @user]
Category: SERVER
    """
    user_permissions = message.author.permissions_in(message.channel)
    if (not user_permissions.administrator and not user_permissions.manage_messages):
        return
    user: discord.Member = None
    number: int = None
    if data is not None and "<@" in data:
        user = client.get_user(int(data.replace("<@!", '').replace(">", '')))
    elif data is not None:
        number = int(data)
    helper = clear_helper(number, user)
    try:
        async with message.channel.typing():
            while True:
                history = await message.channel.history(limit=None).flatten()
                for message in history:
                    if helper.check(message):
                        if datetime.datetime.now() - message.created_at < datetime.timedelta(14):
                            helper.add_to_bulk(message)
                        else:
                            helper.trigger_bulk(message.channel)
                            loop.create_task(message.delete())
                    if helper.is_finished():
                        break
                if helper.is_finished() or len(history) == 0:
                    break
    except discord.Forbidden:
        await message.channel.send("I'm afraid, I can't do that.")
    except Exception as ex:
        errors[datetime.datetime.now(
        )] = f'Exception occured during cleaning:\n```{ex}```'
        await message.channel.send("Sorry, something went wrong!")


async def count(message, channel):
    """Counts the messages for every user in a channel's last 1000 messages. The channel can either be given as a tag, or left empty.
Usage: &count <Optionally tagged channel (with  a '#' character before the name)>
Category: SERVER
    """
    if channel is None:
        channel = message.channel
    else:
        channel = client.get_channel(
            int(channel.replace("<#", '').replace(">", "")))
    if channel is None:
        await message.channel.send("Channel is None! The bot probably doesn't have permission to read it.")
        return
    counter = {}
    async for msg in channel.history(limit=1000):
        counter[msg.author] = counter.setdefault(msg.author, 0) + 1
    try:
        message_to_send = f"```\n{channel.name}\n"
    except:
        message_to_send = f"```\nPrivate Channel\n"
    for user, count in counter.items():
        message_to_send += f"{user}: {count}\n"
    message_to_send += "```"
    await message.channel.send(message_to_send)


async def get_api_key(message, name):
    """Creates an API key for the given application name.
Usage: &API <name of the application the key will be created to>
Category: SOFTWARE
    """
    if str(message.channel) in channels or str(message.author.id) in admins["discord"]:
        await message.channel.send(server.get_api_key_for(name) if server is not None else "API is not avaleable")


async def restart(message, _):
    """Restarts the server it's running on. Admin permissions may be needed for this on the host.
To use this command, you need to be an admin, or need to call it from a selected channel!
Category: HARDWARE
    """
    if str(message.channel) not in channels and str(message.author.id) not in admins["discord"]: return
    await message.channel.send("Attempting to restart the pc...")
    try:
        if os.name == 'nt':
            command = "shutdown /r /t 20"
        else:
            command = "shutdown -r -t 20"
        if os.system(command) != 0:
            await message.channel.send("Permission denied!")
        else:
            await message.channel.send("Exiting")
            stop()
    except Exception as ex:
        await message.channel.send(f"Restart failed with the following exception:\n``` {str(ex)}```")


async def send_errors(message, _=None):
    """Sends all stored errors to the channel the command was sent to.
Category: BOT
    """
    if str(message.channel) not in channels and str(message.author.id) not in admins["discord"]: return
    global errors
    msg = ""
    for date, item in errors.items():
        msg += f"{date}: {item}"
    if msg != "":
        await message.channel.send(msg)
    else:
        await message.channel.send("No errors saved")
    errors = {}


async def terminate_process(message: discord.Message, target):
    """Terminates the specified process. (Admin permission may be needed for this)
Usage: &terminate <existing process' name>
Category: SOFTWARE
    """
    if str(message.channel) not in channels and str(message.author.id) not in admins["discord"]: return
    if target not in process_list:
        for p in process_list:
            if target in p:
                target = p
                break
        else:
            await message.channel.send("Target not found, process can't be safely killed!")
            return
    for process in psutil.process_iter():
        try:
            name = os.path.basename(process.cmdline()[-1])
            if name.lower() == target:
                process.kill()
            break
        except Exception as ex:
            errors[datetime.datetime.now()] = f"Exception occured during terminating process '{target}' {ex}"
    else:
        await message.channel.send(f"Error while stopping {target}!\nManual help needed!")


async def open_browser(message, link):
    """Opens a page in the server's browser.
Usage: &open <url to open>
Category: SOFTWARE
    """
    if str(message.channel) in channels or str(message.author.id) in admins["discord"]:
        if play(link):
            await message.channel.send('Started playing the link')
        else:
            await message.channel.send("Couldn't open the link")


async def set_bar(message, value):
    """Sets the bars' widht to the given value in total character number (the default is 25)
Usage: &bar <integer value to change to>
Category: BOT
    """
    if str(message.channel) in channels or str(message.author.id) in admins["discord"]:
        global bar_size
        bar_size = int(value)
        await message.channel.send(f"Barsize set to {bar_size}")


async def locker(message, value):
    """Locks and unlocks the linked message.
Usage: &lock <message_id>
Category: SERVER
    """
    msg = await message.channel.fetch_message(value)
    for reaction in msg.reactions:
        if str(reaction) == str("🔒"):
            async for user in reaction.users():
                await reaction.remove(user)
            return
    await msg.add_reaction("🔒")


async def stop_at(message, value):
    """Creates a stop signal to the clear command on the message linked.
It will stop at that message.
Usage: &end <message_id>
Category: SERVER
    """
    msg = await message.channel.fetch_message(value)
    for reaction in msg.reactions:
        if str(reaction) == str("🛑"):
            async for user in reaction.users():
                await reaction.remove(user)
            return
    await msg.add_reaction("🛑")


async def help(message, what):
    """Returns the help text for the avaleable commands
Usage: &help <optionaly a specific without the '&' character>
Category: BOT
    """
    is_admin = (str(message.channel) in channels or str(
        message.author.id) in admins["discord"])
    if what == None:
        embed = discord.Embed(
            title="Help", description=f"Currently {len(linking.keys())+len(outside_options.keys())} commands and {len(categories.keys())} categories are avaleable", color=0x0083fb)
        embed.set_author(name="Night Key", url="https://github.com/NightKey",
                         icon_url="https://avatars.githubusercontent.com/u/8132508?s=400&v=4")
        for key, value in categories.items():
            embed.add_field(name=key, value=value, inline=False)
    elif what == 'all':
        embed = discord.Embed(
            title="Help", description=f"Showing all commands!", color=0x0083fb)
        embed.set_author(name="Night Key", url="https://github.com/NightKey",
                         icon_url="https://avatars.githubusercontent.com/u/8132508?s=400&v=4")
        for key, value in linking.items():
            if value[1] and not is_admin:
                continue
            add = False
            txt = value[0].__doc__
            tmp = txt.split("\n")
            for a in tmp:
                if "Usage: " in a:
                    key = a.replace("Usage: &", '')
                try:
                    tmp.remove(f"Usage: &{key}")
                except:
                    pass
            txt = "\n".join(tmp)
            embed.add_field(name=key, value=txt, inline=False)
        if is_admin:
            embed.add_field(name='Added options', value='\u200B', inline=False)
            line = len(embed.fields)
            for key, value in outside_options.items():
                add = False
                txt = value.__doc__
                tmp = txt.split("\n")
                for a in tmp:
                    if "Usage: " in a:
                        key = a.replace("Usage: &", '')
                    try:
                        tmp.remove(f"Usage: &{key}")
                    except:
                        pass
                txt = "\n".join(tmp)
                embed.add_field(name=key, value=txt, inline=False)
            if len(embed.fields) == line:
                embed.remove_field(line-1)
    elif what.upper() in categories:
        embed = discord.Embed(title=f"Help for the {what.upper()} category",
                              description=f"Currently {len(linking.keys())+len(outside_options.keys())} commands and {len(categories.keys())} categories are avaleable", color=0x0083fb)
        embed.set_author(name="Night Key", url="https://github.com/NightKey",
                         icon_url="https://avatars.githubusercontent.com/u/8132508?s=400&v=4")
        for key, value in linking.items():
            if value[1] and not is_admin:
                continue
            add = False
            txt = value[0].__doc__
            tmp = txt.split("\n")
            for a in tmp:
                if "Usage: " in a:
                    key = a.replace("Usage: &", '')
                elif 'Category: ' in a:
                    if a.replace('Category: ', '').upper() == what.upper():
                        add = True
            if add:
                try:
                    tmp.remove(f"Usage: &{key}")
                except:
                    pass
                txt = "\n".join(tmp)
                embed.add_field(name=key, value=txt, inline=False)
        if is_admin:
            embed.add_field(name='Added options', value='\u200B', inline=False)
            line = len(embed.fields)
            for key, value in outside_options.items():
                add = False
                txt = value.__doc__
                tmp = txt.split("\n")
                for a in tmp:
                    if "Usage: " in a:
                        key = a.replace("Usage: &", '')
                    elif 'Category: ' in a:
                        if a.replace('Category: ', '').upper() == what.upper():
                            add = True
                if add:
                    try:
                        tmp.remove(f"Usage: &{key}")
                    except:
                        pass
                    txt = "\n".join(tmp)
                    embed.add_field(name=key, value=txt, inline=False)
            if len(embed.fields) == line:
                embed.remove_field(line-1)
    elif f"{what}" in linking.keys():
        if linking[what][1] and is_admin:
            embed = discord.Embed(
                title=f"Help for the {what} command", description=linking[what][0].__doc__, color=0xb000ff)
            embed.set_author(name="Night Key", url="https://github.com/NightKey",
                             icon_url="https://avatars.githubusercontent.com/u/8132508?s=400&v=4")
    elif f"{what}" in outside_options.keys():
        if is_admin:
            embed = discord.Embed(
                title=f"Help for the {what} command", description=outside_options[what].__doc__, color=0xb000ff)
            embed.set_author(name="Night Key", url="https://github.com/NightKey",
                             icon_url="https://avatars.githubusercontent.com/u/8132508?s=400&v=4")
    try:
        await message.channel.send(embed=embed)
    except:
        await message.channel.send(f"{what} was not found!")


async def add_admin(message, key):
    """Adds an admin using either the admin key, or if an admin uses it, and the other is a user, it adds the user as an admin.
Usage: &admin <admin key or mention a user>
Category: BOT
    """
    if key == admin_key and str(message.author.id) not in admins["discord"]:
        admins["discord"].append(str(message.author.id))
        await message.channel.send("You are now an admin!")
        save_cfg()
    elif str(message.author.id) in admins["discord"] and '<@' in key:
        key = key.replace('<@', '').replace(">", '')
        if key not in admins["discord"]:
            admins["discord"].append(key)
            await message.channel.send(f"{str(client.get_user(int(key))).split('#')[0]} is now an admin!")
        else:
            await message.channel.send(f"{str(client.get_user(int(key))).split('#')[0]} is already an admin!")
        save_cfg()


def voice_connection_managger(request: VCRequest, user_id: Union[str, None] = None, path: Union[str, None] = None) -> Response:
    if VCRequest.need_user(request) and user_id is None:
        return Response(ResponseCode.BadRequest, "User needed for this action!")
    if VCRequest.need_path(request) and path is None:
        return Response(ResponseCode.BadRequest, "Path needed for this action!")
    user_as_member: discord.Member = None
    task: asyncio.Task = None
    logger.debug(f"Voice connection request type: {request}")
    if user_id is not None:
        user_as_member = __get_user(user_id)
        if user_as_member is None:
            return Response(ResponseCode.InternalError, "User not found")
        logger.debug(f"Caller: {user_as_member}")
    if request == VCRequest.connect:
        task = loop.create_task(connect_to_user(user_as_member))
    elif request in [VCRequest.disconnect, VCRequest.forceDisconnect]:
        task = loop.create_task(voice_connection.disconnect(
            request == VCRequest.forceDisconnect))
    elif request == VCRequest.play:
        isSuccess = voice_connection.play(path, user=user_as_member)
        return Response(ResponseCode.Success if isSuccess else ResponseCode.Failed)
    elif request == VCRequest.stop:
        isSuccess = voice_connection.stop(user_as_member)
        return Response(ResponseCode.Success if isSuccess else ResponseCode.Failed)
    elif request == VCRequest.skip:
        isSuccess = voice_connection.skip(user_as_member)
        return Response(ResponseCode.Success if isSuccess else ResponseCode.Failed)
    elif request == VCRequest.add:
        isSuccess = voice_connection.add_mp3_file_to_playlist(path)
        return Response(ResponseCode.Success if isSuccess else ResponseCode.Failed)
    elif request == VCRequest.pause:
        isSuccess = voice_connection.pause(user_as_member)
        return Response(ResponseCode.Success if isSuccess else ResponseCode.Failed)
    elif request == VCRequest.resume:
        isSuccess = voice_connection.resume(user_as_member)
        return Response(ResponseCode.Success if isSuccess else ResponseCode.Failed)
    elif request == VCRequest.queue:
        isSuccess = voice_connection.list_queue()
        return Response(ResponseCode.Success if isSuccess else ResponseCode.Failed)
    else:
        return Response(ResponseCode.BadRequest, "Voice connection request was not from the available list!")
    logger.debug("Waiting on task to finish")
    while not task.done():
        sleep(0.1)
    if task.exception() is not None:
        return Response(ResponseCode.InternalError, f"{task.exception()}")
    return Response(ResponseCode.Success)


async def connect_to_user(user: discord.Member) -> None:
    user_vc = user.voice.channel
    logger.debug(f"User voice channel: {user_vc.name}")
    if user_vc is not None:
        await voice_connection.connect(user_vc)


linking = {
    "add": [add_process, True],
    "admin": [add_admin, False],
    "api": [get_api_key, True],
    "bar": [set_bar, True],
    "clear": [clear, False],
    "count": [count, False],
    "end": [stop_at, False],
    "errors": [send_errors, True],
    "exit": [stop_bot, True],
    "help": [help, False],
    "status": [status_check, True],
    "link": [send_link, False],
    "lock": [locker, False],
    "open": [open_browser, True],
    "ping": [echo, False],
    "remove": [remove, True],
    "restart": [restart, True],
    "roll": [roll, False],
    "terminate": [terminate_process, True],
    "update": [updater, True],
    "decide": [decide, False]
}

outside_options = {}

def edit_linking(data: LinkingEditorData, remove=False):
    """Removes an item from linking. Callback function to the services.py."""
    if remove and data in outside_options:
        del outside_options[data.name]
        telegramm_bot.remove_command(data.name)
        return
    outside_options[data.name] = data.callback
    if (data.add_to_telegramm):
        telegramm_bot.register_callback(
            data.callback, 
            data.name, 
            data.needs_input, 
            data.add_button, 
            CommandPrivilege(data.privilage.value)
        )

categories = {
    'HARDWARE': 'Anything that interacts with the host machine.',
    'SERVER': 'Anything that interacts with the discord server.',
    'NETWORK': "Anything that interacts with the host's network.",
    'SOFTWARE': 'Anything that interacts with the programs running on the host machine.',
    'BOT': "Anything that interacts with the bot's workings.",
    'USER': "Anything that interacts with the users.",
    'AUDIO': "Anything that plays audio trugh the bot."
}


def is_admin(uid: str) -> Response:
    return Response(ResponseCode.Success, uid in admins["discord"])


def get_user(uid: int) -> Response:
    user = __get_user(uid)
    return Response(ResponseCode.Success, user.name) if user is not None else Response(ResponseCode.BadRequest, "User not found")


def __get_user(uid: int) -> Union[discord.Member, None]:
    if isinstance(uid, str):
        uid = int(uid)
    for usr in client.get_all_members():
        if usr.id == uid:
            return usr
    return None


@client.event
async def on_message(message: discord.Message):
    """This get's called when a message was sent to the server. It checks for all the usable commands, and executes them, if they were sent to the correct channel.
    """
    global server
    if message.author == me: return
    if not message.content.startswith('&') and message.channel.type != discord.ChannelType.private: return
    splt = message.content.replace('&', '').split(' ')
    cmd = splt[0]
    etc = " ".join(splt[1:]) if len(splt) > 1 else None
    if cmd in linking.keys() or cmd in outside_options.keys():
        await message.add_reaction("dot:577128688433496073")
        try:
            if cmd in linking.keys():
                await linking[cmd][0](message, etc)
            if cmd in outside_options.keys():
                outside_options[cmd](server, Message.create_message(str(message.author.id), etc, str(message.channel.id), [
                                        Attachment(attachment.filename, attachment.url, attachment.size) for attachment in message.attachments], None, Interface.Discord))
        except Exception as ex:
            await message.channel.send(f"Error runnig the '{cmd}' command: {ex}")
        finally:
            return
    mx = {}
    for key in linking.keys():
        tmp = fuzz.ratio(cmd.lower(), key.lower())
        if 'value' not in mx or mx["value"] < tmp:
            mx["key"] = key
            mx["value"] = tmp
    if mx['value'] == 100:
        try:
            await linking[mx["key"]][0](message, etc)
            await message.add_reaction("dot:577128688433496073")
        except Exception as ex:
            await message.channel.send(f"Error runnig the '{cmd}' command: {ex}\nInterpreted command: {mx['key']}")
        finally:
            return
    for key in outside_options.keys():
        tmp = fuzz.ratio(cmd.lower(), key.lower())
        if 'value' not in mx or mx["value"] < tmp:
            mx["key"] = key
            mx["value"] = tmp
    if 'value' in mx and mx['value'] == 100:
        try:
            outside_options[mx["key"]](server, Message.create_message(str(message.author.id), etc, str(message.channel.id), [
                Attachment(attachment.filename, attachment.url, attachment.size) for attachment in message.attachments], None, Interface.Discord))
            await message.add_reaction("dot:577128688433496073")
        except Exception as ex:
            await message.channel.send(f"Error runnig the '{cmd}' command: {ex}\nInterpreted command: {mx['key']}")
        finally:
            return
    if 'value' in mx and mx['value'] > 70:
        await message.add_reaction("👎")
        await message.channel.send(f"Did you mean `{mx['key']}`? Probability: {mx['value']}%")
    else:
        await message.add_reaction("👎")
        await message.channel.send("Not a valid command!\nUse '&help' for the avaleable commands")


def disconnect_check(loop: asyncio.BaseEventLoop, channels):
    """Restarts the bot, if the disconnected time is greater than one hour"""
    setup = False
    channel = None
    while is_running:
        if not setup:
            global connections
            channel = None
            high_ping_count = 0
            for channel in client.get_all_channels():
                if str(channel) in channels:
                    break
        if was_online and dc_time != None:
            if (datetime.datetime.now() - dc_time) > datetime.timedelta(hours=1):
                logger.warning('Offline for too long. Restarting!')
                save_cfg()
                loop.create_task(client.logout())
                loop.create_task(client.close())
                while not client.is_closed():
                    pass
                watchdog.create_tmp()
                with open("Offline", "w") as f:
                    f.write(str(dc_time.timestamp()))
                signal(signals.restart)
                exit(0)
        if len(connections) > 0 and (datetime.datetime.now() - datetime.datetime.fromtimestamp(connections[0])) >= datetime.timedelta(hours=reset_time):
            del connections[0]
        if len(connections) > 50:
            send_raw_message(
                f"{len(connections)} connections reached within {reset_time} hours!", channel)
        if len(connections) > 500:
            enable_debug_logger()
            send_raw_message(
                f"@everyone {len(connections)} connections reached within {reset_time} hours!\nDebugger enabled!", channel)
        if len(connections) > 990:
            send_raw_message(
                f"@everyone {len(connections)} connections reached within {reset_time} hours!\nExiting!", channel, channel)
            loop.create_task(client.logout())
            loop.create_task(client.close())
            while not client.is_closed():
                pass
            signal(signals.exit)
        # client.latency == client.latency - NaN test
        if was_online and float.is_integer(client.latency) and int(client.latency*1000) > 200:
            high_ping_count += 1
            if high_ping_count == 5:
                send_raw_message(
                    f"Warning! Latency is {int(client.latency*1000)} ms!\nIt was abowe 200 ms for over 10 seconds.", channel)
                high_ping_count = 0
        elif high_ping_count != 0:
            high_ping_count - 1
        sleep(2)


def get_current_status(user: Union[discord.Member, int], status_to_check: Events) -> Response:
    if isinstance(user, int):
        user = __get_user(user)
    if user is None:
        return Response(ResponseCode.Failed, "User not found")
    status = (
        user.activity.name if user.activity is not None else None) if status_to_check == Events.activity else f"{user.name}'s status is {user.status.name}"
    return Response(ResponseCode.Success, status)


def get_channel(id: str) -> discord.TextChannel:
    task: asyncio.tasks.Task = loop.create_task(
        __get_channel(id), name="Get text channel")
    while not task.done():
        sleep(0.1)
    if task.exception() is not None:
        raise task.exception()
    return task.result()


async def __get_channel(id: str) -> discord.TextChannel:
    id = int(id)
    try:
        if usr := client.get_user(id):
            if usr.dm_channel is not None:
                return usr.dm_channel
            else:
                try:
                    await usr.create_dm()
                except Exception as ex:
                    logger.error(
                        f"Exception in creating dm channel with user {usr.name}!")
                    raise ex
                return usr.dm_channel
        for chn in client.get_all_channels():
            if chn.id == id:
                return chn
        return None
    except Exception as ex:
        logger.error(
            f"Exception getting channel by id '{id}': {ex}")
        raise ex


def send_raw_message(msg: str, channel: discord.TextChannel, timeout: int = -1):
    task: asyncio.tasks.Task = loop.create_task(_send_message(
        Message("", msg, "", [], ""), channel), name="Send raw message")
    counter = 0
    while not task.done():
        counter += 1
        if counter > timeout * 10:
            task.cancel()
        sleep(0.1)
    if task.exception() is not None:
        logger.error(f"Exception in task: {task.exception()}")
        return Response(ResponseCode.Failed, task.exception())
    if task.cancelled():
        logger.error(f"Sending message timed out in {timeout} seconds")
        return Response(ResponseCode.Failed, f"Timed out after {timeout} seconds")
    return Response(ResponseCode.Success)


def send_discord_message(msg: Message) -> Response:
    chn = get_channel(msg.channel)
    if chn == None:
        return Response(ResponseCode.NotFound, "User or channel not found")
    task: asyncio.tasks.Task = loop.create_task(
        _send_message(msg, chn), name="Send discord message")
    while not task.done():
        sleep(0.1)
    if task.exception() is not None:
        return Response(ResponseCode.Failed, task.exception())
    return Response(ResponseCode.Success)


async def _send_message(msg: Message, channel: discord.TextChannel):
    embed: Union[discord.Embed, None] = None
    try:
        tmp = json.loads(msg.content)
        logger.debug(f"Creating embed with data: {tmp}")
        embed = discord.Embed()
        [embed.add_field(name=key, value=value)
            for key, value in tmp["fields"].items()]
        embed.title = tmp["title"]
        embed.description = "Created using SMDB API"
        embed.color = 0xB200FF
        embed.set_author(name="Night Key", url="https://github.com/NightKey",
                         icon_url="https://avatars.githubusercontent.com/u/8132508?s=400&v=4")
    except:
        pass
    if 0 < len(msg.attachments) < 10:
        try:
            if embed is not None:
                await channel.send(embed=embed, files=[discord.File(attachment.url, attachment.filename) for attachment in msg.attachments])
            else:
                await channel.send(msg.content, files=[discord.File(attachment.url, attachment.filename) for attachment in msg.attachments])
        except discord.errors.HTTPException as ex:
            if ex.status == 413:
                await channel.send("File too big!")
            else:
                raise ex
        return
    if embed is not None:
        await channel.send(embed=embed)
    else:
        await channel.send(msg.content)


def start_thread(name):
    global threads
    if name == "Watchdog":
        threads[name] = Thread(target=watchdog.run_watchdog, args=[channels, ])
    elif name == "API Server":
        threads[name] = Thread(target=server.start)
    elif name == "Disconnect checker":
        threads[name] = Thread(target=disconnect_check,
                               args=[loop, channels, ])
    threads[name].name = name
    threads[name].start()


def halth(counter: int) -> bool:
    return counter >= 3


async def start_discord_client(counter: int) -> None:
    while True:
        try:
            logger.info("Starting Discord client")
            await client.start(discord_token)
            break
        except TypeError as te:
            logger.error("Type error occured while starting client")
            logger.debug(f"{te}")
            logger.debug("Closing client")
            await client.close()
            stop()
            break
        except discord.errors.DiscordServerError as dse:
            logger.error("Discord server error occured while starting client")
            logger.debug(f"{dse}")
            logger.debug("Closing client")
            await client.close()
            stop()
        except Exception as ex:
            logger.error(
                f"An Exception with a type '{type(ex)}' occured while startig client")
            logger.debug(f"{ex}")
            logger.debug("Closing client")
            await client.close()
            if halth(counter):
                stop()
                break
            else:
                await start_discord_client(counter+1)
# endregion


# region TELEGRAMM
def create_telegramm():
    global telegramm_bot
    telegramm_bot = Telegramm(telegramm_token, log_level, log_folder)

    @telegramm_bot.callback("is_admin", accessable_to_user=False)
    def is_telegram_admin(telegramm_id: int) -> bool:
        return telegramm_id in admins["telegramm"]

    @telegramm_bot.callback(accessable_to_user=False)
    def check_admin_password(key: str) -> bool:
        return key == admin_key

    @telegramm_bot.callback("add_admin", accessable_to_user=False)
    def add_telegramm_admin(telegramm_id: int) -> bool:
        if (telegramm_id in admins["telegramm"]):
            return False
        admins["telegramm"].append(telegramm_id)
        save_cfg()
        return True

    @telegramm_bot.callback(accessable_to_user=False)
    def send_status() -> str:
        host_status = ""
        stts = status.get_graphical(int(bar_size/2), True)
        for key, value in stts.items():
            val = ("Status" if len(value) > 1 else value[0])
            host_status += f"{key} {val}\n"
            if len(value) > 1 and key != "Battery":
                host_status += f'Max: {value[0]}\n'
                host_status += f'{"Used" if key in ["RAM", "SWAP"] else "Free"}: {value[1]}\n'
                host_status += f'Status: {value[2]}\n'
            elif len(value) > 1:
                host_status += f"Battery life: {value[0]}\n"
                host_status += f"Power status: {value[1]}\n"
                host_status += f"Status: {value[2]}\n"
            host_status += "========================\n"
        temp = status.get_temp()
        host_status += f'Temperature: {(f"{temp}°C" if temp is not None else "Not detected!")}'
        return host_status

    @telegramm_bot.callback(show_button=True, privilege=CommandPrivilege.OnlyAdmin)
    def wake(id: int, _) -> None:
        if ("wake" in outside_options):
            outside_options["wake"](server, Message.create_message(
                str(id), "wake", str(id), [], None, Interface.Telegramm))

    @telegramm_bot.callback(show_button=True, privilege=CommandPrivilege.OnlyAdmin)
    def shutdown(id: int, options: Optional[str]) -> None:
        command = "shutdown"
        if (options is not None):
            command += f" {options}"
        if ("shutdown" in outside_options):
            outside_options["shutdown"](server, Message.create_message(
                str(id), command, str(id), [], None, Interface.Telegramm))

    telegramm_bot.start()


def send_telegramm_message(msg: Message) -> Response:
    if (telegramm_bot is None):
        return Response(ResponseCode.Failed, "Telegramm API is not initialized!")
    telegramm_bot.send_message(msg.channel, msg.content)
    return Response(ResponseCode.Success)
# endregion

def create_server():
    global server
    server = Server()
    server.register_callback(edit_linking, "linking_editor")
    server.register_callback(get_status)
    server.register_callback(send_message)
    server.register_callback(get_user)
    server.register_callback(is_admin)
    server.register_callback(voice_connection_managger, "voice_connection_controll")
    server.register_callback(get_current_status, "get_user_status")

def Main(_loop: asyncio.AbstractEventLoop):
    try:
        global loop
        global watchdog
        global server
        global is_running
        global voice_connection
        logger.info('Program started')
        logger.debug("Creating loop")
        loop = _loop
        load()
        if '--al' in os.sys.argv:
            logger.info("Starting discord logger")
            enable_debug_logger()
        logger.info('Setting up watchdog')
        watchdog = Watchdog(loop, client, process_list)
        if "--api" in os.sys.argv:
            logger.info("Setting up the services")
            create_server()
        if "--telegramm" in os.sys.argv:
            logger.info("Setting up Telegramm")
            create_telegramm()
            telegramm_bot.start()
        if "--dev" in os.sys.argv:
            global dev_mode
            dev_mode = True
        voice_connection = VoiceConnection(
            loop, server.track_finished if server is not None else None)
        logger.info('Starting all processes')
        runner(loop)
    except Exception as ex:
        _, _, exc_tb = sys.exc_info()
        logger.error(f"{ex} on line {exc_tb.tb_lineno}")
        stop()
        logger.info("Restarting...")
        signal(signals.restart)


if __name__ == "__main__":
    logger.header('STARTUP')
    logger.debug("Creating bot thread...")
    Bot = Thread(target=Main, args=[asyncio.get_event_loop(), ])
    Bot.name = "Bot thread"
    logger.debug("Starting bot thread...")
    Bot.start()
    Bot.join()
