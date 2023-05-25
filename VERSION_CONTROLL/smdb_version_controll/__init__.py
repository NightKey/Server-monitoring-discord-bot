from io import TextIOWrapper
from typing import Union, List
from time import sleep
from subprocess import Popen
import urllib3


class Version:
    VERSION_HEADER = "SMDB VERSION FILE"

    def __init__(self, major: int, minor: int, nano: int) -> None:
        self.major = int(major)
        self.minor = int(minor)
        self.nano = int(nano)

    def to_file(self):
        with open("version", "w") as fp:
            fp.write(f"{Version.VERSION_HEADER}\n{self}")

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return False
        return self.major > other.major or (self.major == other.major and self.minor > other.minor) or (self.major == other.major and self.minor == other.minor and self.nano > other.nano)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return False
        return self.major == other.major and self.minor == other.minor and self.nano == other.nano

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return False
        return other > self

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.nano}"

    @staticmethod
    def __from_version_by_list(data: list[str]) -> "Version":
        if data[0] != Version.VERSION_HEADER:
            raise IOError("Versoin file not correct!")
        version = data[1].split('.')
        return Version(version[0], version[1], version[2])

    @staticmethod
    def __from_version_by_path(path: str) -> "Version":
        data = []
        with open(path, 'r') as fp:
            data = fp.read(-1).split('\n')
        if data[0] != Version.VERSION_HEADER:
            raise IOError("Versoin file not correct!")
        version = data[1].split('.')
        return Version(version[0], version[1], version[2])

    @staticmethod
    def from_version(o: Union[str, List[Union[str, int]]]):
        if isinstance(o, str):
            return Version.__from_version_by_path(o)
        if type(o) is list:
            return Version.__from_version_by_list(o)
        return None


class Updater:

    def __init__(self, github_url: str, branch: str, prefix: str = "") -> None:
        github_url += branch if github_url.endswith("/") else f"/{branch}"
        self.github_url = github_url
        self.version = github_url.replace(
            "github.com", "raw.githubusercontent.com") + "/version"
        self.command = "git pull" if prefix == "" else f"{prefix} && git pull"

    def needs_update(self, current: Version) -> bool:
        response = urllib3.request.urlopen(self.version)
        github_version = Version.from_version(
            response.read().decode('UTF-8').split('\n'))
        return github_version > current

    def update(self, current: Version) -> bool:
        if self.needs_update(current):
            process = Popen(self.command, shell=True)
            while process.poll() is None:
                sleep(0.5)
            return process.poll() == 0


def create_version_file():
    from os import path
    version = None
    if path.exists("version"):
        version = Version.from_version("version")
    else:
        version = Version(0, 0, 0)
        print("Version file is not found in the current folder.\nIf there is a previous version file, please make sure you run this script from that folder!")
    print(f"Current version: {version}")
    v = input("Please type in the new version separated by a dot(.) (x.y.z): ")
    new = Version.from_version(v.split('.'))
    if new < version:
        print("The new version is older than the previous one!")
        a = input("Are you sure you want to use it? y/n: ")
        if a in ['y', 'Y']:
            new.to_file()
        exit()
    new.to_file()
    print("Version file created")


if __name__ == "__main__":
    create_version_file()
