from modules import writer, status, logger, watchdog
from modules.scanner import scann
from threading import Thread
from time import sleep
import datetime, psutil, os, json, webbrowser, asyncio, logging
trys = 0
while trys < 3:
    try:
        import discord
        break
    except:
        print("Can't import something, trying to install dependencies....")
        with open("dependencies.txt", 'r') as f:
            dep = f.read(-1).split('\n')
        for d in dep:
            os.system(f"{os.sys.path} -m pip install --user {d}")
        trys = 1
if trys >= 3:
    print("Couldn't import something for the 3rd time...")
    input('Exiting... Press return...')
    exit(1)

_logger = logging.getLogger("discord")
_logger.setLevel(logging.DEBUG)
handler = logging.FileHandler("logs/bot_debug.lg", encoding="utf-8", mode="w")
handler.setFormatter(logging.Formatter("%(asciitime)s:%(lelvelname)s:%(name)s: %(message)s"))
_logger.addHandler(handler)


trys = 0
last_stop = None
token = ""
process_list = {}
ptime = 0
retry = 0
was_online=False
id = None
lg = logger.logger("bot", folder="logs")
dc_time = None
what = ""
bar_size=25
channels = ["commands"]

def split(text, error=False):
    """Logs to both stdout and a log file, using both the writer, and the logger module
    """
    writer.write(text)
    lg.log(text, error=error)

writer = writer.writer("Bot")
print = split   #Changed print to the split function
client = discord.Client()       #Creates a client instance using the discord  module

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
    print("Loading data...")
    if os.path.exists(os.path.join("data", "bot.cfg")):
        try:
            with open(os.path.join("data", "bot.cfg"), "r") as f:
                tmp = json.load(f)
            token = tmp["token"]
            id = tmp["id"]
            print("Data loading finished!")
        except: #incase there is an error, the program deletes the file, and restarts
            os.remove(os.path.join("data", "bot.cfg"))
            print("Error in cfg file... Restarting")
            os.system("restarter.py bot.py")
            exit(0)
    else:
        print("Data not found!")
        token = input("Type in the token: ")
        me = int(input("Type in this bot's user id: "))
        id = me
        tmp = {"token":token, "id":id}
        with open(os.path.join("data", "bot.cfg"), "w") as f:
            json.dump(tmp, f)
    del tmp
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
    embed = discord.Embed(title="Processes", color=0x14f9a2)
    embed.set_author(name="Night Key", url="https://github.com/NightKey", icon_url="https://cdn.discordapp.com/avatars/165892968283242497/e2dd1a75340e182d73dda34e5f1d9e38.png?size=128")
    for key, value in process_list.items():
        embed.add_field(name=key, value=("running" if value[0] else "stopped"), inline=True)
        process_list[key] = [False, False]
    else:
        await channel.send(embed=embed)
        embed = discord.Embed(title="Status", color=0x14f9a2)
        embed.set_author(name="Night Key", url="https://github.com/NightKey", icon_url="https://cdn.discordapp.com/avatars/165892968283242497/e2dd1a75340e182d73dda34e5f1d9e38.png?size=128")
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
    print('Startup check ...')
    global was_online
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
                global last_stop
                if last_stop != None:
                    await channel.send(f"Unexcepted shutdown!\nError message:\n```Python{last_stop}```")
                    last_stop = None
                else:
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
    await channel.send(f'echo {int(client.latency)} ms')

async def send_link(channel, _):
    """Responds with the currently running bot's invite link
    """
    await channel.send(f"Bot - https://discordapp.com/oauth2/authorize?client_id={id}&scope=bot&permissions=199680")

async def stop_bot(channel, _):
    """Stops the bot.
    """
    await channel.send("Exiting")
    await client.logout()
    signal('Exit')
    exit(0)

async def clear(channel, number):
    """Clears all messages from this channel.
Usage: &clear <optionally the number of messages>
    """
    try:
        count = 0
        while True:
            is_message=False
            async for message in channel.history():
                await message.delete()
                is_message=True
                count += 1
                if number != None and count == int(number):
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
Usage: &play <url to open>    
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

linking = {
    "&status":status_check,
    "&echo":echo,
    "&link":send_link,
    "&add":add_process,
    "&exit":stop_bot,
    "&clear":clear,
    "&restart":restart,
    "&terminate":terminate_process,
    "&remove": remove,
    "&open":open_browser,
    "&bar":set_bar,
    "&update":updater
}

async def help(channel, what):
    """Returns the help text for the avaleable commands
Usage: &help <optionaly a specific without the '&' character>
    """
    if what == None:
        embed = discord.Embed(title="Help", description=f"Currently {len(linking.keys())} commands are avaleable", color=0x0083fb)
        embed.set_author(name="Night Key", url="https://github.com/NightKey", icon_url="https://cdn.discordapp.com/avatars/165892968283242497/e2dd1a75340e182d73dda34e5f1d9e38.png?size=128")
        for key, value in linking.items():
            txt = value.__doc__
            if len(txt.split('\n'))>2:
                key = txt.split('\n')[1].replace('Usage: ', '')
                txt = txt.split('\n')[0]
            embed.add_field(name=key, value=txt, inline=False)
    elif f"&{what}" in linking.keys():
        embed = discord.Embed(title=f"Help for the {what} command", description=linking[f"&{what}"].__doc__, color=0xb000ff)
        embed.set_author(name="Night Key", url="https://github.com/NightKey", icon_url="https://cdn.discordapp.com/avatars/165892968283242497/e2dd1a75340e182d73dda34e5f1d9e38.png?size=128")
    await channel.send(embed=embed)

linking["&help"] = help

@client.event
async def on_message(message):
    """This get's called when a message was sent to the server. It checks for all the usable commands, and executes them, if they were sent to the correct channel.
    """
    me = client.get_user(id)
    if str(message.channel) in channels and message.author != me:
        if message.content.startswith('&'):
            splt = message.content.split(' ')
            cmd = splt[0]
            etc = " ".join(splt[1:]) if len(splt) > 1 else None
            if cmd in linking.keys():
                await linking[cmd](message.channel, etc)
            else:
                await message.channel.send("Not a valid command!\nUse '&help' for the avaleable commands")

def disconnect_check(loop):
    """
    Restarts the bot, if the disconnected time is greater than one hour
    """
    while True:
        if was_online and dc_time != None:
            if (datetime.datetime.now() - dc_time) > datetime.timedelta(hours=1):
                print('Offline for too long. Restarting!')
                loop.create_task(client.logout())
                sleep(10)
                with open("Offline", "w") as f:
                    f.write(str(datetime.datetime.now() - dc_time))
                signal("Restart")
                exit(0)
        sleep(2)

def runner(loop):
    """
    Runs the needed things in a way, the watchdog can access the bot client.
    """
    dcc = Thread(target=disconnect_check, args=[loop,])
    dcc.name = "Disconnect checker"
    dcc.start()
    wd = Thread(target=_watchdog.run_watchdog, args=[channels,])
    wd.name = "Watchdog"
    wd.start()
    loop.run_until_complete(client.start(token))

if __name__ == "__main__":
    while True:
        trys += 1
        if trys <= 3:
            try:
                load()
                print("started")
                loop = asyncio.get_event_loop()
                _watchdog = watchdog.watchdog(loop, client, process_list)
                runner(loop)
                #client.run(token)
            except Exception as ex:
                print(str(ex), error=True)
                last_stop = str(ex)
        else:
            print("Restart failed 3 times...")
            print("Exiting...")
            break