# shdwbot (League of Legends tool)
A very handy League of Legends Discord Bot that monitors a list of summoners and more (WIP)

# Features

- Monitors a list of summoners and sends an embed when they join a game
- Automatically edits the embed when the game finishes with the match duration and the KDA scoreboard
- Monitors the summoners' LP loss and gains
- Jungler.gg integration 
<br> !blue (jungleChampion) would return recommended tips for blue side for that jungle champion
<br> !red (jungleChampion) would return recommended tips for red side for that jungle champion

> When that summoner is found in a game, it will send a Discord embed to a specified Discord channel.
> <br>Eventually, when the game finishes, it will react with a W or an L (depending on the summoner's side)
![cmdline](https://i.imgur.com/2xsBbGJ.png)

> Multisearch feature (copy and paste the lobby join messages)
![cmdline](https://i.imgur.com/6pGBliH.png)

> **Update 4/21/2021** <br>The embed now changes when the game finishes with the match duration and everyone's scores
![cmdline](https://i.imgur.com/oHTYONq.gif)

> Now monitor's everybody's LP gains/loss<br>
![cmdline](https://i.imgur.com/9eOMPEv.png)

> Jungler.gg integration (!blue (jgChamp) or !red (jgChamp))
![cmdline](https://i.imgur.com/o3GjRbG.png)
# Instructions

- Edit the first few lines to put in the list of summoners and your Riot API key.
- Edit the last line to add in your Discord Bot token
- Run the .py

# Requirements

- Python
- Riot API Key (obtained from Riot Developer Portal)
