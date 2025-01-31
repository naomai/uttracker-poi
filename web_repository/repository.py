import sqlite3
import os
import time
from .web_client import WebClient

class Repository:
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
                'package': packageName.casefold(),
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
        
    