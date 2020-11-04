from modules import writer, status, logger, watchdog
from modules.services import server
from modules.scanner import scann
from modules.response import response
from threading import Thread
from time import sleep, process_time
import datetime, psutil, os, json, webbrowser, asyncio, logging
trys = 0
while trys < 3:
    try:
        import discord
        from fuzzywuzzy import fuzz
        break
    except:
        print("Can't import something, trying to install dependencies")
        with open("dependencies.txt", 'r') as f:
            dep = f.read(-1).split('\n')
        for d in dep:
            os.system(f"pip install --user {d}")
        trys = 1
if trys >= 3:
    print("Couldn't import something for the 3rd time...")
    input('Exiting... Press return...')
    exit(1)

trys = 0
token = ""
reset_time = 2  #hours
process_list = {}
ptime = 0
was_online=False
id = None
lg = logger.logger("bot", folder="logs")
dc_time = None
bar_size=18
connections = []
channels = ["commands"]
is_running = True
errors = {}
threads = {}
admins = []
loop = None
_watchdog = None
_server = None
admin_key = None

def split(text, error=False, log_only=False, print_only=False):
    """Logs to both stdout and a log file, using both the writer, and the logger module
    """
    if not log_only: writer.write(text)
    if not print_only: lg.log(text, error=error)

writer = writer.writer("Bot")
print = split   #Changed print to the split function
client = discord.Client(heartbeat_timeout=120)       #Creates a client instance using the discord  module

def play(link):
    """Opens an URL in the default browser
Category: SERVER
    """
    print(f"The url was {link}", print_only=True)
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
    handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
    handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
    _logger.addHandler(handler)

async def updater(message, _=None):
    """Updates the bot, and restarts it after a successfull update.
Category: BOT
    """
    from modules import updater
    if updater.main():
        if message is not None:
            await message.channel.send("Restarting...")
        try: await client.logout()
        except: pass
        signal('Restart')
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
    print("Loading data...")
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
            print("Data loading finished!")
            del tmp
        except Exception as ex: #incase there is an error, the program deletes the file, and restarts
            from datetime import datetime
            with open("Loading_error", 'a') as f:
                f.write(f"[{datetime.now()}]: {type(ex)} -> {ex}")
            os.remove(os.path.join("data", "bot.cfg"))
            print("Error in cfg file... Restarting")
            signal("Restart")
            exit(0)
    else:
        print("Data not found!")
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
        print("Process list update detected!", print_only=True)
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
Usage: &status <long if you want to see the API status too>
Category: SOFTWARE
    """
    global process_list
    try:
        channel = message.channel
    except:
        channel = message
    process_list = scann(process_list, psutil.process_iter())
    embed = discord.Embed(title="Interal status", color=0x14f9a2)
    embed.add_field(name=f"Reconnectoins in the past {reset_time} hours", value=len(connections), inline=False)
    for name, thread in threads.items():
        embed.add_field(name=name, value=("Active" if thread.is_alive() else "Inactive"))
    embed.set_author(name="Night Key", url="https://github.com/NightKey", icon_url="https://cdn.discordapp.com/avatars/165892968283242497/e2dd1a75340e182d73dda34e5f1d9e38.png?size=128")
    await channel.send(embed=embed)
    embed = discord.Embed(title="Watched processes' status", color=0x14f9a2)
    for key, value in process_list.items():
        embed.add_field(name=key, value=("running" if value[0] else "stopped"), inline=True)
        process_list[key] = [False, False]
    else:
        await channel.send(embed=embed)
        if stype is not None and stype.lower() == "long":
            embed = discord.Embed(title="API Status", color=0x14f9a2)
            api_status = _server.get_api_status()
            for key, values in api_status.items():
                if values == []: continue
                embed.add_field(name=key, value="\u200B", inline=False)
                for item in list(values):
                    embed.add_field(value="\u200B", name=item, inline=True)
            if embed.fields != []:
                await channel.send(embed=embed)
        embed = discord.Embed(title="Host status", color=0x14f9a2)
        embed.set_footer(text="Created by Night Key @ https://github.com/NightKey", icon_url="https://cdn.discordapp.com/avatars/165892968283242497/e2dd1a75340e182d73dda34e5f1d9e38.png?size=128")
        stts = status.get_graphical(bar_size, True)
        for key, value in stts.items():
            val = ("Status" if len(value) > 1 else value[0])
            embed.add_field(name=key, value=val, inline=False)
            if len(value) > 1 and key != "Battery":
                embed.add_field(name="Max", value=value[0])
                embed.add_field(name="Used", value=value[1])
                embed.add_field(name="Status", value=value[2])
            elif len(value) > 1:
                embed.add_field(name="Battery life", value=value[0])
                embed.add_field(name="Power status", value=value[1])
                embed.add_field(name="Status", value=value[2])
        await channel.send(embed=embed)

async def add_process(message, name):
    """Adds a process to the watchlist. The watchdog automaticalli gets updated with the new list.
Usage: &add <existing process name>
Category: BOT
    """
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
    global process_list
    try:
        del process_list[name]
    except:
        await message.channel.send(f"Couldn't delete the '{name}' item.")
    with open(os.path.join("data", "process_list.json"), "w") as f:
        json.dump(process_list, f)
    
async def roll(message, value):
    """Rolls the dice specifyed.
Usage: &roll <(# of dices)d(# of sides)>
Category: SERVER
    """
    import random
    if value is None:
        await message.channel.send("Called incorrectly")
        return
    num = int(value.split('d')[0])
    sides = int(value.split('d')[1])
    res = []
    res_s = []
    for _ in range(num):
        n = random.randint(1, sides)
        res.append(n)
        res_s.append(str(n))
    await message.delete()
    await message.channel.send(f"{message.author.name} rolled {sum(res)}")

@client.event
async def on_message_edit(before, after):
    await on_message(after)

def offline(online):
    if not online:
        print("Connection lost!")
        global dc_time
        dc_time = datetime.datetime.now()
        _watchdog.not_ready()

@client.event
async def on_disconnect():
    try:
        await _watchdog.check_connection(offline)
    except Exception as ex:
        errors[datetime.datetime.now()] = f"Exception occured during disconnect event {type(ex)} --> {ex}"

@client.event
async def on_ready():
    """When the client is all set up, this sectio get's called, and runs once.
It does a system scann for the running programs.
    """
    global connections
    connections.append(datetime.datetime.now().timestamp())
    print('Startup check started')
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
    print('Startup check finished')
    print(f"Startup check took {finish-start} s", log_only=True)
    _watchdog.ready()
    global trys
    trys = 0
    print("Bot started up correctly!")      #The bot totally started up, and ready.

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
        embed.add_field(name="Server monitoring Discord bot", value=f"You can invite this bot to your server on [this](https://discordapp.com/oauth2/authorize?client_id={id}&scope=bot&permissions=199680) link!")
        embed.add_field(name="Warning!", value="This bot only monitors the server it runs on. If you want it to monitor a server you own, wisit [this](https://github.com/NightKey/Server-monitoring-discord-bot) link instead!")
        embed.color=0xFF00F3
        await message.channel.send(embed=embed)
    except Exception as ex:
        errors[datetime.datetime.now()] = f"Exception occured during link sending {type(ex)} --> {ex}"

async def stop_bot(message, _):
    """Stops the bot. To use this command, you need to be an admin, or need to call it from a selected channel!
Category: BOT
    """
    global is_running
    if str(message.channel) in channels or str(message.author.id) in admins:
        await message.channel.send("Exiting")
        await client.logout()
        _watchdog.stop()
        is_running = False
        signal('Exit')
        exit(0)

async def clear(message, number):
    """Clears all messages from this channel.
Usage: &clear [optionally the number of messages or @user]
Category: SERVER
    """
    try: number = number.replace("<@", '').replace('>', '')
    except: pass
    if number is not None:
        user = client.get_user(int(number))
    else:
        user = None
    if user is not None:
        number = None
    try:
        count = 0
        clean = True
        while clean:
            is_message=False
            async for message in message.channel.history():
                skip = False
                if user is not None and message.author != user:
                    skip = True
                for reaction in message.reactions:
                    if str(reaction) == str("🔒"):
                        skip = True
                    elif str(reaction) == str("🛑"):
                        clean = False
                if skip:
                    if not clean:
                        break
                    else:
                        continue
                await message.delete()
                is_message=True
                count += 1
                if (number != None and count == int(number)) or not skip:
                    break
            else:
                if not is_message:
                    break
            if number != None and count == int(number):
                break
    except discord.Forbidden:
        await message.channel.send("I'm afraid, I can't do that.")
    except Exception as ex:
        await message.channel.send(f'Exception occured during cleaning:\n```{type(ex)} --> {ex}```')

async def get_api_key(message, name):
    """Creates an API key for the given application name.
Usage: &API <name of the application the key will be created to>
Category: SOFTWARE
    """
    await message.channel.send(_server.get_api_key_for(name))

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
                global is_running
                _watchdog.stop()
                is_running = False
                await client.logout()
                signal("Exit")
        except Exception as ex:
            await message.channel.send(f"Restart failed with the following exception:\n```{type(ex)} -> {str(ex)}```")

async def send_errors(message, _=None):
    """Sends all stored errors to the channel the command was sent to.
Category: BOT
    """
    global errors
    msg = ""
    for date, item in errors:
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
            errors[datetime.datetime.now()] = f"Exception occured during terminating process '{target}' {type(ex)} --> {ex}"
    else: await message.channel.send(f"Error while stopping {target}!\nManual help needed!")

async def open_browser(message, link):
    """Opens a page in the server's browser.
Usage: &open <url to open>
Category: SOFTWARE   
    """
    if play(link): await message.channel.send('Started playing the link')
    else:   await message.channel.send("Couldn't open the link")

async def set_bar(message, value):
    """Sets the bars' widht to the given value in total character number (the default is 25)
Usage: &bar <integer value to change to>
Category: BOT
    """
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
It will stop AFTER that message. To keep a message, refer to the '&lock' command.
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
    if what == None:
        embed = discord.Embed(title="Help", description=f"Currently {len(linking.keys())+len(outside_options.keys())} commands and {len(categories.keys())} categories are avaleable", color=0x0083fb)
        embed.set_author(name="Night Key", url="https://github.com/NightKey", icon_url="https://cdn.discordapp.com/avatars/165892968283242497/e2dd1a75340e182d73dda34e5f1d9e38.png?size=128")
        for key, value in categories.items():
            embed.add_field(name=key, value=value, inline=False)
    elif what == 'all':
        embed = discord.Embed(title="Help", description=f"Showing all commands!", color=0x0083fb)
        embed.set_author(name="Night Key", url="https://github.com/NightKey", icon_url="https://cdn.discordapp.com/avatars/165892968283242497/e2dd1a75340e182d73dda34e5f1d9e38.png?size=128")
        for key, value in linking.items():
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
        embed = discord.Embed(title=f"Help for the {what} category", description=f"Currently {len(linking.keys())+len(outside_options.keys())} commands and {len(categories.keys())} categories are avaleable", color=0x0083fb)
        embed.set_author(name="Night Key", url="https://github.com/NightKey", icon_url="https://cdn.discordapp.com/avatars/165892968283242497/e2dd1a75340e182d73dda34e5f1d9e38.png?size=128")
        for key, value in linking.items():
            add = False
            txt = value.__doc__
            tmp = txt.split("\n")
            for a in tmp:
                if "Usage: " in a:
                    key = a.replace("Usage: &", '')
                elif 'Category: ' in a:
                    if a.replace('Category: ', '').upper() == what:
                        add = True
            if add:
                try: tmp.remove(f"Usage: &{key}")
                except: pass
                txt = "\n".join(tmp)
                embed.add_field(name=key, value=txt, inline=False)
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
                    if a.replace('Category: ', '').upper() == what:
                        add = True
            if add:
                try: tmp.remove(f"Usage: &{key}")
                except: pass
                txt = "\n".join(tmp)
                embed.add_field(name=key, value=txt, inline=False)
        if len(embed.fields) == line: embed.remove_field(line-1)
    elif f"{what}" in linking.keys():
        embed = discord.Embed(title=f"Help for the {what} command", description=linking[what].__doc__, color=0xb000ff)
        embed.set_author(name="Night Key", url="https://github.com/NightKey", icon_url="https://cdn.discordapp.com/avatars/165892968283242497/e2dd1a75340e182d73dda34e5f1d9e38.png?size=128")
    elif f"{what}" in outside_options.keys():
        embed = discord.Embed(title=f"Help for the {what} command", description=linking[what].__doc__, color=0xb000ff)
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
    "add":add_process,
    "admin":add_admin,
    "api":get_api_key,
    "bar":set_bar,
    "clear":clear,
    "echo":echo,
    "end":stop_at,
    "errors":send_errors,
    "exit":stop_bot,
    "help":help,
    "status":status_check,
    "link":send_link,
    "lock":locker,
    "open":open_browser,
    "remove": remove,
    "restart":restart,
    "roll":roll,
    "terminate":terminate_process,
    "update":updater
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
                    if cmd in linking.keys(): await linking[cmd](message, etc)
                    elif cmd in outside_options.keys(): outside_options[cmd](_server, str(message.channel.id), (str)(message.author.id), etc)
                except Exception as ex:
                    await message.channel.send(f"Error runnig the {cmd} command: {type(ex)} -> {ex}")
            else:
                await message.add_reaction("👎")
                mx = {}
                for key in linking.keys():
                    tmp=fuzz.ratio(cmd.lower(), key.lower())
                    if 'value' not in mx or mx["value"] < tmp:
                        mx["key"] = key
                        mx["value"] = tmp
                if mx['value'] == 100:
                    try:
                        await linking[mx["key"]](message, etc)
                        await message.add_reaction("dot:577128688433496073")
                        await message.remove_reaction("👎", me)
                    except Exception as ex: await message.channel.send(f"Error runnig the {cmd} command: {type(ex)} -> {ex}")
                elif mx['value'] > 70:
                    await message.channel.send(f"Did you mean `{mx['key']}`? Probability: {mx['value']}%")
                else:
                    mx = {}
                    for key in outside_options.keys():
                        tmp=fuzz.ratio(cmd.lower(), key.lower())
                        if 'value' not in mx or mx["value"] < tmp:
                            mx["key"] = key
                            mx["value"] = tmp
                    if mx['value'] == 100:
                        try:
                            outside_options[mx["key"]](_server, str(message.channel.id), (str)(message.author.id), etc)
                            await message.add_reaction("dot:577128688433496073")
                            await message.remove_reaction("👎", me)
                        except Exception as ex: await message.channel.send(f"Error runnig the {cmd} command: {type(ex)} -> {ex}")
                    elif mx['value'] > 70:
                        await message.channel.send(f"Did you mean `{mx['key']}`? Probability: {mx['value']}%")
                    else:
                        await message.channel.send("Not a valid command!\nUse '&help' for the avaleable commands")

def disconnect_check(loop, channels):
    """Restarts the bot, if the disconnected time is greater than one hour"""
    global connections
    channel = None
    for channel in client.get_all_channels():
        if str(channel) in channels:
            break
    while is_running:
        if was_online and dc_time != None:
            if (datetime.datetime.now() - dc_time) > datetime.timedelta(hours=1):
                print('Offline for too long. Restarting!')
                save_cfg()
                loop.create_task(client.logout())
                loop.create_task(client.close())
                while not client.is_closed(): pass
                _watchdog.create_tmp()
                with open("Offline", "w") as f:
                    f.write(str(dc_time.timestamp()))
                signal("Restart")
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
            signal("Exit")
        sleep(2)

def send_message(msg, user=None):
    """Callback function to the services.py.
    """
    if user is None:
        loop.create_task(_watchdog.send_msg(msg))
        return response("Success")
    else:
        for usr in client.users:
            if (str)(usr.id) == user:
                if usr.dm_channel is not None:
                    loop.create_task(usr.dm_channel.send(msg))
                    return response("Success")
                else:
                    loop.create_task(usr.create_dm())
                    while usr.dm_channel is None:
                        sleep(0.01)
                    loop.create_task(usr.dm_channel.send(msg))
                    return response("Success")
        for chn in client.get_all_channels():
            if (str)(chn.id) == user:
                chn.send(msg)
                return response("Success")
        return response("Internal error", "User or Channel wasn't found!")

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
    start_thread("Disconnect checker")
    if '--nowd' not in os.sys.argv:
        start_thread("Watchdog")
    if "--api" in os.sys.argv:
        start_thread("API Server")
    loop.create_task(client.start(token))
    loop.run_forever()
    
def Main(_loop):
    try:
        global loop
        global _watchdog
        global _server
        global is_running
        print('---------------------------------------------------------------------', log_only=True)
        print('Program started', log_only=True)
        print("Creating loop")
        loop = _loop
        loop.create_task(updater(None))
        load()
        if '--al' in os.sys.argv:
            print("Starting discord logger", print_only=True)
            enable_debug_logger()
        print('Setting up watchdog')
        _watchdog = watchdog.watchdog(loop, client, process_list)
        if "--api" in os.sys.argv:
            print("Setting up the services")
            _server = server(edit_linking, get_status, send_message, get_user, is_admin)
        print('Starting all processes', print_only=True)
        runner(loop)
    except Exception as ex:
        print(str(ex), error=True)
        if _watchdog.is_ready():
            print("Sending stop signal to discord...")
            loop.create_task(client.logout())
            loop.create_task(client.close())
            print("Waiting for discord to close...")
            while not client.is_closed():
                pass
        print("Stopping watchdogs")
        _watchdog.create_tmp()
        print("Stopping disconnect checker")
        is_running = False
        loop.stop()
        print("Restarting...")
        lg.close()
        signal("Restart")

if __name__ == "__main__":
    print("Creating bot thread...")
    Bot = Thread(target=Main, args=[asyncio.get_event_loop(), ])
    Bot.name = "Bot thread"
    print("Starting bot thread...")
    Bot.start()