from unreal_engine import ucc, UEPackageInfo
from os import path
import re
from content_downloader import downloader
import unreal_engine
from installed_packages_store import InstalledPackagesStore
from web_repository import RepositoryManager
import shutil
import orchestration

destination_dir = "./Storage/MapContent"
installed_store: InstalledPackagesStore = None
web_repo: RepositoryManager = None

def process_job(job: dict):
    map_name = job['jobData']['mapName']
    map_file = path.join(job['unpackDir'], map_name + ".unr")

    if not path.exists(map_file):
        return
    
    resolved = resolve_dependencies(map_file, job)
    if resolved:
        orchestration.queue_add("dependencies_complete", job)

    


def resolve_dependencies(map_file: str, job: dict):
    with open(map_file, "rb") as pkg_file:
        pkg = unreal_engine.loadPackageInfo(pkg_file)
    
    deps = get_missing_dependencies(pkg)

    if len(deps) == 0:
        return True

    for dependency in deps:
        print(f"Looking for {dependency['name']} (of {len(deps)})...")
        if not "depsProcessed" in job["jobData"]:
            job["jobData"]["depsProcessed"] = []

        if dependency['filename'] in job["jobData"]["depsProcessed"]:
            # skip downloading current dependency, since we already tried
            # it might magically appear with next ones 
            continue

        (url, fileName) = web_repo.get_package_link_info(dependency['name'])
        if not url:
            notify_skip_dependency(dependency['filename'], job)
            return False


        downloader.download(url, fileName, {
                'workflow': 'missing_dependency',
                'missingFile': fileName,
                'superJob': job,
            })
        # single download scheduled, end task
        return False
    
    # exhausted all options, abort
    notify_failure(job)
    return False

def process_dependency_after_download(job: dict):
    job_super = job['jobData']['superJob']
    job_super["jobData"]["depsProcessed"].append(job['jobData']['missingFile'])
    orchestration.queue_add("dependencies_retry", job_super)
    
    
    
def get_missing_dependencies(package: UEPackageInfo):
    missing = []
    deps = package.getDependencies()

    for dep in deps:
        file = dep["filename"]
        storeLoc = installed_store.find(file)
        if len(storeLoc) == 0:
            missing.append(dep)

    return missing

def notify_skip_dependency(dependency_filename: str, job: dict):
    job["jobData"]["depsProcessed"].append(dependency_filename)
    orchestration.queue_add("dependencies_retry", job)

def notify_failure(job: dict):
    orchestration.queue_add("dependencies_failure", job)