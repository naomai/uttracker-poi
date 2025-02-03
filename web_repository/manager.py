import os
import re
import sqlite3
from .repository import Repository

class RepositoryManager:
    """
    Manages repositories of download links
    """
    __db = None
    __repos: dict[str, Repository] = {}
    cache_dir: str = "/Storage/Repositiories"
    refresh_interval: int = 10080

    def __init__(self, dbFile: str):
        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(os.path.dirname(dbFile), exist_ok=True)
        self.__db = sqlite3.connect(dbFile)
        self.__ensure_db_structure()

    def register_repository(self, signature: str) -> Repository:
        """
        Creates a new `LinkRepository` instance for use with repo adapters

        Args:
            signature: unique short name for repository. 
            1-4 alphanumeric characters
        Returns:
            Prepared `LinkRepository` object
        """
        self.__verify_signature(signature)

        cur = self.__db.cursor()
        repo = Repository(signature, cur)
        repo.cache_dir = os.path.join(os.path.realpath(self.cache_dir), signature) 

        if not os.path.exists(repo.cache_dir):
            os.mkdir(repo.cache_dir)

        self.__repos[signature] = repo
        return repo

    def get_expired_repos(self) -> list[Repository]:
        """
        List all repositories with links cache older than 
        LinkStore.refreshInterval

        Returns:
            `list` of expired repositories
        """
        expired = []
        for repo in self.__repos.values():
            age = repo.get_cache_age()
            if age >= self.refresh_interval * 60:
                expired.append(repo)
        return expired

    def refresh(self):
        """
        Download pages and parse links for all expired repositories
        """
        expired = self.get_expired_repos()
        
        for repo in expired:
            try:
                repo.refresh()
            finally:
                self.__db.commit()
    
    def get_package_link_info(self, package) -> tuple[str, str]:
        cur = self.__db.cursor()
        res = cur.execute("SELECT `url`, `filename` FROM `links` WHERE `package`=:package",
                                    {'package':package.casefold()}
                                )
        repo_row = res.fetchone()

        if not repo_row:
            return None, None
        
        return repo_row[0], repo_row[1]

    def __verify_signature(_, signature: str):
        if not re.match("^[a-zA-Z0-9]{1,4}$", signature):
            raise ValueError("Invalid repository signature string")

    def __ensure_db_structure(self):
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

        
