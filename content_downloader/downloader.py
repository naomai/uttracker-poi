import os
import re
from urllib.parse import urlparse
import asyncio
import aiohttp
import orchestration

target_dir = "./Storage/Downloads"

def download(url: str, filename = None, job = None):
    """
    Request download of a file 

    Args:
        url: a URL of file to be downloaded
        filename: name of the file (includes extension)
    """
    if not url:
        print(f"Download URL not provided")
        return
    
    job['url'] = url
    job['file'] = filename
    
    if is_downloaded(filename):
        # skip downloading and fall through, maybe add skipped flag?
        notify_complete(url, filename, get_download_path(filename), job)
        return

    orchestration.queue_add("download_request", job)

def process_job(job: dict):
    asyncio.run(__fetch(job['url'], job['file'], job))

async def __fetch(url, filename = None, job = None):
    """
    Fetch file from URL asynchronously, and notify orchestrator

    Args:
        url: a URL of file to be downloaded
        filename: name of the file (includes extension)
        job: job object received from previous step
    """
    async with aiohttp.ClientSession() as client:
        async with client.get(url) as resp:
            print(url)
            path = urlparse(url).path

            if filename == None:
                filename = os.path.basename(path)
                if "Content-Disposition" in resp.headers:
                    header_match = re.match("filename=\"?([^\s\"/\\]+)\"?", resp.headers['Content-Disposition'])
                    if header_match:
                        filename = header_match[0]
            
            
            target_file = os.path.join(target_dir, filename)

            try:
                with open(target_file, "wb") as pkg:
                    while True:
                        data = await resp.content.read()
                        if not data:
                            break
                        pkg.write(data)
                notify_complete(url, filename, target_file, job)
            except Exception:
                pass

def is_downloaded(filename):
    """
    Check if file has aleady been downloaded and is present in cache

    Args:
        filename: name of the file (includes extension)
    """
    if not filename:
        return False
    target_file = os.path.join(target_dir, filename)
    return os.path.exists(target_file)

def get_download_path(filename):
    """
    Get absolute path to the cache of file

    Args:
        filename: name of the file (includes extension)
    """

    return os.path.join(target_dir, filename)

def notify_complete(url, file_name, file_path, job):
    """
    Mark this task as complete, and pass the job params to the next step
    """
    job['url'] = url
    job['file'] = file_name
    job['filePath'] = file_path

    orchestration.queue_add("download_complete", job)
    
