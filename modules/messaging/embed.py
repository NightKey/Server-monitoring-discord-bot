from dataclasses import dataclass, field
from typing import List, Literal, Any

import discord.embeds

@dataclass
class Footer:
    text: str
    icon_url: str

@dataclass
class Author:
    name: str
    url: str
    icon_url: str

@dataclass
class EmbedField:
    name: str
    value: str
    inline: bool

@dataclass
class Embed:
    title: str | None = field(default=None)
    description: str | None = field(default=None)
    color: int | None = field(default=None)
    url: str | None = field(default=None)
    type: Literal['rich', 'image', 'video', 'gifv', 'article', 'link', 'poll_result'] = field(default="rich")
    fields: List[EmbedField] = field(compare=False, default_factory=list)
    author: Author | None = field(default=None)
    footer: Footer | None = field(default=None)

    def add_field(self, name: str, value: Any, inline: bool = True) -> None:
        self.fields.append(EmbedField(name=name, value=str(value), inline=inline))

    def set_author(self, name: str, url: str, icon_url: str) -> None:
        self.author = Author(name=name, url=url, icon_url=icon_url)

    def set_footer(self, text: str, icon_url: str) -> None:
        self.footer = Footer(text=text, icon_url=icon_url)

    def to_discord_embed(self) -> discord.embeds.Embed:
        result = discord.embeds.Embed(title=self.title, description=self.description, color=self.color, url=self.url, type=self.type)
        for _field in self.fields:
            result.add_field(name=_field.name, value=_field.value, inline=_field.inline)
        if self.author is not None:
            result.set_author(name=self.author.name, url=self.author.url, icon_url=self.author.icon_url)
        if self.footer is not None:
            result.set_footer(text=self.footer.text, icon_url=self.footer.icon_url)
        return result

    def to_string_representation(self) -> str:
        return str(self)

    def __str__(self) -> str:
        result = f"**{self.title}**\n"
        for _field in self.fields:
            result += f"{' - ' if not _field.inline else '  '}**{_field.name}**: {_field.value}{'\n' if not _field.inline else ''}"
        if self.footer is not None:
            result += f"\n{self.footer.text}"
        return result