import os
from os.path import realpath
import glob
from functools import reduce
from pprint import pprint
import shutil

class InstalledPackagesStore:
    paths={}
    downloads_dir: str
    main_dir: str

    def __init__(self):
        pass
        
    def paths_from_config(self, config: dict):
        """
        Imports scan location from config dict to the store

        Args:
            config: dictionary with `main` key containing primary path,
            and optionally `additional` key with list of other scan locations 

        Raises:
            OSError: If one of paths does not exist, or is invalid 
            UE game location
        """

        self.main_dir = realpath(config['main'])
        self.add_scan_path(self.main_dir)

        if not "additional" in config:
            return
        for path in config['additional']:
            self.add_scan_path(realpath(path))
    
    def add_scan_path(self, path: str):
        """
        Adds package scan location to the store

        Args:
            path: location of UE game instance - directory containing 
            subfolders `System`, `Textures`, etc.
        Raises:
            OSError: If supplied path does not exist, or is invalid 
            UE game location
        """
        pathReal = os.path.realpath(path)

        if not pathReal in self.paths:
            self.__update_ue_directory(pathReal)

    def find(self, package_name: str) -> list[str]:
        """
        Searches local store for package. 
        If the package is present in cache, silently pull it
        into `UTTDownloads` folder.

        Args:
            package: name of package to be found
        Returns:
            List of all locations in which the package was found, 
            provided as dicts: 
            {
                'name': "CTF-Face.unr", 
                'package': "CTF-Face", 
                'path': "/mnt/usb0/Unreal/Maps/CTF-Face.unr"
            }
        """

        def _append_matching(acc: list, f: dict):
            if f['package'].casefold()  == package_name.casefold():
                acc.append(f)
            return acc

        files = []
        cache = []
        for path in self.paths.values():
            reduce(_append_matching, path['packages'], files)
            reduce(_append_matching, path['cache'], cache)

        if len(files)==0 and len(cache) > 0:
            pulled = self.__pull_from_cache(cache[0])
            if pulled:
                files.append(pulled)

        return files
    
    def reload(self):
        """
        Reload cached list of installed packages
        in all UE instances of this store
        """
        for path in self.paths:
            self.__update_ue_directory(path)
    
    def __update_ue_directory(self, path: str):
        self.__validate_ue_installation(path)

        self.paths[path] = {
            'packages': self.__scan_ue_installed_packages(path),
            'cache': self.__scan_ue_cache(path),
        }

    def __scan_ue_installed_packages(self, path: str):
        """
        Reload this object's list of packages for UE instance directory

        Args:
            path: location of UE game instance - directory containing 
            subfolders `System`, `Textures`, etc.

        Raises:
            OSError: when directory is not a valid UE game instance
        """
        self.__validate_ue_installation(path)
        self.paths[path] = {
            'packages': self.__scan_ue_installed_packages(path),
            'cache': self.__scan_ue_cache(path),
        }

    def __scan_ue_installed_packages(self, path: str):
        """
        Scan UE instance directory for installed packages

        Args:
            path: location of UE game instance - directory containing 
            subfolders `System`, `Textures`, etc.

        Returns:
            List of all found packages, provided as dicts: 
            ```
            {
                'name': "CTF-Face.unr", 
                'package': "CTF-Face",
                'path': "/mnt/usb0/Unreal/Maps/CTF-Face.unr"
            }
            ```
        """
        cache = []
        cache.extend(self.__find_files_by_pattern("Maps/*.unr", path))
        cache.extend(self.__find_files_by_pattern("System/*.u", path))
        cache.extend(self.__find_files_by_pattern("Music/*.umx", path))
        cache.extend(self.__find_files_by_pattern("Sounds/*.uax", path))
        cache.extend(self.__find_files_by_pattern("Textures/*.utx", path))
        cache.extend(self.__find_files_by_pattern("UTTDownloads/*.u*", path))
        cache.extend(self.__find_files_by_pattern("UTTDownloads/*.u*", path))

        return cache

    def __find_files_by_pattern(_, pattern: str, root_dir: str):
        """
        Find files matching provided pattern 

        Args:
            pattern: the pattern, allowing special characters from function `glob`
            rootDir: directory in which the matching will occur

        Returns:
            List of all matching files, provided as dicts: 
            ```
            {
                'name': "CTF-Face.unr", 
                'package': "CTF-Face",
                'path': "/mnt/usb0/Unreal/Maps/CTF-Face.unr"
            }
            ```
        """
        files = []
        glob_list = glob.glob(pathname=pattern, root_dir=root_dir)
        files = list(map(
            lambda f: {
                'name': os.path.basename(f),
                'package': os.path.splitext(os.path.basename(f))[0],
                'path': os.path.join(root_dir, f),
            },
            glob_list
        ))
        return files

    def __scan_ue_cache(self, path: str):
        """
        Scan cache of UE instance

        Args:
            path: location of UE game instance - directory containing 
            subfolder `Cache`

        Returns:
            List of all found packages, provided as dicts: 
            ```
            {
                'name': "CTF-LiandriDocks.unr", 
                'package': "CTF-LiandriDocks", 
                'path': "/mnt/usb0/Unreal/Cache/9BFAA89C45FB592A549F63B481225292.uxx"
            }
            ```
        """
        cache_dir = os.path.join(path, "Cache")
        cache_file = os.path.join(cache_dir, "cache.ini")
        cache = self.__parse_ue_cache_file(cache_file)

        list = []
        
        for cache_raw_entry in cache:
            entry_path = os.path.join(cache_dir, cache_raw_entry[0] + ".uxx")

            if os.path.exists(entry_path):
                cache_entry = {
                    'name': cache_raw_entry[1],
                    'package': os.path.splitext(cache_raw_entry[1])[0],
                    'path': entry_path,
                }
                list.append(cache_entry)
        return list


    def __parse_ue_cache_file(self, cacheFilePath: str) -> list:
        """
        Read UE cache.ini file into a list of
        ```
        [hash, fileName]
        ```
        """
        try:
            with open(cacheFilePath) as f:
                cache = [line.rstrip().split("=",1) for line in f]
        except Exception:
            return []
        return cache
    
    def __pull_from_cache(self, cacheEntry):
        """
        Copy package from cache into `UTTDownloads` directory

        Args:
            cacheEntry: Dict describing cached file:
            ```
            {'name': "CTF-LiandriDocks.unr", 'path': "/mnt/usb0/Unreal/Cache/9BFAA89C45FB592A549F63B481225292.uxx"}
            ```
        Returns:
            Dict containing new `path` of copied file
        """
        if os.path.exists(cacheEntry['path']):
            dest = os.path.join(self.downloads_dir, cacheEntry['name'])
            shutil.copy2(cacheEntry['path'], dest)
            self.__update_ue_directory(self.main_dir)
            return {
                'name': cacheEntry['name'],
                'path': dest,
            }
        return None
    
    def __validate_ue_installation(self, dir: str):
        """
        Check if directory has valid structure of Unreal Engine game

        Raises:
            OSError: when directory is not a valid UE game instance
        """
        if not os.path.exists(dir + "/Maps") \
                or not os.path.exists(dir + "/Textures") \
                or not os.path.exists(dir + "/Music") \
                or not os.path.exists(dir + "/Sounds") \
                or not os.path.exists(dir + "/System"):
            raise OSError("Not a valid UE game instance")
