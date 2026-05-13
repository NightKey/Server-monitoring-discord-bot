from enum import Enum

class Capability(Enum):
    # messaging related
    HISTORY = 0
    DELETE = 1
    MODIFY = 2
    # reaction related
    REACT = 10
    # user related
    BAN = 100

all_messaging_capabilities = [
    Capability.HISTORY,
    Capability.DELETE,
    Capability.MODIFY,
]

all_reaction_capabilities = [
    Capability.REACT
]

all_user_capabilities = [
    Capability.BAN
]
