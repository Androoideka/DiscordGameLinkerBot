import discord
import asyncio
import os

#Title
#Icon
#Description
#Link
#Optional
#Optional
#Optional

TOKEN = os.environ["TOKEN"]
GUILD = os.environ["GUILD"]
DATANAME = os.environ["DATA_CHANNEL"]
SERVINGNAME = os.environ["SERVING_CHANNEL"]

client = discord.Client()
reaction_emoji = None
servingchannel = None
datachannel = None

games = None
row_number = 6

async def setchannels(channel):
    global datachannel

    datachannel = discord.utils.get(client.get_all_channels(), guild__name=GUILD, name=DATANAME)
    if not channel:
        await set_serving(discord.utils.get(client.get_all_channels(), guild__name=GUILD, name=SERVINGNAME))
    else:
        await set_serving(channel)


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('gti Reset'):
        await setchannels(message.channel)
        await start()


async def set_serving(channel):
    global servingchannel

    if servingchannel:
        async for message in servingchannel.history():
            await message.delete()
    async for message in channel.history():
        await message.delete()
    servingchannel = channel


async def start():
    global games

    await setchannels(None)
    if not datachannel:
        print("Data channel not set!")
        return
    await getemoji()
    games = []
    async for message in datachannel.history():
        list = message.content.split("\n", row_number)
        if len(list) > 1:
            games.append(list[0])
    for game in reversed(games):
        message = await servingchannel.send(embed = discord.Embed(title = game))
        await message.add_reaction(reaction_emoji)


async def getemoji():
    global reaction_emoji

    message = await datachannel.fetch_message(datachannel.last_message_id)
    reaction_emoji = message.content
    print(message.content)


async def parse(request):
    title = request.embeds[0].title
    embed = None
    async for message in datachannel.history():
        if message.content.startswith(title):
            list = message.content.split("\n", row_number)
            etitle = list[0]
            eicon = list[1]
            edesc = list[2]
            eurl = list[3]    
            esize = list[4]
            embed=discord.Embed(title="Download Link", url=eurl, description=edesc, color=0x0fb0f5)
            embed.set_author(name=etitle)
            embed.set_thumbnail(url=eicon)

            for i in range(4, len(list)):
                field = list[i].split(": ", 1)
                efieldname = field[0]
                efield = field[1]
                embed.add_field(name=efieldname, value=efield, inline=False)
            return embed
    return embed
    
    
@client.event
async def on_reaction_add(reaction, user):
    if (user != client.user 
            and reaction.message.author == client.user 
            and servingchannel 
            and reaction.message.channel == servingchannel):
        if(reaction.emoji == reaction_emoji):
            embed = await parse(reaction.message)
            if not embed:
                print("Couldn't find game")
            else:
                await user.send(embed=embed)
        await reaction.message.remove_reaction(reaction.emoji, user)
        return


@client.event
async def on_ready():
    await start()
    print("Logged in")

client.run(TOKEN)