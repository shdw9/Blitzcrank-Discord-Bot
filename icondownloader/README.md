# ARCHIVED, THIS IS NO LONGER NEEDED

## icon downloader - emojis for Blitzcrank

Instructions down below to get emojis in Blitzcrank bot (shown below)

<br>![](https://i.imgur.com/NEWuB4f.png)

files: 

> scraper.py - used to download all league of legends champion icons, will create multiple folders of 50 icons

> idscraper.py - used to pull emoji id's from discord servers that the bot is invited in

## instructions

1) use your league discord bot token and save it for later
2) run scraper.py to download all the current champion icons - this will create X amount of folders.
3) create X amount of discord SERVERS based on the amount of folders (this will be used to store the emojis, each server has a limit of 50 emojis)
4) upload all of the contents of each folder per discord server
5) upload the files found in /icons/ of this repo (it includes site icons and rank icons)
6) invite the league discord bot from step 1 to ALL of the discord servers you created
7) run idscraper.py to scrape all of the emojis that the discord bot is in 
8) copy and paste the link generated into the iconsPastebin setting in Blitzcrank
9) set useIconEmojis setting to true
10) set the orbId - challengerId that can be found in the link generated in the following format: <:emojiName:emojiId>
