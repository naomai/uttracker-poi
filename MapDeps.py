import os
import yaml

import orchestration
from installed_packages_store import InstalledPackagesStore
from web_repository import RepositoryManager, RepositoryLoader
from content_downloader import downloader, unpacker, link_lookup
from map_converter import dependency_resolver
import web_service

# CONFIG
with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)['unrealpoi']

ue_downloads_path = os.path.join(config['game']['main'], "UTTDownloads")

# REPOSITORIES
local_packages = InstalledPackagesStore()
local_packages.paths_from_config(config['game'])
local_packages.downloads_dir = ue_downloads_path

links_repo = RepositoryManager("Storage/Repositories/links.db")
links_repo.cacheDir = config['linkstore']['pages_dir']
os.makedirs(links_repo.cacheDir, exist_ok=True)
links_repo.refreshInterval = config['linkstore']['refresh_interval_min']
RepositoryLoader.load(links_repo)
links_repo.refresh()

# WORKER MODULES
link_lookup.repository = links_repo
link_lookup.downloader = downloader

downloader.targetDir = config['downloads']['temp_dir']
os.makedirs(downloader.targetDir, exist_ok=True)

unpacker.workingDir = config['downloads']['unpack_dir']
unpacker.destinationDir = ue_downloads_path
os.makedirs(unpacker.workingDir, exist_ok=True)
os.makedirs(unpacker.destinationDir, exist_ok=True)

dependency_resolver.installed_store = local_packages
dependency_resolver.web_repo = links_repo
dependency_resolver.destination_dir = config['content_dir']
os.makedirs(dependency_resolver.destination_dir, exist_ok=True)

# HTTP SERVICE
web_service.store = links_repo
web_service.downloader = downloader
web_service.init(addr="0.0.0.0", port=39801)

# ORCHESTRATOR
orchestration.init()
