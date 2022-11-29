from discord.ext import commands
import requests

bot = commands.Bot(command_prefix='!')

@bot.event
async def on_ready():
    print("Pulling all emoji ids ...")

    text = ""
    for guild in bot.guilds:
        for emoji in guild.emojis:
            text += emoji.name + " " + str(emoji.id) + "\n"

    print("Finished pulling all emojis!")

    a = requests.post("https://hastebin.com/documents", data = text)
    link = "https://hastebin.com/raw/" + a.json()["key"]

    print("\nUse this link for emojiIds for Blitzcrank BOT:")
    print(link)
    

bot.run("")
