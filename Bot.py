from fuzzywuzzy import fuzz
from fuzzywuzzy import process
from Descriptor import Descriptor
from Descriptor import is_emoji
from dateutil.tz import gettz
from datetime import datetime, timedelta
import dateutil.parser
import asyncio
import discord
import os

#commands:
#add movie/game name \n icon \n description/date \n distributions
#modify/update movie/game name -i/d value
#remove/delete movie/game name
#send/dada movie/game name [- emoji]
#rename movie/game name - newname
#append movie/game name emoji link \n field \n field
#repertoire x - y

TOKEN = os.environ["TOKEN"]
GUILD = os.environ["GUILD"]
MDCNAME = os.environ["MOVIE_DATA_CHANNEL"]
GDCNAME = os.environ["GAME_DATA_CHANNEL"]
GSCNAME = os.environ["SERVING_CHANNEL"]
OWNERID = int(os.environ["OWNER"])

tzinfos = { "CET": gettz("CET"), "CEST": gettz("CET"), "PKT": gettz("Asia/Karachi"), "IST": gettz("Asia/Kolkata"), "GST": gettz("Asia/Dubai") }

client = discord.Client()

owner = None

gdc = None
mdc = None
gsc = None

semaphore = 0

gamedictionary = { }
moviedictionary = { }

async def load(channel):
    global gamedictionary
    global moviedictionary

    if channel == gdc:
        mediadict = gamedictionary
    elif channel == mdc:
        mediadict = moviedictionary
    else:
        return

    messageBundle = []
    tasks = []
    async for message in channel.history():
        lines = message.content.split("\n")
        if await is_emoji(lines[0][0]):
            messageBundle.append(lines)
        else:
            lines[2] = await handledparam(channel, lines[2])
            messageBundle.append(lines[1:])
            messageBundle.reverse()
            descriptor = Descriptor()
            tasks.append(asyncio.create_task(Descriptor.load(descriptor, messageBundle)))
            mediadict[lines[0]] = descriptor
            messageBundle = []
    asyncio.gather(*tasks)

async def save(channel):
    global semaphore

    semaphore += 1
    await asyncio.sleep(5)
    semaphore -= 1
    if semaphore > 0:
        return

    if channel == gdc:
        mediadict = gamedictionary
    elif channel == mdc:
        mediadict = moviedictionary
    else: 
        return

    await channel.purge()

    for key in mediadict.keys():
        descriptor = mediadict[key]
        messageBundle = await descriptor.save(key)
        for message in messageBundle:
            await channel.send(message)

async def getcorrectname(name, mediadict):
    acronyms = { "".join([word[0] for word in x.split(" ")]):x for x in mediadict.keys()}

    nameslist = process.extract(name, mediadict.keys(), scorer = fuzz.ratio, limit = 5)
    if nameslist:
        if len(max(acronyms, key=len)) > len(name):
            nameslist += process.extract(name, acronyms.keys(), scorer = fuzz.ratio, limit = 5)
            nameslist = sorted(nameslist, key=lambda x: x[1], reverse = True)
        maxMatch = nameslist[0][0]
        maxRatio = fuzz.partial_ratio(name, maxMatch[0])
        for entry in nameslist:
            currentRatio = fuzz.partial_ratio(name, entry[0])
            if currentRatio > maxRatio:
                maxMatch = entry[0]
                maxRatio = currentRatio
        if maxMatch not in mediadict:
            maxMatch = acronyms[maxMatch]
        return maxMatch

async def handledparam(channel, parameter):
    if channel == mdc:
        try:
            result = dateutil.parser.parse(parameter, tzinfos = tzinfos, dayfirst = True, fuzzy = True)
            result = result.replace(tzinfo=result.tzinfo or tzinfos["PKT"])
            return result
        except ValueError:
            return None
    elif channel == gdc:
        return parameter

async def add(descriptor, channel, param):
    if len(param) < 3:
        return "Command is supposed to be gti add game/movie name\nicon\ndescription/date (You forgot the icon or description/date)"

    param[2] = await handledparam(channel, param[2])
    if not param[2]:
        return "Date is wrong"

    await Descriptor.read(descriptor, param[1:])
    await save(channel)

async def modify(descriptor, channel, param):
    arg = param.split(" ", 1)

    if len(arg) < 2:
        return "Command is supposed to be gti modify game/movie name -d/i new value (you didn't specify a new value)"

    arg = arg[1]
    if param.startswith("i"):
        descriptor.icon = arg
    elif param.startswith("d"):
        arg = await handledparam(channel, arg)
        if not arg:
            return "Date is wrong"
        descriptor.datea = arg
    else:
        return "Command is supposed to be gti modify game/movie name -d/i new value (You put something other than d or i)"
    await save(channel)

async def parse(command, channel):
    global gamedictionary
    global moviedictionary

    listofargs = command.split(" ", 2)
    if len(listofargs) < 3:
        return "Command, movie/game or name missing"

    listofargs[0] = listofargs[0].lower()
    listofargs[1] = listofargs[1].lower()

    if "game" in listofargs[0:2]:
        media = gdc
        mediadict = gamedictionary
    elif "movie" in listofargs[0:2]:
        media = mdc
        mediadict = moviedictionary
    else:
        return "Didn't clarify whether it's movie or game"

    remainder = listofargs[2].split("\n")
    name = remainder[0]
    if "add" in listofargs[0:2]:
        descriptor = Descriptor()
        mediadict[name] = descriptor
        return await add(descriptor, media, remainder)
    else:
        twonames = name.split(" -")
        name = await getcorrectname(twonames[0], mediadict)
        if not name:
            return "Name not found"
        elif "modify" in listofargs[0:2] or "update" in listofargs[0:2]:
            if len(twonames) < 2:
                return "Command is supposed to be gti modify game/movie name -d/i new value (You're missing a -d/i)"
            descriptor = mediadict[name]
            return await modify(descriptor, media, remainder)
        elif "remove" in listofargs[0:2] or "delete" in listofargs[0:2]:
            if len(twonames) < 2:
                del mediadict[name]
            else:
                emoji = twonames[1].strip()
                if emoji not in mediadict[name].distributions:
                    return "Emoji not there"
                else:
                    del mediadict[name].distributions[emoji]
            await save(media)
        elif "send" in listofargs[0:2] or "dada" in listofargs[0:2]:
            descriptor = mediadict[name]
            if len(twonames) < 2:
                await descriptor.showcasemessage(name, channel)
            else:
                emoji = twonames[1].strip()
                embed = await descriptor.assembleembed(name, emoji)
                if not embed:
                    return "Emoji not there"
                await channel.send(embed=embed)
        elif "rename" in listofargs[0:2]:
            if len(twonames) < 2:
                return "Command is supposed to be gti rename game/movie oldname - newname (You're missing the - separator)"
            newname = twonames[1].strip()
            descriptor = mediadict.pop(name)
            mediadict[newname] = descriptor
            await save(media)
        elif "append" in listofargs[0:2]:
            descriptor = mediadict[name]
            await descriptor.appendfrom(remainder, 1)
            await save(media)
        else:
            return "Command doesn't exist"

async def clearolder():
    sortedArray = sorted(moviedictionary, key = lambda name: moviedictionary[name].datea)
    timezone = tzinfos["PKT"]
    d = datetime.now(timezone) - timedelta(days=1)
    for key in sortedArray:
        if moviedictionary[key].datea < d:
            del moviedictionary[key]
    sortedArray[:] = [x for x in sortedArray if x in moviedictionary]
    return sortedArray

async def repertoire(args, channel):
    span = args.split("-")
    if len(span) < 2:
        return "Command is supposed to be gti repertoire number - number (You're missing the - separator)"
    try:
        start = int(span[0])
        end = int(span[1])
    except ValueError:
        return "Command doesn't contain numbers"
    sortedArray = await clearolder()
    savingtask = asyncio.create_task(save(mdc))
    for key in sortedArray[start:end]:
        await moviedictionary[key].showcasemessage(key, channel)
    await savingtask

async def reset():
    global gamedictionary
    global moviedictionary

    await gdc.purge()
    await mdc.purge()

    gamedictionary = { }
    moviedictionary = { }

async def setchannels():
    global gdc
    global mdc
    global gsc

    gdc = discord.utils.get(client.get_all_channels(), guild__name=GUILD, name=GDCNAME)
    mdc = discord.utils.get(client.get_all_channels(), guild__name=GUILD, name=MDCNAME)
    gsc = discord.utils.get(client.get_all_channels(), guild__name=GUILD, name=GSCNAME)

    await load(gdc)
    await load(mdc)
    await gsc.purge()

async def start():
    global owner

    await setchannels()
    owner = client.get_user(OWNERID)
    for game in gamedictionary.keys():
        await gamedictionary[game].showcasemessage(game, gsc)

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if message.content.startswith('gti'):
        command = message.content[4:].split(" ", 1)
        command[0] = command[0].lower()
        if len(command) == 0:
            await message.channel.send("Available commands: add, update/modify, append, remove/delete, rename, refresh.\nOwner only: reset")
        elif message.author == owner and command[0] == 'reset':
            await reset()
            await start()
        elif command[0] == 'refresh':
            await start()
        elif command[0] == 'repertoire':
            result = await repertoire(command[1], message.channel)
            if result:
                await message.channel.send(result)
        else:
            result = await parse(message.content[4:], message.channel)
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