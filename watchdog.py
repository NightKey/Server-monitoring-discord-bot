import discord, psutil, os, json
from modules import writer, logger, status
from modules.scanner import scann
from time import sleep

token = ""
process_list = {}   #Formatting: "PROCESS-NAME":[IS-RUNNING, WAS-SENT-SINCE-LAST-STOPPED]
ptime = 0
error = ""
lg = logger.logger("watchdog", folder="logs")
battery_warning = False

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
    if os.path.exists(os.path.join("data", "bot.cfg")):
        try:
            with open(os.path.join("data", "bot.cfg"), "r") as f:
                tmp = json.load(f)
            token = tmp["token"]
            print("Data loading finished!")
        except: #incase there is an error, the program deletes the file, and restarts
            os.remove(os.path.join("data", "bot.cfg"))
            print("Error in cfg file... Restarting")
            os.system("restarter.py watchdog.py")
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

async def watchdog():
    """This method scanns the system for runing processes, and if no process found, sends a mention message to all of the valid channels.
    This scan runs every 10 secound. And every 50 Secound, the program scanns for updates in the process list.
    """
    global battery_warning
    channel = None
    channels = ["commands"]
    for channel in client.get_all_channels():
        if str(channel) in channels:
            break
    print("started")
    n = 5
    while True:
        if n == 5:
            check_process_list()
        global process_list
        process_list = scann(process_list, psutil.process_iter())
        if n % 2 == 0:
            _, _, battery = status.get_pc_status()
            if battery != None:
                if not battery["power_plugged"]:
                    if not battery_warning:
                        await channel.send(f"@here The Battery is not plugged in!")
                        battery_warning = True
                elif battery_warning:
                    battery_warning = False
        if n >= 5:
            n = 0
        else:
            n += 1
        global error
        for key, value in process_list.items():
            if not value[1] and not value[0]:
                error += f"{key} stopped working!\n"    #Adds the process name, to the message
                process_list[key] = [False, True]       #Don't want to send the same process more than once every time it stops
            else:
                process_list[key] = [False, value[1]]
        if error != "":
            print(error)
            await channel.send(f"@here\n{error}")
            error = ""
        if os.path.exists("stop.wd"):
            os.remove("stop.wd")
            await client.logout()
            exit(0)
        sleep(5)

if __name__=="__main__":
    try:
        load()
        client.run(token)
    except Exception as ex:
        print(str(ex), error=True) #If error occures, it get's written to the logs