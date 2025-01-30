import os
from os.path import realpath
import glob
from functools import reduce
from pprint import pprint
import shutil

class PackageLocalStore:
    paths={}
    downloadsDir: str
    mainDir: str

    def __init__(self):
        pass
        
    def pathsFromConfig(self, config: dict):
        """
        Imports scan location from config dict to the store

        Args:
            config: dictionary with `main` key containing primary path,
            and optionally `additional` key with list of other scan locations 
        """

        self.mainDir = realpath(config['main'])
        self.addScanPath(self.mainDir)

        if not "additional" in config:
            return
        for path in config['additional']:
            self.addScanPath(realpath(path))
    
    def addScanPath(self, path: str):
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
            self.__updateUeDirectory(pathReal)

    def find(self, file: str):
        """
        Searches local store for file. 
        If the file is present in cache, silently pull it
        into `UTTDownloads` folder.

        Args:
            file: name of file to be found
        Returns:
            List of all locations in which the file was found, provided as dicts: 
            {'name': "CTF-Face.unr", 'path': "/mnt/usb0/Unreal/Maps/CTF-Face.unr"}
        """

        def _appendMatching(acc: list, f: dict):
            if f['name'].casefold()  == file.casefold():
                acc.append(f)
            return acc

        files = []
        cache = []
        for path in self.paths.values():
            reduce(_appendMatching, path['packages'], files)
            reduce(_appendMatching, path['cache'], cache)

        if len(files)==0 and len(cache) > 0:
            pulled = self.pullFromCache(cache[0])
            if pulled:
                files.append(pulled)

        return files
    
    def __updateUeDirectory(self, path: str):
        self.__validateUeInstallation(path)

        self.paths[path] = {
            'packages': self.__scanUeInstalledPackages(path),
            'cache': self.__scanUeCache(path),
        }

    def __scanUeInstalledPackages(self, path: str):
        """
        Scan UE instance directory for common packages

        Args:
            path: location of UE game instance - directory containing 
            subfolders `System`, `Textures`, etc.

        Returns:
            List of all found packages, provided as dicts: 
            ```
            {'name': "CTF-Face.unr", 'path': "/mnt/usb0/Unreal/Maps/CTF-Face.unr"}
            ```
        """
        cache = []
        cache.extend(self.__findFilesByPattern("Maps/*.unr", path))
        cache.extend(self.__findFilesByPattern("System/*.u", path))
        cache.extend(self.__findFilesByPattern("Music/*.umx", path))
        cache.extend(self.__findFilesByPattern("Sounds/*.uax", path))
        cache.extend(self.__findFilesByPattern("Textures/*.utx", path))
        cache.extend(self.__findFilesByPattern("UTTDownloads/*.u*", path))

        return cache

    def __findFilesByPattern(_, pattern: str, rootDir: str):
        """
        Find files matching provided pattern 

        Args:
            pattern: the pattern, allowing special characters from function `glob`
            rootDir: directory in which the matching will occur

        Returns:
            List of all matching files, provided as dicts: 
            ```
            {'name': "CTF-Face.unr", 'path': "/mnt/usb0/Unreal/Maps/CTF-Face.unr"}
            ```
        """
        files = []
        globList = glob.glob(pathname=pattern, root_dir=rootDir)
        files = list(map(
            lambda f: {
                'name': os.path.basename(f),
                'path': os.path.join(rootDir, f),
            },
            globList
        ))
        return files

    def __scanUeCache(self, path: str):
        """
        Scan cache of UE instance

        Args:
            path: location of UE game instance - directory containing 
            subfolder `Cache`

        Returns:
            List of all found packages, provided as dicts: 
            ```
            {'name': "CTF-LiandriDocks.unr", 'path': "/mnt/usb0/Unreal/Cache/9BFAA89C45FB592A549F63B481225292.uxx"}
            ```
        """
        cacheDir = os.path.join(path, "Cache")
        cacheFile = os.path.join(cacheDir, "cache.ini")
        cache = self.__parseUeCacheFile(cacheFile)

        list = []
        
        for cacheRawEntry in cache:
            entryPath = os.path.join(cacheDir, cacheRawEntry[0] + ".uxx")

            if os.path.exists(entryPath):
                cacheEntry = {
                    'name': cacheRawEntry[1],
                    'path': entryPath,
                }
                list.append(cacheEntry)
        pprint(list)
        return list


    def __parseUeCacheFile(self, cacheFilePath: str):
        with open(cacheFilePath) as f:
            cache = [line.rstrip().split("=",1) for line in f]
        
        return cache
    
    def pullFromCache(self, cacheEntry):
        if os.path.exists(cacheEntry['path']):
            dest = os.path.join(self.downloadsDir, cacheEntry['name'])
            shutil.copy2(cacheEntry['path'], dest)
            self.__updateUeDirectory(self.mainDir)
            return {
                'name': cacheEntry['name'],
                'path': dest,
            }
        return None
    
    def __validateUeInstallation(self, dir: str):
        if not os.path.exists(dir + "/Maps") \
                or not os.path.exists(dir + "/Textures") \
                or not os.path.exists(dir + "/Music") \
                or not os.path.exists(dir + "/Sounds") \
                or not os.path.exists(dir + "/System"):
            raise OSError("Not a valid UE game instance")
