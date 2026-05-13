from typing import Any

from modules.messaging import Message


class NamedCallable:
    def __call__(self, message: Message) -> Any:
        pass
    name: str