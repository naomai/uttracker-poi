from unreal_engine import ucc, UEPackageInfo
from os import path
import re
from content_downloader import downloader
import unreal_engine
from installed_packages_store import InstalledPackagesStore
import shutil
import orchestration

destination_dir = "./Storage/MapContent"
installed_store = None
web_repo = None

def process_job(job: dict):
    map_name = job['jobData']['mapName']
    map_file = path.join(job['unpackDir'], map_name + ".unr")

    if not path.exists(map_file):
        return
    
    resolved = resolve_dependencies(map_file, job)
    if resolved:
        orchestration.queue_add("depencencies_complete", job)

    


def resolve_dependencies(map_file: str, job: dict):
    with open(map_file, "rb") as pkg_file:
        pkg = unreal_engine.loadPackageInfo(pkg_file)
    
    deps = get_missing_dependencies(pkg)

    if len(deps) == 0:
        return True

    for dependency in deps:
        if not "depsProcessed" in job["jobData"]:
            job["jobData"]["depsProcessed"] = []

        if dependency['name'] in job["jobData"]["depsProcessed"]:
            # skip downloading current dependency, since we already tried
            # it might magically appear with next ones 
            continue

        (url, fileName) = web_repo.getPackageLinkInfo(dependency['name'])
        
        downloader.download(url, fileName, {
                'workflow': 'missing_dependency',
                'missingFile': fileName,
                'superJob': job,
            })
        # single download scheduled, end task
        return False
    
    # exhausted all options, abort (TODO)

def process_dependency_download(job: dict):
    job_super = job['jobData']['superJob']
    job_super["jobData"]["depsProcessed"].append(job['jobData']['missingFile'])
    orchestration.queue_add("unpack_complete", job_super)
    
    
    
def get_missing_dependencies(package: UEPackageInfo):
    missing = []
    deps = package.getDependencies()

    for dep in deps:
        file = dep["filename"]
        storeLoc = installed_store.find(file)
        if len(storeLoc) > 0:
            missing.append(dep)

    return missing