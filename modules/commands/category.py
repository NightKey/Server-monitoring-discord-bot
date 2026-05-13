from enum import Enum
from typing import List, cast

from .described_callable import DescribedCallable

class CommandCallable(DescribedCallable):
    """
    :raises:
         PermissionError - If user has insufficient permission to run the command
         ValueError - If the command requires an argument but go nothing
    """
    category: Category

class Category(Enum):
    HARDWARE = "Anything that interacts with the host machine."
    NETWORK = "Anything that interacts with the host's network."
    SOFTWARE = "Anything that interacts with the programs running on the host machine."
    BOT = "Anything that interacts with the bot's workings."
    SERVER = "Anything that interacts with the discord server."
    USER = "Anything that interacts with the users."
    AUDIO = "Anything that plays audio trough the bot."

    def __call__(self, func: DescribedCallable) -> CommandCallable:
        func.category = self
        return cast(CommandCallable, func)

    @staticmethod
    def all() -> List["Category"]:
        return [
            Category.HARDWARE,
            Category.NETWORK,
            Category.SOFTWARE,
            Category.BOT,
            Category.SERVER,
            Category.USER,
            Category.AUDIO
        ]