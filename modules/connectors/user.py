from dataclasses import dataclass
from typing import List

@dataclass
class UserId:
    connector: str
    id: str

@dataclass
class User:
    name: str
    ids: List[UserId]
    isAdmin: bool
