from collections.abc import Callable
from typing import List, Any


def chunk(_list: List[Any], size: int, transformer: Callable[..., Any]):
    for i in range(0, len(_list), size):
        yield [transformer(x) for x in _list[i: i + size]]