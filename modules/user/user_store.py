from dataclasses import dataclass, field
from json import dumps, loads
from typing import List

from .user import User


@dataclass
class UserStore:
    users: List[User] = field(default_factory=list)

    def __getitem__(self, _id: str) -> User | None:
        for user in self.users:
            if _id == user.UUID:
                return user
        else:
            return None

    def get_for_connector(self, _id: str, connector: str) -> User | None:
        for user in self.users:
            if _id == user.connector_ids[connector]:
                return user
        else:
            return None

    def put(self, item: User) -> None:
        for user in self.users:
            if user == item:
                return None
        self.users.append(item)
        return None

    def add_id(self, UUID: str, _id: str, connector: str) -> User:
        select_user: User | None = None
        for index, user in enumerate(self.users):
            if user.UUID == UUID:
                select_user = self.users.pop(index)
                break
        if select_user is None:
            raise KeyError(f"UUID {UUID} not found in user list")
        if connector in select_user.connector_ids.keys():
            self.users.append(select_user)
            raise KeyError(f"User {select_user} already has a connector id for connector {connector}")
        select_user.connector_ids[connector] = _id
        self.users.append(select_user)
        return select_user

    def to_json(self) -> str:
        return dumps({"users": self.users})

    @staticmethod
    def from_json(json: str) -> 'UserStore':
        data = loads(json)
        return UserStore(data["users"])
