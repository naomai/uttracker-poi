import os
import re
import sqlite3
from pprint import pprint
from .repository import Repository

class RepositoryManager:
    """
    Manages repositories of download links
    """
    __db = None
    __repos = {}
    cacheDir: str = "/Storage/Repositiories"
    refreshInterval: int = 10080

    def __init__(self, dbFile: str):
        os.makedirs(self.cacheDir, exist_ok=True)
        os.makedirs(os.path.dirname(dbFile), exist_ok=True)
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
        repo = Repository(signature, cur)
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
    
    def getPackageLinkInfo(self, package):
        cur = self.__db.cursor()
        res = cur.execute("SELECT `url`, `filename` FROM `links` WHERE `package`=:package",
                                    {'package':package.casefold()}
                                )
        repoRow = res.fetchone()

        if not repoRow:
            return None, None
        
        return repoRow[0], repoRow[1]

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

        
