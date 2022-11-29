# emojis for league bot

this is the setup to let blitzcrank bot use emojis for champion icons

<br>![](https://i.imgur.com/pYtGSAT.png)

# icon downloader

scraper.py - used to download all league of legends champion icons

it will create multiple folders of 50 icons that will allow you to mass upload them into discord servers

idscraper.py - used to pull emoji id's from discord servers that the bot is invited in

# instructions

1) create a new discord bot in the discord developer portal
2) run scraper.py to download all champion icons
3) create X amount of discord servers (used to store emojis), where X is the amount of folders
4) mass upload each folder of icons into each emoji discord server
5) invite the discord bot into all of the discord servers
6) run idscraper.py to get all the emoji id's for all the emojis
7) copy and paste all the emojis and id
