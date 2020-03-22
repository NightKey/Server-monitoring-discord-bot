def scann(process_list, piter):
    import os
    r"""Checks the currently running processes for the last argument in them. 
    If a .exe program is being checked, the last argument is the program's name.
    If a .py or other, console run program running, without any additional argument, the script's path will be the the last argument.
    For example:
        Discord's last argument: "path\to\discord\discord.exe"
        This bot's last argument: "path\to\bot\bot.py"
    If how ever, the program has any argument, it can't bi monitored by this methode.
    """
    for process in piter:
        try:
            if os.path.exists(process.cmdline()[-1]):
                name = os.path.basename(process.cmdline()[-1])
            else:
                name = os.path.basename(process.cmdline()[0])
            if name.lower() in process_list.keys():
                process_list[name.lower()] = [True, False]
        except:
            pass
    return process_list