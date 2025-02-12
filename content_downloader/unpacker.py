import threading
from queue import Queue
import patoolib
import os
import time
import shutil
from glob import glob
from os import path
import orchestration

working_dir = None
destination_dir = None

def process_job(job: dict):
    dest_dir = unpack(job['filePath'])
    job['unpackDir'] = path.realpath(dest_dir)
    orchestration.queue_add("unpack_complete", job)

def unpack(archive_path: str):
    """
    Extract all files from provided archive file into `destination_dir`

    Args:
        archive_path: a path to the archive
    """
    wd = path.join(working_dir, str(time.time()))
    os.makedirs(wd)
    try:
        patoolib.extract_archive(archive=archive_path, outdir=wd)
        copy_flat(wd, destination_dir)
    finally:
        shutil.rmtree(wd)
    return destination_dir
    
def copy_flat(src: str, dest: str):
    """
    Copy Unreal package files, flattening directory structure
    Scans `src` directory and its subdirectories for game content,
    and copies all files to `dest` leaving out the original directories.

    `/src/CTF-Face/CTF-Face.unr` -> `/dst/CTF-Face.unr`
    """
    files = []
    files.extend(glob(root_dir=src, pathname="**/*.u", recursive=True))
    files.extend(glob(root_dir=src, pathname="**/*.unr", recursive=True))
    files.extend(glob(root_dir=src, pathname="**/*.uax", recursive=True))
    files.extend(glob(root_dir=src, pathname="**/*.umx", recursive=True))
    files.extend(glob(root_dir=src, pathname="**/*.utx", recursive=True))
    
    for file in files:
        fullPath = path.join(src, file)
        shutil.copy2(fullPath, dest)
    
    