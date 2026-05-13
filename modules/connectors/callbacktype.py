from enum import Enum


class CallbackType(Enum):
    """The type of callback. The value represents the number of arguments."""
    READY = 1
    DISCONNECTED = 1
    COMMAND = 3
    RESULT = 3
    FAILED = 2
    PRESENCE = 4
