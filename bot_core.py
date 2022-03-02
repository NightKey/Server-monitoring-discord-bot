from modules import status, watchdog, log_level
from modules.logger import logger_class
from platform import node
from modules.services import server, Message, Attachment
from modules.scanner import scann
from modules.response import response
from threading import Thread
from time import sleep, process_time
import datetime, psutil, os, json, webbrowser, asyncio, logging
import discord
from fuzzywuzzy import fuzz

trys = 0
token = ""
reset_time = 2  #hours
process_list = {}
ptime = 0
was_online=False
id = None
logger = logger_class("logs/bot.log", level=log_level, log_to_console=True, use_caller_name=True, use_file_names=True)
dc_time = None
bar_size=18
connections = []
channels = ["commands"]
is_running = True
errors = {}
threads = {}
admins = []
loop: asyncio.AbstractEventLoop = None
_watchdog: watchdog = None
_server = None
admin_key = None

class signals:
    exit = "Exit"
    restart = "Restart"

intents = discord.Intents.default()
intents.members = True
client = discord.Client(heartbeat_timeout=120, intents=intents)       #Creates a client instance using the discord  module

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
    try: _server.run = False
    except: pass
    with open(what, 'w') as _: pass   

def enable_debug_logger():
    _logger = logging.getLogger('discord')
    _logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler(filename=os.path.join('logs', 'discord.log'), encoding='utf-8', mode='w')
    handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
    _logger.addHandler(handler)

async def updater(message, _=None):
    """Updates the bot, and restarts it after a successfull update.
Category: BOT
    """
    if message is None or str(message.channel) in channels or str(message.author.id) in admins:
        from modules import updater
        os.system("pip3 install --user --upgrade smdb_api > update.lg")
        with open("update.lg", "r") as f:
            tmp = f.read(-1).split("\n")
        os.remove("update.lg")
        if len(tmp) > 2 and message is not None:
            await message.channel.send("API updated!")
        if _server is not None:
            _server.request_all_update()
        if updater.main():
            if message is not None:
                await message.channel.send("Restarting...")
            try: await client.logout()
            except: pass
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
    logger.debug(f"Your key is {key}")
    return key

def save_cfg():
    tmp = {"token":token, "id":id, 'connections':connections, "admins":admins, "admin key": admin_key}
    with open(os.path.join("data", "bot.cfg"), "w") as f:
        json.dump(tmp, f)

def load():
    """This function loads in the data, and sets up the program variables. 
    In the case of a missing, or corrupt cfg file, this function requests the data's input through console inpt.
    The data is stored in a json like cfg file with the following format:
    {"token":"BOT-TOKEN-HERE", "id":{"bot":BOT-ID-HERE}}
    """
    if not os.path.exists("data"):
        os.mkdir("data")
    global token    #The discord bot's login tocken
    global id      #The discord bots' ID
    global connections
    global admins
    global admin_key
    logger.debug("Loading data...")
    if os.path.exists(os.path.join("data", "bot.cfg")):
        try:
            with open(os.path.join("data", "bot.cfg"), "r") as f:
                tmp = json.load(f)
            token = tmp["token"]
            id = tmp["id"]
            try:
                connections = tmp['connections']
            except:
                connections = []
            admins = tmp["admins"]
            try:
                admin_key = tmp['admin key']
            except:
                admin_key = get_passcode()
                save_cfg()
            logger.info("Data loading finished!")
            del tmp
        except Exception as ex: #incase there is an error, the program deletes the file, and restarts
            from datetime import datetime
            with open("Loading_error", 'a') as f:
                f.write(f"[{datetime.now()}]: {ex}")
            os.remove(os.path.join("data", "bot.cfg"))
            logger.error("Error in cfg file... Restarting")
            signal(signals.restart)
            exit(0)
    else:
        logger.warning("Data not found!")
        token = input("Type in the token: ")
        me = int(input("Type in this bot's user id: "))
        admins = str(input("Type in the admin user's ID, separated by a coma (,): ")).split(',')
        id = me
        save_cfg()
    check_process_list()

def check_process_list():
    """Looks for update in the process list. To lighten the load, it uses the last modified date.
    As a side effect, too frequent updates are not possible.
    """
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
    status["SupportingFunctions"] = {name:("Active" if thread.is_alive() else "Inactive") for name, thread in threads.items()}
    try: 
        status["Ping"] = int(client.latency*1000) 
    except: 
        status["Ping"] = 'Nan'
    return status

async def status_check(message, stype="short"):
    """Scanns the system for the running applications, and creates a message depending on the resoults.
Usage: &status <long if you want to see the API status too or module name for specific module status [bot, watchdog, api, host/pc_name]>
Category: SOFTWARE
    """
    global process_list
    if stype is None:
        stype = "short"
    try:
        channel = message.channel
    except:
        channel = message
    if str(channel) not in channels and isinstance(message, discord.Message) and str(message.author.id) not in admins:
        await echo(message)
        return
    if stype.lower() in ["short", "long", "bot"]:
        bot_status = discord.Embed(title="Bot status", color=0x14f9a2)
        bot_status.add_field(name=f"Reconnectoins in the past {reset_time} hours", value=len(connections), inline=False)
        for name, thread in threads.items():
            bot_status.add_field(name=name, value=("Active" if thread.is_alive() else "Inactive"))
        bot_status.set_author(name="Night Key", url="https://github.com/NightKey", icon_url="https://cdn.discordapp.com/avatars/165892968283242497/e2dd1a75340e182d73dda34e5f1d9e38.png?size=128")
    
    if stype.lower() in ["short", "long", "watchdog"]:
        process_list = scann(process_list, psutil.process_iter())
        watchdog_status = discord.Embed(title="Watched processes' status", color=0x14f9a2)
        for key, value in process_list.items():
            watchdog_status.add_field(name=key, value=("running" if value[0] else "stopped"), inline=True)
            process_list[key] = [False, False]
    
    if stype.lower() in ["long", "api"]:
        api_server_status = discord.Embed(title="API Status", color=0x14f9a2)
        api_status = _server.get_api_status() if _server is not None else {"API":"Offline"}
        for key, values in api_status.items():
            if values == []: continue
            api_server_status.add_field(name=key, value="\u200B", inline=False)
            for item in list(values):
                api_server_status.add_field(value="\u200B", name=item, inline=True)
    
    pc_name = node()
    if stype.lower() in ["short", "long", "host", pc_name.lower()]:
        host_status = discord.Embed(title=f"{pc_name}'s status", color=0x14f9a2)
        host_status.set_footer(text="Created by Night Key @ https://github.com/NightKey", icon_url="https://cdn.discordapp.com/avatars/165892968283242497/e2dd1a75340e182d73dda34e5f1d9e38.png?size=128")
        stts = status.get_graphical(bar_size, True)
        for key, value in stts.items():
            val = ("Status" if len(value) > 1 else value[0])
            host_status.add_field(name=key, value=val, inline=False)
            if len(value) > 1 and key != "Battery":
                host_status.add_field(name="Max", value=value[0])
                host_status.add_field(name="Used" if key in ["RAM", "SWAP"] else "Free", value=value[1])
                host_status.add_field(name="Status", value=value[2])
            elif len(value) > 1:
                host_status.add_field(name="Battery life", value=value[0])
                host_status.add_field(name="Power status", value=value[1])
                host_status.add_field(name="Status", value=value[2])
        temp = status.get_temp()
        host_status.add_field(name="Temperature", value=(f"{temp}°C" if temp is not None else "Not detected!"))
    
    if stype.lower() in ["short", "long", "bot"]:
        await channel.send(embed=bot_status)
    
    if stype.lower() in ["short", "long", "watchdog"]:
        await channel.send(embed=watchdog_status)

    if stype.lower() in ["long", "api"] and api_server_status.fields != []:
        await channel.send(embed=api_server_status)
    
    if stype.lower() in ["short", "long", "host", pc_name.lower()]:
        await channel.send(embed=host_status)

async def add_process(message, name):
    """Adds a process to the watchlist. The watchdog automaticalli gets updated with the new list.
Usage: &add <existing process name>
Category: BOT
    """
    if str(message.channel) in channels or str(message.author.id) in admins:
        global process_list
        process_list[name] = [False, False]
        with open(os.path.join("data", "process_list.json"), "w") as f:
            json.dump(process_list, f)
        await message.channel.send('Process added')

async def remove(message, name):
    """Removes the given program from the watchlist
Usage: &remove <watched process name>
Category: BOT
    """
    if str(message.channel) in channels or str(message.author.id) in admins:
        global process_list
        try:
            del process_list[name]
        except:
            await message.channel.send(f"Couldn't delete the '{name}' item.")
        with open(os.path.join("data", "process_list.json"), "w") as f:
            json.dump(process_list, f)
    
async def roll(message, value):
    """Rolls the dice specifyed.
Usage: &roll <(# of dices)d(# of sides) or default 1d20>
Category: SERVER
    """
    import random
    if value is None:
        value = '1d20'
    num = int(value.split('d')[0])
    sides = int(value.split('d')[1])
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
    except discord.Forbidden: pass
    await message.channel.send(f"{tag}{message.author.name}`[{num}d{sides}]` rolled [{'+'.join([str(n) for n in res])}]: {sum(res)}") #Add a preferrence setting option for more costumisable bot

@client.event
async def on_message_edit(before, after):
    await on_message(after)

def offline(online):
    if not online:
        logger.info("Connection lost!")
        global dc_time
        dc_time = datetime.datetime.now()
        _watchdog.not_ready()

@client.event
async def on_disconnect():
    try:
        await _watchdog.check_connection(offline)
    except Exception as ex:
        errors[datetime.datetime.now()] = f"Exception occured during disconnect event {ex}"

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
    for channel in client.get_all_channels():   #Sets the channel to the first valid channel, and runs a scann.
        if str(channel) in channels:
            if os.path.exists("Offline"):
                with open("Offline", 'r') as f:
                    td = f.read(-1)
                os.remove("Offline")
                check_process_list()
                _watchdog.was_restarted()
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
                if dc_time is None: break
                if (now - dc_time) > datetime.timedelta(seconds=2) and '--scilent' not in os.sys.argv:
                    await channel.send("Back online!")
                    await channel.send(f"Was offline for {now - dc_time}")
            break
    finish = process_time()
    logger.info('Startup check finished')
    logger.debug(f"Startup check took {finish-start} s")
    _watchdog.ready()
    global trys
    trys = 0
    logger.info("Bot started up correctly!")      #The bot totally started up, and ready.

async def echo(message, _):
    """Responds with 'echo' and shows the current latency
Category: SERVER
    """
    await message.channel.send(f'echo {int(client.latency*1000)} ms')

async def send_link(message, _):
    """Responds with the currently running bot's invite link
Category: SERVER
    """
    try:
        embed = discord.Embed()
        embed.add_field(name="Server monitoring Discord bot", value=f"You can invite this bot to your server on [this](https://discordapp.com/oauth2/authorize?client_id={id}&scope=bot&permissions=2147953728) link!")
        embed.add_field(name="Warning!", value="This bot only monitors the server it runs on. If you want it to monitor a server you own, wisit [this](https://github.com/NightKey/Server-monitoring-discord-bot) link instead!")
        embed.color=0xFF00F3
        await message.channel.send(embed=embed)
    except Exception as ex:
        errors[datetime.datetime.now()] = f"Exception occured during link sending {ex}"

async def stop_bot(message, _):
    """Stops the bot. To use this command, you need to be an admin, or need to call it from a selected channel!
Category: BOT
    """
    global is_running
    if str(message.channel) in channels or str(message.author.id) in admins:
        await message.channel.send("Exiting")
        stop()

class clear_helper:
    def __init__(self, number, user) -> None:
        self.finished = False
        self.number = number
        self.user = user
        self.count = 0
        self.lock = discord.Reaction(message=None, data={"count": 1, "me":None}, emoji=str("🔒"))
        self.stop = discord.Reaction(message=None, data={"count": 1, "me":None}, emoji=str("🛑"))
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
        if len(self.bulk) == 0: return
        loop.create_task(channel.delete_messages(self.bulk))
        self.bulk = []
    
    def is_finished(self):
        return self.finished or (self.number is not None and self.count == self.number)


async def clear(message: discord.Message, data: None):
    """Clears all messages from this channel.
Usage: &clear [optionally the number of messages or @user]
Category: SERVER
    """
    user_permissions = message.author.permissions_in(message.channel)
    if (not user_permissions.administrator and not user_permissions.manage_messages): return
    user: discord.Member = None
    number: int = None
    if data is not None and "<@" in data: 
        user = client.get_user(int(data.replace("<@!", '').replace(">", '')))
    elif data is not None:
        number = int(data)
    helper = clear_helper(number, user)
    try:
       async  with message.channel.typing():
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
        errors[datetime.datetime.now()] = f'Exception occured during cleaning:\n```{ex}```'
        await message.channel.send("Sorry, something went wrong!")


async def count(message, channel):
    """Counts the messages for every user in a channel's last 1000 messages. The channel can either be given as a tag, or left empty.
Usage: &count <Optionally tagged channel (with  a '#' character before the name)>
Category: SERVER
    """
    if channel is None:
        channel = message.channel
    else:
        channel = client.get_channel(int(channel.replace("<#", '').replace(">", "")))
    if channel is None: 
        await message.channel.send("Channel is None! The bot probably doesn't have permission to read it.")
        return
    counter = {}
    async for msg in channel.history(limit=1000):
        counter[msg.author] = counter.setdefault(msg.author, 0) + 1
    try: message_to_send = f"```\n{channel.name}\n"
    except: message_to_send = f"```\nPrivate Channel\n"
    for user, count in counter.items():
        message_to_send += f"{user}: {count}\n"
    message_to_send += "```"
    await message.channel.send(message_to_send)

async def get_api_key(message, name):
    """Creates an API key for the given application name.
Usage: &API <name of the application the key will be created to>
Category: SOFTWARE
    """
    if str(message.channel) in channels or str(message.author.id) in admins:
        await message.channel.send(_server.get_api_key_for(name) if _server is not None else "API is not avaleable")

async def restart(message, _):
    """Restarts the server it's running on. Admin permissions may be needed for this on the host.
To use this command, you need to be an admin, or need to call it from a selected channel!
Category: HARDWARE
    """
    if str(message.channel) in channels or str(message.author.id) in admins:
        await message.channel.send("Attempting to restart the pc...")
        try:
            if os.name == 'nt':
                command = "shutdown /r /t 15"
            else:
                command = "shutdown -r -t 15"
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
    if str(message.channel) in channels or str(message.author.id) in admins:
        global errors
        msg = ""
        for date, item in errors.items():
            msg += f"{date}: {item}"
        if msg != "":
            await message.channel.send(msg)
        else:
            await message.channel.send("No errors saved")
        errors = {}

async def terminate_process(message, target):
    """Terminates the specified process. (Admin permission may be needed for this)
Usage: &terminate <existing process' name>
Category: SOFTWARE
    """
    if str(message.channel) in channels or str(message.author.id) in admins:
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
        else: await message.channel.send(f"Error while stopping {target}!\nManual help needed!")

async def open_browser(message, link):
    """Opens a page in the server's browser.
Usage: &open <url to open>
Category: SOFTWARE   
    """
    if str(message.channel) in channels or str(message.author.id) in admins:
        if play(link): await message.channel.send('Started playing the link')
        else:   await message.channel.send("Couldn't open the link")

async def set_bar(message, value):
    """Sets the bars' widht to the given value in total character number (the default is 25)
Usage: &bar <integer value to change to>
Category: BOT
    """
    if str(message.channel) in channels or str(message.author.id) in admins:
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
    is_admin = (str(message.channel) in channels or str(message.author.id) in admins)
    if what == None:
        embed = discord.Embed(title="Help", description=f"Currently {len(linking.keys())+len(outside_options.keys())} commands and {len(categories.keys())} categories are avaleable", color=0x0083fb)
        embed.set_author(name="Night Key", url="https://github.com/NightKey", icon_url="https://cdn.discordapp.com/avatars/165892968283242497/e2dd1a75340e182d73dda34e5f1d9e38.png?size=128")
        for key, value in categories.items():
            embed.add_field(name=key, value=value, inline=False)
    elif what == 'all':
        embed = discord.Embed(title="Help", description=f"Showing all commands!", color=0x0083fb)
        embed.set_author(name="Night Key", url="https://github.com/NightKey", icon_url="https://cdn.discordapp.com/avatars/165892968283242497/e2dd1a75340e182d73dda34e5f1d9e38.png?size=128")
        for key, value in linking.items():
            if value[1] and not is_admin: continue
            add = False
            txt = value[0].__doc__
            tmp = txt.split("\n")
            for a in tmp:
                if "Usage: " in a:
                    key = a.replace("Usage: &", '')
                try: tmp.remove(f"Usage: &{key}")
                except: pass
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
                    try: tmp.remove(f"Usage: &{key}")
                    except: pass
                txt = "\n".join(tmp)
                embed.add_field(name=key, value=txt, inline=False)
            if len(embed.fields) == line: embed.remove_field(line-1)
    elif what.upper() in categories:
        embed = discord.Embed(title=f"Help for the {what.upper()} category", description=f"Currently {len(linking.keys())+len(outside_options.keys())} commands and {len(categories.keys())} categories are avaleable", color=0x0083fb)
        embed.set_author(name="Night Key", url="https://github.com/NightKey", icon_url="https://cdn.discordapp.com/avatars/165892968283242497/e2dd1a75340e182d73dda34e5f1d9e38.png?size=128")
        for key, value in linking.items():
            if value[1] and not is_admin: continue
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
                try: tmp.remove(f"Usage: &{key}")
                except: pass
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
                    try: tmp.remove(f"Usage: &{key}")
                    except: pass
                    txt = "\n".join(tmp)
                    embed.add_field(name=key, value=txt, inline=False)
            if len(embed.fields) == line: embed.remove_field(line-1)
    elif f"{what}" in linking.keys():
        if linking[what][1] and is_admin:
            embed = discord.Embed(title=f"Help for the {what} command", description=linking[what][0].__doc__, color=0xb000ff)
            embed.set_author(name="Night Key", url="https://github.com/NightKey", icon_url="https://cdn.discordapp.com/avatars/165892968283242497/e2dd1a75340e182d73dda34e5f1d9e38.png?size=128")
    elif f"{what}" in outside_options.keys():
        if is_admin:
            embed = discord.Embed(title=f"Help for the {what} command", description=outside_options[what].__doc__, color=0xb000ff)
            embed.set_author(name="Night Key", url="https://github.com/NightKey", icon_url="https://cdn.discordapp.com/avatars/165892968283242497/e2dd1a75340e182d73dda34e5f1d9e38.png?size=128")
    try:
        await message.channel.send(embed=embed)
    except: await message.channel.send(f"{what} was not found!")

async def add_admin(message, key):
    """Adds an admin using either the admin key, or if an admin uses it, and the other is a user, it adds the user as an admin.
Usage: &admin <admin key or mention a user>
Category: BOT
    """
    if key == admin_key and str(message.author.id) not in admins:
        admins.append(str(message.author.id))
        await message.channel.send("You are now an admin!")
        save_cfg()
    elif str(message.author.id) in admins and '<@' in key:
        key = key.replace('<@', '').replace(">", '')
        if key not in admins:
            admins.append(key)
            await message.channel.send(f"{str(client.get_user(int(key))).split('#')[0]} is now an admin!")
        else:
            await message.channel.send(f"{str(client.get_user(int(key))).split('#')[0]} is already an admin!")
        save_cfg()

linking = {
    "add":[add_process, True],
    "admin":[add_admin, False],
    "api":[get_api_key, True],
    "bar":[set_bar, True],
    "clear":[clear, False],
    "count":[count, False],
    "echo":[echo, False],
    "end":[stop_at, False],
    "errors":[send_errors, True],
    "exit":[stop_bot, True],
    "help":[help, False],
    "status":[status_check, True],
    "link":[send_link, False],
    "lock":[locker, False],
    "open":[open_browser, True],
    "remove": [remove, True],
    "restart":[restart, True],
    "roll":[roll, False],
    "terminate":[terminate_process, True],
    "update":[updater, True]
}

outside_options = {}

def edit_linking(data, remove=False):
    """Removes an item from linking. Callback function to the services.py."""
    if remove and data in outside_options:
        del outside_options[data]
    elif not remove:
        outside_options[data[0]] = data[1]

categories = {
    'HARDWARE':'Anything that interacts with the host machine.',
    'SERVER':'Anything that interacts with the discord server.',
    'NETWORK':"Anything that interacts with the host's network.",
    'SOFTWARE':'Anything that interacts with the programs running on the host machine.',
    'BOT':"Anything that interacts with the bot's workings.",
    'USER': "Anything that interacts with the users."
}

def is_admin(uid):
    return response("Success", uid in admins)

def get_user(key):
    for usr in client.users:
        if (str)(usr.id) == key:
            return response("Success", usr.name)
    else:
        return response("Internal error", "User not found")

@client.event
async def on_message(message):
    """This get's called when a message was sent to the server. It checks for all the usable commands, and executes them, if they were sent to the correct channel.
    """
    global _server
    me = client.get_user(id)
    if message.author != me:
        if message.content.startswith('&') or message.channel.type == discord.ChannelType.private:
            splt = message.content.replace('&', '').split(' ')
            cmd = splt[0]
            etc = " ".join(splt[1:]) if len(splt) > 1 else None
            if cmd in linking.keys() or cmd in outside_options.keys():
                await message.add_reaction("dot:577128688433496073")
                try:
                    if cmd in linking.keys(): await linking[cmd][0](message, etc)
                    elif cmd in outside_options.keys(): outside_options[cmd](_server, Message.create_message(str(message.author.id), etc, str(message.channel.id), [Attachment.from_discord_attachment(attachment) for attachment in message.attachments], None))
                except Exception as ex:
                    await message.channel.send(f"Error runnig the '{cmd}' command: {ex}")
            else:
                mx = {}
                for key in linking.keys():
                    tmp=fuzz.ratio(cmd.lower(), key.lower())
                    if 'value' not in mx or mx["value"] < tmp:
                        mx["key"] = key
                        mx["value"] = tmp
                if mx['value'] == 100:
                    try:
                        await linking[mx["key"]][0](message, etc)
                        await message.add_reaction("dot:577128688433496073")
                    except Exception as ex: await message.channel.send(f"Error runnig the '{cmd}' command: {ex}\nInterpreted command: {mx['key']}")
                elif mx['value'] > 70:
                    await message.add_reaction("👎")
                    await message.channel.send(f"Did you mean `{mx['key']}`? Probability: {mx['value']}%")
                else:
                    mx = {}
                    for key in outside_options.keys():
                        tmp=fuzz.ratio(cmd.lower(), key.lower())
                        if 'value' not in mx or mx["value"] < tmp:
                            mx["key"] = key
                            mx["value"] = tmp
                    if 'value' in mx and mx['value'] == 100:
                        try:
                            outside_options[mx["key"]](_server, Message.create_message(str(message.author.id), etc, str(message.channel.id), [Attachment.from_discord_attachment(attachment) for attachment in message.attachments], None))
                            await message.add_reaction("dot:577128688433496073")
                        except Exception as ex: await message.channel.send(f"Error runnig the '{cmd}' command: {ex}\nInterpreted command: {mx['key']}")
                    elif 'value' in mx and mx['value'] > 70:
                        await message.add_reaction("👎")
                        await message.channel.send(f"Did you mean `{mx['key']}`? Probability: {mx['value']}%")
                    else:
                        await message.add_reaction("👎")
                        await message.channel.send("Not a valid command!\nUse '&help' for the avaleable commands")

def disconnect_check(loop, channels):
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
                while not client.is_closed(): pass
                _watchdog.create_tmp()
                with open("Offline", "w") as f:
                    f.write(str(dc_time.timestamp()))
                signal(signals.restart)
                exit(0)
        if len(connections) > 0 and (datetime.datetime.now() - datetime.datetime.fromtimestamp(connections[0])) >= datetime.timedelta(hours=reset_time):
            del connections[0]
        if len(connections) > 50:
            loop.create_task(channel.send(f"{len(connections)} connections reached within {reset_time} hours!"))
        if len(connections) > 500:
            enable_debug_logger()
            loop.create_task(channel.send(f"@everyone {len(connections)} connections reached within {reset_time} hours!\nDebugger enabled!"))
        if len(connections) > 990:
            loop.create_task(channel.send(f"@everyone {len(connections)} connections reached within {reset_time} hours!\nExiting!"))
            loop.create_task(client.logout())
            loop.create_task(client.close())
            while not client.is_closed(): pass
            signal(signals.exit)
        if was_online and float.is_integer(client.latency) and int(client.latency*1000) > 200:  #client.latency == client.latency - NaN test
            high_ping_count += 1
            if high_ping_count == 5:
                loop.create_task(channel.send(f"Warning! Latency is {int(client.latency*1000)} ms!\nIt was abowe 200 ms for over 10 seconds."))
                high_ping_count = 0
        elif high_ping_count != 0:
            high_ping_count - 1
        sleep(2)

def get_channel(user: str) -> discord.TextChannel:
    if usr := client.get_user(int(user)):
        if usr.dm_channel is not None:
            return usr.dm_channel
        else:
            loop.create_task(usr.create_dm())
            while usr.dm_channel is None:
                sleep(0.1)
            return usr.dm_channel
    for chn in client.get_all_channels():
        if (str)(chn.id) == user:
            return chn
    return None

def send_message(msg: Message):
    """Callback function to the services.py.
    """
    if msg.channel is None:
        loop.create_task(_watchdog.send_msg(msg.content))
        return response("Success")
    else:
        if chn := get_channel(msg.channel) != None:
            task = loop.create_task(_send_message(msg, chn))
            while not task.done():
                sleep(0.1)
            if task.exception() is not None:
                return response("Internal error", f"{task.exception()}")
            return response("Success")
        else:
            return response("Internal error", "User or Channel wasn't found!")

async def _send_message(msg: Message, channel: discord.TextChannel):
    if len(msg.attachments) > 0:
        try:
            await channel.send(msg.content, file=discord.File(msg.attachments[0].url, msg.attachments[0].filename))
        except discord.errors.HTTPException as ex:
            if ex.status == 413: await channel.send("File too big!")
            else: raise ex
        return
    await channel.send(msg.content)

def start_thread(name):
    global threads
    if name == "Watchdog":
        threads[name] = Thread(target=_watchdog.run_watchdog, args=[channels,])
    elif name == "API Server":
        threads[name] = Thread(target=_server.start)
    elif name == "Disconnect checker":
        threads[name] = Thread(target=disconnect_check, args=[loop, channels,])
    threads[name].name = name
    threads[name].start()

def runner(loop):
    """Runs the needed things in a way, the watchdog can access the bot client."""
    if '--nodcc' not in os.sys.argv and "--remote" not in os.sys.argv:
        start_thread("Disconnect checker")
    if '--nowd' not in os.sys.argv and "--remote" not in os.sys.argv:
        start_thread("Watchdog")
    if "--api" in os.sys.argv:
        start_thread("API Server")
    if "--remote" not in os.sys.argv:
        loop.create_task(client.start(token))
        loop.run_forever()
    else:
        logger.debug("Started in remote mode...")
        logger.debug("Gathering IP and Authentication code")
        ip = port = auth = name = None
        try:
            """ ip = os.sys.argv[os.sys.argv.index('--ip') + 1]
            port = int(os.sys.argv[os.sys.argv.index('--port') + 1])
            auth = os.sys.argv[os.sys.argv.index('--auth') + 1]
            name = os.sys.argv[os.sys.argv.index('--name') + 1]
            from API import smdb_api
            _api = smdb_api.API(name, auth, ip, port)
            _api.validate(10)
            if not _api.valid:
                logger.debug("Validation failed!")
                signal(signals.exit)
            _api.create_function("status", "Scanns the system for the running applications, and creates a message depending on the resoults.\nUsage: &status <long if you want to see the API status too>\nCategory: SOFTWARE") """
        except Exception as ex:
            logger.error(f"Exception: {ex}")
            logger.error(f"IP: {ip or 'None'} Port: {port or 'None'} Auth: {auth or 'None'} Name: {name or 'None'}")
            logger.error("IP and Authentication code needed in remote mode!")
            stop()
            signal(signals.exit)

def stop():
    global is_running
    if was_online:
        logger.info("Sending stop signal to discord...")
        loop.create_task(client.logout())
        loop.create_task(client.close())
        logger.debug("Waiting for discord to close...")
        while not client.is_closed():
            pass
    if _watchdog is not None:
        logger.info("Stopping watchdogs")
        _watchdog.create_tmp()
        _watchdog.stop()
    logger.info("Stopping disconnect checker")
    is_running = False
    if _server is not None and _server.run:
        _server.stop()
    if loop is not None:
        loop.stop()
    signal(signals.exit)
    
def Main(_loop):
    try:
        global loop
        global _watchdog
        global _server
        global is_running
        logger.info('Program started')
        logger.debug("Creating loop")
        loop = _loop
        loop.create_task(updater(None))
        load()
        if '--al' in os.sys.argv:
            logger.info("Starting discord logger")
            enable_debug_logger()
        logger.info('Setting up watchdog')
        _watchdog = watchdog.watchdog(loop, client, process_list)
        if "--api" in os.sys.argv:
            logger.info("Setting up the services")
            _server = server(edit_linking, get_status, send_message, get_user, is_admin)
        logger.info('Starting all processes')
        runner(loop)
    except Exception as ex:
        logger.error(str(ex), error=True)
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