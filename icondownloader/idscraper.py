from discord.ext import commands
import discord, asyncio, datetime, random, asyncio, os
from discord.ext.commands import CommandNotFound

bot = commands.Bot(command_prefix='!')

@bot.event
async def on_ready():
    print('=> Logged in as {0.user}'.format(bot))

    for guild in bot.guilds:
        for emoji in guild.emojis:
            print(emoji.name, emoji.id) 
    

bot.run("token")
