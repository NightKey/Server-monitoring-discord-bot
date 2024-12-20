from connector_base import Connector
from discord import Client, Intents, errors
from threading import Thread
from voice_connection import VoiceConnection
from asyncio import get_running_loop

class Discord(Connector):
    name = "Discord"
    api: Client
    
    def __setup__(self) -> None:
        intents = Intents.default()
        intents.members = True
        intents.voice_states = True
        intents.message_content = True
        intents.presences = True

        self.api = Client(heartbeat_timeout=120, intents=intents)
    
    async def __loop(self) -> None:
        start_counter = 0
        while not self.stop_flag.is_set():
            try:
                self.logger.info("Starting Discord client")
                start_counter += 1
                await self.api.start(self.token)
            except TypeError as te:
                self.logger.error(f"Type error occured while starting client: {te}")
                self.stop()
            except errors.DiscordServerError as dse:
                self.logger.error(f"Discord server error occured while starting client: {dse}")
                self.stop()
            except Exception as ex:
                self.logger.error(f"Exception occured while starting client: {te}")
                if start_counter > 5:
                    self.stop()

    def is_alive(self) -> bool:
        return not self.api.is_closed() and self.api.is_ready()

    def __start(self) -> None:
        get_running_loop().create_task(self.__loop())

    def __clean_up(self) -> None:
        self.api.close()