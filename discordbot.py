from re import L
from discord.ext import commands
from bs4 import BeautifulSoup
from requests.structures import CaseInsensitiveDict
from PIL import Image
import discord, cassiopeia as cass, datetime, asyncio, requests, json, roleidentification, random, os
from discord.ext.commands import CommandNotFound

##########################################################################
# ---------------------------- BOT SETTINGS ---------------------------- #
##########################################################################

riotAPI = ""

watchedSummoners = ['zhdw']

sendNotificationsChannelID = ""

rankupdatesId = ""

##########################################################################
# ------------------------- SUMMONER FUNCTIONS ------------------------- #
##########################################################################

# retrieves summoner information based on summonerName
def getSummoner(summoner):
    loadingAttempts = 10
    while(True):
        loadingAttempts -= 1
        if loadingAttempts != 0:
            try:
                summonerData = requests.get("https://na1.api.riotgames.com/lol/summoner/v4/summoners/by-name/" + summoner + "?api_key=" + riotAPI).json()
                name = summonerData["name"]
                return summonerData
            except:
                pass
        else:
            print("Timed out for " + summoner)
            return

# checks to see if there is an ONGOING game going with summoner name
def isPlaying(summonerID):
    results = requests.get("https://na1.api.riotgames.com/lol/spectator/v4/active-games/by-summoner/" + summonerID + "?api_key=" + riotAPI)
    if results.status_code != 200:
        return False
    else:
        return True

# checks to see if the summoner exists
def summonerExists(summonerName):
    r = requests.get("https://na1.api.riotgames.com/lol/summoner/v4/summoners/by-name/" + summonerName +  "?api_key=" + riotAPI).json()
    if "name" in r:
        return True
    else:
        print("Summoner name " + summonerName + " does not exist!")
        return False

async def getHighestRank(summoner):
    summonerId = getSummoner(summoner)["id"]
    highestTier = "UNRANKED"
    highestRank = "IV"
    lastTier = -1
    lastRank = -1
    tiers = ["IRON","BRONZE","SILVER","GOLD","PLATINUM","DIAMOND","MASTER","GRANDMASTER","CHALLENGER"]
    ranks = ["IV","III","II","I"]
    r = requests.get("https://na1.api.riotgames.com/lol/league/v4/entries/by-summoner/" + summonerId +"?api_key=" + riotAPI ).json()
    for x in r:
        if tiers.index(x["tier"]) > lastTier:
            highestTier = x["tier"]
            highestRank = x["rank"]
            lastTier = tiers.index(x["tier"])
            lastRank = ranks.index(x["rank"])
        elif tiers.index(x["tier"]) == lastTier:
            if ranks.index(x["rank"]) > lastRank:
                highestRank = x["rank"]
                lastRank = ranks.index(x["rank"])
    return {"tier":highestTier,"rank":romanToInt(highestRank)}

###########################################################################
# ------------------------------- PARSERS ------------------------------- #
###########################################################################

# converts seconds to a formatted minutes and seconds
def convert(seconds):
    seconds = seconds % (24 * 3600)
    hour = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
      
    return "%02dm %02ds" % (minutes, seconds)

# parses a queue ID
def parseQueue(queue):
    for q in requests.get("https://static.developer.riotgames.com/docs/lol/queues.json").json():
        if (queue == q["queueId"]):
            queueType = q["description"]
            return queueType.replace("games","").replace("5v5","")

# parse item build from leagueOfGraphs
def parseBuild(list):
    meow = []
    for x in str(list).split("\n"):
        if "<img alt" in x:
            meow.append(x.split("<img alt=\"")[1].split("\"")[0])
    return meow

# parse runes from leagueOfGraphs
def parseRunes(list):
    runes = []
    runeImages = []
    for x in list:
        stringed = str(x)
        if "<div style=\"\">" in stringed:
            runes.append(stringed.split("<img alt=\"")[1].split("\"")[0])
            rune = stringed.split("class=\"perk-")[1].split("-")[0]
            if rune.startswith("5"):
                runeImages.append("https://www.ultimate-bravery.net/images/rune-stats/" + rune + ".png")
            else:
                runeImages.append("https://www.ultimate-bravery.net/images/runes/" + rune + ".png")
    # items
    return [runes,runeImages]

def parseList(list):
    parsedString = ""
    for x in list:
        parsedString += x + "\n"
    return parsedString

def romanToInt(roman):
    rom_val = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
    int_val = 0
    for i in range(len(roman)):
        if i > 0 and rom_val[roman[i]] > rom_val[roman[i - 1]]:
            int_val += rom_val[roman[i]] - 2 * rom_val[roman[i - 1]]
        else:
            int_val += rom_val[roman[i]]
    return int_val

def downloadImage(url):
    fileName = str(random.randint(1000,2000)) + url.split("/")[-1]
    f = open("./discord bots/leaguebot/" + fileName,"wb")
    response = requests.get(url)
    f.write(response.content)
    f.close()
    return "./discord bots/leaguebot/" + fileName

latestVersion = requests.get("https://ddragon.leagueoflegends.com/realms/na.json").json()["v"]
championDatabase = requests.get("https://ddragon.leagueoflegends.com/cdn/" + latestVersion + "/data/en_US/championFull.json").json()

###########################################################################
# --------------------------- DISCORD METHODS --------------------------- #
###########################################################################

bot = commands.Bot(command_prefix='!')

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Streaming(name="Patch " + latestVersion, url='https://www.twitch.tv/muffincheez'))
    print('=> Logged in as {0.user}'.format(bot))

checkCooldown = int(len(watchedSummoners)/0.8)

async def background_task():
    await bot.wait_until_ready()

    while(True):
        for summoner in watchedSummoners:
            if summonerExists(summoner):
                await gameCheck()
                await gamerCheck(summoner)
                await getLeagueRanks(summoner)
                await asyncio.sleep(checkCooldown)
        await asyncio.sleep(60)

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    searchQuery = "https://na.op.gg/multisearch/na?summoners="
    if "joined the lobby" in str(message.content):
        for line in message.content.split("\n"):
            name = line.split(" joined")[0].replace(" ","+")
            searchQuery += name + "%2C"
        await message.channel.send(searchQuery[:len(searchQuery)-3],reference=message)
        try:
            await message.delete()
        except:
            pass
    elif "님이 로비에 참가하셨습니다" in str(message.content):
        for line in message.content.split("\n"):
            name = line.split(" 님이")[0].replace(" ","+")
            searchQuery += name + "%2C"
        await message.channel.send(searchQuery[:len(searchQuery)-3],reference=message)
        try:
            await message.delete()
        except:
            pass
    elif "がロビーに参加しました" in str(message.content):
        for line in message.content.split("\n"):
            name = line.split("がロビーに参加しました")[0].strip().replace(" ","+")
            searchQuery += name + "%2C"
        await message.channel.send(searchQuery[:len(searchQuery)-3],reference=message)
        try:
            await message.delete()
        except:
            pass
    await bot.process_commands(message)

cass.set_riot_api_key(riotAPI)
# This command sends you the information of a champion's passive and abilities descriptions and cooldowns
@bot.command()
async def abilities(ctx, *, args):
    keys = { 0:"Q", 1:"W", 2:"E",3:"R" }
    embed=discord.Embed(timestamp=datetime.datetime.utcnow(), color=0x62C979)
    args = args.title().replace(" ","")
    if args not in championDatabase["data"]:
        await ctx.reply(content="That is not a valid champion! :x:\n\nYour input: `" + args + "`")
        return
    try:
        champicon = "https://ddragon.leagueoflegends.com/cdn/" + latestVersion + "/img/champion/" + args + ".png"
        embed.set_thumbnail(url=champicon)
    except:
        await ctx.reply(content="Could not find any data for " + args + " :x:")
        return

    embed.set_author(name=args + " Information", icon_url=champicon)
    embed.set_footer(text="powered by shdw 👻",icon_url="https://i.imgur.com/ri6NrsN.png")
    embed.add_field(name="NA.OP.GG",value="https://na.op.gg/champion/" + args + "/statistics/",inline=True)
    embed.add_field(name="Passive - " + championDatabase["data"][args.title()]["passive"]["name"],value=championDatabase["data"][args.title()]["passive"]["description"],inline=False)
    try:
        for x in range(len(championDatabase["data"][args.title()]["spells"])):
            embed.add_field(name=keys[x] + " - " + championDatabase["data"][args.title()]["spells"][x]["name"],value=championDatabase["data"][args.title()]["spells"][x]["description"] + "\nCooldown: **" + str(championDatabase["data"][args.title()]["spells"][x]["cooldown"]) + "**" ,inline=False)
    except Exception as e:
        pass
    await ctx.send(embed=embed)

foundGames = []
watchedGames = []

# Checks if any watched games are finished
# Also empties if the length of foundGames is greater than 10
async def gameCheck():
    global foundGames
    global watchedGames

    cleanGames = False

    winEmotes = ["https://i.imgur.com/ieWmRWb.png","https://i.imgur.com/batBGnC.png","https://i.imgur.com/LAyQgjj.png","https://i.imgur.com/qIchruZ.png","https://i.imgur.com/Q6nkk8B.png","https://i.imgur.com/EQQjHIY.png","https://i.imgur.com/ltYuPxd.png","https://i.imgur.com/goS2pMy.png","https://i.imgur.com/5yBfUAN.png"]
    sadEmotes = ["https://i.imgur.com/q3u0c40.png","https://i.imgur.com/iurybFl.png","https://i.imgur.com/osGlgMV.png","https://i.imgur.com/RUKiZo7.png","https://i.imgur.com/u7eFXdk.png","https://i.imgur.com/fTptmUI.png","https://i.imgur.com/LyD9a3O.png"]

    if (len(foundGames) >= 10):
        cleanGames = True
        print("[LEAGUE BOT] Cleaning foundGames ...")
        foundGames.clear()

    for game in watchedGames:
        matchID = game[0]
        summonerPUUID = game[1]

        if (cleanGames):
            foundGames.append(int(matchID))
            
        matchResults = requests.get("https://americas.api.riotgames.com/lol/match/v5/matches/NA1_" + matchID + "?api_key=" + riotAPI)
        if (matchResults.status_code == 200):
            print("[LEAGUE BOT] Match ID " + matchID + " has been finished")
            matchData = matchResults.json()
            key = matchData["metadata"]["participants"].index(summonerPUUID)
            gameWon = matchData["info"]["participants"][key]["win"]
            gameDuration = matchData["info"]["gameDuration"]
            embed = game[2]
            currentSummoner = requests.get("https://na1.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/"+ summonerPUUID + "?api_key=" + riotAPI).json()
            summonerName = currentSummoner["name"]
            await getLeagueRanks(summonerName)
            if (gameWon):
                await embed.add_reaction("🇼")
                newEmbed=discord.Embed(description="NA.OP.GG: [Link 🔗](https://na.op.gg/summoner/userName=" + summonerName.replace(" ","") +") | Mobalytics: [Link 🔗](https://app.mobalytics.gg/lol/profile/na/"+ summonerName.replace(" ","") +") | LeagueOfGraphs: [Link 🔗](https://www.leagueofgraphs.com/summoner/na/"+ summonerName.replace(" ","%20") +")\n\nMatch Duration: `"+ convert(gameDuration)+"` [*](https://app.mobalytics.gg/lol/match/na/" + summonerName.replace(" ","") + "/" + matchID + ")",timestamp=datetime.datetime.utcnow(), color=0x8BD3E6)
                emote = random.choice(winEmotes)
            else:
                await embed.add_reaction("🇱")
                newEmbed=discord.Embed(description="NA.OP.GG: [Link 🔗](https://na.op.gg/summoner/userName=" + summonerName.replace(" ","") +") | Mobalytics: [Link 🔗](https://app.mobalytics.gg/lol/profile/na/"+ summonerName.replace(" ","") +") | LeagueOfGraphs: [Link 🔗](https://www.leagueofgraphs.com/summoner/na/"+ summonerName.replace(" ","%20") +")\n\nMatch Duration: `"+ convert(gameDuration)+"` [*](https://app.mobalytics.gg/lol/match/na/" + summonerName.replace(" ","") + "/" + matchID + ")",timestamp=datetime.datetime.utcnow(), color=0xE7548C)
                emote = random.choice(sadEmotes)

            blueteamcomp = ""
            redteamcomp = ""
            blueTeamKills = 0
            redTeamKills = 0
            queue = matchData["info"]["queueId"]
            for q in requests.get("https://static.developer.riotgames.com/docs/lol/queues.json").json():
                if (queue == q["queueId"]):
                    queueType = q["description"]

            count = 0
            for player in matchData["info"]["participants"]:
                if count < 5:
                    rank = await getHighestRank(player["summonerName"].strip())
                    blueteamcomp += "\n" + player["championName"].replace("MonkeyKing","Wukong") + " - `" + player["summonerName"].strip() + "` (" + str(player["kills"]) + "/" + str(player["deaths"]) + "/" + str(player["assists"]) + ") `" + rank["tier"][0] + str(rank["rank"]) + "`"
                    blueTeamKills += player["kills"]
                else:
                    rank = await getHighestRank(player["summonerName"].strip())
                    redteamcomp += "\n" + player["championName"].replace("MonkeyKing","Wukong") + " - `" + player["summonerName"].strip() + "` (" + str(player["kills"]) + "/" + str(player["deaths"]) + "/" + str(player["assists"]) + ") `" + rank["tier"][0] + str(rank["rank"]) + "`"
                    redTeamKills += player["kills"]
                count+=1
            
            newEmbed.set_author(name=summonerName + "'s Match Results",icon_url="https://ddragon.leagueoflegends.com/cdn/" + latestVersion + "/img/profileicon/" + str(currentSummoner["profileIconId"]) + ".png")
            newEmbed.set_footer(text="ID: " + matchID + " • powered by shdw 👻",icon_url="https://i.imgur.com/ri6NrsN.png")
            newEmbed.add_field(name="Gamemode",value=queueType.replace("games","").replace("5v5",""),inline = False)
            newEmbed.add_field(name="Blue Team (" + str(blueTeamKills) + " kills)",value=blueteamcomp, inline=True)
            newEmbed.add_field(name="Red Team (" + str(redTeamKills) + " kills)",value=redteamcomp, inline=True)
            newEmbed.set_image(url=emote)
            await embed.edit(embed=newEmbed)
            watchedGames.remove(game)

# Checks if a summoner is currently in game (does not work for TFT)
champion_roles = roleidentification.pull_data()
async def gamerCheck(name):
    try:
        global foundGames
        global watchedGames

        try:
            summoner = getSummoner(name)
            name = summoner["name"]
        except:
            return

        if (isPlaying(summoner["id"])):
            current = cass.get_current_match(summoner=name,region="NA")
            if current.id in foundGames:
                return # game is already found, prevents spam

            matchQueue = parseQueue(requests.get("https://na1.api.riotgames.com/lol/spectator/v4/active-games/by-summoner/" + summoner["id"] + "?api_key=" + riotAPI).json()["gameQueueConfigId"])
            
            # format discord embed with teams, players, and champions
            blueteam = []
            blueSummoners = {}
            for x in current.blue_team.participants:
                blueSummoners[x.champion.id] = x.summoner.name
                blueteam.append(x.champion.id)
            blueteamcomp = ""
            try:
                blueteamroles = roleidentification.get_roles(champion_roles,blueteam)
                for x in blueteamroles:
                    rank = await getHighestRank(blueSummoners[blueteamroles[x]].strip())
                    blueteamcomp += "\n" + championDatabase["keys"][str(blueteamroles[x])].replace("MonkeyKing","Wukong") + " - `" + blueSummoners[blueteamroles[x]].strip() + "` " + rank["tier"][0] + str(rank["rank"])
            except:
                for x in blueSummoners:
                    blueteamcomp += "\n" + championDatabase["keys"][str(x)].replace("MonkeyKing","Wukong") + " - `" + blueSummoners[x].strip() + "`"

            redteam = []
            redSummoners = {}
            for x in current.red_team.participants:
                redSummoners[x.champion.id] = x.summoner.name
                redteam.append(x.champion.id)
            redteamcomp = ""
            try:
                redteamroles = roleidentification.get_roles(champion_roles,redteam)
                for x in redteamroles:
                    rank = await getHighestRank(redSummoners[redteamroles[x]].strip())
                    redteamcomp += "\n" + championDatabase["keys"][str(redteamroles[x])].replace("MonkeyKing","Wukong") + " - `" + redSummoners[redteamroles[x]].strip() + "` " + rank["tier"][0] + str(rank["rank"])
            except:
                for x in redSummoners:
                    redteamcomp += "\n" + championDatabase["keys"][str(x)].replace("MonkeyKing","Wukong") + " - `" + redSummoners[x].strip() + "`"

            embed=discord.Embed(description="NA.OP.GG: [Link 🔗](https://na.op.gg/summoner/userName=" + name.replace(" ","") +") | Mobalytics: [Link 🔗](https://app.mobalytics.gg/lol/profile/na/"+ name.replace(" ","") +") | Porofessor: [Link 🔗](https://porofessor.gg/live/na/"+ name.replace(" ","%20") + ")",timestamp=datetime.datetime.utcnow(), color=0x62C979)
            embed.set_author(name=name + "'s Live Game Found 👁‍🗨",icon_url="https://ddragon.leagueoflegends.com/cdn/" + latestVersion + "/img/profileicon/" + str(summoner["profileIconId"]) + ".png")
            embed.set_footer(text="ID: " + str(current.id) + " • powered by shdw 👻",icon_url="https://i.imgur.com/ri6NrsN.png")
            embed.add_field(name="Gamemode",value=matchQueue,inline = False)
            embed.add_field(name="Blue Team",value=blueteamcomp, inline=True)
            embed.add_field(name="Red Team",value=redteamcomp, inline=True)
            sentEmbed = await bot.get_channel(int(sendNotificationsChannelID)).send(embed=embed)

            # if successfully sent, add to foundGames, and watchedGames
            foundGames.append(current.id)
            print("[LEAGUE BOT] Now watching Match ID " + str(current.id) + " for " + name)
            watchedGames.append([str(current.id),summoner["puuid"],sentEmbed])
    except Exception as e:
        print("Gamercheck error: ")
        print(e)
    
leaguePointsBook = {}
for x in watchedSummoners:
    leaguePointsBook[x] = {}

async def getLeagueRanks(summoner):
    summonerInfo = getSummoner(summoner)
    try:
        summonerID = summonerInfo["id"]
    except:
        return

    req = requests.get("https://na1.api.riotgames.com/lol/league/v4/entries/by-summoner/"+ summonerID + "?api_key=" + riotAPI).json()

    #print("Checking ranks ...")
    try:
        for gamemode in req:
            queue = gamemode["queueType"]
            tier = gamemode["tier"]
            rank = gamemode["rank"]
            leaguePoints = gamemode["leaguePoints"]

            try:
                if leaguePointsBook[summoner][queue]["rank"] != tier + " " + rank:
                    
                    leagueOfLegendsRanks = {"IRON":"https://static.wikia.nocookie.net/leagueoflegends/images/f/fe/Season_2022_-_Iron.png","BRONZE":"https://static.wikia.nocookie.net/leagueoflegends/images/e/e9/Season_2022_-_Bronze.png","SILVER":"https://static.wikia.nocookie.net/leagueoflegends/images/4/44/Season_2022_-_Silver.png","GOLD":"https://static.wikia.nocookie.net/leagueoflegends/images/8/8d/Season_2022_-_Gold.png","PLATINUM":"https://static.wikia.nocookie.net/leagueoflegends/images/3/3b/Season_2022_-_Platinum.png","DIAMOND":"https://static.wikia.nocookie.net/leagueoflegends/images/e/ee/Season_2022_-_Diamond.png","MASTER":"https://static.wikia.nocookie.net/leagueoflegends/images/e/eb/Season_2022_-_Master.png","GRANDMASTER":"https://static.wikia.nocookie.net/leagueoflegends/images/f/fc/Season_2022_-_Grandmaster.png","CHALLENGER":"https://static.wikia.nocookie.net/leagueoflegends/images/0/02/Season_2022_-_Challenger.png"}
                    print(summoner + " rank changed from " + leaguePointsBook[summoner][queue]["rank"] + " to " + tier + " " + rank + "!")

                    embed=discord.Embed(timestamp=datetime.datetime.utcnow(), color=0xff00ff)
                    embed.set_author(name="🚨 " + summoner.upper() + " RANK UPDATE 🚨",icon_url="https://ddragon.leagueoflegends.com/cdn/" + latestVersion + "/img/profileicon/" + str(summonerInfo["profileIconId"]) + ".png")
                    embed.add_field(name=queue.replace("_"," ").replace("SR","").replace("5x5",""),value=leaguePointsBook[summoner][queue]["rank"] + " **----->** " + tier + " " + rank)
                    embed.set_footer(text="powered by shdw 👻",icon_url="https://i.imgur.com/ri6NrsN.png")
                    embed.set_image(url=leagueOfLegendsRanks[tier])
                    await bot.get_channel(int(rankupdatesId)).send(embed=embed)
                elif leaguePointsBook[summoner][queue]["leaguePoints"] < leaguePoints:
                    print(summoner + " gained " + str(leaguePoints-leaguePointsBook[summoner][queue]["leaguePoints"]) + " LP in " + queue)

                    embed=discord.Embed(description="**+" + str(leaguePoints-leaguePointsBook[summoner][queue]["leaguePoints"]) + "** LP in " + queue.replace("_"," ").replace("SR","").replace("5x5",""),timestamp=datetime.datetime.utcnow(), color=0x62C979)
                    embed.set_author(name="🚨 " + summoner.upper() + " LP UPDATE 🚨",icon_url="https://ddragon.leagueoflegends.com/cdn/" + latestVersion + "/img/profileicon/" + str(summonerInfo["profileIconId"]) + ".png")
                    embed.add_field(name=queue.replace("_"," ").replace("SR","").replace("5x5",""),value=tier + " " + rank + " - " + str(leaguePoints) + " LP")
                    embed.set_footer(text="powered by shdw 👻",icon_url="https://i.imgur.com/ri6NrsN.png")
                    embed.set_thumbnail(url="https://i.imgur.com/0m1B3Et.png")
                    await bot.get_channel(int(rankupdatesId)).send(embed=embed)
                elif leaguePointsBook[summoner][queue]["leaguePoints"] > leaguePoints:
                    print(summoner + " lost " + str(leaguePointsBook[summoner][queue]["leaguePoints"]-leaguePoints) + " LP in " + queue)

                    embed=discord.Embed(description="*-" + str(leaguePointsBook[summoner][queue]["leaguePoints"]-leaguePoints) + "* LP in " + queue.replace("_"," ").replace("SR","").replace("5x5",""),timestamp=datetime.datetime.utcnow(), color=0xE7548C)
                    embed.set_author(name="🚨 " + summoner.upper() + " LP UPDATE 🚨",icon_url="https://ddragon.leagueoflegends.com/cdn/" + latestVersion + "/img/profileicon/" + str(summonerInfo["profileIconId"]) + ".png")
                    embed.add_field(name=queue.replace("_"," ").replace("SR","").replace("5x5",""),value=tier + " " + rank + " - " + str(leaguePoints) + " LP")
                    embed.set_footer(text="powered by shdw 👻",icon_url="https://i.imgur.com/ri6NrsN.png")
                    embed.set_thumbnail(url="https://i.imgur.com/bTORHF3.png")
                    await bot.get_channel(int(rankupdatesId)).send(embed=embed)
            except Exception as e:
                pass

            # update dictionary
            leaguePointsBook[summoner][queue] = {"leaguePoints":leaguePoints,"rank":tier + " " + rank}
    except Exception as e:
        #print(e)
        pass
    #print("Done checking ranks")

# red side jungle tips for a given champion
@bot.command()
async def red(ctx,*,args):
    r = requests.get("https://jungler.gg/champions/" + args)
    soup = BeautifulSoup(r.text,"html.parser")

    try:
        championImage = soup.find("img",class_="ct-image champion-header-image_img")["src"]
    except:
        await ctx.reply("That is not a valid champion!")
        return

    proClearTitle = soup.find("h2",class_="ct-headline jungle-path-title-label").text
    proClearGuide = soup.find("div",class_="oxy-rich-text jungle-pathing-container_inner__data___text").text
    redSideProClear = soup.find("div",class_="oxy-tab-content tabs-contents-8127-tab jungle-pathing_tabscontents__two").img["src"]

    redSideProEmbed = discord.Embed(description=proClearGuide,timestamp=datetime.datetime.utcnow(), color=0xFF6D6A)
    redSideProEmbed.set_author(name=proClearTitle,icon_url=championImage,url="https://jungler.gg/champions/" + args.replace(" ","-"))
    redSideProEmbed.set_image(url=redSideProClear)
    redSideProEmbed.add_field(name="NA.OP.GG Item Build ⬇️",value="https://na.op.gg/champions/" + args.lower().replace(" ",""))
    redSideProEmbed.set_footer(text="from Jungler.GG",icon_url="https://i.imgur.com/ri6NrsN.png")

    noobClearTitle = soup.find_all("h2",class_="ct-headline jungle-path-title-label")[-1].text
    noobClearGuide = soup.find_all("div",class_="oxy-rich-text jungle-pathing-container_inner__data___text")[-1].text
    redSideNoobClear = soup.find_all("div",class_="oxy-tab-content tabs-contents-8127-tab jungle-pathing_tabscontents__two")[-1].img["src"]

    redSideNoobEmbed = discord.Embed(description=noobClearGuide,timestamp=datetime.datetime.utcnow(), color=0xFF6D6A)
    redSideNoobEmbed.set_author(name=noobClearTitle,icon_url=championImage,url="https://jungler.gg/champions/" + args.replace(" ","-"))
    redSideNoobEmbed.set_image(url=redSideNoobClear)
    redSideNoobEmbed.add_field(name="NA.OP.GG Item Build ⬇️",value="https://na.op.gg/champions/" + args.lower().replace(" ",""))
    redSideNoobEmbed.set_footer(text="from Jungler.GG",icon_url="https://i.imgur.com/ri6NrsN.png")

    await ctx.send(embed=redSideProEmbed)
    await ctx.send(embed=redSideNoobEmbed)
 
# blue side jungle tips for a given champion
@bot.command()
async def blue(ctx,*,args):
    r = requests.get("https://jungler.gg/champions/" + args)
    soup = BeautifulSoup(r.text,"html.parser")

    try:
        championImage = soup.find("img",class_="ct-image champion-header-image_img")["src"]
    except:
        await ctx.reply("That is not a valid champion!")
        return

    proClearTitle = soup.find("h2",class_="ct-headline jungle-path-title-label").text
    proClearGuide = soup.find("div",class_="oxy-rich-text jungle-pathing-container_inner__data___text").text
    blueSideProClear = soup.find("div",class_="oxy-tab-content tabs-contents-8127-tab jungle-pathing_tabscontents__one").img["src"]

    blueSideProEmbed = discord.Embed(description=proClearGuide,timestamp=datetime.datetime.utcnow(), color=0x8BD3E6)
    blueSideProEmbed.set_author(name=proClearTitle,icon_url=championImage,url="https://jungler.gg/champions/" + args.replace(" ","-"))
    blueSideProEmbed.set_image(url=blueSideProClear)
    blueSideProEmbed.add_field(name="NA.OP.GG Item Build ⬇️",value="https://na.op.gg/champions/" + args.lower().replace(" ",""))
    blueSideProEmbed.set_footer(text="from Jungler.GG")

    noobClearTitle = soup.find_all("h2",class_="ct-headline jungle-path-title-label")[-1].text
    noobClearGuide = soup.find_all("div",class_="oxy-rich-text jungle-pathing-container_inner__data___text")[-1].text
    blueSideNoobClear = soup.find_all("div",class_="oxy-tab-content tabs-contents-8127-tab jungle-pathing_tabscontents__one")[-1].img["src"]

    blueSideNoobEmbed = discord.Embed(description=noobClearGuide,timestamp=datetime.datetime.utcnow(), color=0x8BD3E6)
    blueSideNoobEmbed.set_author(name=noobClearTitle,icon_url=championImage,url="https://jungler.gg/champions/" + args.replace(" ","-"))
    blueSideNoobEmbed.set_image(url=blueSideNoobClear)
    blueSideNoobEmbed.add_field(name="NA.OP.GG Item Build ⬇️",value="https://na.op.gg/champions/" + args.lower().replace(" ",""))
    blueSideNoobEmbed.set_footer(text="from Jungler.GG")

    await ctx.send(embed=blueSideProEmbed)
    await ctx.send(embed=blueSideNoobEmbed)
    
# mmr command using whatismymmr.com
@bot.command()
async def mmr(ctx, *, args):
    try:
        summonerInfo = getSummoner(args)
        r = requests.get("https://na.whatismymmr.com/api/v1/summoner?name=" + args).json()
        embed=discord.Embed(description="Here is your MMR for the following modes",timestamp=datetime.datetime.utcnow(), color=0xAC4FC6)
        embed.set_author(name="🪙 " + args.upper() + "'s MMR 🪙")
        embed.add_field(name="Ranked",value=str(r["ranked"]["closestRank"]))
        embed.add_field(name="Normal",value=str(r["normal"]["closestRank"]))
        embed.add_field(name="ARAM",value=str(r["ARAM"]["closestRank"]))
        embed.set_footer(text="from whatismymmr.com",icon_url="https://i.imgur.com/ri6NrsN.png")
        embed.set_thumbnail(url="https://ddragon.leagueoflegends.com/cdn/" + latestVersion + "/img/profileicon/" + str(summonerInfo["profileIconId"]) + ".png")
        await ctx.reply(embed=embed)
    except:
        await ctx.reply("We don't have enough data for that summoner!")

# helper functions for matchup 

def createImage(runes1,runes2):
    try:
        runeImages = [*runes1,*runes2]
        files = []
        for x in range(len(runeImages)):
            fileName = downloadImage(runeImages[x])
            files.append(fileName)
        primaryRune = Image.open(files[0]).convert('RGBA').resize((120,120))
        rune1 = Image.open(files[1]).convert('RGBA').resize((60,60))
        rune2 = Image.open(files[2]).convert('RGBA').resize((60,60))
        rune3 = Image.open(files[3]).convert('RGBA').resize((60,60))
        secondaryRune1 = Image.open(files[4]).convert('RGBA').resize((60,60))
        secondaryRune2 = Image.open(files[5]).convert('RGBA').resize((60,60))
        statRune1 = Image.open(files[6]).convert('RGBA')
        statRune2 = Image.open(files[7]).convert('RGBA')
        statRune3 = Image.open(files[8]).convert('RGBA')
        dst = Image.new('RGBA', (primaryRune.width + primaryRune.width, primaryRune.height + rune1.height + rune2.height + rune3.height))
        dst.paste(primaryRune, (0,0))
        dst.paste(rune1, (30,primaryRune.height))
        dst.paste(rune2, (30,primaryRune.height + rune1.height))
        dst.paste(rune3, (30,primaryRune.height + rune1.height + rune2.height))
        dst.paste(secondaryRune1, (primaryRune.width,45))
        dst.paste(secondaryRune2, (primaryRune.width,45 + secondaryRune1.height))
        dst.paste(statRune1, (primaryRune.width + 15,50 + secondaryRune1.height + secondaryRune2.height))
        dst.paste(statRune2, (primaryRune.width + 15,50 + secondaryRune1.height + secondaryRune2.height + statRune1.height))
        dst.paste(statRune3, (primaryRune.width + 15,50 + secondaryRune1.height + secondaryRune2.height + statRune1.height + statRune2.height))
        for x in files:
            os.remove(x)
        dst.save("./discord bots/leaguebot/matchupPath.png","PNG")
        return True
    except:
        return False

# matchup command which returns winrates against a champion
# starting build, gold diff @ 15, core and end builds
@bot.command()
async def matchup(ctx,arg1,arg2):
    await ctx.message.add_reaction('🔁')
    try:
        url = "https://www.leagueofgraphs.com/champions/builds/" + arg1.lower() + "/vs-" + arg2.lower()

        headers = CaseInsensitiveDict()
        headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9"
        headers["Accept-Language"] = "en-US,en;q=0.9"
        headers["Cache-Control"] = "max-age=0"
        headers["Connection"] = "keep-alive"
        headers["Cookie"] = "lolg_euconsent=nitro; darkMode=1; lolg_euconsent=nitro"
        headers["Sec-Fetch-Dest"] = "document"
        headers["Sec-Fetch-Mode"] = "navigate"
        headers["Sec-Fetch-Site"] = "none"
        headers["Sec-Fetch-User"] = "?1"
        headers["Sec-GPC"] = "1"
        headers["Upgrade-Insecure-Requests"] = "1"
        headers["User-Agent"] = requests.get("https://fake-useragent.herokuapp.com/browsers/0.1.11").json()["browsers"]["chrome"][0]

        results = requests.get(url, headers=headers)
        soup = BeautifulSoup(results.text,"html.parser")

        champ1WR = str(soup.find("div",id="graphDD1").text.strip())
        champ2WR = str(soup.find("div",id="graphDD2").text.strip())
        goldDiff = str(soup.find("div",id="graphDD3").text.strip())

        # runes
        primaryRunes = parseRunes(soup.find("table",class_="perksTableOverview").find_all("div",class_="img-align-block"))
        secondaryRunes = parseRunes(soup.find("table",class_="perksTableOverview secondary").find_all("div",class_="img-align-block"))

        # build
        startingBuild = parseBuild(soup.find_all("div",class_="iconsRow")[1])
        coreBuild = parseBuild(soup.find_all("div",class_="iconsRow")[2])
        boots = parseBuild(soup.find_all("div",class_="iconsRow")[3])
        endBuild = parseBuild(soup.find_all("div",class_="iconsRow")[4])

        try:
            embed=discord.Embed(description="Boots against " + arg2.title() + ": **" + str(boots).split("[\"")[1].split("\"")[0] + "**",timestamp=datetime.datetime.utcnow(), color=0xAC4FC6)
            embed.set_author(name=arg1.title() + " vs " + arg2.title(),icon_url="https://ddragon.leagueoflegends.com/cdn/" + latestVersion + "/img/champion/" + arg1.title() + ".png")
        except:
            embed=discord.Embed(title=arg1.title() + " vs " + arg2.title(),timestamp=datetime.datetime.utcnow(), color=0xAC4FC6)
        
        embed.add_field(name=arg1.title() + "'s WR",value=champ1WR)
        embed.add_field(name=arg2.title() + "'s WR",value=champ2WR,inline=True)
        embed.add_field(name="Gold Diff @ 15",value=goldDiff,inline=True)
        embed.add_field(name="Primary Runes",value=parseList(primaryRunes[0]))
        embed.add_field(name="Secondary Runes",value=parseList(secondaryRunes[0]),inline=True)
        embed.add_field(name="Starting Build",value=parseList(startingBuild))
        embed.add_field(name="Core Build",value=parseList(coreBuild),inline=True)
        embed.add_field(name="End Build",value=parseList(endBuild),inline=True)

        if (createImage(primaryRunes[1],secondaryRunes[1])):
            uploadFile = requests.post("https://shdwrealm.com/upload-file",files = {'file': open("./discord bots/leaguebot/matchupPath.png",'rb')}).json()["link"]
            embed.set_thumbnail(url=uploadFile)

        embed.set_footer(text="from leagueofgraphs.com",icon_url="https://i.imgur.com/ri6NrsN.png")
        await ctx.message.clear_reaction('🔁')
        await ctx.reply(embed=embed)
        await ctx.message.add_reaction('✅')
    except Exception as e:
        print(e)
        await ctx.message.add_reaction('❌')
        await ctx.reply("Could not find any information on this matchup! Did you check spelling?")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, CommandNotFound):
        return
    raise error

def createItemImage(itemPath, summonerSpells, runesPath,spellKeyImage):
    files = []
    for x in itemPath:
        itemUrl = itemPath[x]
        fileName = downloadImage(itemUrl)
        files.append(fileName)
    for x in summonerSpells:
        spellUrl = summonerSpells[x]
        fileName = downloadImage(spellUrl)
        files.append(fileName)
    for x in runesPath["primary"]:
        runeUrl = "https://www.ultimate-bravery.net/images/runes/" + runesPath["primary"][x]
        fileName = downloadImage(runeUrl)
        files.append(fileName)
    for x in runesPath["secondary"]:
        runeUrl = "https://www.ultimate-bravery.net/images/runes/" + runesPath["secondary"][x]
        fileName = downloadImage(runeUrl)
        files.append(fileName)
    for x in runesPath["stats"]:
        runeUrl = "https://www.ultimate-bravery.net/images/rune-stats/" + x["image"]
        fileName = downloadImage(runeUrl)
        files.append(fileName)
    spellKeyImg = downloadImage(spellKeyImage)
    files.append(spellKeyImg)
    im1 = Image.open(files[0]).convert('RGBA')
    im2 = Image.open(files[1]).convert('RGBA')
    im3 = Image.open(files[2]).convert('RGBA')
    im4 = Image.open(files[3]).convert('RGBA')
    im5 = Image.open(files[4]).convert('RGBA')
    im6 = Image.open(files[5]).convert('RGBA')
    spell1 = Image.open(files[6]).convert('RGBA').resize((64,64))
    spell2 = Image.open(files[7]).convert('RGBA').resize((64,64))
    primaryRune = Image.open(files[8]).convert('RGBA').resize((120,120))
    rune1 = Image.open(files[9]).convert('RGBA').resize((60,60))
    rune2 = Image.open(files[10]).convert('RGBA').resize((60,60))
    rune3 = Image.open(files[11]).convert('RGBA').resize((60,60))
    secondaryRune1 = Image.open(files[12]).convert('RGBA').resize((60,60))
    secondaryRune2 = Image.open(files[13]).convert('RGBA').resize((60,60))
    statRune1 = Image.open(files[14]).convert('RGBA')
    statRune2 = Image.open(files[15]).convert('RGBA')
    statRune3 = Image.open(files[16]).convert('RGBA')
    spellKey = Image.open(files[17]).resize((128,128))
    dst = Image.new('RGBA', (im1.width + im2.width + im3.width + im4.width + im5.width + im6.width, im1.height + im2.height + primaryRune.height + rune1.height + rune2.height + rune3.height))
    # items
    dst.paste(im1, (0, 0))
    dst.paste(im2, (im1.width, 0))
    dst.paste(im3, (im1.width + im2.width,0))
    dst.paste(im4, (im1.width + im2.width + im3.width,0))
    dst.paste(im5, (im1.width + im2.width + im3.width + im4.width,0))
    dst.paste(im6, (im1.width + im2.width + im3.width + im4.width + im5.width,0))
    # summoner spells
    dst.paste(spell1, (im1.width + im2.width + im3.width + spellKey.width, im5.height + 15))
    dst.paste(spell2, (im1.width + im2.width + im3.width + spellKey.width, im5.height + spell1.height + 15))
    # primary runes
    dst.paste(primaryRune, (0,10 + im1.height))
    dst.paste(rune1, (30,10 + im1.height + primaryRune.height))
    dst.paste(rune2, (30,10 + im1.height + primaryRune.height + rune1.height))
    dst.paste(rune3, (30,10 + im1.height + primaryRune.height + rune1.height + rune2.height))
    # secondary runes
    dst.paste(secondaryRune1, (110, 10 + im1.height + primaryRune.height))
    dst.paste(secondaryRune2, (110, 10 + im1.height + secondaryRune1.height + primaryRune.height))
    # stat runes
    dst.paste(statRune1, (125, 10 + im1.height + primaryRune.height + secondaryRune1.height + secondaryRune2.height))
    dst.paste(statRune2, (125, 10 + im1.height + primaryRune.height + secondaryRune1.height + secondaryRune2.height + statRune1.height))
    dst.paste(statRune3, (125, 10 + im1.height + primaryRune.height + secondaryRune1.height + secondaryRune2.height + statRune1.height + statRune2.height))
    # first maxed spell
    dst.paste(spellKey, (im1.width + im2.width + im3.width, im5.height + 15))
    for x in files:
        os.remove(x)
    dst.save("./discord bots/leaguebot/itemBuildPath.png","PNG")
    return True

def getBuild(mapId, champId):
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive',
        'Content-Type': 'application/json;charset=UTF-8',
        'Origin': 'https://www.ultimate-bravery.net',
        'Referer': 'https://www.ultimate-bravery.net/',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
        'Sec-GPC': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.114 Safari/537.36',
    }

    # map - 11 SR, 12 ARAM
    json_data = {
        'map': mapId,
        'level': 3,
        'roles': [
            0,
            1,
            2,
            3,
            4,
        ],
        'language': 'en',
        'champions': [
            champId,
        ],
    }

    response = requests.post('https://api2.ultimate-bravery.net/bo/api/ultimate-bravery/v1/classic/dataset', headers=headers, json=json_data).json()
    return response

@bot.command()
async def build(ctx,map,champName):
    await ctx.message.add_reaction('🔁')

    if map.lower() == "sr":
        map = 11
    elif map.lower() == "aram":
        map = 12
    else:
        map = 11

    champName = champName.title().replace(" ","")
    if champName not in championDatabase["data"]:
        await ctx.reply(content="That is not a valid champion! :x:\n\nYour input: `" + champName + "`")
        await ctx.message.clear_reaction('🔁')
        await ctx.message.add_reaction('❌')
        return
        
    champId = championDatabase["data"][champName]["key"]

    chosenBuild = getBuild(map,int(champId))
    try:
        buildTitle = chosenBuild["data"]["title"]
        champName = chosenBuild["data"]["champion"]["name"]
        champImage = chosenBuild["data"]["champion"]["image"]

        # build
        spellKeyImage = chosenBuild["data"]["champion"]["spell"]["image"]
        spellKey = chosenBuild["data"]["champion"]["spell"]["key"]
        spellKeyName = chosenBuild["data"]["champion"]["spell"]["name"]

        itemPath = chosenBuild["data"]["items"]
        summonerSpells = chosenBuild["data"]["summonerSpells"]
        runesPath = chosenBuild["data"]["runes"]
        if (createItemImage(itemPath, summonerSpells, runesPath,spellKeyImage)):
            uploadFile = requests.post("https://shdwrealm.com/upload-file",files = {'file': open("./discord bots/leaguebot/itemBuildPath.png",'rb')})
            embed=discord.Embed(title=buildTitle,url="https://www.ultimate-bravery.net/Classic?s=" + str(chosenBuild["data"]["seedId"]),timestamp=datetime.datetime.utcnow(), color=0xAC4FC6)
            embed.set_thumbnail(url=champImage)
            embed.add_field(name="First Maxed Spell",value=spellKey + " - " + spellKeyName)
            embed.set_image(url=uploadFile.json()["link"])
            embed.set_footer(text="Ultimate Bravery",icon_url="https://www.ultimate-bravery.net/images/BB_LOGO_NAV.png")
            await ctx.message.clear_reaction('🔁')
            await ctx.message.add_reaction('✅')
            await ctx.reply(embed=embed)
    except:
        await ctx.message.clear_reaction('🔁')
        await ctx.message.add_reaction('🛑')

bot.loop.create_task(background_task())
print("[LEAGUE BOT] Using information from Patch " + latestVersion)
bot.run('')
