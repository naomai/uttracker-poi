import os
import orchestration
from web_repository import RepositoryManager
from installed_packages_store import InstalledPackagesStore

repository: RepositoryManager = None
downloader = None
installed_packages: InstalledPackagesStore = None

# Why this module?
# WebService is in separate thread, we cannot safely access
# database from it.
# Solution: run orchestration job in main thread 

def request(package: str):
        orchestration.queue_add("download_find_link", {
            'package': package,
            'jobData': {
                'workflow': 'map_download',
            },
        })

def process_job(job: dict):
    package = job['package']
    job['mapName'] = package
    del job['package']
    
    filename = f"{package}.unr"

    local_paths = installed_packages.find(filename)

    if len(local_paths) > 0:
        job['jobData']['mapName'] = package
        job['unpackDir'] = os.path.dirname(local_paths[0]['path'])
        orchestration.queue_add("dependencies_retry", job)
        return

    (url, filename) = repository.get_package_link_info(package)

    downloader.download(url, filename, job)
