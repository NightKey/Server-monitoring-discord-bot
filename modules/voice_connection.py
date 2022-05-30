import asyncio
from enum import Enum
from threading import Thread
from typing import Any, Callable, Coroutine, List, Union
from datetime import timedelta
from time import sleep
from discord import VoiceClient, VoiceChannel, opus, FFmpegPCMAudio, Member
from smdb_logger import Logger
from . import log_level, log_folder
from os import path

logger = Logger("VCConnectionHelper.log", log_folder=log_folder, level=log_level, log_to_console=True, use_caller_name=True, use_file_names=True)

class VCStatus(Enum):
    disconnected = 0
    differentChannel = 1
    connected = 2
    sameChannel = 4

    def from_bool(boolean: bool) -> 'VCStatus':
        return VCStatus.connected if boolean else VCStatus.disconnected
    
    def to_bool(status: 'VCStatus') -> bool:
        return status.value != VCStatus.disconnected.value

class VCRequest(Enum):
    queue = -3
    forceDisconnect = -2
    disconnect = -1
    connect = 0
    play = 1
    pause = 2
    add = 3
    resume = 4
    stop = 6
    skip = 8

    def need_path(value: "VCRequest") -> bool:
        return (value.value > 0 and value.value % 2 != 0) or value.value == 0
    
    def need_user(value: "VCRequest") -> bool:
        return value.value > 0 and value != VCRequest.add

class IdleTimer:
    def __init__(self) -> None:
        self.cancelled = False
        self.sleep_time = 2
        self.time_to_wait: int = None
        self.call_after: Callable = None
        self.thread: Thread = None

    def start(self, time_to_wait: int, call_after: Callable) -> None:
        if self.thread != None and self.thread.is_alive():
            self.cancel()
            self.thread.join()
        self.thread = Thread(target=self.__timer)
        self.cancelled = False
        self.time_to_wait = time_to_wait
        self.call_after = call_after
        self.thread.name = "IdleTimer"
        self.thread.start()

    def __timer(self) -> None:
        counter = 0
        for _ in range(0, self.time_to_wait, self.sleep_time):
            if self.cancelled: return self.__reset()
            sleep(self.sleep_time)
            counter += 1
            if self.cancelled: return self.__reset()
        else:
            if self.time_to_wait%counter != 0:
                sleep(1)
            self.call_after()
            return

    def __reset(self) -> None:
        self.thread = None
        self.cancelled = False

    def cancel(self) -> None:
        self.cancelled = True

class VoiceConnection:
    
    def __init__(self, loop: asyncio.AbstractEventLoop, track_finished_callback: Union[Callable[[str], None], None] = None) -> None:
        self.is_connected = False
        self.voice_channel: Union[VoiceChannel, None] = None
        self.client: Union[VoiceClient, None] = None
        self.play_list: List[str] = []
        self.currently_playing = ""
        self.playing = False
        self.paused = False
        self.loop = loop
        logger.header("Object created")
        self.disconnect_time = timedelta(minutes=3)
        self.disconnect_timer = IdleTimer()
        self.manually_stopped = False
        self.track_finished_callback = track_finished_callback
    
    def __connect(self, channel: VoiceChannel) -> None:
        task = self.loop.create_task(self.connect(channel))
        while not task.done():
            sleep(0.1)

    def start_disconnect_timer(self):
        self.disconnect_timer.start(self.disconnect_time.seconds, self.__disconnect)
    
    def connection_status(self, channel: Union[VoiceChannel, None]) -> VCStatus:
        if channel is None: return VCStatus.from_bool(self.is_connected)
        elif not self.is_connected: return VCStatus.disconnected
        elif self.voice_channel == channel: return VCStatus.sameChannel
        else: return VCStatus.differentChannel

    def __should_proceed(self, user: Member) -> bool:
        return self.connection_status(user.voice.channel) == VCStatus.sameChannel

    async def connect(self, channel: VoiceChannel) -> bool:
        logger.debug(f"Connecting to voice channel: {channel.name}")
        if not opus.is_loaded() and not opus._load_default(): return False
        status = self.connection_status(channel)
        if status == VCStatus.sameChannel: return True
        if status != VCStatus.disconnected: 
            await self.client.move_to(channel)
            return True
        self.is_connected = True
        self.voice_channel = channel
        self.client = await self.voice_channel.connect()
        self.client
        return True

    def __disconnect(self) -> None:
        if self.paused or not self.playing:
            self.loop.create_task(self.disconnect(True))

    async def disconnect(self, force: bool = False) -> None:
        logger.debug("Disconnecting from current channel")
        if self.is_connected: await self.client.disconnect(force=force)
        self.disconnect_timer.cancel()
        if self.playing: self.stop()
        self.__reset_state()
    
    def __reset_state(self) -> None:
        self.playing = False
        self.paused = False
        self.play_list = []
        self.currently_playing = ""
        self.is_connected = False
        self.voice_channel = None
        self.client = None

    def __track_finished(self) -> None:
        if self.track_finished_callback is not None:
            self.track_finished_callback(self.currently_playing)

    def __finished_playing(self, ex: BaseException = None) -> bool:
        if ex is not None: 
            logger.error("Exception while playing mp3 file!")
            logger.debug(f"Currently playing: {self.currently_playing}")
            logger.debug(f"Playlist: {self.play_list}")
            logger.debug(f"{ex}")
            self.__reset_state()
            return False
        if self.manually_stopped:
            self.manually_stopped = False
            return
        logger.debug("Song finished")
        self.__track_finished()
        if self.play_list != []:
            self.play_next()
            return True
        self.start_disconnect_timer()
        self.playing = False
        self.paused = False
            
    def play_next(self) -> Coroutine['VoiceConnection', Any, None]:
        if self.playing:
            self.stop()
        if len(self.play_list) <= 0: return
        tmp = str(self.play_list[0])
        logger.debug(f"Starting new song {path.split(tmp)[1]}")
        del self.play_list[0]
        self.play(tmp, _forced=True)

    def add_mp3_file_to_playlist(self, path: str) -> bool:
        if path not in self.play_list: self.play_list.append(path)
        return True
    
    def pause(self, user: Member) -> bool:
        if not self.__should_proceed(user): return False
        self.client.pause()
        self.paused = True
        self.start_disconnect_timer()
        return True

    def resume(self, user: Member) -> bool:
        if not self.__should_proceed(user): return False
        self.client.resume()
        self.paused = False
        self.disconnect_timer.cancel()
        return True

    def stop(self, user: Member = None, forced: bool = False) -> bool:
        if (user is not None and not self.__should_proceed(user)): return False
        if user is None and not forced: return False
        if not self.playing: return False
        self.playing = False
        self.paused = False
        self.manually_stopped = True
        self.client.stop()
        self.__track_finished()
        self.start_disconnect_timer()
        return True

    def skip(self, user: Member) -> bool:
        if not self.__should_proceed(user): return False
        if self.play_list == [] or not self.playing: 
            logger.debug("Playlist is empty!" if self.play_list == [] else "Not playing anything!")
            return False
        self.client.stop()
        self.__track_finished()
        self.play_next()
        return True

    def list_queue(self) -> List[str]:
        return [path.split(self.currently_playing)[1], *[path.split(item)[1] for item in self.play_list]]

    def __prepare_file(self, path: str) -> Union[FFmpegPCMAudio, None]:
        try:
            return FFmpegPCMAudio(path)
        except:
            return None

    def play(self, path: str, user: Union[Member, None] = None, _forced: bool = False) -> bool:
        if (not opus.is_loaded() and not opus._load_default()): return False
        logger.debug(f"Request file path: {path}")
        if not _forced and not self.is_connected and user.voice.channel is not None: 
            thread = Thread(target=self.__connect, args=[user.voice.channel, ])
            thread.start()
            thread.join()
        elif not _forced and user.voice.channel is None: return False
        if user is not None and not self.__should_proceed(user): return False
        if user is None and not _forced: return False
        if self.playing and not self.paused and not _forced:
            self.add_mp3_file_to_playlist(path)
            return True
        source = self.__prepare_file(path)
        if source is None:
            logger.warning(f"File was not available or readeable {path}")
            return False
        if self.playing and self.paused:
            self.paused = False
            self.play_list = []
            self.currently_playing = ""
        self.currently_playing = path
        self.client.play(source, after=self.__finished_playing)
        self.playing = True
        self.disconnect_timer.cancel()
        return True
