from enum import Enum
from typing import List

from smdb_api import Privilege

from modules.capability import Capability


class Command:
    name: str
    privilege: Privilege
    required: List[Capability]
    is_default: bool
    show_button: bool
    needs_argument: bool

    def __init__(
            self, 
            name: str, 
            privilege: Privilege,
            required: List[Capability] | None = None,
            is_default: bool = False, 
            show_button: bool = False,
            needs_argument: bool = False,
        ) -> None:
        
        self.name = name
        self.privilege = privilege
        self.required = required if required is not None else []
        self.is_default = is_default
        self.show_button = show_button
        self.needs_argument = needs_argument

    def __eq__(self, other) -> bool:
        if isinstance(other, Command):
            return self.name == other.name
        elif isinstance(other, str):
            return self.name == other
        else:
            return False

    def should_show_button(self, show_all: bool, privilege: Privilege) -> bool:
        return self.show_button and (self.is_default or show_all) and self.privilege.should_show(privilege)


class WellKnownCommands(Enum):
    GetUser = Command(name="get_user", privilege=Privilege.Internal, is_default=True)