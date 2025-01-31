import asyncio
import threading
import queue

from content_downloader import downloader, unpacker

task_queue = queue.Queue()
my_thread = None

def queue_add(tag: str, data: dict):
    task_queue.put((tag, data))

def init():
    my_thread = threading.Thread(target=loop)
    my_thread.start()

def loop():
    while True:
        job = task_queue.get()
        dispatch_job(job)
        
def dispatch_job(job: tuple):
    (tag, data) = job

    if tag == "download_request":
        downloader.process_job(data)
    elif tag == "download_complete":
        unpacker.process_job(data)
    elif tag == "unpack_complete":
        if data['workflow'] == "map_download":
            pass # conversion
        elif data['workflow'] == "missing_dependency":
            pass # resume data['super_job']

