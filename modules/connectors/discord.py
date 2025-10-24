from typing import Dict, Callable
from connector import Connector, VoiceStatus
from smdb_api import Interface
from . import Server
from discord import Client, Intents, errors
from discord import Message as DSMessage
from discord import User as DSUser
from asyncio import AbstractEventLoop

class Discord(Connector):
    token: str
    client: Client
    me: DSUser
    
    def __init__(self, server: Server, token: str, loop: AbstractEventLoop, *args, **kwargs):
        super().__init__(server, Interface.Discord, *args, **kwargs)
        self.token = token
        self.voice_status = VoiceStatus()
        intents = self.create_intents()
        self.client = Client(intents=intents, heartbeat_timeout=120)
        self.loop = loop
    
    def create_intents(self) -> Intents:
        intents = Intents.default()
        intents.members = True
        intents.voice_states = True
        intents.message_content = True
        intents.presences = True
        return intents

    def start(self, *args, **kwargs):
        self.logger.info("Starting Discord connector")
        try:
            task = self.loop.create_task(self.client.start(self.token))
            while not task.done() and not self.stop_event.is_set():
                self.stop_event.wait(.1)
            if (ex := task.exception()) != None:
                raise ex
            if self.stop_event.is_set():
                self.stop()
        except TypeError as te:
            self.logger.error(f"Exception during discord startup: {te}")
            self.stop()
        except errors.DiscordServerError as dse:
            self.logger.error(f"Discord error: {dse}")
            self.stop()
        except Exception as ex:
            self.logger.error(f"Exception during discord startup: {te}")
            self.stop()
    