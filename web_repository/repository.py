import sqlite3
import os
import time
from .web_client import WebClient

class Repository:
    """
    Provides interface to Repository Adapters for managing links and caches of
    downloaded pages.
    """
    cache_dir: str
    refresh_interval: int = 10800
    __cur: sqlite3.Cursor = None
    __signature: str
    __repo_db_id: int
    __refresh_callback: callable
    __modified: bool = False
    __ratelimiter_interval: int = 0
    __ratelimiter_last_time: int = 0

    def __init__(self, signature: str, cur: sqlite3.Cursor):
        self.__cur = cur
        self.__signature = signature
        self.__create_table_entry()

    def store_link(self, container_filename: str, url: str, package_name: str=None, filename: str=None):
        """
        Save encountered file link. 

        Args:
            filename: name of the file which the link targets to
            url: an URL pointing directly to the file - when visited,
            a download should be initiated.
        """
        self.__modified = True

        if package_name == None:
            if filename != None:
                package_name = os.path.splitext(filename)[0]
            else:
                package_name = os.path.splitext(container_filename)[0]

        self.__cur.execute("""
            INSERT OR IGNORE INTO `links` (`repo_id`, `package`, `container_filename`, `url`, 'filename')
            VALUES(:repo, :package, :container_filename, :url, :filename)
            """, {
                'repo': self.__repo_db_id,
                'package': package_name.casefold(),
                'container_filename': container_filename,
                'url': url,
                'filename': filename
            })


    def get_cache_age(self) -> int:
        """
        Get time since the repository has been updated.

        Returns:
            int: number of seconds since the last successful update
        """
        res = self.__cur.execute("SELECT strftime('%s', 'now') - `last_update` FROM `repos` WHERE `signature`=:signature",
                                    {'signature':self.__signature}
                                )
        repo_row = res.fetchone()
        return repo_row[0]
    
    def download_page(self, page_cache_filename: str, url: str) -> bytes:
        """
        Visit the page of repository, and store it in a cache file.

        Args:
            page_cache_filename: name of local cache file in which
            the page will be saved (includes extension)
            url: an URL of the page to be visited

        Returns:
            bytes: contents of the page on success
        
        Raises:
            RuntimeError: when unable to fetch the page (ie. HTTP error)
        """
        self.__wait_ratelimiter()

        http = WebClient(url).follow(3).get()

        if http.status() != 200:
            raise RuntimeError("Page download error")

        contents = http.body()
        self.store_page_cache_file(page_cache_filename, contents)
        return contents

    def store_page_cache_file(self, page_cache_filename: str, contents: str|bytes):
        """
        Save content of page to a cache file.

        Args:
            page_cache_filename: name of local cache file in which
            the page will be saved (includes extension)
            contents: content of page to be saved
        """
        cache_path = self.__get_page_cache_path(page_cache_filename)
        with open(cache_path, "wb") as stream:
            stream.write(contents)

    def get_page_cache_file(self, page_cache_filename: str) -> bytes:
        """
        Get content of page from cache file.

        Args:
            page_cache_filename: name of local cache file from which
            the page will be retrieved (includes extension)

        Returns:
            bytes: content of the requested page
        """
        cache_path = self.__get_page_cache_path(page_cache_filename)
        with open(cache_path, "rb") as stream:
            return stream.read()
        
    def get_page_cache_age(self, page_cache_filename: str):
        """
        Get time since the page cache file was updated.

        Args:
            page_cache_filename: name of local cache file to be checked
            (includes extension)

        Returns:
            int: number of seconds since the last successful update
        """
        cache_path = self.__get_page_cache_path(page_cache_filename)

        if not os.path.exists(cache_path):
            return None

        mod_time = os.path.getmtime(cache_path)
        return int(time.time() - mod_time)

    def __get_page_cache_path(self, page_cache_filename: str):
        """
        Generate absolute path pointing to cache file of page 

        Args:
            page_cache_filename: name of local cache file to be checked
            (includes extension)

        Returns:
            str: absolute path pointing to requested file
        """
        return os.path.join(self.cache_dir, page_cache_filename)
    
    def set_adapter_refresh_callback(self, callback: callable):
        """
        Set the callback to Adapter's code that will execute when
        repository refresh is requested. 
        This is an opportunity for adapter to search for new links,
        and use Repository.store_link(...) if they are found.
        The refreshes happen periodically, and can be configured
        in RepositoryManager.

        Args:
            callback: a function that will be called on refresh
        """
        self.__refresh_callback = callback

    def refresh(self):
        """
        Trigger update process of this Repository
        """
        self.__cur.execute(
            """UPDATE `repos` SET `last_check`=strftime('%s', 'now') 
                WHERE `signature`=:signature""",
                    {
                        'signature': self.__signature,
                    }
                )
        self.__refresh_callback()

        if self.__modified:
            self.__cur.execute(
                """UPDATE `repos` SET `last_update`=strftime('%s', 'now') 
                    WHERE `signature`=:signature""",
                        {
                            'signature': self.__signature,
                        }
                    )


    def set_ratelimiter_interval(self, seconds: int):
        """
        Set interval between consecutive HTTP requests for this Repository.
        We're trying to be polite, by not hogging the hosts with tens
        of page visits per second.

        Args:
            seconds: amount of time to wait between requests
        """
        self.__ratelimiter_interval = seconds

    def __wait_ratelimiter(self):
        """
        Wait until the next request can be made
        Current thread is frozen, until the desired number of seconds
        passes since last request.
        """
        elapsed_seconds = time.time() - self.__ratelimiter_last_time
        remaining_seconds = self.__ratelimiter_interval - elapsed_seconds

        if remaining_seconds > 0:
            time.sleep(remaining_seconds)

        self.__ratelimiter_last_time = time.time()

    def __create_table_entry(self):
        """
        Creates row for this repository in database
        """
        self.__cur.execute(
            """INSERT OR IGNORE INTO `repos` (`signature`) VALUES (:signature) """,
                    {
                        'signature': self.__signature,
                    }
                )
        self.__get_repo_database_id()


    def __get_repo_database_id(self) -> int:
        """
        Gets row ID for this repository in database
        """
        res = self.__cur.execute("SELECT `repo_id` FROM `repos` WHERE `signature`==:signature",
                {'signature': self.__signature}
            )
        self.__repo_db_id = res.fetchone()[0]

        return self.__repo_db_id
        
    