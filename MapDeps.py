import UnrealEngine
from PackageLocalStore import PackageLocalStore
from ContentDownloader.LinkStore import LinkStore
from ContentDownloader import RepositoryLoader
import WebService
from ContentDownloader import Downloader
import yaml
import glob
import Unpacker
import os
from pprint import pprint

with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)['unrealpoi']


localStore = PackageLocalStore()
localStore.pathsFromConfig(config['game'])

linkStore = LinkStore("Storage/Repositories/links.db")
linkStore.cacheDir = config['linkstore']['pages_dir']
os.makedirs(linkStore.cacheDir, exist_ok=True)
linkStore.refreshInterval = config['linkstore']['refresh_interval_min']
RepositoryLoader.load(linkStore)
linkStore.refresh()

downloader = Downloader
downloader.targetDir = config['downloads']['temp_dir']
os.makedirs(downloader.targetDir, exist_ok=True)
downloader.init()

Unpacker.finishedDownloads = downloader.finishedQueue
Unpacker.workingDir = config['downloads']['unpack_dir']
Unpacker.destinationDir = os.path.join(config['game']['main'], "UTTDownloads")
os.makedirs(Unpacker.workingDir, exist_ok=True)
os.makedirs(Unpacker.destinationDir, exist_ok=True)
Unpacker.init()

WebService.store = linkStore
WebService.downloader = downloader
WebService.init(addr="0.0.0.0", port=39801)

#mapFile = config['game']['main'] + r'/Maps/AS-Frigate.unr'
#
#with open(mapFile, "rb") as pkgFile:
#    pkg = UnrealEngine.loadPackage(pkgFile)
#
#deps = pkg.getDependencies()
#
#for dep in deps:
#    file = dep["filename"]
#    storeLoc = localStore.find(file)
#    print(file + ": " + str(len(storeLoc)))


