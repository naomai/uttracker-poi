from unreal_engine import ucc, UEPackageInfo
from os import path
import re
from content_downloader import downloader
import unreal_engine
from installed_packages_store import InstalledPackagesStore
from web_repository import RepositoryManager
import orchestration

destination_dir = "./Storage/MapContent"
installed_store: InstalledPackagesStore = None
web_repo: RepositoryManager = None

missing_deps = []

def process_job(job: dict):
    map_name = job['mapName']
    map_file = path.join(job['unpackDir'], map_name + ".unr")

    if not path.exists(map_file):
        return
    
    missing_count = resolve_dependencies(map_file, job)

    if missing_count == 0:
        orchestration.queue_add("dependencies_complete", job)
        return

    job['jobData']['downloadsPending'] = missing_count
    job['jobData']['downloadsComplete'] = 0

    for dep in missing_deps:
        process_missing_dependency(dep)


def resolve_dependencies(map_file: str, job: dict):
    with open(map_file, "rb") as pkg_file:
        pkg = unreal_engine.loadPackageInfo(pkg_file)
    
    deps = get_missing_dependencies(pkg)

    if len(deps) == 0:
        return 0

    print(f"Missing dependencies: {deps}")

    for dependency in deps:
        missing_deps.append({
            "info": dependency,
            "job": job,
        })
    
    return len(deps)

def process_missing_dependency(dependency: dict):
    job = dependency['job']
    print(f"Looking for {dependency['info']['name']} guess: {dependency['info']['filename']}")

    (url, archive_filename, filename) = web_repo.get_package_link_info(dependency['info']['name'])
    if not url:
        notify_skip_dependency(dependency['info'], job)
        return False

    subjob = {
        "jobData": {
            'workflow': 'missing_dependency',
            'missingFile': filename,
            'superJob': job,
        }
    }

    downloader.download(url, archive_filename, subjob)
    # single download scheduled, end task
    return False

def process_dependency_after_download(job: dict):
    job_super = job['jobData']['superJob']
    job_super["jobData"]["downloadsComplete"] = job_super["jobData"]["downloadsComplete"] + 1

    if job_super["jobData"]["downloadsPending"] == job_super["jobData"]["downloadsComplete"]: 
        installed_store.reload()
        orchestration.queue_add("dependencies_retry", job_super)
    
    
    
def get_missing_dependencies(package: UEPackageInfo):
    missing = []
    deps = package.getDependencies()

    for dep in deps:
        file = dep["name"]
        storeLoc = installed_store.find(file)
        if len(storeLoc) != 0:
            continue


        missing.append(dep)

    return missing

def notify_skip_dependency(dependency_filename: str, job: dict):
    job["jobData"]["downloadsComplete"] = job["jobData"]["downloadsComplete"] + 1
    #orchestration.queue_add("dependencies_retry", job)

def notify_failure(job: dict):
    orchestration.queue_add("dependencies_failure", job)