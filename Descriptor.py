from emoji import UNICODE_EMOJI
from Distribution import Distribution
from datetime import datetime
import discord
import asyncio

async def is_emoji(s):
    count = 0
    for emoji in UNICODE_EMOJI:
        count += s.count(emoji)
        if count > 1:
            return False
    return bool(count)

class Descriptor(object):
    """Attributes for any kind of media content"""
    def __init__(self, icon=None, datea=None):
        self.icon = icon
        self.datea = datea
        self.distributions = { }

    @classmethod
    async def load(cls, descriptor, content):
        descriptor.icon = content[0][0]
        descriptor.datea = content[0][1]

        for i in range(1,len(content)):
            distributionid = content[i][0].split(" ")
            if len(distributionid) > 1:
                distribution = Distribution(distributionid[1])
                descriptor.distributions[content[i][0][0]] = distribution
                await Distribution.load(distribution, content[i][1:])

    @classmethod
    async def read(cls, descriptor, content):
        descriptor.icon = content[0]
        descriptor.datea = content[1]

        i = 2
        await descriptor.appendfrom(content, i)

    async def appendfrom(self, content, i):
        distribution = None
        while i < len(content):
            if await is_emoji(content[i][0]):
                if distribution:
                    await Distribution.load(distribution, content[start:i])
                if content[i][0] in self.distributions:
                    distribution = self.distributions[content[i][0]]
                else:
                    distributionid = content[i].split(" ")
                    if len(distributionid) > 1:
                        distribution = Distribution(distributionid[1])
                        self.distributions[content[i][0]] = distribution
                start = i+1
            i += 1
        if distribution:
            await Distribution.load(distribution, content[start:i])

    async def updatedistribution(self, emoji, distribution):
        if await is_emoji(emoji):
            self.distributions[emoji] = distribution

    async def showcasemessage(self, name, channel):
        embed = discord.Embed(title = name)
        if type(self.datea) is datetime:
            embed.timestamp = self.datea
        message = await channel.send(embed = embed)
        for key in self.distributions.keys():
            await message.add_reaction(key)

    async def assembleembed(self, name, emoji):
        if emoji not in self.distributions:
            return None
        embed = embed=discord.Embed(title=name, color=0x0fb0f5)
        embed.set_thumbnail(url=self.icon)
        if type(self.datea) is datetime:
            embed.timestamp = self.datea
        else:
            embed.add_field(name="Instructions", value=self.datea, inline=False)
        await self.distributions[emoji].attachtoembed(embed)
        return embed

    #Format: name \n icon \n datea
    async def save(self, name):
        messageBundle = []
        messageBundle.append(name + "\n" + self.icon + "\n")
        if type(self.datea) is datetime:
            messageBundle[0] += self.datea.strftime("%c %Z")
        else:
            messageBundle[0] += self.datea
        for key in self.distributions.keys():
            message = key + " "
            message = await self.distributions[key].attachtostring(message)
            messageBundle.append(message)
        return messageBundle