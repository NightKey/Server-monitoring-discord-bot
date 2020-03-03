import datetime
import os

class logger:
    def __init__(self, name, folder=""):
        """
        Sets up the logger class.
        Input: name - The name of the program being logged, folder - The folder the logs go in. It can create this folder, if it isn't exist.
        Output: Nothing
        Return: Nothing
        """
        if folder != "":
            if not os.path.exists(folder):
                os.mkdir(folder)
        self.file = "{}.lg".format(os.path.join(folder, name))
        with open(self.file, "a") as f:
            f.write("OPENED AT {}\n".format(datetime.datetime.now()))     
    def log(self, string, error=False):
        """
        Logs the given event into the file. It can log Errors with an alert part in front of it.
        Input: string - The string to be written out; error - Determines, if the string contains an errorlog or no
        Output: Nothing
        Return: Nothing
        """
        with open(self.file, 'a') as f:
            if error:
                f.write("---ERROR OCCURED!---\n")
            f.write("{} - {}\n".format(datetime.datetime.now().time(), string))
    def close(self):
        """
        Closes the log file.
        """
        with open(self.file, "a") as f:
            f.write("CLOSED AT {}\n".format(datetime.datetime.now()))

if __name__ == "__main__":
    log = logger("test")
    log.log("test log")
    log.close()