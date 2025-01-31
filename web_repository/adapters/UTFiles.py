from ..manager import Manager
from ..repository import Repository
from pyquery import PyQuery as pq
import urllib

WEBSITE_URL = "https://ut-files.com/index.php"
CACHE_MAX_AGE = 60 * 60 * 24 * 7 # 7 days
RATE_LIMITER = 5

__repo: Repository

def init(store: Manager):
    global __repo
    __repo = store.registerRepository("utfi")
    __repo.setRefreshCallback(refreshAll)
    __repo.setRateLimiterInterval(RATE_LIMITER)

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
        __repo.storeLink(fileName, url)

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
    age = __repo.getCacheFileAge(cacheFileFull)
    if age != None and age < CACHE_MAX_AGE:
        return None
    return __repo.storeCacheFileFromWeb(cacheFileFull, __resolveUrl(path))
    
def __resolveUrl(path: str):
    return WEBSITE_URL + "?dir=Maps/" + path
