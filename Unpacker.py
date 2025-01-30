import threading
from queue import Queue
import patoolib
import os
import time
import shutil
from glob import glob
from os import path

finishedDownloads: Queue = None
thread = None
workingDir = None
destinationDir = None

def init():
    thread = threading.Thread(target=loop)
    thread.start()

def loop():
    while True:
        downloadInfo = finishedDownloads.get()
        unpack(downloadInfo['filePath'])

def unpack(file: str):
    wd = path.join(workingDir, str(time.time()))
    os.makedirs(wd)
    try:
        patoolib.extract_archive(archive=file, outdir=wd)
        copyFlat(wd, destinationDir)
    finally:
        shutil.rmtree(wd)
    
def copyFlat(src: str, dest: str):
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
    
    