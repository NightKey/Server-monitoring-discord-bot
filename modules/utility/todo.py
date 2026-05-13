def TODO(*args) -> None:
    if len(args) == 0: raise Exception("TODO Without a messaging")
    raise Exception(args[0])
