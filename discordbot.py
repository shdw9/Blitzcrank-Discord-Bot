from re import L
from discord.ext import commands
from bs4 import BeautifulSoup
import discord, cassiopeia as cass, datetime, asyncio, requests, json, roleidentification
from discord.ext.commands import CommandNotFound

riotAPI = ""

watchedSummoners = ['BLACKCAR','lrradical','IlIlIIllIllIllIl','Randomdude2468','ASOKO TENSEI','Amumu Main','Yasuo Meister','KRÂM','Motoaki Tanigo','Drch1cken','Burnt Toast741']

sendNotificationsChannelID = ""

#######################################################

latestVersion = requests.get("https://ddragon.leagueoflegends.com/realms/na.json").json()["v"]
championDatabase = requests.get("https://ddragon.leagueoflegends.com/cdn/" + latestVersion + "/data/en_US/championFull.json").json()

bot = commands.Bot(command_prefix='!')
cass.set_riot_api_key(riotAPI)

foundGames = []
watchedGames = []

# retrieves summoner information based on summonerName
def getSummoner(summoner):
    return requests.get("https://na1.api.riotgames.com/lol/summoner/v4/summoners/by-name/" + summoner + "?api_key=" + riotAPI).json()

# checks to see if there is an ONGOING game going with summoner name
def isPlaying(summonerID):
    results = requests.get("https://na1.api.riotgames.com/lol/spectator/v4/active-games/by-summoner/" + summonerID + "?api_key=" + riotAPI)
    if results.status_code != 200:
        return False
    else:
        return True

# parses a queue ID
def parseQueue(queue):
    for q in requests.get("https://static.developer.riotgames.com/docs/lol/queues.json").json():
        if (queue == q["queueId"]):
            queueType = q["description"]
            return queueType.replace("games","")

# converts seconds to a formatted minutes and seconds
def convert(seconds):
    seconds = seconds % (24 * 3600)
    hour = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
      
    return "%02dm %02ds" % (minutes, seconds)

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="LEAGUE OF LEGENDS"))
    print('=> Logged in as {0.user}'.format(bot))

async def background_task():
    await bot.wait_until_ready()

    while(True):
        for summoner in watchedSummoners:
            await gamerCheck(summoner)
            await getLeagueRanks(summoner)
            await asyncio.sleep(30)
        await asyncio.sleep(120)
        await gameCheck()
 
# This command is lets you copy and paste the lobby joined messages 
# and parses it into a na.op.gg link. All you have to do is copy and paste the link
@bot.command()
async def multisearch(ctx,*,args):
    searchQuery = "https://na.op.gg/multisearch/na?summoners="
    if "joined the lobby" in args: # ENGLISH CLIENT
        for line in args.split("\n"):
            name = line.split(" joined")[0].replace(" ","+")
            searchQuery += name + "%2C"
        print(searchQuery)
        await ctx.reply(searchQuery[:len(searchQuery)-3])
        try:
            await ctx.message.delete()
        except:
            pass
    elif "님이 로비에 참가하셨습니다" in args: # KOREAN CLIENT
        for line in args.split("\n"):
            name = line.split(" 님이")[0].replace(" ","+")
            searchQuery += name + "%2C"
        print(searchQuery)
        await ctx.reply(searchQuery[:len(searchQuery)-3])
        try:
            await ctx.message.delete()
        except:
            pass
    else:
        await ctx.reply("Sorry I can't comprehend what you're saying! :sweat_smile: ")

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
        champicon = "https://ddragon.leagueoflegends.com/cdn/12.7.1/img/champion/" + args + ".png"
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

async def gameCheck():
    global watchedGames

    for game in watchedGames:
        matchID = game[0]
        summonerPUUID = game[1]

        matchResults = requests.get("https://americas.api.riotgames.com/lol/match/v5/matches/NA1_" + matchID + "?api_key=" + riotAPI)
        if (matchResults.status_code == 200):
            print("Match ID " + matchID + " has been finished")
            matchData = matchResults.json()
            key = matchData["metadata"]["participants"].index(summonerPUUID)
            gameWon = matchData["info"]["participants"][key]["win"]
            gameDuration = matchData["info"]["gameDuration"]
            embed = game[2]
            currentSummoner = requests.get("https://na1.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/"+ summonerPUUID + "?api_key=" + riotAPI).json()
            summonerName = currentSummoner["name"]
            if (gameWon):
                await embed.add_reaction("🇼")
                newEmbed=discord.Embed(description="NA.OP.GG: [Link 🔗](https://na.op.gg/summoner/userName=" + summonerName.replace(" ","") +") | Mobalytics: [Link 🔗](https://app.mobalytics.gg/lol/profile/na/"+ summonerName.replace(" ","") +")\n\nMatch Duration: `"+ convert(gameDuration)+"`",timestamp=datetime.datetime.utcnow(), color=0x8BD3E6)
            else:
                await embed.add_reaction("🇱")
                newEmbed=discord.Embed(description="NA.OP.GG: [Link 🔗](https://na.op.gg/summoner/userName=" + summonerName.replace(" ","") +") | Mobalytics: [Link 🔗](https://app.mobalytics.gg/lol/profile/na/"+ summonerName.replace(" ","") +")\n\nMatch Duration: `"+ convert(gameDuration)+"`",timestamp=datetime.datetime.utcnow(), color=0xE7548C)
            #await embed.edit(content="Match Duration: `" + convert(gameDuration) + "`")

            blueteamcomp = ""
            redteamcomp = ""
            queue = matchData["info"]["queueId"]
            for q in requests.get("https://static.developer.riotgames.com/docs/lol/queues.json").json():
                if (queue == q["queueId"]):
                    queueType = q["description"]

            count = 0
            for player in matchData["info"]["participants"]:
                if count < 5:
                    blueteamcomp += "\n" + player["championName"] + " - `" + player["summonerName"] + "` (" + str(player["kills"]) + "/" + str(player["deaths"]) + "/" + str(player["assists"]) + ")"
                else:
                    redteamcomp += "\n" + player["championName"] + " - `" + player["summonerName"] + "` (" + str(player["kills"]) + "/" + str(player["deaths"]) + "/" + str(player["assists"]) + ")"
                count+=1

            
            newEmbed.set_author(name=summonerName + " Game Finished!",icon_url="https://ddragon.leagueoflegends.com/cdn/" + latestVersion + "/img/profileicon/" + str(currentSummoner["profileIconId"]) + ".png")
            newEmbed.set_footer(text="ID: " + matchID + " • powered by shdw 👻",icon_url="https://i.imgur.com/ri6NrsN.png")
            newEmbed.add_field(name="Gamemode",value=queueType.replace("games",""),inline = False)
            newEmbed.add_field(name="Blue Team",value=blueteamcomp, inline=True)
            newEmbed.add_field(name="Red Team",value=redteamcomp, inline=True)
            await embed.edit(embed=newEmbed)
            watchedGames.remove(game)


champion_roles = roleidentification.pull_data()
async def gamerCheck(name):
    global foundGames
    global watchedGames

    while(True):
        try:
            summoner = getSummoner(name)
            name = summoner["name"]
            break
        except:
            pass

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
        blueteamroles = roleidentification.get_roles(champion_roles,blueteam)
        blueteamcomp = ""
        for x in blueteamroles:
            blueteamcomp += "\n" + championDatabase["keys"][str(blueteamroles[x])] + " - `" + blueSummoners[blueteamroles[x]].strip() + "`"

        redteam = []
        redSummoners = {}
        for x in current.red_team.participants:
            redSummoners[x.champion.id] = x.summoner.name
            redteam.append(x.champion.id)
        redteamroles = roleidentification.get_roles(champion_roles,redteam)
        redteamcomp = ""
        for x in redteamroles:
            redteamcomp += "\n" + championDatabase["keys"][str(redteamroles[x])] + " - `" + redSummoners[redteamroles[x]].strip() + "`"

        embed=discord.Embed(description="NA.OP.GG: [Link 🔗](https://na.op.gg/summoner/userName=" + name.replace(" ","") +") | Mobalytics: [Link 🔗](https://app.mobalytics.gg/lol/profile/na/"+ name.replace(" ","") +")",timestamp=datetime.datetime.utcnow(), color=0x62C979)
        embed.set_author(name=name + " Game Found!",icon_url="https://ddragon.leagueoflegends.com/cdn/" + latestVersion + "/img/profileicon/" + str(summoner["profileIconId"]) + ".png")
        embed.set_footer(text="ID: " + str(current.id) + " • powered by shdw 👻",icon_url="https://i.imgur.com/ri6NrsN.png")
        embed.add_field(name="Gamemode",value=matchQueue,inline = False)
        embed.add_field(name="Blue Team",value=blueteamcomp, inline=True)
        embed.add_field(name="Red Team",value=redteamcomp, inline=True)
        sentEmbed = await bot.get_channel(int(sendNotificationsChannelID)).send(embed=embed)

        # if successfully sent, add to foundGames, and watchedGames
        foundGames.append(current.id)
        watchedGames.append([str(current.id),summoner["puuid"],sentEmbed])
    
leaguePointsBook = {}
for x in watchedSummoners:
    leaguePointsBook[x] = {}

async def getLeagueRanks(summoner):
    # print("Pulling " + summoner + "'s rank ...")
    try:
        summonerInfo = requests.get("https://na1.api.riotgames.com/lol/summoner/v4/summoners/by-name/" + summoner + "?api_key=" + riotAPI).json()
        summonerID = summonerInfo["id"]
    except:
        return
        pass
    req = requests.get("https://na1.api.riotgames.com/lol/league/v4/entries/by-summoner/"+ summonerID + "?api_key=" + riotAPI).json()
    try:
        for gamemode in req:
            queue = gamemode["queueType"]
            tier = gamemode["tier"]
            rank = gamemode["rank"]
            leaguePoints = gamemode["leaguePoints"]

            try:
                if leaguePointsBook[summoner][queue]["leaguePoints"] < leaguePoints:
                    print(summoner + " gained " + str(leaguePoints-leaguePointsBook[summoner][queue]["leaguePoints"]) + " LP in " + queue)

                    embed=discord.Embed(description="**+" + str(leaguePoints-leaguePointsBook[summoner][queue]["leaguePoints"]) + "** LP in " + queue.replace("_"," "),timestamp=datetime.datetime.utcnow(), color=0x62C979)
                    embed.set_author(name="🚨 " + summoner + " UPDATE 🚨",icon_url="https://ddragon.leagueoflegends.com/cdn/" + latestVersion + "/img/profileicon/" + str(summonerInfo["profileIconId"]) + ".png")
                    embed.add_field(name=queue.replace("_"," "),value=tier + " " + rank + " - " + str(leaguePoints) + " LP")
                    embed.set_footer(text="powered by shdw 👻",icon_url="https://i.imgur.com/ri6NrsN.png")
                    embed.set_thumbnail(url="https://i.imgur.com/Hfvor2h.png")
                    await bot.get_channel(int(sendNotificationsChannelID)).send(embed=embed)
                elif leaguePointsBook[summoner][queue]["leaguePoints"] > leaguePoints:
                    print(summoner + " lost " + str(leaguePointsBook[summoner][queue]["leaguePoints"]-leaguePoints) + " LP in " + queue)

                    embed=discord.Embed(description="*-" + str(leaguePointsBook[summoner][queue]["leaguePoints"]-leaguePoints) + "* LP in " + queue.replace("_"," "),timestamp=datetime.datetime.utcnow(), color=0xE7548C)
                    embed.set_author(name="🚨 " + summoner + " UPDATE 🚨",icon_url="https://ddragon.leagueoflegends.com/cdn/" + latestVersion + "/img/profileicon/" + str(summonerInfo["profileIconId"]) + ".png")
                    embed.add_field(name=queue.replace("_"," "),value=tier + " " + rank + " - " + str(leaguePoints) + " LP")
                    embed.set_footer(text="powered by shdw 👻",icon_url="https://i.imgur.com/ri6NrsN.png")
                    embed.set_thumbnail(url="https://i.imgur.com/gT929Bg.png")
                    await bot.get_channel(int(sendNotificationsChannelID)).send(embed=embed)
            except Exception as e:
                #print(e)
                pass

            # update dictionary
            leaguePointsBook[summoner][queue] = {"leaguePoints":leaguePoints,"rank":tier + " " + rank}
    except:
        pass
    #print(leaguePointsBook)

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
    
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, CommandNotFound):
        return
    raise error
    
bot.loop.create_task(background_task())

bot.run('')
