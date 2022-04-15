from re import L
from discord.ext import commands
import discord, cassiopeia as cass, datetime, asyncio, requests, json, roleidentification

# you need a riot API key (the development one works, but it'll expire after a few days)
# I would suggest applying for one and getting approved for one
riotAPI = ""

# Edit this list with summoners you want to monitor
watchedSummoners = ['BLACKCAR','lrradical','IlIlIIllIllIllIl','Randomdude2468','ASOKO TENSEI','Amumu Main','Yasuo Meister','KRÂM','Motoaki Tanigo','Drch1cken','Burnt Toast741']

# The channel ID to send the notifications to
sendNotificationsChannelID = ""

#######################################################

latestVersion = requests.get("https://ddragon.leagueoflegends.com/realms/na.json").json()["v"]
championDatabase = requests.get("https://ddragon.leagueoflegends.com/cdn/" + latestVersion + "/data/en_US/championFull.json").json()

bot = commands.Bot(command_prefix='!')
cass.set_riot_api_key(riotAPI)

foundGames = []
watchedGames = []

def getSummoner(summoner):
    return requests.get("https://na1.api.riotgames.com/lol/summoner/v4/summoners/by-name/" + summoner + "?api_key=" + riotAPI).json()

def isPlaying(summonerID):
    results = requests.get("https://na1.api.riotgames.com/lol/spectator/v4/active-games/by-summoner/" + summonerID + "?api_key=" + riotAPI)
    if results.status_code != 200:
        return False
    else:
        print("Match found!")
        return True

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="LEAGUE OF LEGENDS"))
    print('=> Logged in as {0.user}'.format(bot))

async def background_task():
    await bot.wait_until_ready()

    while(True):
        for x in range(len(watchedSummoners)):
            await gamerCheck(watchedSummoners[x])
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
    embed.set_footer(text="powered by shdw 👻")
    embed.add_field(name="NA.OP.GG",value="https://na.op.gg/champion/" + args + "/statistics/",inline=True)
    embed.add_field(name="Passive - " + championDatabase["data"][args.title()]["passive"]["name"],value=championDatabase["data"][args.title()]["passive"]["description"],inline=False)
    try:
        for x in range(len(championDatabase["data"][args.title()]["spells"])):
            embed.add_field(name=keys[x] + " - " + championDatabase["data"][args.title()]["spells"][x]["name"],value=championDatabase["data"][args.title()]["spells"][x]["description"] + "\nCooldown: **" + str(championDatabase["data"][args.title()]["spells"][x]["cooldown"]) + "**" ,inline=False)
    except Exception as e:
        pass
    await ctx.send(embed=embed)

# Iterates through watchedGames list, if match finished, check match results 
# and then remove from watchedGames
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
            embed = game[2]
            if (gameWon):
                await embed.add_reaction("🇼")
            else:
                await embed.add_reaction("🇱")
            watchedGames.remove(game)


champion_roles = roleidentification.pull_data()
async def gamerCheck(name):
    global foundGames
    global watchedGames

    summoner = getSummoner(name)
    name = summoner["name"]
    if (isPlaying(summoner["id"])):
        current = cass.get_current_match(summoner=name,region="NA")
        if current.id in foundGames:
            return # game is already found, prevents spam

        # format discord embed with teams, players, and champions
        blueteam = []
        blueSummoners = {}
        for x in current.blue_team.participants:
            blueSummoners[x.champion.id] = x.summoner.name
            blueteam.append(x.champion.id)
        blueteamroles = roleidentification.get_roles(champion_roles,blueteam)
        blueteamcomp = ""
        for x in blueteamroles:
            blueteamcomp += "\n" + championDatabase["keys"][str(blueteamroles[x])] + " - `" + blueSummoners[blueteamroles[x]] + "`"

        redteam = []
        redSummoners = {}
        for x in current.red_team.participants:
            redSummoners[x.champion.id] = x.summoner.name
            redteam.append(x.champion.id)
        redteamroles = roleidentification.get_roles(champion_roles,redteam)
        redteamcomp = ""
        for x in redteamroles:
            redteamcomp += "\n" + championDatabase["keys"][str(redteamroles[x])] + " - `" + redSummoners[redteamroles[x]] + "`"

        embed=discord.Embed(title=name + " Game Found!",description="NA.OP.GG: [Link 🔗](https://na.op.gg/summoner/userName=" + name.replace(" ","") +")",timestamp=datetime.datetime.utcnow(), color=0x62C979)
        embed.set_thumbnail(url="https://ddragon.leagueoflegends.com/cdn/" + latestVersion + "/img/profileicon/" + str(summoner["profileIconId"]) + ".png")
        embed.set_footer(text="Match ID: " + str(current.id) + " • powered by shdw 👻")
        embed.add_field(name="Gamemode",value=str(current.queue).split('Queue.')[1].capitalize().replace("_"," ").title(),inline = False)
        embed.add_field(name="Blue Team",value=blueteamcomp, inline=True)
        embed.add_field(name="Red Team",value=redteamcomp, inline=True)
        sentEmbed = await bot.get_channel(int(sendNotificationsChannelID)).send(embed=embed)

        # if successfully sent, add to foundGames, and watchedGames
        # will add the following item:
        # [matchID, summonerPUUID, discordEmbed]
        foundGames.append(current.id)
        watchedGames.append([str(current.id),summoner["puuid"],sentEmbed])
    
bot.loop.create_task(background_task())

bot.run(')
