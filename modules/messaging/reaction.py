from dataclasses import dataclass

@dataclass
class Reaction:
    """
    Represents a reaction as the core sees it

    me: bool - Was the reacter the connector
    reaction: str - A string representation of a reaction
    """
    me: bool
    reaction: str

    def __str__(self):
        return self.reaction
