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
        api.create_function("Test", "Test Description", dummy_callback)
        msg = smdb_api.Message("sender", "content", "channel", None, None)
        server.Test(server, msg)

def dummy_callback(_input):
    print("callback called")
    API_CreationTest.assertEqual(_input.sender, "sender")

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

class Message_function_test(unittest.TestCase):

    def test_1_message_contains_user(self):
        msg = smdb_api.Message("sender", "the message content <@!000000000000000000>", "channel", [], "called")
        self.assertTrue(msg.contains_user())
        msg = smdb_api.Message("sender", "the message content", "channel", [], "called")
        self.assertFalse(msg.contains_user())
    
    def test_2_message_returns_correct_tag(self):
        msg = smdb_api.Message("sender", "the message content <@!000000000000000000>", "channel", [], "called")
        self.assertEquals("000000000000000000", msg.get_contained_user_id())
        msg = smdb_api.Message("sender", "the message content", "channel", [], "called")
        self.assertEquals("", msg.get_contained_user_id())
        msg = smdb_api.Message("sender", "the <@!000000000000000000> message content", "channel", [], "called")
        self.assertEquals("000000000000000000", msg.get_contained_user_id())

    def test_3_message_has_attachment(self):
        msg = smdb_api.Message("sender", "the message content", "channel", [], "called")
        self.assertFalse(msg.has_attachments())
        msg = smdb_api.Message("sender", "the message content", "channel", [smdb_api.Attachment("name", "url", 12)], "called")
        self.assertTrue(msg.has_attachments())

if __name__ == "__main__":
    print("Creating dummy server...")
    services.verbose = False
    server = services.server(linking_editor, get_status, send_message, get_user, is_admin)
    server._start_for_test()
    th = threading.Thread(target=server.loop)
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
    th.join()