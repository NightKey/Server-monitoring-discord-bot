from enum import Enum

class CommandPrivilege(Enum):
    Anyone = 0
    OnlyAdmin = 1
    OnlyUnknown = 2

    def should_show(privilege: 'CommandPrivilege', is_admin: bool) -> bool:
        if (is_admin):
            return privilege.value < 2
        else:
            return privilege.value != 1
        
class Command:
    name: str
    privilege: "CommandPrivilege"
    is_default: bool
    show_button: bool
    needs_argument: bool

    def __init__(
            self, 
            name: str, 
            privilege: "CommandPrivilege",
            is_default: bool = False, 
            show_button: bool = False,
            needs_argument: bool = False,
        ) -> None:
        
        self.name = name
        self.privilege = privilege
        self.is_default = is_default
        self.show_button = show_button
        self.needs_argument = needs_argument
