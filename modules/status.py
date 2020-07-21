import psutil
from modules import bar
from datetime import timedelta

a = 97
z = 123

def get_pc_status():
    """With the help of the psutil module, scanns the PC for information about all the drives, the memory and the battery, if it has one.
    Returns disk, memory, battery in this order.
    """
    disk = dict()
    for letter in range(a, z):
        try:
            disk[chr(letter)] = psutil.disk_usage("{}:".format(chr(letter)))._asdict()
        except:
            pass
    memory = psutil.virtual_memory()._asdict()
    try:
        battery = psutil.sensors_battery()._asdict()
    except:
        battery = None
    return disk, memory, battery

def get_graphical(bar_size, in_dict=False):
    """Using the bar module, creates a visual representation of the system's status.
    It shows the disks' and the momory's percentage, the used and the total space, and the battery's remaning lifetime, if it's pugged, and the battery's percentage.
    """
    disk, memory, battery = get_pc_status()
    bars = bar.loading_bar("", 100, size=bar_size, show="▓", off_show="░")
    for letter in range(a, z):
        try:
            bars.update(round(disk[chr(letter)]["percent"], 1), False)
            disk[chr(letter)]["bar"] = bars.bar()
        except:
            pass
    bars.update(round(memory["percent"], 1), False)
    memory["bar"] = bars.bar()
    if battery != None:
        bars.update(round(battery["percent"], 1), False)
        battery["bar"] = bars.bar()
    if in_dict:
        d = {}
    else:
        string = ""
    for letter in range(a, z):
        try:
            letter = chr(letter)
            dbar = disk[letter]["bar"]
            tmp = round(int(disk[letter]["total"]) / (1024 **3), 2)
            total = f"{tmp} GB"
            tmp = round(int(disk[letter]["used"]) / (1024 **3), 2)
            used = f"{tmp} GB"
            if in_dict:
                d[letter]=[total, used, dbar]
            else:
                string += f"{letter}: Max: {total}, used: {used}\n{dbar}\n"
        except:
            pass
    tmp = round(int(memory["used"]) / (1024 **3), 2)
    used = f"{tmp} GB"
    tmp = round(int(memory["free"]) / (1024 **3), 2)
    free = f"{tmp} GB"
    if in_dict:
        d["Memory"]=[free, used, memory['bar']]
    else:
        string += f"Free memory: {free} / Used memory: {used}\n{memory['bar']}\n"
    if battery == None:
        if in_dict:
            d['Battery']=["Not detected"]
        else:
            string += "Battery not detected!"
    else:
        tmp = "" if battery["power_plugged"] else "not "
        if in_dict:
            d["Battery"]=[timedelta(seconds=battery['secsleft']), f"The power is {tmp}plugged in", battery['bar']]
        else:
            string += f"Remaining battery life: {timedelta(seconds=battery['secsleft'])} and it's {tmp}plugged in.\nBattery status:\n {battery['bar']}"
    if in_dict:
        return d
    else:
        return string


if __name__ == "__main__" :
    print(get_graphical(25))
