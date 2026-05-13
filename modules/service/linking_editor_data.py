from dataclasses import dataclass, field
from typing import Callable, Any

from smdb_api import Privilege


@dataclass
class LinkingEditorData:
    name: str
    callback: Callable[..., Any] = field(default_factory=None)
    add_to_telegram: bool = False
    add_button: bool = False
    privilege: Privilege = field(default=Privilege.Admin)
    needs_input: bool = False
