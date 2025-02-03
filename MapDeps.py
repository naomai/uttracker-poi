import os
import yaml

import orchestration
from installed_packages_store import InstalledPackagesStore
from web_repository import RepositoryManager, RepositoryLoader
from content_downloader import downloader, unpacker, link_lookup
from map_converter import dependency_resolver
from unreal_engine import ucc
import web_service

# CONFIG
with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)['unrealpoi']

ue_downloads_path = os.path.join(config['game']['main'], "UTTDownloads")
ucc.game_path = config['game']['main']

# REPOSITORIES
local_packages = InstalledPackagesStore()
local_packages.paths_from_config(config['game'])
local_packages.downloads_dir = ue_downloads_path

links_repo = RepositoryManager("Storage/Repositories/links.db")
links_repo.cache_dir = config['linkstore']['pages_dir']
os.makedirs(links_repo.cache_dir, exist_ok=True)
links_repo.refresh_interval = config['linkstore']['refresh_interval_min']
RepositoryLoader.load(links_repo)
links_repo.refresh()

# WORKER MODULES
link_lookup.repository = links_repo
link_lookup.downloader = downloader

downloader.target_dir = config['downloads']['temp_dir']
os.makedirs(downloader.target_dir, exist_ok=True)

unpacker.working_dir = config['downloads']['unpack_dir']
unpacker.destination_dir = ue_downloads_path
os.makedirs(unpacker.working_dir, exist_ok=True)
os.makedirs(unpacker.destination_dir, exist_ok=True)

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
