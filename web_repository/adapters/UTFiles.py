from ..manager import RepositoryManager
from ..repository import Repository
from pyquery import PyQuery as pq
import urllib

WEBSITE_URL = "https://ut-files.com/index.php"
CACHE_MAX_AGE = 60 * 60 * 24 * 7 # 7 days
RATE_LIMITER = 5

__repo: Repository

def init(store: RepositoryManager):
    global __repo
    __repo = store.register_repository("utfi")
    __repo.set_adapter_refresh_callback(refreshAll)
    __repo.set_ratelimiter_interval(RATE_LIMITER)

def refreshAll():
    refreshPath("Airfight/","af")
    refreshPath("Assault/","as")
    refreshPath("CTF/","ctf")
    refreshPath("CTF4/","ctf4")
    refreshPath("CTFM/","ctfm")
    refreshPath("DeathMatch/","dm", True)
    refreshPath("BunnyTrack/","bt1")
    refreshPath("BunnyTrack/BT/","bt2")
    refreshPath("BunnyTrack/CTF-BT/","cbt")
    refreshPath("Jailbreak/","jb")
    refreshPath("MonsterHunt/","mh")
    refreshPath("SLV/","slv")

def refreshPath(path: str, cacheFile: str, recursive: bool = False):
    global __repo
    contents = fetchIfOld(path, cacheFile)
    if contents == None:
        return
    
    page = pq(contents)
    links = page("table.autoindex_table a[href*='file=']").items()
    for link in links:
        urlRel = link.attr('href')
        url = urllib.parse.urljoin(WEBSITE_URL, urlRel)
        fileName = link.text()
        __repo.store_link(fileName, url)

    if recursive:
        sublinkImgs = page("table.autoindex_table a img[alt='[dir]']").items()
        for img in sublinkImgs:
            link = img.parents('a')
            subdir = link.text()
            if subdir == "Parent Directory":
                continue
            refreshPath(path + "/" + subdir, cacheFile + "_" + subdir, True)

def fetchIfOld(path: str, cacheFile: str):
    global __repo
    cacheFileFull = cacheFile + ".html"
    age = __repo.get_page_cache_age(cacheFileFull)
    if age != None and age < CACHE_MAX_AGE:
        return None
    return __repo.download_page(cacheFileFull, __resolveUrl(path))
    
def __resolveUrl(path: str):
    return WEBSITE_URL + "?dir=Maps/" + path
