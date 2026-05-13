from collections.abc import Callable
from functools import wraps
from typing import Any, cast

from smdb_api import Privilege

from . import NamedCallable, PrivilegedCallable, DescribedCallable
from modules.messaging import Message

def with_privilege(required: Privilege):
    def decorator(func: NamedCallable):
        @wraps(func)
        def wrapper(message: Message):
            if not message.sender.privilege.can_use(required) or (required == Privilege.Admin and not message.channel.is_admin): raise PermissionError("Permission denied")
            return func(message)

        wrapper.privilege = required
        wrapper.name = func.name
        return wrapper

    return decorator

def named(name: str | None = None):
    def decorator(func: Callable[[Message], Any]):
        func.name = name or func.__name__
        return func

    return decorator

def with_description_and_usage(*, /, descr: str, required_usage: str | None = None, optional_usage: str | None = None):
    def decorator(func: PrivilegedCallable) -> DescribedCallable:
        func.__doc__ = descr
        func.description = descr
        _optional_usage = f'<{optional_usage}>' if optional_usage else None
        func.usage = f"{func.name}{' ' if required_usage else ''}{required_usage if required_usage else ''}{' Optional:' if _optional_usage else ''}{_optional_usage if _optional_usage else ''}"
        return cast(DescribedCallable, func)

    return decorator

def requires_arguments(func: Callable[[Message], Any]):
    def decorator():
        @wraps(func)
        def wrapper(message: Message):
            if message.get_arguments() is None: raise ValueError(f"The method {func.__name__} requires at least one argument.")
            return func(message)

        return wrapper
    return decorator