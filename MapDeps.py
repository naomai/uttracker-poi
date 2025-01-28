import UnrealEngine
from PackageLocalStore import PackageLocalStore
from ContentDownloader.LinkStore import LinkStore
from ContentDownloader import RepositoryLoader
import yaml
import glob
from pprint import pprint

with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)['unrealpoi']


store = PackageLocalStore()
store.pathsFromConfig(config['game'])

mapFile = config['game']['main'] + r'/Maps/AS-Frigate.unr'

with open(mapFile, "rb") as pkgFile:
    pkg = UnrealEngine.loadPackage(pkgFile)

deps = pkg.getDependencies()

for dep in deps:
    file = dep["filename"]
    storeLoc = store.find(file)
    print(file + ": " + str(len(storeLoc)))


store = LinkStore("Storage/Repositories/links.db")
RepositoryLoader.load(store)
store.refreshInterval = config['linkstore']['refresh_interval_min']
store.refresh()