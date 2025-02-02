import asyncio
import threading
import queue

from content_downloader import downloader, unpacker, link_lookup
from map_converter import converter, dependency_resolver

task_queue = queue.Queue()
my_thread = None

def queue_add(tag: str, data: dict):
    task_queue.put((tag, data))

def init():
    loop()

def loop():
    while True:
        job = task_queue.get()
        dispatch_job(job)
        
def dispatch_job(job: tuple):
    (tag, data) = job

    print(f"JobTag={tag}")

    if tag == "download_find_link":
        link_lookup.process_job(data)
    elif tag == "download_request":
        downloader.process_job(data)
    elif tag == "download_complete":
        unpacker.process_job(data)
    elif tag == "unpack_complete" \
        or tag == "dependencies_retry":
            if data['jobData']['workflow'] == "map_download":
                dependency_resolver.process_job(data)
            elif data['jobData']['workflow'] == "missing_dependency":
                dependency_resolver.process_dependency_after_download(data)
    elif tag == "dependencies_complete":
        converter.process_job(data)
    elif tag == "dependencies_failure":
        print(f"Failed processing map {data['jobData']['mapName']}")
