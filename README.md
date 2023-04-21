# 🤖 Blitzcrank Discord Bot
A League of Legends Discord bot that monitors specific players and tracks of their live games and ranked progress.
Can also be used to track TFT ranked progress. Uses Riot Developer Key, with an optional TFT Developer Key

![embed](https://i.imgur.com/6IqKRDR.png)

![postgame](https://i.imgur.com/ryQOJnx.png)

# 📌 Features

- Monitors a list of summoners and sends a Discord embed when they join a game / finish a game
- Spectate Button in embed to spectate games without being logged into League of Legends
- Automatically edits the embed when the game finishes with the match duration and the KDA scoreboard
- Monitors the summoners' LP loss and gains

## Multisearch feature
![cmdline](https://i.imgur.com/6pGBliH.png)

## Track LP Gain/Loss
![cmdline](https://i.imgur.com/9eOMPEv.png)

# 📋 Instructions

- Install the required libraries, one of them is https://github.com/meraki-analytics/role-identification
- Edit the lines under BOT SETTINGS in the discordbot.py
- Run the .py

To enable emoji support, follow instructions in /icondownloader in this repo

# 🧷 Requirements

- Python
- Riot API Key (obtained from Riot Developer Portal)
- Discord Bot Token with INTENTS ENABLED
