from ftplib import FTP
import glob

connectionInfo = {
    "server": None,
    "username": None,
    "password": None,
    "remote_dir": None
}

def process_task(job: dict):
    if not connectionInfo.host:
        notify_done(job)
        return
    

    notify_done(job)

def push_glob(dir: str, glob: str):
    remote = FTP(connectionInfo['server'], user=connectionInfo['username'], passwd=connectionInfo['password'])
    list = glob.glob(pathname=glob, root_dir=dir, recursive=True)

def notify_done(job: dict):
    orchestration.queue_add("sync_complete", job)