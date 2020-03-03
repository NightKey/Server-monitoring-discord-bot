import discord, psutil, os, json
from modules import writer, status, logger
from modules.scanner import scann
from threading import Thread
from time import sleep

trys = 0
last_stop = None
token = ""
process_list = {}
ptime = 0
retry = 0
ids = {}
lg = logger.logger("bot", folder="logs")

def split(text, error=False):
    """Logs to both stdout and a log file, using both the writer, and the logger module
    """
    writer.write(text)
    lg.log(text, error=error)

writer = writer.writer("Key Server")
print = split   #Changed print to the split function
client = discord.Client()       #Creates a client instance using the discord  module

def load():
    """This function loads in the data, and sets up the program variables. 
    In the case of a missing, or corrupt cfg file, this function requests the data's input through console inpt.
    The data is stored in a json like cfg file with the following format:
    {"token":"BOT-TOKEN-HERE", "ids":{"bot":BOT-ID-HERE, "watchdog":WATCHDOG-ID-HERE}}
    """
    if not os.path.exists("data"):
        os.mkdir("data")
    global token    #The discord bot's login tocken
    global ids      #The discord bots' ID (If watchdog is used too)
    print("Loading data...")
    if os.path.exists(os.path.join("data", "bot.cfg")):
        try:
            with open(os.path.join("data", "bot.cfg"), "r") as f:
                tmp = json.load(f)
            token = tmp["token"]
            ids = tmp["ids"]
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
        wd = int(input("Type in the watchdog's user id, or press enter: ") or -1)
        ids["me"] = me
        ids['watchdog'] = wd
        tmp = {"token":token, "ids":ids}
        with open(os.path.join("data", "bot.cfg"), "w") as f:
            json.dump(tmp, f)
    del tmp

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
        if ids["watchdog"] != -1:
            process_list["watchdog.py"] = [False, False]
        ptime = mtime

async def status_check(channel):
    """Scanns the system for the running applications, and creates a message depending on the resoults.
    """
    global retry
    global process_list
    while True:
        process_list = scann(process_list, psutil.process_iter())
        text = ""
        for key, value in process_list.items():
            if key == "watchdog.py" and not value[0]:
                if retry < 1:
                    await channel.send("Watchdog offline!")
                    try:
                        with open(os.path.join("logs", "watchdog.lg"), 'r') as f:
                            print("Watchdog logs opened")
                            text = f.read(-1).split('\n')
                        if text[-3] == "---ERROR OCCURED!---":      #If the watchdog program stopped with an error, the bot will attempt to send a message containing that error
                            print("Line found!")
                            await channel.send(f"Watchdog error: {text[-2]}")
                    except Exception as ex:
                        print(f"Error in opening the log file:\n{ex}")
                if retry < 3:
                    await channel.send("Attempting to restart...")
                    os.startfile("watchdog.py")
                    retry += 1
                    sleep(3)
                    break
                else:
                    await channel.send("Watchdog can't be started automatically!")
            text += "{}\t{}\n".format(key, ("running" if value[0] else "stopped"))
            process_list[key] = [False, False]
        else:
            await channel.send(f"```diff\n{text}```\n{status.get_graphical()}")
            break

def add_process(name):
    """Adds a process to the watchlist. The watchdog automaticalli checks the watchlist file every 10 secounds to lighten the load.
    """
    global process_list
    process_list[name] = [False, False]
    try:
        del process_list["watchdog.py"] #If the watchdog's ID is not given during the setup, the program won't have it in it's process list.
    except:
        pass
    with open(os.path.join("data", "process_list.json"), "w") as f:
        json.dump(process_list, f)

@client.event
async def on_message_edit(before, after):
    await on_message(after)

@client.event
async def on_ready():
    """When the client is all set up, this sectio get's called, and runs once.
    It does a system scann for the running programs, and if watchdog is offline, but ID is given, it attempts to restart it 3 times
    """
    channels = ["commands"]
    for channel in client.get_all_channels():   #Sets the channel to the first valid channel, and runs a scann.
        if str(channel) in channels:
            global last_stop
            if last_stop != None:
                await channel.send(f"Unexcepted shutdown!\nError message:\n```Python{last_stop}```")
                last_stop = None
            else:
                await channel.send("Bot started")
            check_process_list()
            await status_check(channel)
            break
    print("Bot started up correctly!")      #The bot totally started up, and ready.
    global trys
    trys = 0

@client.event
async def on_message(message):
    """This get's called when a message was sent to the server. It checks for all the usable commands, and executes them, if they were sent to the correct channel.
    """
    channels = ["commands"]
    me = client.get_user(ids["me"])
    if message.author == me:
        return
    if str(message.channel) in channels:
        if message.content == "&echo":
            await message.channel.send("echo")
        if message.content == "&status":
            status_check(message.channel)
        if message.content == "&link":
            text = f"Watchdog - https://discordapp.com/oauth2/authorize?client_id={ids['watchdog']}&scope=bot&permissions=199680\n" if ids["watchdog"] != -1 else ""
            text += f"Bot - https://discordapp.com/oauth2/authorize?client_id={ids['me']}&scope=bot&permissions=199680"
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
        if message.content == "&restart watchdog":
            for process in psutil.process_iter():
                try:
                    name = os.path.basename(process.cmdline()[-1])
                    if name.lower() == "watchdog.py":
                        process.kill()
                    os.system("restarter.py watchdog.py")
                    await message.channel.send("Restarting watchdog...")
                    break
                except:
                    pass
            else: await message.channel.send("Error in restarting watchdog!\nManual help needed!")
        if message.content == "&help":
            text = """Every time the bot starts up, it runs a system check for the running program. If watchdog is not running, trys to start it 3 times.
&echo - Response test
&status - The Key Server's status
&link - Link to invite both bots
&add <name> - Add a process to the watchlist
&hush now - Stops this bot
&clear - Clears the current chanel, if the promission was granted
&restart - Restarts the bot.
&restart watchdog - Restarts the watchdog application.
&help - This help list"""
            await message.channel.send(f"```{text}```")

if __name__ == "__main__":
    while True:
        trys += 1
        if trys <= 3:
            try:
                load()
                print("started")
                client.run(token)
            except Exception as ex:
                print(str(ex), error=True)
                last_stop = str(ex)
        else:
            print("Restart failed 3 times...")
            print("Exiting...")
    