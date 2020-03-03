from __future__ import print_function
import sys
if sys.version_info[0] < 3:
    print("Python version 2.x.x detected!\nPlease make sure, to use python 3.x.x for best resoults!")

"""
An easy to use tool to print loading bars in aplications. You may only print one line at once!
"""
import os

class loading_bar():
    def writer(self, string):
        """
        Writes out the string variable, with an added carrage return synbole in front of it, and without a newline in it.
        Input: string - The string to be printed
        Output: Prints out the string after a carage return, with no new line at the end.
        Return: Nothing
        """
        print("\r{}".format(string), end='')

    def translate(self, value, inmin, inmax, outmin, outmax):
        """
        Translates the value from range inmin - inmax into the range outmin - outmax. Returns an integer!
        Input: Value - The value to be translated; inmin, inmax - The input value's minimum, and maximum possible value; outmin, outmax - The return values minimum and maximum possible value.
        Output: Nothing
        Return: Float rounded to 2 digits. The value is between outmin and outmax, and is the translated value of the input value.
        """
        inspan = inmax - inmin
        outspan = outmax - outmin
        scaled = float(value - inmin) / float(inspan)
        return round(outmin + (scaled * outspan), 2)

    def bar(self):
        """
        Creates a bar, with the specified parameters. The bar will be 100 
        Input: Nothing
        Output: Nothing
        Return: Returns the string representation of the created bar. The bar is created using the values stored within the class.
        """
        string = ("|" if self.corners else "")
        done = self.translate(self.done, 0, 100, 0, self.size)
        for i in range(self.size):
            if i <= done - 1: 
                string += self.char
            elif done - i != 0 and i <= done:
                string += str(int(done*10 - int(done) * 10))
            else: string += "░"
        if self.corners: string += "|"
        if self.percentage: string += " {}%".format(self.done)
        return string

    def __init__(self, message, total, show="#", corners=True, percentage=True, separator="\t"):
        self.message = message
        try:
	        self.size = (int(os.popen('stty size', 'r').read().split()[1]) - (len(message) + (2 if corners else 0) + (8 if percentage else 0) + len(separator)))
        except:
	        self.size = 100
        self.total = total
        self.char = show
        self.corners = corners
        self.percentage = percentage
        self.done = 0
        self.separator = separator
    
    def show(self):
        """ Shows the bar, without changing anything. Handels errors """
        try:
            self.writer("{}{}{}".format(self.message, self.separator, self.bar()))
        except Exception as ex:
            print("\nAn exception occured!")
            print("Exceptyon type: {}".format(str(type(ex))))
            print("Exceptyon text: {}".format(str(ex)))

    def update(self, value, show=True):
        """
        Updates the done to the given value, and shows the bar
        Input: value - The new value of the 'done' value.
        Output: Shows the loadingbar, with the new value.
        Return: Nothing
        """
        self.done = value
        if self.total != 100: self.done = self.translate(self.done, 0, self.total, 0, 100)
        if self.total < 100: self.done = int(self.done)
        if show: self.show()

if __name__=="__main__":
    import time
    print("Test 1: 0-100")
    test = loading_bar("Test 1", 100)
    for i in range(101):
        time.sleep(0.25)
        test.update((i))
    print("\nTest 2: 0-10")
    test = loading_bar("Test 2", 10)
    test.show()
    for i in range(11):
        time.sleep(0.25)
        test.update(i)
    print("\nTest 3: 0-1000")
    test = loading_bar("Test 3", 1000)
    test.show()
    for i in range(1001):
        time.sleep(0.0625)
        test.update(i)