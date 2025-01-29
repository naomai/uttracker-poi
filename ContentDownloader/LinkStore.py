import os
import re
import time
import sqlite3
from pprint import pprint
from .WebClient import WebClient

class LinkStore:
    """
    Manages repositories of download links
    """
    __db = None
    __repos = {}
    cacheDir: str = "/Storage/Repositiories"
    refreshInterval: int = 10080

    def __init__(self, dbFile: str):
        self.__db = sqlite3.connect(dbFile)
        self.__ensureDbStructure()

    def registerRepository(self, signature: str):
        """
        Creates a new `LinkRepository` instance for use with repo adapters

        Args:
            signature: unique short name for repository. 
            1-4 alphanumeric characters
        Returns:
            Prepared `LinkRepository` object
        """
        self.__verifySignature(signature)

        cur = self.__db.cursor()
        repo = LinkRepository(signature, cur)
        repo.cacheDir = os.path.join(os.path.realpath(self.cacheDir), signature) 

        if not os.path.exists(repo.cacheDir):
            os.mkdir(repo.cacheDir)

        self.__repos[signature] = repo
        return repo

    def getExpiredRepos(self):
        """
        List all repositories with links cache older than 
        LinkStore.refreshInterval

        Returns:
            `list` of expired repositories
        """
        expired = []
        for repo in self.__repos.values():
            age = repo.getCacheAge()
            if age >= self.refreshInterval * 60:
                expired.append(repo)
        return expired

    def refresh(self):
        """
        Download pages and parse links for all expired repositories
        """
        expired = self.getExpiredRepos()
        
        for repo in expired:
            try:
                repo.refreshStart()
                repo.refreshEnd()
            finally:
                self.__db.commit()

    def __verifySignature(_, signature: str):
        if not re.match("^[a-zA-Z0-9]{1,4}$", signature):
            raise ValueError("Invalid repository signature string")

    def __ensureDbStructure(self):
        cur = self.__db.cursor()

        cur.execute("""CREATE TABLE IF NOT EXISTS `repos` (
                    `repo_id` INTEGER PRIMARY KEY,
                    `signature` VARCHAR(4) NOT NULL UNIQUE,
                    `last_check` INTEGER DEFAULT 0,
                    `last_update` INTEGER DEFAULT 0
                    )""")

        cur.execute("""CREATE TABLE IF NOT EXISTS `links` (
                    `link_id` INTEGER PRIMARY KEY,
                    `repo_id` INTEGER NOT NULL,
                    `package` TEXT NOT NULL,
                    `filename` TEXT NOT NULL,
                    `url` TEXT NOT NULL UNIQUE
                    )""")
        self.__db.commit()

        
class LinkRepository:
    """
    Provides interface to Repository Adapters for managing links and caches of
    downloaded pages.
    """
    __cur: sqlite3.Cursor = None
    __signature: str
    __repoId: int
    __refreshCallback: callable
    cacheDir: str
    __isModified: bool = False
    __rateLimiterInterval: int = 0
    __rateLimiterLastTime: int = 0

    def __init__(self, signature: str, cur: sqlite3.Cursor):
        self.__cur = cur
        self.__signature = signature
        self.__createTableEntry()

    def storeLink(self, filename: str, url: str):
        self.__isModified = True

        packageName = os.path.splitext(filename)[0]

        self.__cur.execute("""
            INSERT OR IGNORE INTO `links` (`repo_id`, `package`, `filename`, `url`)
            VALUES(:repo, :package, :filename, :url)
            """, {
                'repo': self.__repoId,
                'package': packageName,
                'filename': filename,
                'url': url   
            })


    def getCacheAge(self):
        res = self.__cur.execute("SELECT strftime('%s', 'now') - `last_update` FROM `repos` WHERE `signature`=:signature",
                                    {'signature':self.__signature}
                                )
        repoRow = res.fetchone()
        return repoRow[0]
    
    def storeCacheFileFromWeb(self, fileName: str, url: str):
        self.__waitRateLimiter()

        http = WebClient(url).follow(3).get()

        if http.status() != 200:
            raise RuntimeError("Page download error")

        contents = http.body()
        self.storeCacheFile(fileName, contents)
        return contents

    def storeCacheFile(self, fileName: str, contents: str|bytes):
        filePath = self.__getCacheFilePath(fileName)
        with open(filePath, "wb") as stream:
            stream.write(contents)

    def getCacheFile(self, fileName: str):
        filePath = self.__getCacheFilePath(fileName)
        with open(filePath, "rb") as stream:
            return stream.read()
        
    def getCacheFileAge(self, fileName):
        filePath = self.__getCacheFilePath(fileName)

        if not os.path.exists(filePath):
            return None

        modTime = os.path.getmtime(filePath)
        return int(time.time() - modTime)

    def __getCacheFilePath(self, fileName: str):
        return os.path.join(self.cacheDir, fileName)
    
    def setRefreshCallback(self, callback: callable):
        self.__refreshCallback = callback

    def refreshStart(self):
        self.__cur.execute(
            """UPDATE `repos` SET `last_check`=strftime('%s', 'now') 
                WHERE `signature`=:signature""",
                    {
                        'signature': self.__signature,
                    }
                )
        self.__refreshCallback()

    def refreshEnd(self):
        if self.__isModified:
            self.__cur.execute(
                """UPDATE `repos` SET `last_update`=strftime('%s', 'now') 
                    WHERE `signature`=:signature""",
                        {
                            'signature': self.__signature,
                        }
                    )

    def setRateLimiterInterval(self, seconds: int):
        self.__rateLimiterInterval = seconds

    def __waitRateLimiter(self):
        elapsedTime = time.time() - self.__rateLimiterLastTime
        waitTime = self.__rateLimiterInterval - elapsedTime

        if waitTime > 0:
            time.sleep(waitTime)

        self.__rateLimiterLastTime = time.time()

    def __createTableEntry(self):
        self.__cur.execute(
            """INSERT OR IGNORE INTO `repos` (`signature`) VALUES (:signature) """,
                    {
                        'signature': self.__signature,
                    }
                )
        self.__getMyId()


    def __getMyId(self):
        res = self.__cur.execute("SELECT `repo_id` FROM `repos` WHERE `signature`==:signature",
                {'signature': self.__signature}
            )
        self.__repoId = res.fetchone()[0]

        return self.__repoId;
        
    
