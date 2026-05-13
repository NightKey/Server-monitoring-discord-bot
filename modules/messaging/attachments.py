from dataclasses import dataclass


@dataclass
class Attachment:
    """
    Represents an attachment as the core sees it

    file_name: str - The name of the file
    url: str - The URL to download from
    size: int - The size of the file
    """
    file_name: str
    url: str
    size: int
