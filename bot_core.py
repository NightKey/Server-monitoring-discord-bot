from modules import writer, status, logger, watchdog
from modules.scanner import scann
from threading import Thread
from time import sleep
import datetime, psutil, os, json, webbrowser, asyncio, logging
trys = 0
while trys < 3:
    try:
        import discord
        from fuzzywuzzy import fuzz
        break
    except:
        print("Can't import something, trying to install dependencies....")
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
what = ""
bar_size=18
connections = []
channels = ["commands"]
dcc = None
wd = None

def split(text, error=False):
    """Logs to both stdout and a log file, using both the writer, and the logger module
    """
    writer.write(text)
    lg.log(text, error=error)

writer = writer.writer("Bot")
print = split   #Changed print to the split function
client = discord.Client(heartbeat_timeout=120)       #Creates a client instance using the discord  module

def play():
    """
    Opens an URL in the default browser
    """
    print(f"The url was {what}")
    webbrowser.open(what)

def signal(what):
    """
    Sends a signal to the runner.
    """

    with open(what, 'w') as _: pass   

player = Thread(target=play)
player.name = "Player"

def enable_debug_logger():
    _logger = logging.getLogger('discord')
    _logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
    handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
    _logger.addHandler(handler)

async def updater(channel, _=None):
    """Updates the bot, and restarts it after a successfull update.
    """
    from modules import updater
    if updater.main():
        await channel.send("Restarting...")
        await client.logout()
        signal('Restart')
    else:
        await channel.send('Nothing was updated!')

async def processes(channel):
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
            await channel.send(f"{text}{chr(96)*3}")
            text = f"{(chr(96) * 3)}\n"
    await channel.send(f'{text}{chr(96)*3}')

def save_cfg():
    tmp = {"token":token, "id":id, 'connections':connections}
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
        print("Process list update detected!")
        with open(os.path.join("data", "process_list.json"), "r") as f:
            process_list = json.load(f)
        ptime = mtime

async def status_check(channel, _=None):
    """Scanns the system for the running applications, and creates a message depending on the resoults.
    """
    global process_list
    process_list = scann(process_list, psutil.process_iter())
    embed = discord.Embed(title="Interal status", color=0x14f9a2)
    embed.add_field(name=f"Reconnectoins in the past {reset_time} hours", value=len(connections), inline=False)
    embed.add_field(name="Warchdog", value=("Active" if wd.is_alive else "Inactive"))
    embed.add_field(name="Disconnect Checker", value=("Active" if dcc.is_alive else "Inactive"))
    embed.set_author(name="Night Key", url="https://github.com/NightKey", icon_url="https://cdn.discordapp.com/avatars/165892968283242497/e2dd1a75340e182d73dda34e5f1d9e38.png?size=128")
    await channel.send(embed=embed)
    embed = discord.Embed(title="Watched processes' status", color=0x14f9a2)
    for key, value in process_list.items():
        embed.add_field(name=key, value=("running" if value[0] else "stopped"), inline=True)
        process_list[key] = [False, False]
    else:
        await channel.send(embed=embed)
        embed = discord.Embed(title="Server status", color=0x14f9a2)
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

async def add_process(channel, name):
    """Adds a process to the watchlist. The watchdog automaticalli gets updated with the new list.
Usage: &add <existing process name>
    """
    global process_list
    process_list[name] = [False, False]
    with open(os.path.join("data", "process_list.json"), "w") as f:
        json.dump(process_list, f)
    await channel.send('Process added')

async def remove(channel, name):
    """Removes the given program from the watchlist
Usage: &remove <watched process name>
    """
    global process_list
    try:
        del process_list[name]
    except:
        await channel.send(f"Couldn't delete the '{name}' item.")
    with open(os.path.join("data", "process_list.json"), "w") as f:
        json.dump(process_list, f)
    

@client.event
async def on_message_edit(before, after):
    await on_message(after)

@client.event
async def on_disconnect():
    print("Connection lost!")
    global dc_time
    dc_time = datetime.datetime.now()
    _watchdog.not_ready()

@client.event
async def on_ready():
    """When the client is all set up, this sectio get's called, and runs once.
It does a system scann for the running programs.
    """
    global connections
    connections.append(datetime.datetime.now().timestamp())
    print('Startup check ...')
    global was_online
    #print(client.emojis)
    for channel in client.get_all_channels():   #Sets the channel to the first valid channel, and runs a scann.
        if str(channel) in channels:
            if os.path.exists("Offline"):
                with open("Offline", 'r') as f:
                    td = f.read(-1)
                os.remove("Offline")
                check_process_list()
                _watchdog.was_restarted()
                await channel.send(f"Bot restarted after being offline for {td}")
                was_online = True
            elif not was_online:
                await channel.send("Bot started")
                check_process_list()
                await status_check(channel)
                was_online = True
            else:
                now = datetime.datetime.now()
                if (now - dc_time) > datetime.timedelta(seconds=2):
                    await channel.send("Back online!")
                    await channel.send(f"Was offline for {now - dc_time}")
            break
    print('Startup check finished')
    _watchdog.ready()
    global trys
    trys = 0
    print("Bot started up correctly!")      #The bot totally started up, and ready.

async def echo(channel, _):
    """Responds with 'echo' and shows the current latency
    """
    await channel.send(f'echo {int(client.latency*1000)} ms')

async def send_link(channel, _):
    """Responds with the currently running bot's invite link
    """
    embed = discord.Embed()
    embed.add_field(name="Server monitoring Discord bot", value=f"You can invite this bot to your server on [this](https://discordapp.com/oauth2/authorize?client_id={id}&scope=bot&permissions=199680) link!")
    embed.add_field(name="Warning!", value="This bot only monitors the server it runs on. If you want it to monitor a server you own, wisit [this](https://github.com/NightKey/Server-monitoring-discord-bot) link instead!")
    embed.color=0xFF00F3
    await channel.send(embed=embed)

async def stop_bot(channel, _):
    """Stops the bot.
    """
    if str(channel) in channels:
        await channel.send("Exiting")
        await client.logout()
        signal('Exit')
        exit(0)

async def clear(channel, number):
    """Clears all messages from this channel.
Usage: &clear [optionally the number of messages or @user]
    """
    try: number = number.replace("<@!", '').replace('>', '')
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
            async for message in channel.history():
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
        await channel.send("I'm afraid, I can't do that.")
    except Exception as ex:
        await channel.send(f'Exception occured during cleaning:\n```{type(ex)} --> {ex}```')

async def restart(channel, _):
    """Restarts the server it's running on. (Admin permissions may be needed for this)
    """
    if str(channel) in channels:
        await channel.send("Attempting to restart the pc...")
        try:
            if os.name == 'nt':
                command = "shutdown /r /t 5"
            else:
                command = "shutdown -r -t 5"
            if os.system(command) != 0:
                await channel.send("Permission denied!")
            else:
                await client.logout()
        except Exception as ex:
            await channel.send(f"Restart failed with the following exception:\n```{type(ex)} -> {str(ex)}```")

async def terminate_process(channel, target):
    """Terminates the specified process. (Admin permission may be needed for this)
Usage: &terminate <existing process' name>
    """
    if target not in process_list:
        for p in process_list:
            if target in p:
                target = p
                break
        else:
            await channel.send("Target not found, process can't be safely killed!")
            return
    for process in psutil.process_iter():
        try:
            name = os.path.basename(process.cmdline()[-1])
            if name.lower() == target:
                process.kill()
            break
        except:
            pass
    else: await channel.send(f"Error while stopping {target}!\nManual help needed!")

async def open_browser(channel, link):
    """Opens a page in the server's browser.
Usage: &open <url to open>    
    """
    global what
    what = link
    player.start()
    await channel.send('Started playing the link')

async def set_bar(channel, value):
    """Sets the bars' widht to the given value in total character number (the default is 25)
Usage: &bar <integer value to change to>
    """
    global bar_size
    bar_size = int(value)
    await channel.send(f"Barsize set to {bar_size}")

async def locker(channel, value):
    """Locks and unlocks the linked message.
    Usage: &lock <message_id>
    """
    msg = await channel.fetch_message(value)
    for reaction in msg.reactions:
        if str(reaction) == str("🔒"):
            async for user in reaction.users():
                await reaction.remove(user)
            return
    await msg.add_reaction("🔒")

async def stop_at(channel, value):
    """Creates a stop signal to the clear command on the message linked.
It will stop AFTER that message. To keep a message, refer to the '&lock' command.
Usage: &end <message_id>
    """
    msg = await channel.fetch_message(value)
    for reaction in msg.reactions:
        if str(reaction) == str("🛑"):
            async for user in reaction.users():
                await reaction.remove(user)
            return
    await msg.add_reaction("🛑")

async def help(channel, what):
    """Returns the help text for the avaleable commands
Usage: &help <optionaly a specific without the '&' character>
    """
    if what == None:
        embed = discord.Embed(title="Help", description=f"Currently {len(linking.keys())} commands are avaleable", color=0x0083fb)
        embed.set_author(name="Night Key", url="https://github.com/NightKey", icon_url="https://cdn.discordapp.com/avatars/165892968283242497/e2dd1a75340e182d73dda34e5f1d9e38.png?size=128")
        for key, value in linking.items():
            txt = value.__doc__
            tmp = txt.split("\n")
            for a in tmp:
                if "Usage: " in a:
                    key = a.replace("Usage: ", '')
                    tmp.remove(a)
                    break
            txt = "\n".join(tmp)
            embed.add_field(name=key, value=txt, inline=False)
    elif f"&{what}" in linking.keys():
        embed = discord.Embed(title=f"Help for the {what} command", description=linking[f"&{what}"].__doc__, color=0xb000ff)
        embed.set_author(name="Night Key", url="https://github.com/NightKey", icon_url="https://cdn.discordapp.com/avatars/165892968283242497/e2dd1a75340e182d73dda34e5f1d9e38.png?size=128")
    await channel.send(embed=embed)

linking = {
    "&add":add_process,
    "&bar":set_bar,
    "&clear":clear,
    "&echo":echo,
    "&end":stop_at,
    "&exit":stop_bot,
    "&help":help,
    "&status":status_check,
    "&link":send_link,
    "&lock":locker,
    "&open":open_browser,
    "&remove": remove,
    "&restart":restart,
    "&terminate":terminate_process,
    "&update":updater
}

@client.event
async def on_message(message):
    """This get's called when a message was sent to the server. It checks for all the usable commands, and executes them, if they were sent to the correct channel.
    """
    me = client.get_user(id)
    if message.author != me:
        if message.content.startswith('&'):
            splt = message.content.split(' ')
            cmd = splt[0]
            etc = " ".join(splt[1:]) if len(splt) > 1 else None
            if cmd in linking.keys():
                await message.add_reaction("dot:577128688433496073")
                try:
                    await linking[cmd](message.channel, etc)
                except Exception as ex:
                    await message.channel.send(f"Error runnig the {cmd} command: {type(ex)} -> {ex}")
            else:
                await message.add_reaction("👎")
                mx = {}
                for key in linking.keys():
                    tmp=fuzz.ratio(cmd.lower().replace("&", ''), key.lower().replace('&', ''))
                    if 'value' not in mx or mx["value"] < tmp:
                        mx["key"] = key
                        mx["value"] = tmp
                if mx['value'] > 70:
                    await message.channel.send(f"Did you mean `{mx['key']}`? Probability: {mx['value']}%")
                else:
                    await message.channel.send("Not a valid command!\nUse '&help' for the avaleable commands")

def disconnect_check(loop, channels):
    """
    Restarts the bot, if the disconnected time is greater than one hour
    """
    global connections
    channel = None
    for channel in client.get_all_channels():
        if str(channel) in channels:
            break
    while True:
        if was_online and dc_time != None:
            if (datetime.datetime.now() - dc_time) > datetime.timedelta(hours=1):
                print('Offline for too long. Restarting!')
                save_cfg()
                loop.create_task(client.logout())
                loop.create_task(client.close())
                while not client.is_closed(): pass
                _watchdog.create_tmp()
                with open("Offline", "w") as f:
                    f.write(str(datetime.datetime.now() - dc_time))
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

def runner(loop):
    """
    Runs the needed things in a way, the watchdog can access the bot client.
    """
    global dcc
    global wd
    dcc = Thread(target=disconnect_check, args=[loop, channels,])
    dcc.name = "Disconnect checker"
    dcc.start()
    wd = Thread(target=_watchdog.run_watchdog, args=[channels,])
    wd.name = "Watchdog"
    wd.start()
    loop.create_task(client.start(token))
    loop.run_forever()

if __name__ == "__main__":
    try:
        load()
        print("Creating loop")
        loop = asyncio.get_event_loop()
        print('Setting up watchdog')
        _watchdog = watchdog.watchdog(loop, client, process_list)
        print('Starting all processes...')
        runner(loop)
        #client.run(token)
    except Exception as ex:
        print("Logging out...")
        print(str(ex), error=True)
        loop.create_task(client.logout())
        loop.create_task(client.close())
        while not client.is_closed():
            pass
        loop.stop()
        print("Restarting...")
        lg.close()
        signal("Restart")