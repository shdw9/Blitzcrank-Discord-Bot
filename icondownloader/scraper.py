import requests, os

os.chdir(os.path.dirname(__file__))
print(os.path.exists("/2"))

latestVersion = requests.get("https://ddragon.leagueoflegends.com/realms/na.json").json()["v"]
championDatabase = requests.get("https://ddragon.leagueoflegends.com/cdn/" + latestVersion + "/data/en_US/championFull.json").json()

print("Total Number of Champions:",len(championDatabase["keys"]))

def downloadIcon(id,folder):
    if not os.path.exists(os.path.dirname(__file__) + "/" + str(folder)):
        os.mkdir(os.path.dirname(__file__) + "/" + str(folder))
    f = open(os.path.dirname(__file__) + "/" + str(folder) + "/" + str(id) + ".png","wb")
    response = requests.get(f"https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/champion-icons/{id}.png")
    f.write(response.content)
    f.close()

print("Downloading",len(championDatabase["keys"]),"icons ...")

counter = 0
folder = 0
for x in championDatabase["keys"]:
    if counter == 50:
        folder += 1
        counter = 0
    downloadIcon(x,folder)
    counter += 1

print("Finished downloading",len(championDatabase["keys"]),"icons")
