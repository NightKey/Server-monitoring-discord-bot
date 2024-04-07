from hashlib import sha256
from io import TextIOWrapper
from smdb_api import Events
from random import Random
from typing import Any, Dict, Iterable, List, Optional, Union, overload


class UserException(Exception):
    """Get's raised, when an invalid action was attempted with a user"""

    def __init__(self, reason: str) -> None:
        self.message = f"Invalid action was attempted with a user! Reason: {reason}"


def create_code(seed: bytes) -> str:
    rng = Random(seed)
    passcode = ""
    for _ in range(60):
        passcode += chr(rng.randint(33, 126))
    return sha256(passcode.encode(encoding="utf-8")).hexdigest()


class User:
    def __init__(self, id: int, discord: int = None, telegramm: int = None) -> None:
        self.id = id
        self.__discord: int = discord
        self.__telegramm: int = telegramm
        self.__code = create_code(sha256(id.to_bytes(4, "little")).digest())
        self.__status = {Events.activity: None, Events.presence_update: None}

    def get_status(self, type: Events) -> Union[str, None]:
        return self.__status[type]

    def set_status(self, type: Events, value: Union[str, None]) -> None:
        self.__status[type] = value

    def add_discord(self, discord: int, validation_code: str) -> None:
        if self.__discord is not None:
            raise UserException("A discord id was already added to user!")
        if validation_code != self.__code:
            raise UserException("Invalid validation code!")
        self.__discord = discord

    def get_discord(self) -> Union[int, None]:
        return self.__discord

    def add_telegramm(self, telegramm: int, validation_code: str) -> None:
        if (self.__telegramm is not None):
            raise UserException("A telegramm id was already added to user!")
        if validation_code != self.__code:
            raise UserException("Invalid validation code!")
        self.__telegramm = telegramm

    def get_telegramm(self) -> Union[int, None]:
        return self.__telegramm

    def get_code(self) -> str:
        return self.__code

    def __dir__(self) -> Dict[str, int]:
        return {"id": self.id, "telegramm": self.__telegramm, "discord": self.__discord}

    def __str__(self) -> str:
        return str(self.__dir__())

    def __repr__(self) -> str:
        return self.__str__()

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, (User, int)):
            return False
        if isinstance(__o, User):
            return self.id == __o.id
        return self.id == __o or self.__discord == __o or self.__telegramm == __o


class UserContainer:
    __users: List[User] = []

    def __init__(self, user_json: Optional[List[Dict[str, int]]] = None) -> None:
        if user_json is not None:
            self.__users = [User(x["id"], x["discord"], x["telegramm"])
                            for x in user_json]

    def to_file(self, fp: TextIOWrapper) -> None:
        for user in self.__users:
            fp.write(dict(user))

    @staticmethod
    def from_file(fp: TextIOWrapper) -> "UserContainer":
        users = fp.read(-1).split("\n")
        return UserContainer(users)

    def remove(self, __item: Union[User, int]) -> None:
        tmp = self[__item]
        if tmp != None:
            del self[self.__users.index(tmp)]

    def pop(self, __item: Union[User, int]) -> Union[User, None]:
        user = self[__item]
        if user != None:
            del self.__users[self.__users.index(user)]
        return user

    @overload
    def append(self, __object: User) -> None:
        if __object in self.__users:
            raise UserException(f"{__object} is already in the user list.")
        self.__users.append(__object)

    def append(self, __object: int) -> None:
        if __object in self.__users:
            raise UserException(
                f"A User with the ID {__object} is already in the user list.")
        self.__users.append(User(__object))

    def __delitem__(self, __i: int) -> None:
        del self.__users[__i]

    def __len__(self) -> int:
        return len(self.__users)

    def __getitem__(self, __o: Union[User, int]) -> Union[User, None]:
        for user in self.__users:
            if user == __o:
                return user
        return None

    def __setitem__(self, __i: Union[User, int], __o: Union[User, int]) -> None:
        index = self.__users.index(__o)
        self.__users[index] = __i

    def __str__(self) -> str:
        return str(self.__users)


if __name__ == "__main__":
    uc = UserContainer()
    uc.append(1)
    uc.append(0)
    print(uc[1])
    uc[0].add_discord(1123456, uc[0].get_code())
    uc[0].add_telegramm(1234567, uc[0].get_code())
    print(uc[0].get_status(Events.activity))
    uc[0].set_status(Events.activity, "Activity")
    print(uc[0].get_status(Events.activity))
    print(uc[1123456])
    print(uc[1234567])
    del uc[0]
    print(uc)
    input("Finished, press return!")
