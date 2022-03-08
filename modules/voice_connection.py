from enum import Enum
from typing import Union
from discord import VoiceClient, VoiceChannel, opus


class VCConnectionStatus(Enum):
    disconnected = 0
    differentChannel = 1
    connected = 2
    sameChannel = 4

    def from_bool(boolean: bool) -> 'VCConnectionStatus':
        return VCConnectionStatus.connected if boolean else VCConnectionStatus.disconnected
    
    def to_bool(status: 'VCConnectionStatus') -> bool:
        return status.value != VCConnectionStatus.disconnected.value

class VCConnectionRequest(Enum):
    connect = 0
    forceConnect = 1
    disconnect = 2
    forceDisconnect = 4
    
    def from_request(value: int) -> 'VCConnectionRequest':
        VCConnectionRequest(value)

class VoiceConnection:
    
    def __init__(self) -> None:
        self.is_connected = False
        self.voice_channel: Union[VoiceChannel, None] = None
        self.client: Union[VoiceClient, None] = None
    
    def connection_status(self, channel: Union[VoiceChannel, None]) -> VCConnectionStatus:
        if channel is None: return VCConnectionStatus.from_bool(self.is_connected)
        elif not self.is_connected: return VCConnectionStatus.disconnected
        elif self.voice_channel == channel: return VCConnectionStatus.sameChannel
        else: return VCConnectionStatus.differentChannel

    async def connect(self, channel: VoiceChannel) -> bool:
        if not opus.is_loaded() and not opus._load_default(): return False
        status = self.connection_status(channel)
        if status.value > 0: return False if status.value < 4 else True
        self.is_connected = True
        self.voice_channel = channel
        self.client = await self.voice_channel.connect()
        self.client
        return True
    
    async def force_reconnection(self, channel: VoiceChannel) -> bool:
        status = self.connection_status(channel)
        if status in [VCConnectionStatus.connected, VCConnectionStatus.differentChannel] : await self.client.move_to(channel)
        elif status == VCConnectionStatus.disconnected: return await self.connect(channel)

    async def disconnect(self, force: bool = False) -> None:
        if self.is_connected: await self.client.disconnect(force=force)
        self.is_connected = False
        self.client = None
        self.voice_channel = None
