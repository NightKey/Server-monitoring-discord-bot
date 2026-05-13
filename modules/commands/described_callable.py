from .privileged_callable import PrivilegedCallable


class DescribedCallable(PrivilegedCallable):
    description: str
    usage: str