from modules import writer, status, logger, watchdog
from modules.scanner import scann
from threading import Thread
from time import sleep
import datetime, psutil, os, json, webbrowser, asyncio
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
bar_size=45
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
    print(f"The url was {what}")
    webbrowser.open(what)
    

player = Thread(target=play)
player.name = "Player"

async def updater(channel):
    from modules import updater
    if updater.main():
        await channel.send("Update installed!")
        f = open("stop.wd", "w")
        f.close()
        os.system("restarter.py bot.py")
        await client.logout()
        exit(0)
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

async def status_check(channel):
    """Scanns the system for the running applications, and creates a message depending on the resoults.
    """
    global process_list
    while True:
        process_list = scann(process_list, psutil.process_iter())
        text = ""
        for key, value in process_list.items():
            text += "{}\t{}\n".format(key, ("running" if value[0] else "stopped"))
            process_list[key] = [False, False]
        else:
            await channel.send(f"```diff\n{text}```\n{status.get_graphical(bar_size)}")
            break

def add_process(name):
    """Adds a process to the watchlist. The watchdog automaticalli gets updated with the new list.
    """
    global process_list
    process_list[name] = [False, False]
    with open(os.path.join("data", "process_list.json"), "w") as f:
        json.dump(process_list, f)

def remove(name):
    """Removes the given program from the watchlist
    """
    global process_list
    try:
        del process_list[name]
    except:
        return False
    with open(os.path.join("data", "process_list.json"), "w") as f:
        json.dump(process_list, f)
    return True
    

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
            if not was_online:
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

@client.event
async def on_message(message):
    """This get's called when a message was sent to the server. It checks for all the usable commands, and executes them, if they were sent to the correct channel.
    """
    me = client.get_user(id)
    if message.author == me:
        return
    if str(message.channel) in channels:
        if message.content == "&echo":
            await message.channel.send("echo")
        if message.content == "&status":
            await status_check(message.channel)
        if message.content == "&link":
            text = f"Bot - https://discordapp.com/oauth2/authorize?client_id={id}&scope=bot&permissions=199680"
            await message.channel.send(text)
        if message.content.startswith("&add"):
            name = message.content.replace("&add ", '')
            add_process(name)
            await message.channel.send("Updated!")
        if message.content == "&hush now":
            await message.channel.send("nini")
            await client.logout()
            exit(0)
        if message.content == "&clear":
            channel = message.channel
            try:
                while True:
                    is_message=False
                    async for message in channel.history():
                        await message.delete()
                        is_message=True
                    else:
                        if not is_message:
                            break
            except discord.Forbidden:
                channel.send("I'm afraid, I can't do that.")
        if message.content == "&restart":
            await message.channel.send("Restarting...")
            os.system("restarter.py bot.py")
            await client.logout()
            exit(0)
        if message.content in ("&restart pc", "&restart server"):
            await message.channel.send("Attempting to restart the pc...")
            try:
                ansv = os.system("shutdown /r /t 5")
                if ansv != 0:
                    await message.chanel.send("Permission denied!")
                else:
                    f = open("stop.wd", "w")
                    f.close()
            except Exception as ex:
                await message.channel.send(f"Restart failed with the following error:\n```{str(ex)}```")
        if "&stop " in message.content or "&terminate " in message.content:
            target = message.content.replace('&stop ', '').replace("&terminate ", '')
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
                except:
                    pass
            else: await message.channel.send(f"Error while stopping {target}!\nManual help needed!")
        if message.content == "&help":
            text = """Every time the bot starts up, it runs a system check for the running program.
&add <name> - Add a process to the watchlist
&bar <int> - Change the bar length when showing status
&clear - Clears the current chanel, if the promission was granted
&echo - Response test
&hush now - Stops this bot
&help - This help list
&link - Link to invite both bots
&list - Lists the currently running processes
&remove <name> - removes the process from the list
&restart - Restarts the bot.
&restart pc or &restart server - Attempts to restart the host machine.
&status - The Key Server's status
&stop <name> or &terminate <name> - Kills the process with the name from the process list only!
&update - update the bots, and restart's them"""
            await message.channel.send(f"```{text}```")
        if message.content == '&update':
            await updater(message.channel)
        if '&remove' in message.content:
            if not remove(message.content.replace('&remove ', '')):
                await message.channel.send(f"Couldn't delete the '{message.content.replace('&remove ')}' item.")
        if message.content == '&list':
            await processes(message.channel)
        if '&play' in message.content:
            global what
            what = message.content.split(' ')[1]
            player.start()
            await message.channel.send('Started playing the link')
        if "&bar" in message.content:
            global bar_size
            bar_size = int(message.content.split(' ')[1])
            await message.channel.send(f"Barsize set to {bar_size}")

def disconnect_check(loop):
    while True:
        if was_online and dc_time != None:
            if (datetime.datetime.now() - dc_time) > datetime.timedelta(hours=1):
                print('Offline for too long. Restarting!')
                os.system("restarter.py bot.py")
                exit(0)
        sleep(2)

def runner(loop):
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