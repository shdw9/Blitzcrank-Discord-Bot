from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
import discord, cassiopeia as cass, datetime, asyncio, requests, roleidentification, random, json, traceback, os, time

JSON_PATH = "leagueData.json"

# List of summoners to monitor
watchedSummoners = ['Sacred Sword']

# [REQUIRED] Riot Developer API Key
riotAPI = ""

# [OPTIONAL] TFT API Key
tftApi = ""

# Discord Bot Token
botToken = ""

# Discord Channel ID to get messages
channelId = ""

# User Agent (for scraping op.gg data)
userAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36"

# Use Emojis in Embed
# Replace with Discord Emoji ID
useIconEmojis = False
uggId = "<:ugg:1045463729875197993>"
opggId = "<:opgg:1045463718445715456>"
porofessorId = "<:porofessorgg:1045463965016277052>"

# read json file
def getData():
    data = {}

    if os.path.exists(JSON_PATH):
        with open(JSON_PATH) as f:
            data = json.load(f)
    
    if "liveGames" not in data:
        data["liveGames"] = {}

    if "recentGames" not in data:
        data["recentGames"] = []

    if "players" not in data:
        data["players"] = {}

    return data

# write to json file
def writeData():
    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(leagueData, f, ensure_ascii=False, indent=4)

latestVersion = requests.get("https://ddragon.leagueoflegends.com/realms/na.json").json()["v"]
championDatabase = requests.get(f"https://ddragon.leagueoflegends.com/cdn/{latestVersion}/data/en_US/championFull.json").json()
champion_roles = roleidentification.pull_data()
cass.set_riot_api_key(riotAPI)

# bot rate limiter to prevent api spam
apiLastAccessed = time.time()
async def rateLimiter():
    global apiLastAccessed
    current = time.time()
    if not current - apiLastAccessed > 1:
        print("waiting 1s")
        asyncio.sleep(1)
        apiLastAccessed = current

# RIOT API - get summoner profile
async def getSummoner(summoner):
    await rateLimiter()
    for x in range(20):
        try:
            summonerData = requests.get(f"https://na1.api.riotgames.com/lol/summoner/v4/summoners/by-name/{summoner}?api_key={riotAPI}",timeout=10).json()
            if "name" in summonerData:
                return summonerData
        except:
            pass
    return {}

# TFT API - get tft profile
async def getTftSummoner(summoner):
    await rateLimiter()
    for x in range(20):
        try:
            summonerData = requests.get(f"https://na1.api.riotgames.com/tft/summoner/v1/summoners/by-name/{summoner}?api_key={tftApi}",timeout=10).json()
            if "name" in summonerData:
                return summonerData
        except:
            pass
    return {}

# RIOT API - check to see if player is in game
async def isPlaying(summonerId):
    await rateLimiter()
    for x in range(10):
        try:
            results = requests.get(f"https://na1.api.riotgames.com/lol/spectator/v4/active-games/by-summoner/{summonerId}?api_key={riotAPI}",timeout=10)
            return [False, None] if results.status_code != 200 else [True, results.json()]
        except:
            pass
    return [False, None]

# RIOT API - retrieve player's ranked information
async def getRiftEntries(summonerId):
    await rateLimiter()
    for x in range(10):
        try:
            results = requests.get(f"https://na1.api.riotgames.com/lol/league/v4/entries/by-summoner/{summonerId}?api_key={riotAPI}",timeout=10).json()
            return results
        except:
            pass
    print(f"[BLITZCRANK] Could not get the ranked entries for {summonerId}")
    return {}

# TFT API - retrieve player's tft ranked information
async def getTftEntries(summonerId):
    await rateLimiter()
    for x in range(10):
        try:
            results = requests.get("https://na1.api.riotgames.com/tft/league/v1/entries/by-summoner/" + summonerId + "?api_key=" + tftApi,timeout=10).json()
            return results
        except:
            pass
    print(f"[BLITZCRANK] Could not get the tft ranked entries for {summonerId}")
    return {}

# RIOT API - get match information
async def getMatchData(matchId):
    await rateLimiter()
    for x in range(20):
        try:
            matchResults = requests.get(f"https://americas.api.riotgames.com/lol/match/v5/matches/NA1_{matchId}?api_key={riotAPI}",timeout=10)
            if matchResults.status_code == 200:
                return [True,matchResults.json()]
        except:
            pass
    return [False,None]

# gets the highest rank of a player from ALL queue types (excluding TFT)
async def getHighestRank(summoner):
    print(f"[BLITZCRANK] Getting {summoner}'s rank data ...")
    try:
        if summoner in watchedSummoners:
            summonerId = leagueData["players"][summoner]["summonerData"]["id"]
        else:
            summonerData = await getSummoner(summoner)
            summonerId = summonerData["id"]
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
                print("[BLITZCRANK] Timed out getting highest rank for " + summoner)
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
            return "U"
        elif highestTier == "MASTER":
            return "M"
        elif highestTier == "GRANDMASTER":
            return "GM"
        elif highestTier == "CHALLENGER":
            return "CHALLENGER"
        else:
            return highestTier[0] + str(romanToInt(highestRank))
        
    except:
        return "?"

# update opgg profile
async def opUpdate(summonerId):
    headers = {
        'authority': 'op.gg',
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-US,en;q=0.9',
        'origin': 'https://www.op.gg',
        'referer': 'https://www.op.gg/',
        'sec-ch-ua': '"Not_A Brand";v="99", "Brave";v="109", "Chromium";v="109"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'sec-gpc': '1',
        'user-agent': userAgent,
    }
    print(f"[BLITZCRANK] Updating OP.GG for {summonerId} ...")
    await asyncio.sleep(15)
    requests.post(f"https://op.gg/api/v1.0/internal/bypass/summoners/na/{summonerId}/renewal",headers=headers)
    print(f"[BLITZCRANK] Updated OP.GG for {summonerId}.")
    await asyncio.sleep(5)

# retrieve summoner's opgg profile data
async def opProfile(summonerName):
    headers = {
        'authority': 'op.gg',
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-US,en;q=0.9',
        'origin': 'https://www.op.gg',
        'referer': 'https://www.op.gg/',
        'sec-ch-ua': '"Not_A Brand";v="99", "Brave";v="109", "Chromium";v="109"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'sec-gpc': '1',
        'user-agent': userAgent,
    }
    try:
        a = requests.get(f"https://www.op.gg/summoners/na/{summonerName}",headers=headers)
        soup = BeautifulSoup(a.text,"html.parser")
        opgg = json.loads(soup.find_all("script",id="__NEXT_DATA__")[0].text)
        return opgg["props"]["pageProps"]["data"]
    except:
        return {}

# retrieve opgg matches from profile
async def opMatches(summonerId, matchDuration, riotParticipants):
    headers = {
        'authority': 'op.gg',
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-US,en;q=0.9',
        'origin': 'https://www.op.gg',
        'referer': 'https://www.op.gg/',
        'sec-ch-ua': '"Not_A Brand";v="99", "Brave";v="109", "Chromium";v="109"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'sec-gpc': '1',
        'user-agent': userAgent,
    }
    await asyncio.sleep(5)
    matches = json.loads(requests.get(f"https://op.gg/api/v1.0/internal/bypass/games/na/summoners/{summonerId}?&limit=20&hl=en_US&game_type=total",headers=headers).text)
    rgParticipants = []
    for x in riotParticipants:
        rgParticipants.append(x["summonerName"].strip())
    for match in matches["data"]:
        if match["game_length_second"] == matchDuration:
            opGGParticipants = []
            for y in match["participants"]:
                opGGParticipants.append(y["summoner"]["name"].strip())
            rgParticipants.sort()
            opGGParticipants.sort()
            if rgParticipants == opGGParticipants:
                #print(match)
                return match
    return {}

# parse op scores from opgg match data
async def opScores(match):
    scores = {}
    redMvp = 10
    blueMvp = 10
    red = ""
    blue = ""
    redWin = False

    for x in match["participants"]:
        emojis = {1:":one:",2:":two:",3:":three:",4:":four:",5:":five:",6:":six:",7:":seven:",8:":eight:",9:":nine:",10:":keycap_ten:"}
        name = x["summoner"]["name"].strip()
        opscore = x["stats"]["op_score_rank"]
        if x["stats"]["result"] == "WIN" and x["team_key"] == "RED":
            redWin = True
        if x["team_key"] == "BLUE" and opscore < blueMvp:
            blueMvp = opscore
            blue = name
        if x["team_key"] == "RED" and opscore < redMvp:
            redMvp = opscore
            red = name
        scores[name] = emojis[opscore]
    if redWin:
        scores[red] = ":star:"
        scores[blue] = ":star:"
    else:
        scores[red] = ":star:"
        scores[blue] = ":star:"
    return scores

# check to see if there is a live game on opgg
async def opLiveGame(opId):
    try:
        headers = {
            'authority': 'op.gg',
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'en-US,en;q=0.5',
            'origin': 'https://www.op.gg',
            'referer': 'https://www.op.gg/',
            'sec-ch-ua': '"Chromium";v="112", "Brave";v="112", "Not:A-Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'sec-gpc': '1',
            'user-agent': userAgent,
        }

        params = {
            'hl': 'en_US',
        }

        response = requests.get(
            f'https://op.gg/api/v1.0/internal/bypass/spectates/na/{opId}',
            params=params,
            headers=headers,
        )

        if response.status_code == 200:
            return [True, response.json()["data"]["game_id"]]
        else:
            return [False, None]
    except:
        return [False,None]

# get spectate script from opgg
async def opSpectate(opGameId):
    headers = {
        'authority': 'op.gg',
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-US,en;q=0.5',
        'origin': 'https://www.op.gg',
        'referer': 'https://www.op.gg/',
        'sec-ch-ua': '"Chromium";v="112", "Brave";v="112", "Not:A-Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'sec-gpc': '1',
        'user-agent': userAgent,
    }

    response = requests.get(
        f'https://op.gg/api/v1.0/internal/bypass/spectates/na/records/{opGameId}',
        headers=headers,
    )

    macScript = response.json()["data"]["mac_script"]
    windowsScript = response.json()["data"]["windows_script"]

    return {"mac":macScript,"windows":windowsScript}

# parses a queue ID to queue type name
async def parseQueue(queue):
    for q in requests.get("https://static.developer.riotgames.com/docs/lol/queues.json").json():
        if (queue == q["queueId"]):
            queueType = q["description"]
            return queueType.replace("games","").replace("5v5","")

# download an image from url and return file location
def downloadImage(url):
    fileName = str(random.randint(1000,2000)) + url.split("/")[-1]
    f = open(fileName,"wb")
    response = requests.get(url)
    f.write(response.content)
    f.close()
    return fileName

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

# converts seconds to a formatted minutes and seconds
async def convert(seconds):
    seconds = seconds % (24 * 3600)
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
      
    return "%02dm %02ds" % (minutes, seconds)

async def generateFile(contents,extension):
    fileName = str(random.randint(1000,2000)) + "." + extension
    file1 = open(fileName,"w",encoding="utf-8")
    file1.write(contents)
    file1.close()
    return fileName
    
leagueData = getData()
bot = discord.Bot(intents=discord.Intents.all())

@bot.event
async def on_ready():
    bot.add_view(SpectateButtons())
    await bot.change_presence(activity=discord.Streaming(name=f"Patch {latestVersion}", url='https://www.twitch.tv/muffincheez'))
    print('=> Logged in as {0.user}'.format(bot))
            
async def background_task():
    await bot.wait_until_ready()

    print(f"[BLITZCRANK] Pulling summoner data of {len(watchedSummoners)} players ...")

    for player in watchedSummoners:

        if player not in leagueData["players"]:
            leagueData["players"][player] = {}

        if "tftLp" not in leagueData["players"][player]:
            leagueData["players"][player]["tftLp"] = {}

        if "riftLp" not in leagueData["players"][player]:
            leagueData["players"][player]["riftLp"] = {}

        print(f"[BLITZCRANK] Pulling {player}'s summoner profile ...")
        playerData = await getSummoner(player)
        if "name" in playerData:
            # store riot profile information
            realName = playerData["name"].strip()
            
            for data in ["name","profileIconId","summonerLevel","id","accountId","puuid"]:
                if "summonerData" not in leagueData["players"][player]:
                    leagueData["players"][player]["summonerData"] = {}

                leagueData["players"][realName]["summonerData"][data] = playerData[data]

            # store op.gg profile information
            leagueData["players"][player]["opggData"] = {}
            opData = await opProfile(player)
            if "summoner_id" in opData:
                leagueData["players"][realName]["opggData"]["summonerId"] = opData["summoner_id"]

    print(f"[BLITZCRANK] Finished pulling summoner data from {len(watchedSummoners)} players!")
    writeData()

    print(f"[BLITZCRANK] Beginning monitor of {len(watchedSummoners)} players.")
    while(True):
        try:
            for player in leagueData["players"]:
                if "summonerData" in leagueData["players"][player]:
                    if "name" in leagueData["players"][player]["summonerData"]:
                        summonerData = leagueData["players"][player]["summonerData"]
                        await isPlayerPlaying(summonerData)
                        await checkGameStatus()
                        await checkRiftLp(summonerData)
                        await checkTftLp(summonerData)
                        await asyncio.sleep(5)
            await asyncio.sleep(15)
        except:
            print("[BLITZCRANK] ERROR:",traceback.format_exc())

# return discord msg object by id
async def getDiscordMessage(msgId):
    messages = await bot.get_channel(int(channelId)).history(limit=30).flatten()
    for x in messages:
        if x.id == int(msgId):
            return x
    print(f"[BLITZCRANK] Cannot find {msgId}!")

# checks to see if there are any rift lp updates
async def checkRiftLp(summoner):
    name = summoner["name"]
    icon = summoner["profileIconId"]
    id = summoner["id"]

    entries = await getRiftEntries(id)

    try:
        for gamemode in entries:
            queue = gamemode["queueType"].replace("_"," ").replace("SR","").replace("5x5","")
            if gamemode["tier"] in ["MASTER","GRANDMASTER","CHALLENGER"]:
                gamemode["rank"] = ""
            currentRank = gamemode["tier"] + " " + gamemode["rank"]
            leaguePoints = gamemode["leaguePoints"]

            if queue not in leagueData["players"][name]["riftLp"]:
                leagueData["players"][name]["riftLp"][queue] = {"leaguePoints":"","rank":"N/A"}

            if leagueData["players"][name]["riftLp"][queue]["rank"].strip() != currentRank.strip():
                # rank was changed, send rank update
                print(f"{name} rank changed from " + leagueData["players"][name]["riftLp"][queue]["rank"] + f" to {currentRank}!")

                rankIcons = {"IRON":"https://static.wikia.nocookie.net/leagueoflegends/images/f/fe/Season_2022_-_Iron.png","BRONZE":"https://static.wikia.nocookie.net/leagueoflegends/images/e/e9/Season_2022_-_Bronze.png","SILVER":"https://static.wikia.nocookie.net/leagueoflegends/images/4/44/Season_2022_-_Silver.png","GOLD":"https://static.wikia.nocookie.net/leagueoflegends/images/8/8d/Season_2022_-_Gold.png","PLATINUM":"https://static.wikia.nocookie.net/leagueoflegends/images/3/3b/Season_2022_-_Platinum.png","DIAMOND":"https://static.wikia.nocookie.net/leagueoflegends/images/e/ee/Season_2022_-_Diamond.png","MASTER":"https://static.wikia.nocookie.net/leagueoflegends/images/e/eb/Season_2022_-_Master.png","GRANDMASTER":"https://static.wikia.nocookie.net/leagueoflegends/images/f/fc/Season_2022_-_Grandmaster.png","CHALLENGER":"https://static.wikia.nocookie.net/leagueoflegends/images/0/02/Season_2022_-_Challenger.png"}
                
                # send embed
                if not leagueData["players"][name]["riftLp"][queue]["rank"].strip() == "N/A":
                    embed=discord.Embed(timestamp=datetime.datetime.utcnow(), color=0xff00ff)
                    embed.set_author(name="🚨 RANK UPDATE: " + name.upper())
                    embed.set_thumbnail(url=f"https://ddragon.leagueoflegends.com/cdn/{latestVersion}/img/profileicon/{icon}.png")
                    embed.add_field(name=queue,value=leagueData["players"][name]["riftLp"][queue]["rank"] + " **----->** " + currentRank + f" ({leaguePoints} LP)")
                    embed.set_footer(text="Blitzcrank",icon_url="https://i.imgur.com/ri6NrsN.png")
                    embed.set_image(url=rankIcons[gamemode["tier"]])
                    await bot.get_channel(int(channelId)).send(embed=embed)
                
            elif leagueData["players"][name]["riftLp"][queue]["leaguePoints"] < leaguePoints:
                # gained lp
                print(f"{name} gained " + str(leaguePoints-leagueData["players"][name]["riftLp"][queue]["leaguePoints"]) + f" LP in {queue}!")

                # send embed
                embed=discord.Embed(description="**+" + str(leaguePoints-leagueData["players"][name]["riftLp"][queue]["leaguePoints"]) + f"** LP in {queue}",timestamp=datetime.datetime.utcnow(), color=0x62C979)
                embed.set_author(name="🚨 LP UPDATE: " + name.upper())
                embed.set_thumbnail(url=f"https://ddragon.leagueoflegends.com/cdn/{latestVersion}/img/profileicon/{icon}.png")
                embed.add_field(name=queue,value=currentRank + " - " + str(leaguePoints) + " LP")
                embed.set_footer(text="Blitzcrank",icon_url="https://i.imgur.com/ri6NrsN.png")
                embed.set_thumbnail(url="https://i.imgur.com/0m1B3Et.png")
                await bot.get_channel(int(channelId)).send(embed=embed)

            elif leagueData["players"][name]["riftLp"][queue]["leaguePoints"] < leaguePoints:
                # lost lp
                print(f"{name} lost " + str(leagueData["players"][name]["riftLp"][queue]["leaguePoints"]-leaguePoints) + f" LP in {queue}!")

                # send embed
                embed=discord.Embed(description="*-" + str(leagueData["players"][name]["riftLp"][queue]["leaguePoints"]-leaguePoints) + "* LP in " + queue,timestamp=datetime.datetime.utcnow(), color=0xE7548C)
                embed.set_author(name="🚨 LP UPDATE: " + name.upper())
                embed.set_thumbnail(url=f"https://ddragon.leagueoflegends.com/cdn/{latestVersion}/img/profileicon/{icon}.png")
                embed.add_field(name=queue,value=currentRank + " - " + str(leaguePoints) + " LP")
                embed.set_footer(text="Blitzcrank",icon_url="https://i.imgur.com/ri6NrsN.png")
                embed.set_thumbnail(url="https://i.imgur.com/bTORHF3.png")
                await bot.get_channel(int(channelId)).send(embed=embed)

            leagueData["players"][name]["riftLp"][queue] = {"leaguePoints":leaguePoints,"rank": currentRank.strip()}
    except:
        pass

    writeData()

# check to see if there are any tft lp updates
async def checkTftLp(summoner):
    if tftApi != "":
        try:
            tftSummoner = await getTftSummoner(summoner["name"])
            tftId = tftSummoner["id"]
            tftData = await getTftEntries(tftId)

            for league in tftData:
                queue = league["queueType"].replace("_"," ").replace("SR","").replace("5x5","")
                if league["tier"] in ["MASTER","GRANDMASTER","CHALLENGER"]:
                    league["rank"] = ""
                currentRank = league["tier"] + " " + league["rank"]
                leaguePoints = league["leaguePoints"]

                if queue not in leagueData["players"][summoner["name"]]["tftLp"]:
                    leagueData["players"][summoner["name"]]["tftLp"][queue] = {"leaguePoints":"","rank":""}

                if leagueData["players"][summoner["name"]]["tftLp"][queue]["rank"] != currentRank:
                    # rank changed
                    print(summoner["name"] + " tft rank changed from " + leagueData["players"][summoner["name"]]["tftLp"][queue]["rank"] + " --> " + currentRank)

                    rankIcons = {"IRON":"https://static.wikia.nocookie.net/leagueoflegends/images/f/fe/Season_2022_-_Iron.png","BRONZE":"https://static.wikia.nocookie.net/leagueoflegends/images/e/e9/Season_2022_-_Bronze.png","SILVER":"https://static.wikia.nocookie.net/leagueoflegends/images/4/44/Season_2022_-_Silver.png","GOLD":"https://static.wikia.nocookie.net/leagueoflegends/images/8/8d/Season_2022_-_Gold.png","PLATINUM":"https://static.wikia.nocookie.net/leagueoflegends/images/3/3b/Season_2022_-_Platinum.png","DIAMOND":"https://static.wikia.nocookie.net/leagueoflegends/images/e/ee/Season_2022_-_Diamond.png","MASTER":"https://static.wikia.nocookie.net/leagueoflegends/images/e/eb/Season_2022_-_Master.png","GRANDMASTER":"https://static.wikia.nocookie.net/leagueoflegends/images/f/fc/Season_2022_-_Grandmaster.png","CHALLENGER":"https://static.wikia.nocookie.net/leagueoflegends/images/0/02/Season_2022_-_Challenger.png"}

                    if not leagueData["players"][summoner["name"]]["tftLp"][queue]["rank"] == "":
                        # send embed
                        embed=discord.Embed(timestamp=datetime.datetime.utcnow(), color=0xff00ff)
                        embed.set_author(name="🚨 TFT RANK UPDATE: " + summoner["name"].upper())
                        embed.set_thumbnail(url=f"https://ddragon.leagueoflegends.com/cdn/{latestVersion}/img/profileicon/" + str(summoner["profileIconId"]) + ".png")
                        embed.add_field(name=queue,value=leagueData["players"][summoner["name"]]["tftLp"][queue]["rank"] + " **----->** " + currentRank)
                        embed.set_footer(text="Pengu",icon_url="https://i.imgur.com/KGsKZFL.png")
                        embed.set_image(url=rankIcons[league["tier"]])
                        await bot.get_channel(int(channelId)).send(embed=embed)

                elif leagueData["players"][summoner["name"]]["tftLp"][queue]["leaguePoints"] < leaguePoints:
                    # gained lp
                    print(summoner["name"] + " gained " + str(leaguePoints - leagueData["players"][summoner["name"]]["tftLp"][queue]["leaguePoints"]) + "LP!")

                    embed=discord.Embed(description="**+" + str(leaguePoints - leagueData["players"][summoner["name"]]["tftLp"][queue]["leaguePoints"]) + f"** LP in {queue}",timestamp=datetime.datetime.utcnow(), color=0x62C979)
                    embed.set_author(name="🚨 TFT LP UPDATE: " + summoner["name"].upper())
                    embed.set_thumbnail(url=f"https://ddragon.leagueoflegends.com/cdn/{latestVersion}/img/profileicon/" + str(summoner["profileIconId"]) + ".png")
                    embed.add_field(name=queue,value=f"{currentRank} - {leaguePoints} LP")
                    embed.set_footer(text="Pengu",icon_url="https://i.imgur.com/KGsKZFL.png")
                    embed.set_thumbnail(url="https://i.imgur.com/0m1B3Et.png")
                    await bot.get_channel(int(channelId)).send(embed=embed)

                elif leagueData["players"][summoner["name"]]["tftLp"][queue]["leaguePoints"] > leaguePoints:
                    # lost lp
                    print(summoner["name"] + " lost " + str(leagueData["players"][summoner["name"]]["tftLp"][queue]["leaguePoints"] - leaguePoints) + "LP!")

                    embed=discord.Embed(description="*-" + str(leagueData["players"][summoner["name"]]["tftLp"][queue]["leaguePoints"] - leaguePoints) + f"* LP in {queue}",timestamp=datetime.datetime.utcnow(), color=0xE7548C)
                    embed.set_author(name="🚨 TFT LP UPDATE: " + summoner["name"].upper())
                    embed.set_thumbnail(url=f"https://ddragon.leagueoflegends.com/cdn/{latestVersion}/img/profileicon/" + str(summoner["profileIconId"]) + ".png")
                    embed.add_field(name=queue,value=f"{currentRank} - {leaguePoints} LP")
                    embed.set_footer(text="Pengu",icon_url="https://i.imgur.com/KGsKZFL.png")
                    embed.set_thumbnail(url="https://i.imgur.com/bTORHF3.png")
                    await bot.get_channel(int(channelId)).send(embed=embed)

                leagueData["players"][summoner["name"]]["tftLp"][queue] = {"leaguePoints":leaguePoints,"rank":currentRank}
        except:
            print("[BLITZCRANK] Error while trying to update TFT entries: ",traceback.format_exc())

class SpectateButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Spectate", custom_id="button-1", style=discord.ButtonStyle.secondary, emoji="▶️")
    async def button_callback(self, button, interaction):
        print(interaction.user,"requested to spectate a game!")

        if len(leagueData["liveGames"]) == 0:
            await interaction.response.send_message("There are no live games right now!", ephemeral=True)
            return

        await bot.get_user(interaction.user.id).send("Here are the games that I am currently watching:")
        
        for game in leagueData["liveGames"]:
            if leagueData["liveGames"][game]["spectateButtons"]:
                file = discord.File(leagueData["liveGames"][game]["spectateFile"])
                gameId = str(game)
                #await interaction.response.send_message(f"--------------------------\n\n**MATCH ID: {gameId}**\n\nHere is the Windows script to spectate " + leagueData["liveGames"][game]["summoner"] + "\n\n> Instructions\n> 1) Download this file and run it", file=file, ephemeral=True)
                await bot.get_user(interaction.user.id).send(f"--------------------------\n\n**MATCH ID: {gameId}**\n\nHere is the Windows script to spectate " + leagueData["liveGames"][game]["summoner"] + "\n\n> Instructions\n> 1) Download this file and run it",file=file)

# loop through live games and see if any games are finished
async def checkGameStatus():
    opScore = {}
    removeGames = []

    for matchId in leagueData["liveGames"]:

        summonerName = leagueData["liveGames"][matchId]["summoner"]
        summoner = leagueData["players"][summonerName]["summonerData"]

        if (len(leagueData["recentGames"]) >= 10):
            leagueData["recentGames"] = []
            leagueData["recentGames"].append(matchId)

        # check if spectate button is attached
        if not leagueData["liveGames"][matchId]["spectateButtons"]:
            # check op gg profile if live

            if not "summonerId" in leagueData["players"][summonerName]["opggData"]:
                return
            
            opStatus = await opLiveGame(leagueData["players"][summonerName]["opggData"]["summonerId"])
            isLive = opStatus[0]
            opGameId = opStatus[1]

            if isLive:
                print("[BLITZCRANK] OPGG Live Game Found! Adding spectate button ...")
                
                spectateScripts = await opSpectate(opGameId)

                macScript = spectateScripts["mac"]
                windowsScript = await generateFile(spectateScripts["windows"],"bat")
                fileWindows = discord.File(windowsScript)

                # create callback

                # edit message
                discordMsg = await getDiscordMessage(leagueData["liveGames"][matchId]["discordMsgId"])
                await discordMsg.edit(view=SpectateButtons())

                leagueData["liveGames"][matchId]["spectateButtons"] = True
                leagueData["liveGames"][matchId]["spectateFile"] = windowsScript

                print("[BLITZCRANK] Added spectate button to message!")

        # check if game is finished
        matchInfo = await getMatchData(matchId)
        if (matchInfo[0]):
            
            # get summoner information
            summonerName = summoner["name"].replace(" ","")

            print(f"[BLITZCRANK] {summonerName}'s match is finished | ID: {matchId}")

            await checkRiftLp(summoner)
            
            # get match results data
            matchData = matchInfo[1]
            key = matchData["metadata"]["participants"].index(summoner["puuid"])
            gameWon = matchData["info"]["participants"][key]["win"]
            blueWin = matchData["info"]["participants"][0]["win"]
            gameDuration = matchData["info"]["gameDuration"]
            queue = matchData["info"]["queueId"]
            queueType = await parseQueue(queue)

            if "summonerId" in leagueData["players"][summoner["name"]]["opggData"]:
                opId = leagueData["players"][summoner["name"]]["opggData"]["summonerId"]
                await opUpdate(opId)
                opMatch = await opMatches(opId,gameDuration,matchData["info"]["participants"])
                if "is_opscore_active" in opMatch and opMatch != {}:
                    if opMatch["is_opscore_active"]:
                        opScore = await opScores(opMatch)

            postGameResults = {"matchId":matchId, "blueWon":blueWin,"blueTeam":{},"blueKills":0,"redTeam":{},"redKills":0, "opScore":{}}

            if opScore != {}:
                postGameResults["opScores"] = opScore
            
            # get match participants data
            count = 0
            for player in matchData["info"]["participants"]:
                name = player["summonerName"].strip()
                if count < 5:
                    # blue team
                    postGameResults["blueTeam"][name] = {"rank":"","kills":player["kills"],"deaths":player["deaths"],"assists":player["assists"],"opScore":0}

                    # if op score active, set opscore
                    if opScore != {}:
                        postGameResults["blueTeam"][name]["opScore"] = opScore[name]

                    postGameResults["blueKills"] += player["kills"]
                else:
                    # red team
                    postGameResults["redTeam"][name] = {"rank":"","kills":player["kills"],"deaths":player["deaths"],"assists":player["assists"],"opScore":0}

                    # if op score active, set opscore
                    if opScore != {}:
                        postGameResults["redTeam"][name]["opScore"] = opScore[name]

                    postGameResults["redKills"] += player["kills"]
                count+=1

            # edit the graphic
            editedImage = await editGraphic(postGameResults)

            # create embed
            embedHeader = f"{uggId} [Link 🔗](https://u.gg/lol/profile/na1/{summonerName}) | {opggId} [Link 🔗](https://na.op.gg/summoner/userName={summonerName}) | {porofessorId} [Link 🔗](https://www.leagueofgraphs.com/summoner/na/{summonerName})\n\n" if useIconEmojis else f"U.GG [Link 🔗](https://u.gg/lol/profile/na1/{summonerName}) | OP.GG [Link 🔗](https://na.op.gg/summoner/userName={summonerName}) | Porofessor [Link 🔗](https://www.leagueofgraphs.com/summoner/na/{summonerName})\n\n"
            if gameDuration < 900 and not queueType.strip() == "ARAM":
                newEmbed=discord.Embed(description=embedHeader + "⚠️**REMAKE**⚠️\n\nMatch Duration: `"+ await convert(gameDuration)+"` [*](https://app.mobalytics.gg/lol/match/na/" + summonerName + "/" + matchId + ")",timestamp=datetime.datetime.utcnow(), color=0xc0c0c0)
            elif (gameWon):
                newEmbed=discord.Embed(description=embedHeader + "Match Duration: `"+ await convert(gameDuration)+"` [*](https://app.mobalytics.gg/lol/match/na/" + summonerName + "/" + matchId + ") :regional_indicator_w:",timestamp=datetime.datetime.utcnow(), color=0x8BD3E6)
            else:
                newEmbed=discord.Embed(description=embedHeader + "Match Duration: `"+ await convert(gameDuration)+"` [*](https://app.mobalytics.gg/lol/match/na/" + summonerName + "/" + matchId + ") :regional_indicator_l:",timestamp=datetime.datetime.utcnow(), color=0xE7548C)
            newEmbed.set_author(name=f"📌 POST GAME: " + summoner["name"])
            newEmbed.set_thumbnail(url=f"https://ddragon.leagueoflegends.com/cdn/{latestVersion}/img/profileicon/" + str(summoner["profileIconId"]) + ".png")
            newEmbed.set_footer(text=f"ID: {matchId} • powered by shdw 👻",icon_url="https://i.imgur.com/ri6NrsN.png")
            newEmbed.add_field(name="Gamemode",value=queueType,inline = False)
            file = discord.File(editedImage)
            newEmbed.set_image(url=f"attachment://{editedImage}")
            
            # embed = game[2] # get message by id
            discordMsg = await getDiscordMessage(leagueData["liveGames"][matchId]["discordMsgId"])

            await discordMsg.edit(embed=newEmbed,file=file,view=None)

            if (gameDuration < 180):
                await discordMsg.add_reaction("🇷")
            elif gameDuration < 900 and not queueType.strip() == "ARAM":
                await discordMsg.add_reaction("🇦")
                await discordMsg.add_reaction("🇫")
                await discordMsg.add_reaction("🇰")
            elif (gameWon):
                await discordMsg.add_reaction("🇼")
                await discordMsg.add_reaction("🇮")
                await discordMsg.add_reaction("🇳")
            else:
                await discordMsg.add_reaction("🇱")

            if not leagueData["liveGames"][matchId]["spectateFile"] == "":
                os.remove(leagueData["liveGames"][matchId]["spectateFile"])
            
            os.remove(editedImage)
            removeGames.append(matchId)

    for x in removeGames:
        del leagueData["liveGames"][x]
        leagueData["recentGames"].append(x)

    writeData()

# check if a player is playing in a game
async def isPlayerPlaying(summoner):
    playStatus = await isPlaying(summoner["id"])

    if (playStatus[0]):
        summonerName = summoner["name"]
        profileIcon = summoner["profileIconId"]

        currentGame = cass.get_current_match(summoner=summonerName,region="NA")

        if str(currentGame.id) in leagueData["liveGames"] or str(currentGame.id) in leagueData["recentGames"]:
            return
        
        print(f"[BLITZCRANK] {summonerName} is currently in game! | ID: {currentGame.id}")
        matchQueue = await parseQueue(playStatus[1]["gameQueueConfigId"])

        # format blue side
        blueChampions = []
        blueTeam = {}
        orderedBlue = {}

        for blueParticipants in currentGame.blue_team.participants:
            rank = ""
            try:
                rank = await getHighestRank(blueParticipants.summoner.name)
            except:
                pass
            blueTeam[blueParticipants.summoner.name.strip()] = {"role":"","champ":championDatabase["keys"][str(blueParticipants.champion.id)],"champId": blueParticipants.champion.id,"rank":rank}
            blueChampions.append(blueParticipants.champion.id)

        blueOrganized = roleidentification.get_roles(champion_roles, blueChampions) # returns {'TOP': 122, 'JUNGLE': 64, 'MIDDLE': 69, 'BOTTOM': 119, 'UTILITY': 201}
        for role in blueOrganized:
            for player in blueTeam:
                if blueTeam[player]["champId"] == blueOrganized[role]:
                    orderedBlue[player] = blueTeam[player]
                    orderedBlue[player]["role"] = role

        # format red side
        redChampions = []
        redTeam = {}
        orderedRed = {}

        for redParticipants in currentGame.red_team.participants:
            rank = ""
            try:
                rank = await getHighestRank(redParticipants.summoner.name)
            except:
                pass
            redTeam[redParticipants.summoner.name.strip()] = {"role":"","champ":championDatabase["keys"][str(redParticipants.champion.id)],"champId": redParticipants.champion.id,"rank":rank}
            redChampions.append(redParticipants.champion.id)

        redOrganized = roleidentification.get_roles(champion_roles, redChampions) # returns {'TOP': 122, 'JUNGLE': 64, 'MIDDLE': 69, 'BOTTOM': 119, 'UTILITY': 201}
        for role in redOrganized:
            for player in redTeam:
                if redTeam[player]["champId"] == redOrganized[role]:
                    orderedRed[player] = redTeam[player]
                    orderedRed[player]["role"] = role

        #create graphic from these dictionaries
        createdImage = await createGraphic(orderedBlue,orderedRed)

        # send discord embed
        summonerName = summonerName.replace(" ","")
        embedHeader = f"{uggId} [Link 🔗](https://u.gg/lol/profile/na1/{summonerName}) | {opggId} [Link 🔗](https://na.op.gg/summoner/userName={summonerName}) | {porofessorId} [Link 🔗](https://www.leagueofgraphs.com/summoner/na/{summonerName})" if useIconEmojis else f"U.GG [Link 🔗](https://u.gg/lol/profile/na1/{summonerName}) | OP.GG [Link 🔗](https://na.op.gg/summoner/userName={summonerName}) | Porofessor [Link 🔗](https://www.leagueofgraphs.com/summoner/na/{summonerName})"
        embed=discord.Embed(description=embedHeader,timestamp=datetime.datetime.utcnow(), color=0x62C979)
        embed.set_author(name="👁‍🗨 LIVE GAME: " + summoner["name"])
        embed.set_thumbnail(url=f"https://ddragon.leagueoflegends.com/cdn/{latestVersion}/img/profileicon/{profileIcon}.png")
        embed.set_footer(text=f"ID: {currentGame.id}",icon_url="https://i.imgur.com/ri6NrsN.png")
        embed.add_field(name="Gamemode",value=matchQueue,inline = False)
        file = discord.File(createdImage)
        embed.set_image(url=f"attachment://{createdImage}")
        sentEmbed = await bot.get_channel(int(channelId)).send(embed=embed,file=file)
        os.remove(createdImage)

        # store in watched live games
        leagueData["liveGames"][str(currentGame.id)] = {"summoner": summoner["name"], "discordMsgId":sentEmbed.id, "blueTeam":blueTeam, "redTeam":redTeam, "matchDetailsImg":sentEmbed.embeds[0].to_dict()["image"]["url"],"spectateButtons":False,"spectateFile":""}
        leagueData["recentGames"].append(str(currentGame.id))

        print("[BLITZCRANK] Now watching game id:" + str(currentGame.id))
        writeData()

miniRankIcons = {"?": ["https://i.imgur.com/We6MJsw.png", (81, 72, 74)] ,
                "U": ["https://i.imgur.com/We6MJsw.png", (81, 72, 74)] ,
                "I": ["https://opgg-static.akamaized.net/images/medals_mini/iron.png", (81, 72, 74)],
                 "B": ["https://opgg-static.akamaized.net/images/medals_mini/bronze.png", (140, 81, 58)],
                 "S": ["https://opgg-static.akamaized.net/images/medals_mini/silver.png", (128, 152, 157)],
                 "G": ["https://opgg-static.akamaized.net/images/medals_mini/gold.png", (205, 136, 55)],
                 "P": ["https://opgg-static.akamaized.net/images/medals_mini/platinum.png", (78, 153, 150)],
                 "D": ["https://opgg-static.akamaized.net/images/medals_mini/diamond.png", (87, 107, 206)],
                 "M": ["https://opgg-static.akamaized.net/images/medals_mini/master.png", (157, 72, 224)],
                 "GM": ["https://opgg-static.akamaized.net/images/medals_mini/grandmaster.png", (205, 69, 69)],
                 "C": ["https://opgg-static.akamaized.net/images/medals_mini/challenger.png", (244, 200, 116)]}

# create a graphic based on teams
async def createGraphic(blueDict, redDict):
    print("[BLITZCRANK] Creating match graphic ...")

    graphic = Image.new('RGBA',(840,640))

    # download background
    bgImage = "https://i.imgur.com/VmYpgXI.png"
    bgImageLoc = downloadImage(bgImage)
    im = Image.open(bgImageLoc).resize((840,640))
    graphic.paste(im, (0,0))
    os.remove(bgImageLoc)

    # font settings
    fName = "CascadiaMonoPL-Bold.otf" # file name
    fColor = (255,255,255) # color
    fSize = 20 

    # blue side
    i = 10
    for player in blueDict:
        # download and paste image to graphic
        champId = blueDict[player]["champId"]
        icon = downloadImage(f"https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/champion-icons/{champId}.png")
        im = Image.open(icon).convert('RGBA')
        graphic.paste(im, (10, i))
        os.remove(icon)

        # write text to image
        ImageDraw.Draw(graphic).text((150,i+50), player, fill=fColor, font=ImageFont.truetype(fName,fSize))

        # paste rank icon
        if blueDict[player]["rank"] == "GM":
            rank = "GM"
        else:
            rank = blueDict[player]["rank"][0]
        rankIcon = miniRankIcons[rank][0]
        rankColor = miniRankIcons[rank][1]
        rankTitle = blueDict[player]["rank"]
        if rankTitle == "M":
            rankTitle = "MASTER"
        elif rankTitle == "GM":
            rankTitle = "GRANDMASTER"
        elif rankTitle == "CH":
            rankTitle = "CHALLENGER"
        elif rankTitle == "U":
            rankTitle = "UNRANKED"
        icon = downloadImage(rankIcon)
        im = Image.open(icon).resize((40,40))
        graphic.paste(im, (150,i+10),im)
        os.remove(icon)

        # write rank in rank color
        ImageDraw.Draw(graphic).text((200,i+17), rankTitle, fill=rankColor, font=ImageFont.truetype(fName,fSize))

        i += 125

    # red side
    i = 10
    for player in redDict:
        # download and paste image to graphic
        champId = redDict[player]["champId"]
        icon = downloadImage(f"https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/champion-icons/{champId}.png")
        im = Image.open(icon).convert('RGBA')
        graphic.paste(im, (710, i))
        os.remove(icon)

        # write text to image
        ImageDraw.Draw(graphic).text((500,i+50), player, fill=fColor, font=ImageFont.truetype(fName,fSize))

        # paste rank icon
        if redDict[player]["rank"] == "GM":
            rank = "GM"
        else:
            rank = redDict[player]["rank"][0]
        rankIcon = miniRankIcons[rank][0]
        rankColor = miniRankIcons[rank][1]
        rankTitle = redDict[player]["rank"]
        if rankTitle == "M":
            rankTitle = "MASTER"
        elif rankTitle == "GM":
            rankTitle = "GRANDMASTER"
        elif rankTitle == "CH":
            rankTitle = "CHALLENGER"
        elif rankTitle == "U":
            rankTitle = "UNRANKED"
        icon = downloadImage(rankIcon)
        im = Image.open(icon).resize((40,40))
        graphic.paste(im, (500,i+10),im)
        os.remove(icon)

        # write rank with rank color
        ImageDraw.Draw(graphic).text((550,i+17), rankTitle, fill=rankColor, font=ImageFont.truetype(fName,fSize))

        i += 125

    fileName = str(random.randint(1000,2000)) + ".png"
    graphic.save(fileName,"PNG")
    print(f"[BLITZCRANK] Successfully saved graphic {fileName}!")
    return fileName

# edit a graphic for post game
async def editGraphic(postGameDict):
    print("[BLITZCRANK] Creating post match graphic ...")

    graphic = Image.new('RGBA',(840,640))

    # download background
    bgImage = "https://i.imgur.com/VmYpgXI.png"
    bgImageLoc = downloadImage(bgImage)
    im = Image.open(bgImageLoc).resize((840,640))
    graphic.paste(im, (0,0))
    os.remove(bgImageLoc)

    # font size
    fName = "CascadiaMonoPL-Bold.otf" # file name
    fColor = (255,255,255) # color
    fSize = 20 

    # write blue team stats
    i = 10
    for player in postGameDict["blueTeam"]:
        # download and paste champion icon
        champId = leagueData["liveGames"][postGameDict["matchId"]]["blueTeam"][player]["champId"]
        icon = downloadImage(f"https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/champion-icons/{champId}.png")
        im = Image.open(icon).convert('RGBA')
        graphic.paste(im, (10, i))
        os.remove(icon)

        # write player name
        ImageDraw.Draw(graphic).text((150,i+50), player, fill=fColor, font=ImageFont.truetype(fName,fSize))

        # write kda
        text = "(" + str(postGameDict["blueTeam"][player]["kills"]) + "/" + str(postGameDict["blueTeam"][player]["deaths"]) + "/" + str(postGameDict["blueTeam"][player]["assists"]) + ")"
        ImageDraw.Draw(graphic).text((150,i+70), text, fill=fColor, font=ImageFont.truetype(fName,fSize))

        # paste rank icon
        if leagueData["liveGames"][postGameDict["matchId"]]["blueTeam"][player]["rank"] == "GM":
            rank = "GM"
        else:
            rank = leagueData["liveGames"][postGameDict["matchId"]]["blueTeam"][player]["rank"][0]
        rankIcon = miniRankIcons[rank][0]
        rankColor = miniRankIcons[rank][1]
        rankTitle = leagueData["liveGames"][postGameDict["matchId"]]["blueTeam"][player]["rank"]
        if rankTitle == "M":
            rankTitle = "MASTER"
        elif rankTitle == "GM":
            rankTitle = "GRANDMASTER"
        elif rankTitle == "CH":
            rankTitle = "CHALLENGER"
        elif rankTitle == "U":
            rankTitle = "UNRANKED"
        icon = downloadImage(rankIcon)
        im = Image.open(icon).resize((40,40))
        graphic.paste(im, (150,i+10),im)
        os.remove(icon)

        # write rank in rank color
        ImageDraw.Draw(graphic).text((200,i+17), rankTitle, fill=rankColor, font=ImageFont.truetype(fName,fSize))

        i += 125

    # write red team stats
    i = 10
    for player in postGameDict["redTeam"]:
        # download and paste champion icon
        champId = leagueData["liveGames"][postGameDict["matchId"]]["redTeam"][player]["champId"]
        icon = downloadImage(f"https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/champion-icons/{champId}.png")
        im = Image.open(icon).convert('RGBA')
        graphic.paste(im, (710, i))
        os.remove(icon)

        # write player name
        ImageDraw.Draw(graphic).text((500,i+50), player, fill=fColor, font=ImageFont.truetype(fName,fSize))

        # write kda
        text = "(" + str(postGameDict["redTeam"][player]["kills"]) + "/" + str(postGameDict["redTeam"][player]["deaths"]) + "/" + str(postGameDict["redTeam"][player]["assists"]) + ")"
        ImageDraw.Draw(graphic).text((500,i+70), text, fill=fColor, font=ImageFont.truetype(fName,fSize))

        # paste rank icon
        if leagueData["liveGames"][postGameDict["matchId"]]["redTeam"][player]["rank"] == "GM":
            rank = "GM"
        else:
            rank = leagueData["liveGames"][postGameDict["matchId"]]["redTeam"][player]["rank"][0]
        rankIcon = miniRankIcons[rank][0]
        rankColor = miniRankIcons[rank][1]
        rankTitle = leagueData["liveGames"][postGameDict["matchId"]]["redTeam"][player]["rank"]
        if rankTitle == "M":
            rankTitle = "MASTER"
        elif rankTitle == "GM":
            rankTitle = "GRANDMASTER"
        elif rankTitle == "CH":
            rankTitle = "CHALLENGER"
        elif rankTitle == "U":
            rankTitle = "UNRANKED"
        icon = downloadImage(rankIcon)
        im = Image.open(icon).resize((40,40))
        graphic.paste(im, (500,i+10),im)
        os.remove(icon)

        # write rank in rank color
        ImageDraw.Draw(graphic).text((550,i+17), rankTitle, fill=rankColor, font=ImageFont.truetype(fName,fSize))

        i += 125

    # paste overlay
    winnerOverlay = "https://i.imgur.com/dHjQJpy.png" if postGameDict["blueWon"] else "https://i.imgur.com/GRZjKfU.png"
    overlay = downloadImage(winnerOverlay)
    overlayIm = Image.open(overlay).convert('RGBA')
    graphic.paste(overlayIm, (0,0), overlayIm)
    os.remove(overlay)

    # return image file location
    fileName = str(random.randint(1000,2000)) + ".png"
    graphic.save(fileName,"PNG")
    print(f"[BLITZCRANK] Successfully saved post match graphic {fileName}!")
    return fileName

bot.loop.create_task(background_task())
bot.run(botToken)
