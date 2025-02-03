import orchestration
from web_repository import RepositoryManager

repository: RepositoryManager = None
downloader = None

# Why this module?
# WebService is in separate thread, we cannot safely access
# database from it.
# Solution: run orchestration job in main thread 

def request(package: str):
        orchestration.queue_add("download_find_link", {
            'workflow': 'map_download',
            'package': package,
            'jobData': {},
        })

def process_job(job: dict):
    package = job['package']

    (url, filename) = repository.get_package_link_info(package)

    #if downloader.isDownloaded(filename):
        #response = {'status': 'Already downloaded'}
        # call download() anyway, as we'll fall through to the next task
    
    job['mapName'] = package
    del job['package']

    downloader.download(url, filename, job)
