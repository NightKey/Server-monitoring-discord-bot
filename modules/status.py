from typing import Collection, Dict, Union
from modules import bar
from datetime import timedelta
import psutil
valid_fstypes = ["ntfs", "ext4", "ext3"]

def get_temp() -> float:
    if not hasattr(psutil, "sensors_temperatures"):
        return None
    temps = psutil.sensors_temperatures()
    if not temps:
        return None
    cpu_temps = temps["coretemp"]
    return cpu_temps[0].current

def get_disk_status() -> Dict[str, str]:
    disks = dict()
    partitions = psutil.disk_partitions()
    for partition in partitions:
        if partition.fstype.lower() in valid_fstypes:
            disks[partition._asdict()["mountpoint"]] = psutil.disk_usage("{}".format(partition._asdict()["mountpoint"]))._asdict()
    return disks

def get_pc_status() -> Union[Dict[str, str], Dict[str, dict], Dict[str, str]]:
    """With the help of the psutil module, scanns the PC for information about all the drives, the memory and the battery, if it has one.
    Returns disk, memory, battery in this order.
    """
    disks = get_disk_status()
    memory = {"RAM":psutil.virtual_memory()._asdict(), "SWAP": psutil.swap_memory()._asdict()}
    battery = get_battery_status()
    return disks, memory, battery

def get_battery_status() -> Dict[str, str]:
    try:
        battery = psutil.sensors_battery()._asdict()
    except:
        battery = None
    return battery

def get_graphical(bar_size, in_dict=False) -> Union[str, Dict[str, str]]:
    """Using the bar module, creates a visual representation of the system's status.
    It shows the disks' and the momory's percentage, the used and the total space, and the battery's remaning lifetime, if it's pugged, and the battery's percentage.
    """
    disks, memory, battery = get_pc_status()
    bars = bar.loading_bar("", 100, size=bar_size, show="▓", off_show="░")
    if battery != None:
        bars.update(round(battery["percent"], 1), False)
        battery["bar"] = bars.bar()
    if in_dict:
        d = {}
    else:
        string = ""
    for mp, disk in disks.items():
        bars.update(round(disk["percent"], 1), False)
        dbar = bars.bar()
        tmp = round(int(disk["total"]) / (1024 **3), 2)
        total = f"{tmp} GiB"
        tmp = round(int(disk["used"]) / (1024 **3), 2)
        used = f"{tmp} GiB"
        if in_dict:
            d[f"{mp.upper()}"]=[total, used, dbar]
        else:
            string += f"{mp}: Max: {total}, used: {used}\n{dbar}\n"
    for key in ["RAM", "SWAP"]:
        tmp = round(int(memory[key]["used"]) / (1024 **3), 2)
        used = f"{tmp} GiB"
        tmp = round(int(memory[key]["total"]) / (1024 **3), 2)
        _max = f"{tmp} GiB"
        bars.update(round(memory[key]["percent"], 1), False)
        _bar = bars.bar()
        if in_dict:
            d[key]=[_max, used, _bar]
        else:
            string += f"Max RAM memory: {_max} / Used memory: {used}\n{_bar}\n"
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
