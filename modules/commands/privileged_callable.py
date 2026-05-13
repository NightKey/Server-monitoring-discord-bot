from smdb_api import Privilege

from .named_callable import NamedCallable


class PrivilegedCallable(NamedCallable):
    privilege: Privilege