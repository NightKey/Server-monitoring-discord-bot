import discord, psutil, os, json
from modules import writer, logger
from time import sleep

token = ""
process_list = {}   #Formatting: "PROCESS-NAME":[IS-RUNNING, WAS-SENT-SINCE-LAST-STOPPED]
ptime = 0
error = ""
lg = logger.logger("watchdog", folder="logs")

def split(text, error=False):
    """Logs to both stdout and a log file, using both the writer, and the logger module
    """
    writer.write(text)
    lg.log(text, error=error)

writer = writer.writer("Watchdog")
print = split       #Changed print to the split function
client = discord.Client()       #Creates a client instance using the discord  module

def load():
    """This function loads in the data, and sets up the program variables. 
    In the case of a missing, or corrupt cfg file, this function requests the data's input through console inpt.
    The data is stored in a json like cfg file with the following format:
    {"token":"WATCHDOG-TOKEN-HERE"}
    """
    if not os.path.exists("data"):
        os.mkdir("data")
    global token
    print("Loading data...")
    if os.path.exists(os.path.join("data", "watchdog.cfg")):
        try:
            with open(os.path.join("data", "watchdog.cfg"), "r") as f:
                tmp = json.load(f)
            token = tmp["token"]
        except:
            os.remove(os.path.join("data", "watchdog.cfg"))
            print("Error in cfg file... Restarting")
            os.system("restarter.py watchdog.py")
            exit(0)
    else:
        print("Data not found!")
        token = input("Type in the token: ")
        tmp = {"token":token}
        with open(os.path.join("data", "watchdog.cfg"), "w") as f:
            json.dump(tmp, f)
    del tmp

@client.event
async def on_ready():
    await watchdog()

def check_process_list():
    """Looks for update in the process list. To lighten the load, it uses the last modified date.
    As a side effect, too frequent updates are not possible.
    """
    mtime = os.path.getmtime(os.path.join("data", "process_list.json"))
    global ptime
    if ptime < mtime:
        global process_list
        print("Process list update detected!")
        with open(os.path.join("data", "process_list.json")) as f:
            process_list = json.load(f)
        ptime = mtime

def scann(n):
    r"""Checks the currently running processes for the last argument in them. 
    If a .exe program is being checked, the last argument is the program's name.
    If a .py or other, console run program running, without any additional argument, the script's path will be the the last argument.
    For example:
        Discord's last argument: "path\to\discord\discord.exe"
        This bot's last argument: "path\to\bot\bot.py"
    If how ever, the program has any argument, it can't bi monitored by this methode.
    """
    if n >= 5:
        check_process_list()
    for process in psutil.process_iter():
        try:
            name = os.path.basename(process.cmdline()[-1])
            if name.lower() in process_list.keys():
                process_list[name.lower()] = [True, False]
        except:
            pass

async def watchdog():
    """This method scanns the system for runing processes, and if no process found, sends a mention message to all of the valid channels.
    This scan runs every 10 secound. And every 50 Secound, the program scanns for updates in the process list.
    """
    print("started")
    n = 5
    while True:
        scann(n)
        if n >= 5:
            n = 0
        else:
            n += 1
        global process_list
        global error
        for key, value in process_list.items():
            if not value[1] and not value[0]:
                error += f"{key} stopped working!\n"    #Adds the process name, to the message
                process_list[key] = [False, True]       #Don't want to send the same process more than once every time it stops
            else:
                process_list[key] = [False, value[1]]
        if error != "":
            print(error)
            channels = ["commands"]
            for channel in client.get_all_channels():
                if str(channel) in channels:
                    await channel.send(f"@here\n{error}")
            error = ""
        sleep(10)

if __name__=="__main__":
    try:
        load()
        client.run(token)
    except Exception as ex:
        print(str(ex), error=True) #If error occures, it get's written to the logs
