from fuzzywuzzy import fuzz
from fuzzywuzzy import process
from Descriptor import Descriptor
from Descriptor import is_emoji
from dateutil.tz import gettz
from datetime import datetime
import dateutil.parser
import asyncio
import discord
import os

#commands:
#add movie/game name \n icon \n description/date \n distribution
#modify movie/game name -i/d value
#remove movie/game name
#send movie/game name [- emoji]
#rename movie/game name - newname
#append emoji link \n field \n field
#repertoire x - y

TOKEN = os.environ["TOKEN"]
GUILD = os.environ["GUILD"]
MDCNAME = os.environ["MOVIE_DATA_CHANNEL"]
GDCNAME = os.environ["GAME_DATA_CHANNEL"]
GSCNAME = os.environ["SERVING_CHANNEL"]
OWNERID = int(os.environ["OWNER"])

tzinfos = { "CET": gettz("CET"), "PKT": gettz("Asia/Karachi"), "IST": gettz("Asia/Kolkata"), "GST": gettz("Asia/Dubai") }

client = discord.Client()

owner = None

gdc = None
mdc = None
gsc = None

gamedictionary = { }
moviedictionary = { }

async def load(media):
    global gamedictionary
    global moviedictionary

    if media == "game":
        mediadict = gamedictionary
        channel = gdc
    elif media == "movie":
        mediadict = moviedictionary
        channel = mdc

    messageBundle = []
    async for message in channel.history():
        lines = message.content.split("\n")
        if await is_emoji(lines[0][0]):
            messageBundle.append(lines)
        else:
            lines[2] = await handledparam(media, lines[2])
            messageBundle.append(lines[1:])
            messageBundle.reverse()
            descriptor = Descriptor()
            await Descriptor.load(descriptor, messageBundle)
            mediadict[lines[0]] = descriptor
            messageBundle = []

async def save(mediadict):
    if mediadict == gamedictionary:
        channel = gdc
    elif mediadict == moviedictionary:
        channel = mdc
    async for message in channel.history():
        await message.delete()
    for key in mediadict.keys():
        descriptor = mediadict[key]
        messageBundle = await descriptor.save(key)
        for message in messageBundle:
            await channel.send(message)

async def getcorrectname(name, mediadict):
    nameslist = process.extract(name, mediadict.keys(), scorer = fuzz.ratio, limit = 5)
    if nameslist:
        max = nameslist[0][0]
        maxRatio = fuzz.partial_ratio(name, max[0])
        for entry in nameslist:
            currentRatio = fuzz.partial_ratio(name, entry[0])
            if currentRatio > maxRatio:
                max = entry[0]
                maxRatio = currentRatio
        return max

async def handledparam(media, parameter):
    if media == "movie":
        try:
            result = dateutil.parser.parse(parameter, tzinfos = tzinfos, dayfirst = True, fuzzy = True)
            result = result.replace(tzinfo=result.tzinfo or tzinfos["PKT"])
            return result
        except ValueError:
            return None
    elif media == "game":
        return parameter

async def add(descriptor, name, mediadict, remainder, media):
    if len(remainder) < 3:
        return "Command is supposed to be gti add game/movie name\nicon\ndescription/date (You forgot the icon or description/date)"
    remainder[2] = await handledparam(media, remainder[2])
    if not remainder[2]:
        return "Date is wrong"
    await Descriptor.read(descriptor, remainder[1:])
    mediadict[name] = descriptor
    await save(mediadict)

async def modify(descriptor, mediadict, param, media):
    arg = param.split(" ", 1)
    if len(arg) < 2:
        return "Command is supposed to be gti modify game/movie name -d/i new value (you didn't specify a new value)"
    arg = arg[1]
    if param.startswith("i"):
        descriptor.icon = arg
    if param.startswith("d"):
        arg = await handledparam(media, arg)
        if not arg:
            return "Date is wrong"
        descriptor.datea = arg
    await save(mediadict)

async def parse(command, channel):
    global gamedictionary
    global moviedictionary

    listofargs = command.split(" ", 2)
    if len(listofargs) < 3:
        return "Command, media or name not specified"

    listofargs[0] = listofargs[0].lower()
    listofargs[1] = listofargs[1].lower()

    if (listofargs[0] != "add" 
        and listofargs[0] != "modify"
        and listofargs[0] != "update"
        and listofargs[0] != "delete"
        and listofargs[0] != "remove"
        and listofargs[0] != "send"
        and listofargs[0] != "dada"
        and listofargs[0] != "rename"
        and listofargs[0] != "append"):
        return "Command doesn't exist"

    if listofargs[1] == "game":
        mediadict = gamedictionary
    elif listofargs[1] == "movie":
        mediadict = moviedictionary
    else:
        return "Misspelled the word game or movie"

    remainder = listofargs[2]
    remainder = remainder.split("\n")
    name = remainder[0]
    if listofargs[0] == "add":
        descriptor = Descriptor()
        return await add(descriptor, name, mediadict, remainder, listofargs[1])
    elif listofargs[0] == "modify" or listofargs[0] == "update":
        twonames = name.split(" -")
        if len(twonames) < 2:
            return "Command is supposed to be gti modify game/movie name -d/i new value (You're missing a -d/i)"
        name = await getcorrectname(twonames[0], mediadict)
        if not name:
            return "Name not found"
        descriptor = mediadict[name]
        return await modify(descriptor, mediadict, twonames[1], listofargs[1])
    elif listofargs[0] == "remove" or listofargs[0] == "delete":
        twonames = name.split(" - ")
        name = await getcorrectname(twonames[0], mediadict)
        if not name:
            return "Name not found"
        if len(twonames) < 2:
            del mediadict[name]
        else:
            if twonames[1] not in mediadict[name].distributions:
                return "Emoji not there"
            else:
                del mediadict[name].distributions[twonames[1]]
        await save(mediadict)
    elif listofargs[0] == "send" or listofargs[0] == "dada":
        twonames = name.split(" - ")
        name = await getcorrectname(twonames[0], mediadict)
        if not name:
            return "Name not found"
        descriptor = mediadict[name]
        if len(twonames) < 2:
            await descriptor.showcasemessage(name, channel)
        else:
            embed = await descriptor.assembleembed(name, twonames[1])
            if not embed:
                return "Emoji not there"
            await channel.send(embed=embed)
    elif listofargs[0] == "rename":
        twonames = name.split(" - ")
        if len(twonames) < 2:
            return "Command is supposed to be gti rename game/movie oldname - newname (You're missing the - separator)"
        name = await getcorrectname(twonames[0], mediadict)
        if not name:
            return "Name not found"
        descriptor = mediadict.pop(name)
        mediadict[twonames[1]] = descriptor
        await save(mediadict)
    elif listofargs[0] == "append":
        name = await getcorrectname(name, mediadict)
        if not name:
            return "Name not found"
        descriptor = mediadict[name]
        await descriptor.appendfrom(remainder, 1)
        await save(mediadict)
    else:
        return "Misspelled the command word"

async def repertoire(args, channel):
    span = args.split(" - ")
    if len(span) < 2:
        return "Command is supposed to be gti repertoire number - number (You're missing the - separator)"
    try:
        start = int(span[0])
        end = int(span[1])
    except ValueError:
        return "Command doesn't contain numbers"
    sortedArray = sorted(moviedictionary, key = lambda name: moviedictionary[name].datea)
    for key in sortedArray[start:end]:
        await moviedictionary[key].showcasemessage(key, channel)

async def reset():
    global gamedictionary
    global moviedictionary

    async for message in gdc.history():
        await message.delete()
    async for message in mdc.history():
        await message.delete()

    gamedictionary = { }
    moviedictionary = { }

async def setchannels():
    global gdc
    global mdc
    global gsc

    gdc = discord.utils.get(client.get_all_channels(), guild__name=GUILD, name=GDCNAME)
    mdc = discord.utils.get(client.get_all_channels(), guild__name=GUILD, name=MDCNAME)
    gsc = discord.utils.get(client.get_all_channels(), guild__name=GUILD, name=GSCNAME)

    await load("game")
    await load("movie")

async def start():
    global owner

    await setchannels()
    owner = client.get_user(OWNERID)
    async for message in gsc.history():
        await message.delete()
    for game in gamedictionary.keys():
        await gamedictionary[game].showcasemessage(game, gsc)

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if message.content.startswith('gti'):
        command = message.content[4:]
        if len(command) == 0:
            await message.channel.send("Available commands: add, update/modify, append, remove/delete, rename, refresh.\nOwner only: reset")
        elif message.author == owner and command.lower().startswith('reset'):
            await reset()
            await start()
        elif command.lower().startswith('refresh'):
            await start()
        elif command.lower().startswith('repertoire'):
            fragment = command[11:]
            result = await repertoire(fragment, message.channel)
            if result:
                await message.channel.send(result)
        else:
            result = await parse(command, message.channel)
            if result:
                await message.channel.send(result)

@client.event
async def on_reaction_add(reaction, user):
    if (user != client.user 
        and reaction.message.author == client.user
        and reaction.message.embeds):
        title = reaction.message.embeds[0].title
        if title in gamedictionary.keys():
            descriptor = gamedictionary[title]
        elif title in moviedictionary.keys():
            descriptor = moviedictionary[title]
        else:
            return
        embed = await descriptor.assembleembed(title, reaction.emoji)
        await user.send(embed=embed)
        await reaction.message.remove_reaction(reaction.emoji, user)

@client.event
async def on_ready():
    await start()
    print("Logged in")

client.run(TOKEN)

#Title
#Icon
#Description / Timeframe
#Distribution
#Distribution
#Distribution

#Emoji Link
#Field
#Field
#Field