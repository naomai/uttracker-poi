import unreal_engine
from installed_packages_store import InstalledPackagesStore
from web_repository import Manager, Loader
import web_service
from content_downloader import downloader, unpacker, link_lookup
from map_converter import dependency_resolver
import yaml
import glob
import orchestration
import os
from pprint import pprint

with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)['unrealpoi']

ueDownloadsPath = os.path.join(config['game']['main'], "UTTDownloads")

localStore = InstalledPackagesStore()
localStore.pathsFromConfig(config['game'])
localStore.downloadsDir = ueDownloadsPath

linkStore = Manager("Storage/Repositories/links.db")
linkStore.cacheDir = config['linkstore']['pages_dir']
os.makedirs(linkStore.cacheDir, exist_ok=True)
linkStore.refreshInterval = config['linkstore']['refresh_interval_min']
Loader.load(linkStore)
linkStore.refresh()

link_lookup.repository = linkStore
link_lookup.downloader = downloader

downloader.targetDir = config['downloads']['temp_dir']
os.makedirs(downloader.targetDir, exist_ok=True)

unpacker.workingDir = config['downloads']['unpack_dir']
unpacker.destinationDir = ueDownloadsPath
os.makedirs(unpacker.workingDir, exist_ok=True)
os.makedirs(unpacker.destinationDir, exist_ok=True)

dependency_resolver.installed_store = localStore
dependency_resolver.web_repo = linkStore
dependency_resolver.destination_dir = config['content_dir']
os.makedirs(dependency_resolver.destination_dir, exist_ok=True)

web_service.store = linkStore
web_service.downloader = downloader
web_service.init(addr="0.0.0.0", port=39801)

orchestration.init()

#mapFile = config['game']['main'] + r'/Maps/AS-Frigate.unr'
#
#with open(mapFile, "rb") as pkgFile:
#    pkg = unreal_engine.loadPackageInfo(pkgFile)
#
#deps = pkg.getDependencies()
#
#for dep in deps:
#    file = dep["filename"]
#    storeLoc = localStore.find(file)
#    print(file + ": " + str(len(storeLoc)))


