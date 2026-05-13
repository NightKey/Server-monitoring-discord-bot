import sys, random
from sys import argv
from typing import Optional, Union, Dict, List

from modules import status, log_level, log_folder, with_privilege, Category, with_description_and_usage, \
    CommandCallable, Connector, named, Capability, requires_arguments, TODO
from modules.messaging import Reaction, Message, Channel, Embed
from modules.signals import Signals
from modules.user import UserStore, User, Presence
from modules.watchdog import Watchdog
from smdb_logger import Logger
from smdb_api import Interface, Response, ResponseCode, Events, Privilege
from platform import node
from modules.service.server import LinkingEditorData, Server
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
import discord
from fuzzywuzzy import fuzz
from modules.connectors import Telegram


trys = 0
discord_token = ""
reset_time = 2  # hours
process_list = {}
ptime = 0
was_online = False
bot_id: int | None = None
logger = Logger("bot.log", log_folder=log_folder, level=log_level, log_to_console=True, use_caller_name=True, use_file_names=True)
dc_time = None
bar_size = 18
connections = {}
channels = ["commands"]
is_running = True
errors = {}
threads: Dict[str, Thread] = {}
admins: Dict[str, list] = {}
telegramm_bot: Telegram | None = None
telegramm_token: str = ""
loop: asyncio.AbstractEventLoop
watchdog: Watchdog
server: Server
admin_key: str | None = None
dev_mode: bool = False
connectors: Dict[str, Connector] = {}
user_store: UserStore = UserStore()

# Creates a client instance using the discord  module
voice_connection: VoiceConnection | None = None

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

#<editor-fold desc="Remote commands">
@Category.SOFTWARE
@with_description_and_usage(descr="Returns all the running processes on the host.")
@with_privilege(Privilege.Admin)
@named
def show_processes(message: Message):
    text = 'Currently running processes:\n'
    text += f"{(chr(96) * 3)}\n"
    connector_obj = connectors[message.connector]
    for process in psutil.process_iter():
        try:
            if os.path.exists(process.cmdline()[-1]):
                name = os.path.basename(process.cmdline()[-1])
            else:
                name = os.path.basename(process.cmdline()[0])
            if name == "":
                continue
            text += f"{name}\n"
        except Exception:
            pass
        if len(text) > 1900:
            connector_obj.send_message(message.respond_to(sender=connector_obj.me, content=f"{text}{chr(96) * 3}"))
            text = f"{(chr(96) * 3)}\n"
    connector_obj.send_message(message.respond_to(sender=connector_obj.me, content=f'{text}{chr(96) * 3}'))

@Category.BOT
@with_description_and_usage(descr="Updates the bot, and restarts it after a successful update.")
@with_privilege(Privilege.Admin)
@named
def update(message: Message):
    connector_obj = connectors[message.connector]
    from modules import updater
    os.system("pip3 install --upgrade smdb_api > update.lg")
    os.system("pip3 install --upgrade smdb_logger > update.lg")
    with open("update.lg", "r") as f:
        tmp = f.read(-1).split("\n")
    os.remove("update.lg")
    if len(tmp) > 2 and message is not None:
        connector_obj.send_message(message.respond_to(sender=connector_obj.me, content="API updated!"))
    if server is not None and message is not None:
        server.request_all_update()
    if updater.main():
        if message is not None:
            connector_obj.send_message(message.respond_to(sender=connector_obj.me, content="Restarting..."))
        for (name, _connector) in connectors.items():
            _connector.stop()
        signal(Signals.RESTART)
    else:
        if message is not None:
            connector_obj.send_message(message.respond_to(sender=connector_obj.me, content='Nothing was updated!'))

@Category.SOFTWARE
@with_description_and_usage(
    descr="Scans the system for the running applications, and creates a messaging depending on the results.",
    optional_usage="\'full\' if you want to see the API status too or module name for specific module status [bot, watchdog, api, host/pc_name]",
)
@with_privilege(Privilege.Anyone)
@named("status")
def status_check(message: Message):
    connector_obj = connectors[message.connector]
    stype = message.get_arguments() or "short"
    color = 0x14f9a2 if not dev_mode else 0x3273e3
    global process_list
    if stype is None:
        stype = "short"
    if not message.channel.is_admin and message.sender.privilege < Privilege.Admin:
        echo(message, message.connector)
        return

    if stype.lower() in ["short", "full", "bot"]:
        bot_status = Embed(title="Bot status", color=color)
        bot_status.add_field(name=f"Reconnectoins in the past {reset_time} hours", value=len(connections), inline=False)
        for name, thread in threads.items():
            bot_status.add_field(name=name, value=("Active" if thread.is_alive() else "Inactive"))
        bot_status.set_author(name="Night Key", url="https://github.com/NightKey",
                              icon_url="https://avatars.githubusercontent.com/u/8132508?s=400&v=4")

        connector_obj.send_embed(message.channel, bot_status)

    if stype.lower() in ["short", "full", "watchdog"]:
        process_list = scann(process_list, psutil.process_iter())
        watchdog_status = Embed(title="Watched processes' status", color=color)
        for key, value in process_list.items():
            watchdog_status.add_field(name=key, value=(
                "running" if value[0] else "stopped"), inline=True)
            process_list[key] = [False, False]

        connector_obj.send_embed(message.channel, watchdog_status)

    if stype.lower() in ["full", "api"]:
        api_server_status = Embed(title="API Status", color=color)
        api_status = server.get_api_status() if server is not None else {
            "API": "Offline"}
        for key, values in api_status.items():
            if not values:
                continue
            api_server_status.add_field(name=key, value="\u200B", inline=False)
            for item in list(values):
                api_server_status.add_field(
                    value="\u200B", name=item, inline=True)

        connector_obj.send_embed(message.channel, api_server_status)

    pc_name = node()
    if stype.lower() in ["short", "full", "host", pc_name.lower()]:
        host_status = Embed(
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

        connector_obj.send_embed(message.channel, disk_status)
        connector_obj.send_embed(message.channel, host_status)

@Category.BOT
@with_description_and_usage(
    descr="Adds a process to the watchlist. The watchdog automatically gets updated with the new list.",
    required_usage="existing process name"
)
@with_privilege(Privilege.Admin)
@requires_arguments
@named("add")
def add_process(message: Message):
    connector_obj = connectors[message.connector]
    global process_list
    process_list[message.get_arguments()] = [False, False]
    with open(os.path.join("data", "process_list.json"), "w") as f:
        json.dump(process_list, f)
    connector_obj.send_message(message.respond_to(sender=connector_obj.me, content='Process added'))

@Category.BOT
@with_description_and_usage(
    descr="Removes the given program from the watchlist",
    required_usage="watched process name"
)
@with_privilege(Privilege.Admin)
@requires_arguments
@named("remove")
def remove_process(message: Message):
    name = message.get_arguments()
    connector_obj = connectors[message.connector]
    global process_list
    try:
        del process_list[name]
    except:
        connector_obj.send_message(message.respond_to(sender=connector_obj.me, content=f"Couldn't delete the '{name}' item."))
    with open(os.path.join("data", "process_list.json"), "w") as f:
        json.dump(process_list, f)

@Category.SERVER
@with_description_and_usage(
    descr="Decides between options separated by a coma (,)",
    required_usage="option1,option2,[...]"
)
@with_privilege(Privilege.Anyone)
@requires_arguments
@named
def decide(message: Message):
    options = message.get_arguments().split(',')
    selected = random.choice(options)
    selected.strip(" ")
    tag = "@"
    connector_obj = connectors[message.connector]
    try:
        connector_obj.delete_messages(user=None, channel=message.channel, message_ids=[message.id])
    except discord.Forbidden:
        pass
    user_name = connector_obj.get_local_username(message.channel, message.sender)
    connector_obj.send_message(
        message.respond_to(
            sender=connector_obj.me,
            content=f"{tag}{user_name} choose `{selected.strip(' ')}` from the following: `[{', '.join((option.strip(' ') for option in options))}]`"
        )
    )

@Category.SERVER
@with_description_and_usage(
    descr="Rolls the dice specified.",
    optional_usage="(# of dices)d(# of sides) or default 1d20"
)
@with_privilege(Privilege.Anyone)
@named
def roll(message: Message):
    dice = message.get_arguments() or '1d20'
    value = dice.split('d')
    connector_obj = connectors[message.connector]
    if '+' in dice:
        value[-1] = value[-1].split('+')[0]
        value.append(dice.split('+')[-1])
    num = int(value[0]) if value[0] != "" else 1
    sides = int(value[1])
    addition = int(value[2]) if (len(value) > 2) else None
    if num > 1000 or sides > 10000:
        connector_obj.send_message(message.respond_to(sender=connector_obj.me, content="A maximum of 1000 dice with a maximum of 10000 sides are allowed!"))
        return
    res = []
    for _ in range(num):
        n = random.randint(1, sides)
        res.append(n)
    tag = ""
    try:
        connector_obj.delete_messages(user=None, channel=message.channel, message_ids=[message.id])
        tag = "@"
    except discord.Forbidden:
        pass
    # Add a preferrence setting option for more costumisable bot
    user_name = connector_obj.get_local_username(message.channel, message.sender)
    get_addition = f' + {addition}' if addition is not None else ''
    connector_obj.send_message(
        message.respond_to(
            sender=connector_obj.me,
            content=f"{tag}{user_name}`[{num}d{sides}{get_addition}]` rolled [{'+'.join([str(n) for n in res])}]{get_addition}: {sum(res) + (addition if addition is not None else 0)}"
        )
    )

@Category.SERVER
@with_description_and_usage(descr="Responds with 'ping' and shows the current latency, and the PID if the user was an admin")
@with_privilege(Privilege.Anyone)
@named
def echo(message: Message):
    latency = (message.created_at - datetime.datetime.now())
    connector_obj = connectors[message.connector]
    connector_obj.send_message(
        message.respond_to(
            sender=connector_obj.me,
            content=f'ping: {latency.total_seconds() * 1000 + (latency.microseconds / 1000)} ms{f" PID: {os.getpid()}" if message.sender.privilege == Privilege.Admin else ""}{" DEV" if dev_mode else ""}'
        )
    )

@Category.SERVER
@with_description_and_usage(descr="Responds with the currently running bot's invite link")
@with_privilege(Privilege.Anyone)
@named("link")
def send_link(message: Message):
    connector_obj = connectors[message.connector]
    try:
        embed = Embed(color=0xFF00F3)
        embed.add_field(name="Server monitoring Discord bot",
                        value=f"You can invite this bot to your server using [this](https://discord.com/api/oauth2/authorize?client_id={bot_id}&permissions=3615744&scope=bot) link!")
        embed.add_field(name="Warning!",
                        value="This bot only monitors the server it runs on. If you want it to monitor a server you own, visit [this](https://github.com/NightKey/Server-monitoring-discord-bot) link instead!")
        connector_obj.send_embed(message.channel, embed=embed)
    except Exception as ex:
        errors[datetime.datetime.now()] = f"Exception occured during link sending {ex}"

@Category.BOT
@with_description_and_usage(descr="Stops the bot. To use this commands, you need to be an admin, or need to call it from a selected channel!")
@with_privilege(Privilege.Admin)
@named("stop")
def stop_bot(message: Message):
    connector_obj = connectors[message.connector]
    connector_obj.send_message(message.respond_to(sender=connector_obj.me, content="Exiting"))
    stop()

@Category.SERVER
@with_description_and_usage(
    descr="Clears all messages from this channel.",
    optional_usage="the number of messages or @user"
)
@with_privilege(Privilege.Moderator)
@named
def clear(message: Message) -> None:
    connector_obj = connectors[message.connector]
    if Capability.DELETE not in connector_obj.capabilities:
        connector_obj.send_message(message.respond_to(sender=connector_obj.me, content=f"Connector {message.connector} does not support {Capability.DELETE}"))
        return
    connector_obj.delete_messages(user=None, channel=message.channel, message_ids=[message.id])
    if not connector_obj.can_user_use_capability(message.sender, message.channel, Capability.DELETE):
        connector_obj.send_message(message.respond_to(sender=connector_obj.me, content=f"Connector {message.connector} can't delete message."))
        return

    number: int | None = None
    user: str | None = None
    data = message.get_arguments()
    if data is not None and "<@" in data:
        user = user_store.get_for_connector((data.replace("<@!", '').replace(">", '')), message.connector)
    elif data is not None:
        number = int(data)
    helper = ClearHelper(number, user, connector_obj)
    try:
        while True:
            history = connector_obj.get_message_history(user=message.sender, channel=message.channel, count=None)
            for message in history:
                if helper.check(message):
                    if datetime.datetime.now() - message.created_at < datetime.timedelta(14):
                        helper.add_to_bulk(message)
                    else:
                        helper.trigger_bulk(message.channel)
                if helper.is_finished():
                    break
            if helper.is_finished() or len(history) == 0:
                break
    except Exception as ex:
        errors[datetime.datetime.now()] = f'Exception occurred during cleaning:\n```{ex}```'
        connector_obj.send_message(message.respond_to(sender=connector_obj.me, content="Sorry, something went wrong!"))

@Category.SERVER
@with_description_and_usage(
    descr="Bans all users from the provided comma (,) separated list present on this server.",
    required_usage="username/id, ..."
)
@with_privilege(Privilege.Moderator)
@requires_arguments
@named("ban")
def ban_users(message: Message):
    connector_obj = connectors[message.connector]
    connector_obj.can_user_use_capability(message.sender, message.channel, Capability.DELETE)
    users = message.get_arguments().split(",")
    user_names: Dict[str, str] = {}
    for user in users:
        _user = user_store.get_for_connector(user, message.connector)
        user_names[user] = connector_obj.get_local_username(message.channel, _user if _user else User(Privilege.Anyone, {message.connector: user}))
    results = connector_obj.ban_users(message.sender, message.channel, users, f"User {connector_obj.get_local_username(message.channel, message.sender)} invoked a bulk ban!")
    response_message = Embed(title="Banned user(s)")
    for user_id, result in results.items():
        response_message.add_field(name=user_names[user_id] if user_id in user_names else user_id, value="Baned" if result else "Failed to ban", inline=False)
    connector_obj.send_embed(channel=message.channel, embed=response_message)

@Category.SERVER
@with_description_and_usage(
    descr="Counts the messages for every user in a channel's last 1000 messages. The channel can either be given as a tag, or left empty.",
    optional_usage="tagged channel (with  a '#' character before the name)"
)
@with_privilege(Privilege.Moderator)
@named
def count(message: Message):
    connector_obj = connectors[message.connector]
    if message.get_arguments() is not None:
        channel = connector_obj.get_channel(message.sender, message.get_arguments().replace("<#", '').replace(">", ""))
    else:
        channel = message.channel.id

    counter = {}
    for msg in connector_obj.get_message_history(message.sender, Channel(channel, None, False), 1000):
        counter[msg.sender] = counter.setdefault(msg.sender, 0) + 1
    message_to_send = f"```\n{channel.name}\n"
    for user, _count in counter.items():
        message_to_send += f"{user}: {_count}\n"
    message_to_send += "```"
    connector_obj.send_message(message.respond_to(sender=connector_obj.me, content=message_to_send))

@Category.SOFTWARE
@with_description_and_usage(
    descr="Creates an API key for the given application name.",
    required_usage="name of the application the key will be created to"
)
@with_privilege(Privilege.Admin)
@requires_arguments
@named("API")
def get_api_key(message: Message):
    connector_obj = connectors[message.connector]
    connector_obj.send_message(message.respond_to(sender=connector_obj.me, content=server.get_api_key_for(message.get_arguments()) if server is not None else "API is not available"))

@Category.HARDWARE
@with_description_and_usage(descr="Restarts the server it's running on. Admin permissions may be needed for this on the host.")
@with_privilege(Privilege.Admin)
@named("reboot")
def restart_server(message: Message):
    connector_obj = connectors[message.connector]
    connector_obj.send_message(message.respond_to(sender=connector_obj.me, content="Attempting to restart the pc..."))
    try:
        if os.name == 'nt':
            command = "shutdown /r /t 20"
        else:
            command = "shutdown -r -t 20"
        if os.system(command) != 0:
            connector_obj.send_message(message.respond_to(sender=connector_obj.me, content="Permission denied!"))
        else:
            connector_obj.send_message(message.respond_to(sender=connector_obj.me, content="Exiting"))
            stop()
    except Exception as ex:
        connector_obj.send_message(message.respond_to(sender=connector_obj.me, content=f"Restart failed with the following exception:\n``` {str(ex)}```"))

@Category.BOT
@with_description_and_usage(descr="Sends all stored errors to the channel the commands was sent to.")
@with_privilege(Privilege.Admin)
@named("errors")
def send_errors(message: Message):
    connector_obj = connectors[message.connector]
    global errors
    msg = ""
    for date, item in errors.items():
        msg += f"{date}: {item}"
    if msg != "":
        connector_obj.send_message(message.respond_to(sender=connector_obj.me, content=msg))
    else:
        connector_obj.send_message(message.respond_to(sender=connector_obj.me, content="No errors saved"))
    errors = {}

@Category.SOFTWARE
@with_description_and_usage(
    descr="Terminates the specified process. (Admin permission may be needed for this)",
    required_usage="existing process' name"
)
@with_privilege(Privilege.Admin)
@requires_arguments
@named("terminate")
def terminate_process(message: Message):
    connector_obj = connectors[message.connector]
    target = message.get_arguments()
    if target not in process_list:
        for p in process_list:
            if target in p:
                target = p
                break
        else:
            connector_obj.send_message(message.respond_to(sender=connector_obj.me, content="Target not found, process can't be safely killed!"))
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
        connector_obj.send_message(message.respond_to(sender=connector_obj.me, content=f"Error while stopping {target}!\nManual help needed!"))

@Category.SOFTWARE
@with_description_and_usage(descr="Opens a page in the server's browser.", required_usage="url to open")
@with_privilege(Privilege.Admin)
@requires_arguments
@named("open")
def open_browser(message: Message):
    connector_obj = connectors[message.connector]
    if play(message.get_arguments()):
        connector_obj.send_message(message.respond_to(sender=connector_obj.me, content="Started playing the link"))
    else:
        connector_obj.send_message(message.respond_to(sender=connector_obj.me, content="Couldn't open the link"))

@Category.BOT
@with_description_and_usage(
    descr="Sets the bars' width to the given value in total character number (the default is 25)",
    required_usage="integer value to change to"
)
@with_privilege(Privilege.Admin)
@requires_arguments
@named("bar")
def set_bar(message: Message):
    connector_obj = connectors[message.connector]
    global bar_size
    bar_size = int(message.get_arguments())
    connector_obj.send_message(message.respond_to(sender=connector_obj.me, content=f"Bar size set to {bar_size}"))

@Category.SERVER
@with_description_and_usage(descr="Locks and unlocks the linked messaging.", required_usage="message_id")
@with_privilege(Privilege.Moderator)
@requires_arguments
@named
def lock(message: Message):
    connectors[message.connector].toggle_reaction(user=message.sender, channel=message.channel, message_id=message.get_arguments(), reaction="🔒")

@Category.SERVER
@with_description_and_usage(
    descr="Creates a stop signal to the clear commands on the messaging linked. It will stop at that messaging.",
    required_usage="message_id"
)
@with_privilege(Privilege.Moderator)
@requires_arguments
@named("end")
def stop_at(message: Message):
    connectors[message.connector].toggle_reaction(user=message.sender, channel=message.channel, message_id=message.get_arguments(), reaction="🛑")

@Category.BOT
@with_description_and_usage(
    descr="Returns the help text for the available commands",
    optional_usage="a specific command without"
)
@with_privilege(Privilege.Anyone)
@named
def help(message: Message):
    is_admin = message.sender.privilege == Privilege.Admin or message.channel.is_admin
    argument = message.get_arguments()
    connector_object = connectors[message.connector]
    if argument is None:
        embed = Embed(title="Help", description=f"Currently {len(linking)+len(outside_options)} commands and {len(Category.all())} categories are available", color=0x0083fb)
        embed.set_author(name="Night Key", url="https://github.com/NightKey", icon_url="https://avatars.githubusercontent.com/u/8132508?s=400&v=4")
        for __category in Category.all():
            embed.add_field(name=__category.name, value=__category.value, inline=False)
        connector_object.send_embed(message.channel, embed)
    elif argument == 'all':
        embed = Embed(title="Help", description=f"Showing all commands", color=0x0083fb)
        embed.set_author(name="Night Key", url="https://github.com/NightKey", icon_url="https://avatars.githubusercontent.com/u/8132508?s=400&v=4")
        for command in linking:
            if (command.privilege == Privilege.Admin and not is_admin) or command.privilege == Privilege.Internal:
                continue
            txt = "\n".join([command.description, command.usage])
            embed.add_field(name=command.name, value=txt, inline=False)

        connector_object.send_embed(message.channel, embed)

        embed = Embed(title="Help", description=f"Showing all external commands", color=0x0083fb)
        embed.set_author(name="Night Key", url="https://github.com/NightKey", icon_url="https://avatars.githubusercontent.com/u/8132508?s=400&v=4")

        for command in outside_options:
            if (command.privilege == Privilege.Admin and not is_admin) or command.privilege == Privilege.Internal:
                continue
            txt = "\n".join([command.description, command.usage])
            embed.add_field(name=command.name, value=txt, inline=False)

        connector_object.send_embed(message.channel, embed)
    elif argument.upper() in Category.all():
        embed = Embed(title=f"Help for the {argument.upper()} category Internal commands",
                              description=f"Currently {len(linking)} commands and {len(Category.all())} categories are available", color=0x0083fb)
        embed.set_author(name="Night Key", url="https://github.com/NightKey", icon_url="https://avatars.githubusercontent.com/u/8132508?s=400&v=4")
        for command in linking:
            if (command.privilege == Privilege.Admin and not is_admin) or command.privilege == Privilege.Internal:
                continue
            txt = "\n".join([command.description, command.usage])
            embed.add_field(name=command.name, value=txt, inline=False)

        connector_object.send_embed(message.channel, embed)

        embed = Embed(title=f"Help for the {argument.upper()} category External commands",
                      description=f"Currently {len(outside_options)} commands and {len(Category.all())} categories are available",
                      color=0x0083fb)
        embed.set_author(name="Night Key", url="https://github.com/NightKey",
                         icon_url="https://avatars.githubusercontent.com/u/8132508?s=400&v=4")

        for command in outside_options:
            if (command.privilege == Privilege.Admin and not is_admin) or command.privilege == Privilege.Internal:
                continue
            txt = "\n".join([command.description, command.usage])
            embed.add_field(name=command.name, value=txt, inline=False)

        connector_object.send_embed(message.channel, embed)
    elif f"{argument}" in [x.name for x in linking]:
        command = None
        for __command in linking:
            if __command.name == f"{argument}":
                command = __command
                break

        if (command.privilege == Privilege.Admin and not is_admin) or command.privilege == Privilege.Internal:
            return
        embed = Embed(title=f"Help for the {command.name} command", description=command.description, color=0xb000ff)
        embed.set_author(name="Night Key", url="https://github.com/NightKey",
                             icon_url="https://avatars.githubusercontent.com/u/8132508?s=400&v=4")
        embed.add_field(name="Usage", value=command.usage)
        connector_object.send_embed(message.channel, embed)
    elif f"{argument}" in [x.name for x in outside_options]:
        command = None
        for __command in outside_options:
            if __command.name == f"{argument}":
                command = __command
                break

        if (command.privilege == Privilege.Admin and not is_admin) or command.privilege == Privilege.Internal:
            return
        embed = Embed(title=f"Help for the {command.name} external command", description=command.description, color=0xb000ff)
        embed.set_author(name="Night Key", url="https://github.com/NightKey",
                         icon_url="https://avatars.githubusercontent.com/u/8132508?s=400&v=4")
        embed.add_field(name="Usage", value=command.usage)
        connector_object.send_embed(message.channel, embed)
    else:
        connector_object.send_message(message.respond_to(sender=connector_object.me, content=f"{argument} was not found!"))

@Category.BOT
@with_description_and_usage(
    descr="Adds an admin using either the admin key, or if an admin uses it, and the other is a user, it adds the user as an admin.",
    required_usage="admin key or mention a user"
)
@with_privilege(Privilege.Anyone)
@requires_arguments
@named("admin")
def add_admin(message: Message):
    key = message.get_arguments()
    connector_object = connectors[message.connector]
    if key == admin_key and message.sender.privilege < Privilege.Admin:
        user_store[message.sender.UUID].privilege = Privilege.Admin
        connector_object.send_message(message.respond_to(sender=connector_object.me, content="You are now an admin!"))
        save_cfg()
    elif message.sender.privilege >= Privilege.Admin and '<@' in key:
        selected_user = user_store.get_for_connector(key.replace('<@', '').replace(">", ''), message.connector)
        if selected_user < Privilege.Admin:
            selected_user.privilege = Privilege.Admin
            connector_object.send_message(
                message.respond_to(
                    sender=connector_object.me,
                    content=f"{str(connector_object.get_local_username(message.channel, selected_user))} is now an admin!"
                )
            )
        else:
            connector_object.send_message(
                message.respond_to(
                    sender=connector_object.me,
                    content=f"{str(connector_object.get_local_username(message.channel, selected_user))} is already an admin!"
                )
            )
        save_cfg()
#</editor-fold>

#<editor-fold desc="Inner">
def play(link):
    logger.info(f"The url was {link}")
    return webbrowser.open(link)


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
    tmp = {"tokens": {"discord": discord_token, "telegramm": telegramm_token}, "id": bot_id, 'connections': connections,
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
    global bot_id  # The discord bots' ID
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
            bot_id = tmp["id"]
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
            signal(Signals.RESTART)
            exit(0)
    else:
        logger.warning("Data not found!")
        discord_token = input("Type in the token: ")
        me = int(input("Type in this bot's discord user id: "))
        admins = {
            "discord":
            str(input("Type in the admin user's Discord ID, separated by a coma (,): ")).split(
                ','),
            "telegramm":
            str(input(
                "Type in the admin user's Telegramm chat ID, separated by a coma (,): ")).split(',')
        }
        bot_id = me
        save_cfg()
    check_process_list()

def stop_connectors():
    for name, connector in connectors.items():
        logger.debug(f"Stopping {name} connector")
        connector.stop()
    for name, connector in connectors.items():
        start = process_time()
        logger.trace(f"Waiting for {name} connector to stop")
        while not connector.stopped:
            sleep(0.1)
        logger.debug(f"{name} connector stopped under {(process_time() - start) / 1_000_000} ms")


def runner(loop: asyncio.AbstractEventLoop) -> None:
    """Runs the needed things in a way, the watchdog can access the bot client."""
    if '--nodcc' not in argv and "--remote" not in argv:
        start_thread("Disconnect checker")
    if '--nowd' not in argv:
        start_thread("Watchdog")
    if "--api" in argv and "--remote" not in argv:
        start_thread("API Server")
    if "--remote" not in argv:
        loop.create_task(start_discord_client(0))
        loop.run_forever()
    else:
        logger.debug("Started in remote mode...")
        logger.debug("Gathering IP and Authentication code")
        ip = port = auth = name = None
        try:
            ip = argv[argv.index('--ip') + 1]
            port = int(argv[argv.index('--port') + 1])
            auth = argv[argv.index('--auth') + 1]
            name = argv[argv.index('--name') + 1]
            if ip is None or port is None or auth is None or name is None:
                raise ValueError("Ip, Port, Auth and Name is needed for remote mode!")
            from smdb_api import API
            _api = API(name, auth, ip, port)
            _api.validate(10)
            if not _api.valid:
                logger.debug("Validation failed!")
                signal(Signals.EXIT)
            _api.create_function(
                "status", "Scanns the system for the running applications, and creates a messaging depending on the resoults.\nUsage: &status <long if you want to see the API status too>\nCategory: SOFTWARE")
        except Exception as ex:
            logger.error(f"Exception: {ex}")
            logger.error(f"IP: {ip} Port: {port} Auth: {auth} Name: {name}")
            logger.error("IP and Authentication code needed in remote mode!")
            stop()
            signal(Signals.EXIT)


def stop():
    global is_running
    if was_online:
        logger.info("Sending stop signal to connectors...")
        for connector in connectors.values():
            connector.stop()
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
    signal(Signals.EXIT)


def send_message(msg: Message) -> Response:
    """Callback function to the server.py.
    """
    if msg.channel is None:
        loop.create_task(watchdog.send_msg(msg.content))
        return Response(ResponseCode.Success)
    return Response(ResponseCode.Success) if connectors[msg.connector].send_message(msg) else Response(ResponseCode.Failed)


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


def get_status() -> Dict[str, str | dict[str, str] | list[dict[str, str | bool | list[str]]]]:
    """Callback function for server.py. Returns the bot's inner status"""
    status = {
        "Network": "Available" if is_running else "Unavailable",
        "SupportingFunctions": {
            name: ("Active" if thread.is_alive() else "Inactive") for name, thread in threads.items()
        },
        "Connectors": [
            {
                "Name": name,
                "Connected": connector.stopped,
                "Capabilities": [capability.name for capability in connector.capabilities]
            }
            for name, connector in connectors.items()
        ]
    }
    return status

def on_presence_update(user: User, before: Presence, after: Presence, connector: str):
    if before.activity != after.activity:
        server.event_trigger(
            Events.activity,
            before.activity if before.activity is not None else "None",
            after.activity if after.activity is not None else "None",
            user.UUID,
            connector
        )
    if before.status != after.status:
        server.event_trigger(
            Events.presence_update,
            before.status if before.status is not None else "None",
            after.status if after.status is not None else "None",
            user.UUID,
            connector
        )

def on_connector_disconnect(connector: str):
    logger.info(f"Connector {connector} lost connection!")
    try:
        TODO("Implement offline check with a ping for an always online server. Possibly a DNS server?")
        logger.warning("Internet connection lost!")
        global dc_time
        dc_time = datetime.datetime.now()
        watchdog.not_ready()
    except:
        pass


def on_ready(connector: str):
    """When the client is all set up, this sectio get's called, and runs once.
    It does a system scann for the running programs.
    """
    global connections
    global was_online
    connections[connector] = [datetime.datetime.now().timestamp()]
    logger.debug('Startup check started')
    start = process_time()
    # Sets the channel to the first valid channel, and runs a scann.
    if os.path.exists("Offline"):
        with open("Offline", 'r') as f:
            td = f.read(-1)
        os.remove("Offline")
        check_process_list()
        watchdog.was_restarted()
        if '--scilent' not in os.sys.argv:
            difference = datetime.datetime.now() - datetime.datetime.fromtimestamp(float(td))
            (f"Bot restarted after being offline for {str(difference).split('.')[0]}")
        was_online = True
    elif not was_online:
        if '--scilent' not in os.sys.argv:
            await channel.send("Bot started")
            check_process_list()
            await status_check(channel)
        was_online = True
    elif dc_time is not None:
        now = datetime.datetime.now()
        if (now - dc_time) > datetime.timedelta(seconds=2) and '--scilent' not in os.sys.argv:
            await channel.send("Back online!")
            await channel.send(f"Was offline for {now - dc_time}")
    finish = process_time()
    logger.info('Startup check finished')
    logger.debug(f"Startup check took {finish-start} s")
    watchdog.ready()
    global trys
    trys = 0
    # The bot totally started up, and ready.
    logger.info("Bot started up correctly!")

#</editor-fold>

# region DISCORD
class ClearHelper:
    def __init__(self, number: int | None, user: str | None, connector: Connector) -> None:
        self.finished = False
        self.number = number
        self.user = user
        self.connector = connector
        self.count = 0
        self.lock = Reaction(me=True, reaction=str("🔒"))
        self.stop = Reaction(me=True, reaction=str("🛑"))
        self.bulk: List[str] = []

    def check(self, message: Message):
        skip = False
        if self.lock in message.reactions:
            skip = True
        if self.stop in message.reactions:
            self.finished = True
        if self.user is not None and message.sender != self.user:
            skip = True
        if self.number is not None and self.count == self.number:
            self.finished = True
        if not skip and not self.finished:
            self.count += 1
        return not skip and not self.finished

    def add_to_bulk(self, message: Message):
        if len(self.bulk) >= 99:
            self.trigger_bulk(message.channel)
        self.bulk.append(message.id)

    def trigger_bulk(self, channel: Channel):
        if len(self.bulk) == 0:
            return
        self.connector.delete_messages(channel, self.bulk, )
        self.bulk = []

    def is_finished(self):
        return self.finished or (self.number is not None and self.count == self.number)



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


linking: List[CommandCallable] = [
    add_process,
    add_admin,
    get_api_key,
    set_bar,
    clear,
    count,
    stop_at,
    send_errors,
    stop_bot,
    help,
    status_check,
    send_link,
    lock,
    open_browser,
    echo,
    remove_process,
    restart_server,
    roll,
    terminate_process,
    update,
    decide,
    ban_users
]

outside_options: List[CommandCallable] = []

def __call_server_callback(name: str, message: Message):
    outside_options[name](server, message)

def edit_linking(data: LinkingEditorData, remove=False):
    """Removes an item from linking. Callback function to the server.py."""
    if remove and data in outside_options:
        del outside_options[data.name]
        telegramm_bot.remove_command(data.name)
        return
    outside_options[data.name] = data.callback
    if (data.add_to_telegram):
        telegramm_bot.register_callback(
            __call_server_callback, 
            data.name, 
            data.needs_input, 
            data.add_button, 
            CommandPrivilege(data.privilege.value)
        )


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
    """This get's called when a messaging was sent to the server. It checks for all the usable commands, and executes them, if they were sent to the correct channel.
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
            await message.channel.send(f"Error runnig the '{cmd}' commands: {ex}")
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
            await message.channel.send(f"Error runnig the '{cmd}' commands: {ex}\nInterpreted commands: {mx['key']}")
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
            await message.channel.send(f"Error runnig the '{cmd}' commands: {ex}\nInterpreted commands: {mx['key']}")
        finally:
            return
    if 'value' in mx and mx['value'] > 70:
        await message.add_reaction("👎")
        await message.channel.send(f"Did you mean `{mx['key']}`? Probability: {mx['value']}%")
    else:
        await message.add_reaction("👎")
        await message.channel.send("Not a valid commands!\nUse '&help' for the avaleable commands")


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
                signal(Signals.RESTART)
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
            signal(Signals.EXIT)
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
        Message("", msg, "", [], ""), channel), name="Send raw messaging")
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
        logger.error(f"Sending messaging timed out in {timeout} seconds")
        return Response(ResponseCode.Failed, f"Timed out after {timeout} seconds")
    return Response(ResponseCode.Success)


def send_discord_message(msg: Message) -> Response:
    chn = get_channel(msg.channel)
    if chn == None:
        return Response(ResponseCode.NotFound, "User or channel not found")
    task: asyncio.tasks.Task = loop.create_task(_send_message(msg, chn), name="Send discord messaging")
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
                await channel.send(embed=embed, files=[discord.File(attachment.url, attachment.file_name) for attachment in msg.attachments])
            else:
                await channel.send(msg.content, files=[discord.File(attachment.url, attachment.file_name) for attachment in msg.attachments])
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
    telegramm_bot = Telegram(telegramm_token, log_level, log_folder)

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
    telegramm_bot.send_message(msg.content)
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
        signal(Signals.RESTART)


if __name__ == "__main__":
    logger.header('STARTUP')
    logger.debug("Creating bot thread...")
    Bot = Thread(target=Main, args=[asyncio.get_event_loop(), ])
    Bot.name = "Bot thread"
    logger.debug("Starting bot thread...")
    Bot.start()
    Bot.join()
