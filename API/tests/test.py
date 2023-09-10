try:
    from time import sleep
    from smdb_logger import Logger, LEVEL
    import unittest
    import os
    import sys
    import inspect
    import threading
finally:
    currentdir = os.path.dirname(os.path.abspath(
        inspect.getfile(inspect.currentframe())))
    parentdir = os.path.dirname(currentdir)
    sys.path.insert(0, parentdir)
    import smdb_api
    parentdir = os.path.dirname(parentdir)
    sys.path.insert(0, parentdir)
    from modules import services


class API_CreationTest(unittest.TestCase):

    def test_1_api_validates(self):
        self.assertTrue(api.validate(100))
        sleep(0.5)
        self.assertTrue(api.valid)

    def test_2_api_gets_status(self):
        self.assertEqual(api.get_status(), "Avaleable")

    def test_3_api_sends_message(self):
        api.send_message("Test", destination="123456789",
                         interface=smdb_api.Interface.Discord)

    def test_4_api_uses_is_admin(self):
        self.assertTrue(api.is_admin("123"))
        self.assertFalse(api.is_admin("456"))

    def test_5_api_uses_get_username(self):
        self.assertEqual(api.get_username("123"), "123")

    def test_6_api_uses_callback(self):
        api.create_function("Test", "Test Description", self.dummy_callback)
        msg = smdb_api.Message("sender", "content", "channel", [
        ], "Test", smdb_api.Interface.Discord)
        sleep(1)
        server.Test(server, msg)

    def test_7_connect_to_user(self):
        self.assertTrue(api.connect_to_voice("test"))
        self.assertTrue(api.disconnect_from_voice())
        self.assertTrue(api.play_file("Test", "123456789"))
        self.assertTrue(api.add_file("Test2"))
        self.assertTrue(api.pause_currently_playing("123456789"))
        self.assertTrue(api.resume_paused("123456789"))
        self.assertTrue(api.skip_currently_playing("123456789"))
        self.assertTrue(api.stop_currently_playing("123456789"))
        self.assertListEqual(["TestData"], api.get_queue())

    def test_8_rejects_same_message(self):
        self.counter = 0
        api.create_function("Test2", "Test", self.reject)
        sleep(1)
        msg = smdb_api.Message("sender", "content", "channel", [
        ], "Test2", interface=smdb_api.Interface.Discord)
        server.Test2(server, msg)
        server.Test2(server, msg)
        self.assertEqual(self.counter, 1)

    def test_9_can_save_and_load_configs(self):
        file_name = "test.conf"
        smdb_api.API.create_config("name", "key", "ip", 12345, file_name)
        self.assertTrue(os.path.exists(file_name))
        _api = smdb_api.API.from_config(file_name, print)
        self.assertEqual(_api.name, "name")
        self.assertEqual(_api.key, "key")
        self.assertEqual(_api.ip, "ip")
        self.assertEqual(_api.port, 12345)
        os.remove(file_name)

    def reject(self, _input):
        self.counter += 1

    def dummy_callback(self, _input):
        self.assertEqual(_input.sender, "sender")


class Message_function_test(unittest.TestCase):

    def test_10_message_contains_user(self):
        msg = smdb_api.Message(
            "sender", "the message content <@!000000000000000000>", "channel", [], "called", interface=smdb_api.Interface.Discord)
        self.assertTrue(msg.contains_user())
        msg = smdb_api.Message(
            "sender", "the message content", "channel", [], "called", interface=smdb_api.Interface.Discord)
        self.assertFalse(msg.contains_user())

    def test_11_message_returns_correct_tag(self):
        msg = smdb_api.Message(
            "sender", "the message content <@!000000000000000000>", "channel", [], "called", interface=smdb_api.Interface.Discord)
        self.assertEqual("000000000000000000", msg.get_contained_user_id())
        msg = smdb_api.Message(
            "sender", "the message content", "channel", [], "called", interface=smdb_api.Interface.Discord)
        self.assertEqual("", msg.get_contained_user_id())
        msg = smdb_api.Message(
            "sender", "the <@!000000000000000000> message content", "channel", [], "called", interface=smdb_api.Interface.Discord)
        self.assertEqual("000000000000000000", msg.get_contained_user_id())

    def test_12_message_has_attachment(self):
        msg = smdb_api.Message(
            "sender", "the message content", "channel", [], "called", interface=smdb_api.Interface.Discord)
        self.assertFalse(msg.has_attachments())
        msg = smdb_api.Message("sender", "the message content", "channel", [
                               smdb_api.Attachment("name", "url", 12)], "called", interface=smdb_api.Interface.Discord)
        self.assertTrue(msg.has_attachments())

    def test_13_can_get_current_status(self):
        sleep(1)
        self.assertEqual("0 activity", api.get_user_status(
            0, smdb_api.Events.activity))
        self.assertEqual("0 presence_update", api.get_user_status(
            0, smdb_api.Events.presence_update))
    
    def test_14_cleanup(self):
        sleep(1)
        api.close("Ended")


if __name__ == "__main__":
    print("Creating dummy server...")
    services.logger = Logger(
        "test.log", storage_life_extender_mode=False, log_to_console=True, use_caller_name=True, level=LEVEL.DEBUG)
    server = services.Server()
    server._start_for_test()

    th = threading.Thread(target=server.loop)
    th.name = "Dummy server"
    th.start()

    @server.callback()
    def linking_editor(data, remove=False):
        pass
    @server.callback()
    def get_status():
        return smdb_api.Response(smdb_api.ResponseCode.Success, "Avaleable")
    @server.callback()
    def send_message(user=None):
        return smdb_api.Response(smdb_api.ResponseCode.Success)
    @server.callback()
    def get_user(uid):
        return smdb_api.Response(smdb_api.ResponseCode.Success, uid)
    @server.callback()
    def is_admin(uid):
        return smdb_api.Response(smdb_api.ResponseCode.Success, uid == "123")
    @server.callback()
    def voice_connection_controll(request, user_id=None, path=None):
        return smdb_api.Response(smdb_api.ResponseCode.Success, ["TestData"])
    @server.callback()
    def get_user_status(uid, type):
        return smdb_api.Response(smdb_api.ResponseCode.Success, f"{uid} {smdb_api.Events(type).name}")
    
    print("Dummy server started")
    print("Setting up unit test data")
    name = "Test"
    key = server.get_api_key_for("Test")
    api = smdb_api.API(
        name, key, update_function=lambda: print("Update called"))
    print("Unit test started")
    main = threading.Thread(target=unittest.main)
    main.name = "Unittest"
    main.start()
    main.join()
    print("Stopping dummy server")
    server.stop()
    th.join()
    print("Finished!")
    exit(0)
