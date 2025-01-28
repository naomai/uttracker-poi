import sqlite3
from pprint import pprint

class LinkStore:
    __db = None
    __repos = {}
    refreshInterval: int = 10080

    def __init__(self, dbFile: str):
        self.__db = sqlite3.connect(dbFile)
        self.__ensureDbStructure()

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
        
    def registerRepository(self, signature: str):
        cur = self.__db.cursor()
        repo = LinkRepository(signature, cur)
        self.__repos[signature] = repo
        return repo

    def getExpiredRepos(self):
        expired = []
        for repo in self.__repos.values():
            age = repo.getCacheAge()
            if age >= self.refreshInterval * 60:
                expired.append(repo)
        return expired

    def refresh(self):
        expired = self.getExpiredRepos()
        pprint(expired)

        for repo in expired:
            try:
                repo.refreshStart()
                repo.refreshEnd()
            finally:
                self.__db.commit()


        
class LinkRepository:
    __cur: sqlite3.Cursor = None
    __signature: str
    __refreshCallback: callable
    cacheDir: str
    __isModified: bool = False

    def __init__(self, signature: str, cur: sqlite3.Cursor):
        self.__cur = cur
        self.__signature = signature
        self.__createTableEntry()

    def saveLink(self, filename: str, url: str):
        self.__isModified = True

    def getCacheAge(self):
        res = self.__cur.execute("SELECT strftime('%s', 'now') - `last_update` FROM `repos` WHERE `signature`=:signature",
                                    {'signature':self.__signature}
                                )
        repoRow = res.fetchone()
        return repoRow[0]
    
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

    def __createTableEntry(self):
        self.__cur.execute(
            """INSERT OR IGNORE INTO `repos` (`signature`) VALUES (:signature) """,
                    {
                        'signature': self.__signature,
                    }
                )
