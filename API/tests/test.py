import unittest
import os,sys,inspect,threading
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)
import smdb_api
parentdir = os.path.dirname(parentdir)
sys.path.insert(0,parentdir) 
from modules import services
from modules import response
from time import sleep

class API_CreationTest(unittest.TestCase):

    def test_1_api_validates(self):
        self.assertTrue(api.validate())
        sleep(0.5)
        self.assertTrue(api.valid)
    
    def test_2_api_gets_status(self):
        self.assertEqual(api.get_status(), {"dummy server status":"Avaleable"})

    def test_3_api_sends_message(self):
        api.send_message("Test", destination="123456789")

    def test_4_api_uses_is_admin(self):
        self.assertTrue(api.is_admin("123"))
        self.assertFalse(api.is_admin("456"))

    def test_5_api_uses_get_username(self):
        self.assertEqual(api.get_username("123"), "123")

    def test_6_api_uses_callback(self):
        api.create_function("Test", "Test Description", self.dummy_callback, [smdb_api.SENDER])
        server.Test(server, "Channel", "sender", 'input')

    def dummy_callback(self, input):
        self.assertEqual(input, "sender")

def linking_editor(data, remove=False):
    pass

def get_status():
    return {"dummy server status":"Avaleable"}

def send_message(msg, user=None):
    return response.response("Success")

def get_user(uid):
    return response.response("Success", uid)

def is_admin(uid):
    return response.response("Success", uid=="123")

if __name__ == "__main__":
    print("Creating dummy server...")
    services.verbose = False
    server = services.server(linking_editor, get_status, send_message, get_user, is_admin)
    th = threading.Thread(target=server.start)
    th.name = "Dummy server"
    th.start()
    print("Dummy server started")
    print("Setting up unit test data")
    name = "Test"
    key = server.get_api_key_for("Test")
    api = smdb_api.API(name, key, update_function=lambda: print("Update called"))
    print("Unit test started")
    unittest.main(exit=False)
    print("Stopping dummy server")
    server.stop()
    print("Finished!")
    exit(0)