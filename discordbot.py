from sys import argv
import discord
from discord.ext import commands
import cassiopeia as cass
import datetime

bot = commands.Bot(command_prefix='!')
cass.set_riot_api_key("RIOT_API")

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="LEAGUE OF LEGENDS"))
    print("Ready!")

@bot.command()
async def build(ctx, args):
    embed=discord.Embed(timestamp=datetime.datetime.utcnow(), color=0x62C979)
    if (args[0].islower()):
        args = args.capitalize()
    try:
        champicon = cass.Champion(name=args,region="NA").image().url
        embed.set_thumbnail(url=champicon)
    except:
        await ctx.reply(content="That is not a valid champion! :x:")
        
        return

    
    embed.set_author(name=args + " - " + cass.Champion(name=args,region="NA").title, icon_url=champicon)
    embed.set_footer(text="powered by shdw 👻")

    embed.add_field(name="NA.OP.GG",value="https://na.op.gg/champion/" + args + "/statistics/",inline=True)
    try:
        ally = cass.Champion(name=args,region="NA").ally_tips
        enemy = cass.Champion(name=args,region="NA").enemy_tips
        allytips = ""
        enemytips = ""
        for x in range(len(ally)):
            allytips += "\n🔹 " + ally[x]
        for x in range(len(enemy)):
            enemytips += "\n🔸 " + enemy[x]
        if len(ally) == 0:
            allytips = "No ally tips can be found at the moment!"
        if len(enemy) == 0:
            enemytips = "No enemy tips can be found at the moment!"
        embed.add_field(name="Ally Tips ⬇️",value=allytips,inline=False)
        embed.add_field(name="Enemy Tips ⬇️",value=enemytips,inline=False)
    except:
        pass
    
    await ctx.send(embed=embed)

@bot.command()
async def profile(ctx, args):
    try:
        summoner = cass.get_summoner(name=args, region="NA")
        print("\nSummoner Name: " + summoner.name)
        print("Icon: " + summoner.profile_icon().url)
        print("Level: " + str(summoner.level))
        embed=discord.Embed(title=summoner.name + "'s profile",timestamp=datetime.datetime.utcnow(), color=0x62C979)
        embed.description=summoner.champion_masteries[0].champion.__getattribute__('name') + " Main [" + str(summoner.champion_masteries[0].level) + "] with " + str(summoner.champion_masteries[0].points) + " points"
        embed.set_author(name=summoner.name, icon_url=summoner.profile_icon().url)
        embed.set_footer(text="powered by shdw 👻")

        embed.add_field(name="Level",value=str(summoner.level), inline=True)
        embed.add_field(name="NA.OP.GG",value="[Link](https://na.op.gg/summoner/userName=" + args +")",inline=True)

        embed.set_thumbnail(url=summoner.profile_icon().url)
        
        await ctx.send(embed=embed)
    except:
        await ctx.reply(content="That profile does not exist! :x:")

@bot.command()
async def game(ctx, arg):
    try:
        summoner = cass.get_summoner(name=arg, region="NA")
        print("\nSummoner Name: " + summoner.name)
    except:
        print("That summoner name does not exist!")
        await ctx.reply(content="That summoner name does not exist! :x:")
        return
    try:
        current = cass.get_current_match(summoner=arg,region="NA")
        blueteam = []
        redteam = []
        blueteamcomp = ""
        redteamcomp = ""
        currentChamp = ""
        for x in current.blue_team.participants:
            blueteam.append(x.summoner.name + " - " + x.champion.name)
            blueteamcomp += "\n" + x.summoner.name + " - " + x.champion.name
            if (x.summoner.name == summoner.name):
                currentChamp = x.champion.name
                print("Current Champ: " + currentChamp)
        for x in current.red_team.participants:
            redteam.append(x.summoner.name + " - " + x.champion.name)
            redteamcomp += "\n" + x.summoner.name + " - " + x.champion.name
        embed=discord.Embed(title=summoner.name + "'s Current Game",description="NA.OP.GG: [Link 🔗](https://na.op.gg/summoner/userName=" + arg +")",timestamp=datetime.datetime.utcnow(), color=0x62C979)
        if " " in currentChamp:
            linkName = currentChamp.replace(" ", "")
        else:
            linkName = currentChamp
        gamemode = str(current.queue).split('Queue.')[1].capitalize()
        if "_" in gamemode:
            rawr = gamemode.replace("_"," ").title()
            gamemode = rawr
        embed.set_author(name=summoner.name + " is playing as " + currentChamp, icon_url=cass.Champion(name=currentChamp,region="NA").image().url, url="https://na.op.gg/champion/" + linkName + "/statistics/")
        embed.set_thumbnail(url=summoner.profile_icon().url)
        embed.set_footer(text="powered by shdw 👻")
        print(current.queue)
        embed.add_field(name="Gamemode",value=gamemode,inline = False)
        embed.add_field(name="Blue Team",value=blueteamcomp, inline=True)
        embed.add_field(name="Red Team",value=redteamcomp, inline=True)
        await ctx.send(embed=embed)
        del blueteam
        del redteam
    except Exception as e:
        print(e)
        await ctx.reply(content=summoner.name + " is not currently in game! :x:")

bot.run('BOTTOKEN')
