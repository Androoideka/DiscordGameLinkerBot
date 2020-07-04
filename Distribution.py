import discord
import asyncio

class Distribution(object):
    """Contains links and data for the link"""
    def __init__(self, link):
        self.link = link
        self.optional = { }

    @classmethod
    async def load(cls, distribution, content):
        for text in content:
            field = text.split(": ", 1)
            if len(field) > 1:
                distribution.optional[field[0]] = field[1]

    async def attachtoembed(self, embed):
        embed.url = self.link
        for key in self.optional.keys():
            if len(self.optional[keys]) >= 1024:
                embed.description = self.optional[key]
            else:
                embed.add_field(name=key, value=self.optional[key], inline=False)

    async def attachtostring(self, message):
        message += self.link
        for key in self.optional.keys():
            message += "\n" + key + ": " + self.optional[key]
        return message