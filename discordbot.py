from re import L
from bs4 import BeautifulSoup
from requests.structures import CaseInsensitiveDict
from PIL import Image
import discord, cassiopeia as cass, datetime, asyncio, requests, roleidentification, random, os
from discord.ext.commands import CommandNotFound

##########################################################################
# ---------------------------- BOT SETTINGS ---------------------------- #
##########################################################################

# riot developer api
riotAPI = ""

# discord bot token
botToken = ""

# list of summoners to watch for LIVE GAMES, FINISHED GAMES, RANK PROGRESS
watchedSummoners = ['lrradical']

# discord channel to get notifications
channelId = "00000000000000000000"

# set your browser user agent here (pulling stats from mobalytics)
# https://www.whatismybrowser.com/detect/what-is-my-user-agent/
userAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36"

# instructions go into /icondownloader/ of this repo
useIconEmojis = False
iconsPastebin = "https://pastebin.com/raw/YNNGddHi"
orbId = "<:orb:1040379476061716510>"
uggId = "<:ugg:1045463729875197993>"
opggId = "<:opgg:1045463718445715456>"
mobalyticsId = "<:mobalyticsgg:1045463770178277436>"
porofessorId = "<:porofessorgg:1045463965016277052>"
masterId = "<:master:1041177640448557146>"
grandmasterId = "<:grandmaster:1041177639165108246>"
challengerId = "<:challenger:1040403289386262598>"

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
                summonerData = requests.get(f"https://na1.api.riotgames.com/lol/summoner/v4/summoners/by-name/{summoner}?api_key={riotAPI}",timeout=10).json()
                name = summonerData["name"]
                return summonerData
            except:
                pass
        else:
            print(f"[BLITZCRANK] Timed out trying to get summoner data for {summoner}")
            return

# gets tier average of a given team
def tierAverage(teamranks):
    leagueTiers = {"`I4`":1,"`I3`":2,"`I2`":3,"`I1`":4,"`B4`":5,"`B3`":6,"`B2`":7,"`B1`":8,"`S4`":9,"`S3`":10,"`S2`":11,"`S1`":12,"`G4`":13,"`G3`":14,"`G2`":15,"`G1`":16,"`P4`":17,"`P3`":18,"`P2`":19,"`P1`":20,"`D4`":21,"`D3`":22,"`D2`":23,"`D1`":24,"<:master:1041177640448557146>":25,"<:grandmaster:1041177639165108246>":26,"<:challenger:1040403289386262598>":27}

    avg = 0
    count = 0
    for x in teamranks:
        if x in leagueTiers:
            avg += leagueTiers[x]
            count += 1
    avg = avg//count
    for y in leagueTiers:
        if leagueTiers[y] == avg:
            return y

# returns the match MVPs for blue and red side
def getMatchMvp(matchId,summonerName):
    json_data = {
        'operationName': 'LolMatchDetailsQuery',
        'variables': {
            'region': 'NA',
            'summonerName': summonerName,
            'matchId': int(matchId),
        },
        'extensions': {
            'persistedQuery': {
                'version': 1,
                'sha256Hash': '258067fe2687bae0b272f9a4a4b32b19638921440ecfb8b729502d849841b7dc',
            },
        },
    }

    response = requests.post('https://app.mobalytics.gg/api/lol/graphql/v1/query', headers={'authority':'app.mobalytics.gg','accept':'*/*','accept-language':'en_us','content-type':'application/json','origin':'https://app.mobalytics.gg','sec-ch-ua-mobile':'?0','sec-ch-ua-platform':'"Windows"','sec-fetch-dest':'empty','sec-fetch-mode':'cors','sec-fetch-site':'same-origin','sec-gpc':'1','user-agent':userAgent,'x-moba-client':'mobalytics-web','x-moba-proxy-gql-ops-name':'LolMatchDetailsQuery'}, json=json_data).json()
    blueMvpScore = 10
    redMvpScore = 10
    redmvp = ""
    bluemvp = ""
    print(response["data"]["lol"]["player"]["match"]["teams"][0]["teamId"],response["data"]["lol"]["player"]["match"]["teams"][0]["result"],)
    for x in response["data"]["lol"]["player"]["match"]["participants"]:
        if x["team"] == "RED" and x["mvpScore"] < redMvpScore:
            redMvpScore = x["mvpScore"]
            redmvp = x["summonerName"]
        if x["team"] == "BLUE" and x["mvpScore"] < blueMvpScore:
            blueMvpScore = x["mvpScore"]
            bluemvp = x["summonerName"]
    return {"RED":redmvp.strip(),"BLUE":bluemvp.strip()}

# checks to see if there is an ONGOING game going with summoner name
async def isPlaying(summonerID):
    loadingAttempts = 10
    while(True):
        loadingAttempts -= 1
        if loadingAttempts != 0:
            try:
                results = requests.get(f"https://na1.api.riotgames.com/lol/spectator/v4/active-games/by-summoner/{summonerID}?api_key={riotAPI}",timeout=10)
                if results.status_code != 200:
                    return False
                else:
                    return True
            except:
                await asyncio.sleep(5)
                pass
        else:
            print("[BLITZCRANK] Timed out trying to see if summoner ID {summonerID} is in game.")
            return

# gets the highest rank of a player from ALL queue types (excluding TFT)
async def getHighestRank(summoner):
    global currentSummoners

    print(f"[BLITZCRANK] Getting {summoner}'s rank data ...")
    if summoner in watchedSummoners:
        summonerId = watchedSummonerData[summoner]["id"]
    else:
        summonerId = getSummoner(summoner)["id"]
    highestTier = "UNRANKED"
    highestRank = "IV"
    lastTier = -1
    lastRank = -1
    tiers = ["IRON","BRONZE","SILVER","GOLD","PLATINUM","DIAMOND","MASTER","GRANDMASTER","CHALLENGER"]
    ranks = ["IV","III","II","I"]
    loadingAttempts = 10
    while(True):
        loadingAttempts -= 1
        if loadingAttempts != 0:
            try:
                r = requests.get(f"https://na1.api.riotgames.com/lol/league/v4/entries/by-summoner/{summonerId}?api_key={riotAPI}").json()
                break
            except:
                await asyncio.sleep(5)
                pass
        else:
            print("Timed out getting highest rank for " + summoner)
            return "?"
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
                
    if highestTier == "UNRANKED":
        currentSummoners[summoner] = "`U`"
    elif highestTier == "MASTER":
        currentSummoners[summoner] = masterId if useIconEmojis else "`M`"
    elif highestTier == "GRANDMASTER":
        currentSummoners[summoner] = grandmasterId if useIconEmojis else "`GM`"
    elif highestTier == "CHALLENGER":
        currentSummoners[summoner] = challengerId if useIconEmojis else "`CH`"
    else:
        currentSummoners[summoner] =  "`"+highestTier[0] + str(romanToInt(highestRank))+"`"

    return currentSummoners[summoner]

icons = requests.get(iconsPastebin).text.split("\n")

# uses discord emoji ID based on champ id
# if not enabled, will return champion's name instead
async def pullEmoji(champId):
    if useIconEmojis:
        if champId in [1,2,3,4,5,6,7,8,9]:
            champId = str(champId) + "_"
        for x in icons:
            if str(champId) == x.strip().split(" ")[0]:
                return "<:" + str(champId) + ":" + x.strip().split(" ")[1] + ">"
        return orbId
    else:
        return championDatabase["keys"][int(champId)]

# gets current watched summoners data (for live games)
async def getCurrentSummoners(summonerName):
    global currentSummoners

    if summonerName in currentSummoners:
        return currentSummoners[summonerName]
    else:
        return await getHighestRank(summonerName)

###########################################################################
# ------------------------------- PARSERS ------------------------------- #
###########################################################################

# converts seconds to a formatted minutes and seconds
async def convert(seconds):
    seconds = seconds % (24 * 3600)
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
      
    return "%02dm %02ds" % (minutes, seconds)

# parses a queue ID to queue type name
async def parseQueue(queue):
    for q in requests.get("https://static.developer.riotgames.com/docs/lol/queues.json").json():
        if (queue == q["queueId"]):
            queueType = q["description"]
            return queueType.replace("games","").replace("5v5","")

# parse item build from leagueOfGraphs
async def parseBuild(list):
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

# turns a given list into a string
def parseList(list):
    parsedString = ""
    for x in list:
        parsedString += x + "\n"
    return parsedString

# converts roman numeral to integer
def romanToInt(roman):
    rom_val = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
    int_val = 0
    for i in range(len(roman)):
        if i > 0 and rom_val[roman[i]] > rom_val[roman[i - 1]]:
            int_val += rom_val[roman[i]] - 2 * rom_val[roman[i - 1]]
        else:
            int_val += rom_val[roman[i]]
    return int_val

# downloads an image
def downloadImage(url):
    fileName = str(random.randint(1000,2000)) + url.split("/")[-1]
    f = open("./discord bots/leaguebot/" + fileName,"wb")
    response = requests.get(url)
    f.write(response.content)
    f.close()
    return "./discord bots/leaguebot/" + fileName

# gets latest game version and latest champion database
latestVersion = requests.get("https://ddragon.leagueoflegends.com/realms/na.json").json()["v"]
championDatabase = requests.get(f"https://ddragon.leagueoflegends.com/cdn/{latestVersion}/data/en_US/championFull.json").json()

###########################################################################
# --------------------------- DISCORD METHODS --------------------------- #
###########################################################################

bot = discord.Bot(intents=discord.Intents.all())

@bot.event
async def on_ready():
    global watchedGames
    global foundGames

    await bot.change_presence(activity=discord.Streaming(name="Patch " + latestVersion, url='https://www.twitch.tv/muffincheez'))
    print('=> Logged in as {0.user}'.format(bot))

    messages = await bot.get_channel(int(channelId)).history(limit=10).flatten()
    for x in messages:
        try:
            embed = x.embeds[0].to_dict()
            if embed["color"] == 6474105 and "Live Game" in embed["author"]["name"]:
                matchId = embed["footer"]["text"].split("ID: ")[1].split(" • ")[0]
                summonerName = embed["author"]["name"].split("'s")[0].strip()

                foundGames.append(int(matchId))
                watchedGames.append([str(matchId),watchedSummonerData[summonerName],x])
                print(f"[BLITZCRANK] Existing match embed found | ID: {matchId}")
        except:
            pass

async def background_task():
    await bot.wait_until_ready()

    print(f"[BLITZCRANK] Beginning monitor of {len(watchedSummoners)} players.")
    while(True):
        for summoner in watchedSummoners:
            summonerData = watchedSummonerData[summoner]
            if "name" in summonerData:
                await gameCheck()
                await gamerCheck(summonerData)
                await getLeagueRanks(summonerData)
            await asyncio.sleep(5)
        await asyncio.sleep(20)

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    searchQuery = "https://na.op.gg/multisearch/na?summoners="
    msg_content = str(message.content)
    if "joined the lobby" in str(msg_content):
        sep = " joined"
    elif "님이 로비에 참가하셨습니다" in str(msg_content):
        sep = " 님이"
    elif "がロビーに参加しました" in str(msg_content):
        sep = "がロビーに参加しました"
    if sep:
        for line in msg_content.split("\n"):
            name = line.split(sep)[0].replace(" ","+")
            searchQuery += name + "%2C"
        await message.channel.send(searchQuery[:len(searchQuery)-3],reference=message)
        try:
            await message.delete()
        except:
            pass

cass.set_riot_api_key(riotAPI)

foundGames = []
watchedGames = []
currentSummoners = {}

# checks if any watched games are finished
# also empties watched games if there are 10 found games
async def gameCheck():
    global foundGames
    global watchedGames
    global currentSummoners

    winEmotes = ["https://i.imgur.com/ieWmRWb.png","https://i.imgur.com/batBGnC.png","https://i.imgur.com/LAyQgjj.png","https://i.imgur.com/qIchruZ.png","https://i.imgur.com/Q6nkk8B.png","https://i.imgur.com/EQQjHIY.png","https://i.imgur.com/ltYuPxd.png","https://i.imgur.com/goS2pMy.png","https://i.imgur.com/5yBfUAN.png","https://i.imgur.com/cVs5phF.png","https://i.imgur.com/SjsMd3r.png","https://i.imgur.com/lLNXg54.png","https://i.imgur.com/K4S9PJD.png","https://i.imgur.com/YwNWWCx.png","https://i.imgur.com/9OE3pvL.png","https://i.imgur.com/rknehur.png","https://i.imgur.com/x5acRDG.png","https://i.imgur.com/3pwXLHp.png"]
    sadEmotes = ["https://i.imgur.com/q3u0c40.png","https://i.imgur.com/iurybFl.png","https://i.imgur.com/osGlgMV.png","https://i.imgur.com/RUKiZo7.png","https://i.imgur.com/u7eFXdk.png","https://i.imgur.com/fTptmUI.png","https://i.imgur.com/LyD9a3O.png","https://i.imgur.com/IfUHRZh.png","https://i.imgur.com/Lnp8nW7.png","https://i.imgur.com/jxqjzgR.png","https://i.imgur.com/LP3ZjqK.png","https://i.imgur.com/LdP6mWe.png","https://i.imgur.com/79r5uhk.png","https://i.imgur.com/uy2dGPC.png","https://i.imgur.com/wWVzCRI.png","https://i.imgur.com/YB9geur.png","https://i.imgur.com/Vozjla7.png","https://i.imgur.com/iiSrhe6.png"]
    starsMvp = ["✩","★","☆","✺","✰","✯","✦","❅","✵"]

    for game in watchedGames:
        matchID = game[0]
        summoner = game[1]

        if (len(foundGames) >= 10):
            foundGames.clear()
            foundGames.append(int(matchID))

        loadingAttempts = 10
        while(True):
            loadingAttempts -= 1
            if loadingAttempts != 0:
                try:
                    matchResults = requests.get(f"https://americas.api.riotgames.com/lol/match/v5/matches/NA1_{matchID}?api_key={riotAPI}",timeout=10)
                    break
                except:
                    await asyncio.sleep(5)
                    pass
            else:
                print(f"[BLITZCRANK] Timed out trying to get match results for match {matchID}")
                return
                
        if (matchResults.status_code == 200):
            
            # get summoner information
            summonerName = summoner["name"].replace(" ","")

            print(f"[BLITZCRANK] {summonerName}'s match is finished | ID: {matchID}")

            await getLeagueRanks(summoner)

            # get match results data
            matchData = matchResults.json()
            key = matchData["metadata"]["participants"].index(summoner["puuid"])
            gameWon = matchData["info"]["participants"][key]["win"]
            gameDuration = matchData["info"]["gameDuration"]
            queue = matchData["info"]["queueId"]
            for q in requests.get("https://static.developer.riotgames.com/docs/lol/queues.json").json():
                if (queue == q["queueId"]):
                    queueType = q["description"].replace("games","").replace("5v5","").strip()
            mvps = getMatchMvp(matchID,summonerName)
            blueteamcomp = ""
            redteamcomp = ""
            blueRanks=[]
            redRanks=[]
            blueTeamKills = 0
            redTeamKills = 0
            count = 0
            mvpStar = random.choice(starsMvp)

            # get match participants data
            for player in matchData["info"]["participants"]:
                if count < 5:
                    if player["summonerName"].strip() == mvps["BLUE"]:
                        blueteamcomp += "\n" + await pullEmoji(player["championId"]) + " " + mvpStar + " `" + player["summonerName"].strip() + "` (" + str(player["kills"]) + "/" + str(player["deaths"]) + "/" + str(player["assists"]) + ") " + await getCurrentSummoners(player["summonerName"].strip())
                    else:
                        blueteamcomp += "\n" + await pullEmoji(player["championId"]) + " - `" + player["summonerName"].strip() + "` (" + str(player["kills"]) + "/" + str(player["deaths"]) + "/" + str(player["assists"]) + ") " + await getCurrentSummoners(player["summonerName"].strip())
                    blueTeamKills += player["kills"]
                    blueRanks.append(currentSummoners[player["summonerName"].strip()])
                else:
                    if player["summonerName"].strip() == mvps["RED"]:
                        redteamcomp += "\n" + await pullEmoji(player["championId"]) + " " + mvpStar + " `" + player["summonerName"].strip() + "` (" + str(player["kills"]) + "/" + str(player["deaths"]) + "/" + str(player["assists"]) + ") " + await getCurrentSummoners(player["summonerName"].strip())
                    else:
                        redteamcomp += "\n" + await pullEmoji(player["championId"]) + " - `" + player["summonerName"].strip() + "` (" + str(player["kills"]) + "/" + str(player["deaths"]) + "/" + str(player["assists"]) + ") " + await getCurrentSummoners(player["summonerName"].strip())
                    redTeamKills += player["kills"]
                    redRanks.append(currentSummoners[player["summonerName"].strip()])
                count+=1
                currentSummoners.pop(player["summonerName"].strip())

            # create embed
            embedHeader = f"{uggId} [Link 🔗](https://u.gg/lol/profile/na1/{summonerName}) | {opggId} [Link 🔗](https://na.op.gg/summoner/userName={summonerName}) | {mobalyticsId} [Link 🔗](https://app.mobalytics.gg/lol/profile/na/{summonerName}) | {porofessorId} [Link 🔗](https://www.leagueofgraphs.com/summoner/na/{summonerName})\n\n" if useIconEmojis else f"U.GG [Link 🔗](https://u.gg/lol/profile/na1/{summonerName}) | OP.GG [Link 🔗](https://na.op.gg/summoner/userName={summonerName}) | Mobalytics [Link 🔗](https://app.mobalytics.gg/lol/profile/na/{summonerName}) | Porofessor [Link 🔗](https://www.leagueofgraphs.com/summoner/na/{summonerName})\n\n"
            if (gameDuration < 900) and (queueType != "ARAM"):
                newEmbed=discord.Embed(description=embedHeader + "⚠️**REMAKE**⚠️\n\nMatch Duration: `"+ await convert(gameDuration)+"` [*](https://app.mobalytics.gg/lol/match/na/" + summonerName + "/" + matchID + ")",timestamp=datetime.datetime.utcnow(), color=0xc0c0c0)
            elif (gameWon):
                newEmbed=discord.Embed(description=embedHeader + "Match Duration: `"+ await convert(gameDuration)+"` [*](https://app.mobalytics.gg/lol/match/na/" + summonerName + "/" + matchID + ") :regional_indicator_w:",timestamp=datetime.datetime.utcnow(), color=0x8BD3E6)
            else:
                newEmbed=discord.Embed(description=embedHeader + "Match Duration: `"+ await convert(gameDuration)+"` [*](https://app.mobalytics.gg/lol/match/na/" + summonerName + "/" + matchID + ") :regional_indicator_l:",timestamp=datetime.datetime.utcnow(), color=0xE7548C)
            newEmbed.set_author(name=f"{summonerName}'s Match Results",icon_url=f"https://ddragon.leagueoflegends.com/cdn/{latestVersion}/img/profileicon/" + str(summoner["profileIconId"]) + ".png")
            newEmbed.set_footer(text=f"ID: {matchID} • powered by shdw 👻",icon_url="https://i.imgur.com/ri6NrsN.png")
            newEmbed.add_field(name="Gamemode",value=queueType,inline = False)
            newEmbed.add_field(name="🟦 Blue Team (" + str(blueTeamKills) + " kills)",value=blueteamcomp, inline=True)
            newEmbed.add_field(name="🟥 Red Team (" + str(redTeamKills) + " kills)",value=redteamcomp, inline=True)
            newEmbed.set_image(url=random.choice(winEmotes)) if gameWon else newEmbed.set_image(url=random.choice(sadEmotes))
            embed = game[2]

            # edit the original embed sent when game was found
            if (gameDuration < 180):
                await embed.add_reaction("🇷")
            elif (gameDuration < 900) and (queueType != "ARAM"):
                await embed.add_reaction("🇦")
                await embed.add_reaction("🇫")
                await embed.add_reaction("🇰")
            elif (gameWon):
                await embed.add_reaction("🇼")
                await embed.add_reaction("🇮")
                await embed.add_reaction("🇳")
            else:
                await embed.add_reaction("🇱")
            await embed.edit(embed=newEmbed)
            watchedGames.remove(game)

# checks if specified player is IN GAME
champion_roles = roleidentification.pull_data()
async def gamerCheck(summoner):
    try:
        global foundGames
        global watchedGames

        name = summoner["name"]
        profileIcon = summoner["profileIconId"]

        if (await isPlaying(summoner["id"])):
            current = cass.get_current_match(summoner=name,region="NA")

            if current.id in foundGames:
                return

            print(f"[BLITZCRANK] Found an active match {name} | ID: {current.id}")
            loadingAttempts = 10
            while(True):
                loadingAttempts -= 1
                if loadingAttempts != 0:
                    try:
                        summonerId = summoner["id"]
                        matchQueue = await parseQueue(requests.get(f"https://na1.api.riotgames.com/lol/spectator/v4/active-games/by-summoner/{summonerId}?api_key={riotAPI}",timeout=10).json()["gameQueueConfigId"])
                        break
                    except:
                        await asyncio.sleep(5)
                        pass
                else:
                    print(f"[BLITZCRANK] Timed out trying to get matchQueue for {name}")
                    return

            # format discord embed with teams, players, and champions
            blueteam = []
            blueSummoners = {}
            blueRanks = []
            for x in current.blue_team.participants:
                blueSummoners[x.champion.id] = x.summoner.name
                blueteam.append(x.champion.id)
            blueteamcomp = ""
            try:
                blueteamroles = roleidentification.get_roles(champion_roles,blueteam)
                for x in blueteamroles:
                    blueteamcomp += "\n" + await pullEmoji(blueteamroles[x]) + " - `" + blueSummoners[blueteamroles[x]].strip() + "` " + await getHighestRank(blueSummoners[blueteamroles[x]].strip())
                    blueRanks.append(currentSummoners[blueSummoners[blueteamroles[x]].strip()])
            except:
                blueteamcomp = ""
                for x in blueSummoners:
                    blueteamcomp += "\n" + await pullEmoji(str(x)) + " - `" + blueSummoners[x].strip() + "`"

            redteam = []
            redSummoners = {}
            redRanks = []
            for x in current.red_team.participants:
                redSummoners[x.champion.id] = x.summoner.name
                redteam.append(x.champion.id)
            redteamcomp = ""
            try:
                redteamroles = roleidentification.get_roles(champion_roles,redteam)
                for x in redteamroles:
                    redteamcomp += "\n" + await pullEmoji(redteamroles[x]) + " - `" + redSummoners[redteamroles[x]].strip() + "` " + await getHighestRank(redSummoners[redteamroles[x]].strip())
                    redRanks.append(currentSummoners[redSummoners[redteamroles[x]].strip()])
            except:
                redteamcomp = ""
                for x in redSummoners:
                    redteamcomp += "\n" + await pullEmoji(str(x)) + " - `" + redSummoners[x].strip() + "`"
            summonerName = name.replace(" ","")
            embedHeader = f"{uggId} [Link 🔗](https://u.gg/lol/profile/na1/{summonerName}) | {opggId} [Link 🔗](https://na.op.gg/summoner/userName={summonerName}) | {mobalyticsId} [Link 🔗](https://app.mobalytics.gg/lol/profile/na/{summonerName}) | {porofessorId} [Link 🔗](https://www.leagueofgraphs.com/summoner/na/{summonerName})" if useIconEmojis else f"U.GG [Link 🔗](https://u.gg/lol/profile/na1/{summonerName}) | OP.GG [Link 🔗](https://na.op.gg/summoner/userName={summonerName}) | Mobalytics [Link 🔗](https://app.mobalytics.gg/lol/profile/na/{summonerName}) | Porofessor [Link 🔗](https://www.leagueofgraphs.com/summoner/na/{summonerName})"
            embed=discord.Embed(description=embedHeader,timestamp=datetime.datetime.utcnow(), color=0x62C979)
            embed.set_author(name=name + "'s Live Game 👁‍🗨",icon_url=f"https://ddragon.leagueoflegends.com/cdn/{latestVersion}/img/profileicon/{profileIcon}.png")
            embed.set_footer(text=f"ID: {current.id} • powered by shdw 👻",icon_url="https://i.imgur.com/ri6NrsN.png")
            embed.add_field(name="Gamemode",value=matchQueue,inline = False)
            embed.add_field(name="🟦 Blue Team",value=blueteamcomp, inline=True)
            embed.add_field(name="🟥 Red Team",value=redteamcomp, inline=True)
            sentEmbed = await bot.get_channel(int(channelId)).send(embed=embed)

            # if successfully sent, add to foundGames, and watchedGames
            foundGames.append(current.id)
            print(f"[BLITZCRANK] Now watching {summonerName}'s match | ID {current.id}")
            watchedGames.append([str(current.id),summoner,sentEmbed])
    except Exception as e:
        print("Gamercheck error: ")
        print(e)
    
leaguePointsBook = {}
watchedSummonerData = {}
print(f"[BLITZCRANK] Pulling summoner data of {len(watchedSummoners)} players ...")
for x in watchedSummoners:
    leaguePointsBook[x] = {}
    summonerData = getSummoner(x)
    watchedSummonerData[x] = {"id":summonerData["id"],"accountId":summonerData["accountId"],"puuid":summonerData["puuid"],"name":summonerData["name"],"profileIconId":summonerData["profileIconId"],"summonerLevel":summonerData["summonerLevel"]}
print(f"[BLITZCRANK] Finished pulling summoner data of {len(watchedSummoners)} players.")

async def getLeagueRanks(summonerInfo):
    summName = summonerInfo["name"]
    summIcon = summonerInfo["profileIconId"]
    summId = summonerInfo["id"]

    loadingAttempts = 10
    while(True):
        loadingAttempts -= 1
        if loadingAttempts != 0:
            try:
                req = requests.get(f"https://na1.api.riotgames.com/lol/league/v4/entries/by-summoner/{summId}?api_key={riotAPI}",timeout=10).json()
                break
            except:
                await asyncio.sleep(5)
                pass
        else:
            print(f"[BLITZCRANK] Timed out trying to get ranked data for {summName}")
            return

    try:
        for gamemode in req:
            queue = gamemode["queueType"].replace("_"," ").replace("SR","").replace("5x5","")
            currentRank = gamemode["tier"] + " " + gamemode["rank"]
            leaguePoints = gamemode["leaguePoints"]

            try:
                if leaguePointsBook[summName][queue]["rank"] != currentRank:
                    
                    rankIcons = {"IRON":"https://static.wikia.nocookie.net/leagueoflegends/images/f/fe/Season_2022_-_Iron.png","BRONZE":"https://static.wikia.nocookie.net/leagueoflegends/images/e/e9/Season_2022_-_Bronze.png","SILVER":"https://static.wikia.nocookie.net/leagueoflegends/images/4/44/Season_2022_-_Silver.png","GOLD":"https://static.wikia.nocookie.net/leagueoflegends/images/8/8d/Season_2022_-_Gold.png","PLATINUM":"https://static.wikia.nocookie.net/leagueoflegends/images/3/3b/Season_2022_-_Platinum.png","DIAMOND":"https://static.wikia.nocookie.net/leagueoflegends/images/e/ee/Season_2022_-_Diamond.png","MASTER":"https://static.wikia.nocookie.net/leagueoflegends/images/e/eb/Season_2022_-_Master.png","GRANDMASTER":"https://static.wikia.nocookie.net/leagueoflegends/images/f/fc/Season_2022_-_Grandmaster.png","CHALLENGER":"https://static.wikia.nocookie.net/leagueoflegends/images/0/02/Season_2022_-_Challenger.png"}
                    print(summName + " rank changed from " + leaguePointsBook[summName][queue]["rank"] + " to " + currentRank + "!")

                    embed=discord.Embed(timestamp=datetime.datetime.utcnow(), color=0xff00ff)
                    embed.set_author(name="🚨 " + summName.upper() + " RANK UPDATE 🚨",icon_url=f"https://ddragon.leagueoflegends.com/cdn/{latestVersion}/img/profileicon/{summIcon}.png")
                    embed.add_field(name=queue,value=leaguePointsBook[summName][queue]["rank"] + " **----->** " + currentRank)
                    embed.set_footer(text="powered by shdw 👻",icon_url="https://i.imgur.com/ri6NrsN.png")
                    embed.set_image(url=rankIcons[gamemode["tier"]])
                    await bot.get_channel(int(channelId)).send(embed=embed)
                elif leaguePointsBook[summName][queue]["leaguePoints"] < leaguePoints:
                    print(summName + " gained " + str(leaguePoints-leaguePointsBook[summName][queue]["leaguePoints"]) + " LP in " + queue)

                    embed=discord.Embed(description="**+" + str(leaguePoints-leaguePointsBook[summName][queue]["leaguePoints"]) + "** LP in " + queue,timestamp=datetime.datetime.utcnow(), color=0x62C979)
                    embed.set_author(name="🚨 " + summName.upper() + " LP UPDATE 🚨",icon_url=f"https://ddragon.leagueoflegends.com/cdn/{latestVersion}/img/profileicon/{summIcon}.png")
                    embed.add_field(name=queue,value=currentRank + " - " + str(leaguePoints) + " LP")
                    embed.set_footer(text="powered by shdw 👻",icon_url="https://i.imgur.com/ri6NrsN.png")
                    embed.set_thumbnail(url="https://i.imgur.com/0m1B3Et.png")
                    await bot.get_channel(int(channelId)).send(embed=embed)
                elif leaguePointsBook[summName][queue]["leaguePoints"] > leaguePoints:
                    print(summName + " lost " + str(leaguePointsBook[summName][queue]["leaguePoints"]-leaguePoints) + " LP in " + queue)

                    embed=discord.Embed(description="*-" + str(leaguePointsBook[summName][queue]["leaguePoints"]-leaguePoints) + "* LP in " + queue,timestamp=datetime.datetime.utcnow(), color=0xE7548C)
                    embed.set_author(name="🚨 " + summName.upper() + " LP UPDATE 🚨",icon_url=f"https://ddragon.leagueoflegends.com/cdn/{latestVersion}/img/profileicon/{summIcon}.png")
                    embed.add_field(name=queue,value=currentRank + " - " + str(leaguePoints) + " LP")
                    embed.set_footer(text="powered by shdw 👻",icon_url="https://i.imgur.com/ri6NrsN.png")
                    embed.set_thumbnail(url="https://i.imgur.com/bTORHF3.png")
                    await bot.get_channel(int(channelId)).send(embed=embed)
            except Exception as e:
                pass

            # update dictionary
            leaguePointsBook[summName][queue] = {"leaguePoints":leaguePoints,"rank":currentRank}
    except:
        pass

# matchup command which returns winrates against a champion
# starting build, gold diff @ 15, core and end builds
@bot.command(name="matchup",description="Lookup preferred build against a champion")
async def matchup(ctx,champ1,champ2):
    lol = await ctx.respond(f"Getting you the matchup details between {champ1.title()} and {champ2.title()} ...")
    try:
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
        headers["User-Agent"] = userAgent

        results = requests.get(f"https://www.leagueofgraphs.com/champions/builds/{champ1.lower()}/vs-{champ2.lower()}", headers=headers)
        soup = BeautifulSoup(results.text,"html.parser")

        champ1WR = str(soup.find("div",id="graphDD1").text.strip())
        champ2WR = str(soup.find("div",id="graphDD2").text.strip())
        goldDiff = str(soup.find("div",id="graphDD3").text.strip())

        # runes
        primaryRunes = parseRunes(soup.find("table",class_="perksTableOverview").find_all("div",class_="img-align-block"))
        secondaryRunes = parseRunes(soup.find("table",class_="perksTableOverview secondary").find_all("div",class_="img-align-block"))

        # build
        startingBuild = await parseBuild(soup.find_all("div",class_="iconsRow")[1])
        coreBuild = await parseBuild(soup.find_all("div",class_="iconsRow")[2])
        boots = await parseBuild(soup.find_all("div",class_="iconsRow")[3])
        endBuild = await parseBuild(soup.find_all("div",class_="iconsRow")[4])

        try:
            embed=discord.Embed(description=f"Boots against {champ2.title()}: **" + str(boots).split("[\"")[1].split("\"")[0] + "**",timestamp=datetime.datetime.utcnow(), color=0xAC4FC6)
            embed.set_author(name=f"{champ1.title()} vs {champ2.title()}",icon_url=f"https://ddragon.leagueoflegends.com/cdn/{latestVersion}/img/champion/{champ1.title()}.png")
        except:
            embed=discord.Embed(title=f"{champ1.title()} vs {champ2.title()}",timestamp=datetime.datetime.utcnow(), color=0xAC4FC6)
        
        embed.add_field(name=champ1.title() + "'s WR",value=champ1WR)
        embed.add_field(name=champ2.title() + "'s WR",value=champ2WR,inline=True)
        embed.add_field(name="Gold Diff @ 15",value=goldDiff,inline=True)
        embed.add_field(name="Primary Runes",value=parseList(primaryRunes[0]))
        embed.add_field(name="Secondary Runes",value=parseList(secondaryRunes[0]),inline=True)
        embed.add_field(name="Starting Build",value=parseList(startingBuild))
        embed.add_field(name="Core Build",value=parseList(coreBuild),inline=True)
        embed.add_field(name="End Build",value=parseList(endBuild),inline=True)
        embed.set_footer(text="from leagueofgraphs.com",icon_url="https://i.imgur.com/ri6NrsN.png")
        await lol.edit_original_response(content=None,embed=embed)
    except Exception as e:
        print(e)
        await lol.edit_original_response(content="Could not find any information on this matchup! Did you check spelling?")

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

@bot.command(description="Generate a random Ultimate Bravery Build (map: sr, aram)")
async def build(ctx,map:str,championname:str):
    sent = await ctx.respond(content=f'Generating an UB build for {championname.title()} ...')

    if map.lower() == "sr":
        map = 11
    elif map.lower() == "aram":
        map = 12
    else:
        map = 11

    championname = championname.title().replace(" ","")
    if championname not in championDatabase["data"]:
        await sent.edit_original_response(content="That is not a valid champion! :x:\n\nYour input: `" + championname + "`")
        return
        
    champId = championDatabase["data"][championname]["key"]

    chosenBuild = getBuild(map,int(champId))
    try:
        buildTitle = chosenBuild["data"]["title"]
        championname = chosenBuild["data"]["champion"]["name"]
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
            await sent.edit_original_response(content="",embed=embed)
    except Exception as e:
        print(e)
        await sent.edit_original_response(content="Something went wrong, try again later!")


print("[BLITZCRANK] Missing " + str(len(championDatabase["keys"])-len(icons)) + " icons !") if len(icons) != len(championDatabase["keys"]) else print("[BLITZCRANK] Using information from Patch " + latestVersion)
bot.loop.create_task(background_task())
bot.run(botToken)
