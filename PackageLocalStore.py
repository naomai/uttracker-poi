import os
import glob
from functools import reduce
import unicodedata

class PackageLocalStore:
    paths={}

    def __init__(self):
        pass
        
    def pathsFromConfig(self, config: dict):
        """
        Imports scan location from config dict to the store

        Args:
            config: dictionary with `main` key containing primary path,
            and optionally `additional` key with list of other scan locations 
        """
        self.addScanPath(config['main'])

        if not "additional" in config:
            return
        for path in config['additional']:
            self.addScanPath(path)
    
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

        if not os.path.exists(pathReal + "/Maps") \
                or not os.path.exists(pathReal + "/Textures") \
                or not os.path.exists(pathReal + "/Music") \
                or not os.path.exists(pathReal + "/Sounds") \
                or not os.path.exists(pathReal + "/System"):
                
            raise OSError("Not a valid UE game instance")

        if not pathReal in self.paths:
            self.paths[pathReal] = {
                'cache': self.__scanUeDirectory(pathReal),
            }

    def find(self, file: str):
        """
        Searches local store for file
        """

        def _appendMatching(acc: list, f: dict):
            if f['name'].casefold()  == file.casefold():
                acc.append(f)
            return acc

        files = []
        for path in self.paths.values():
            reduce(_appendMatching, path['cache'], files)

        return files


    def __scanUeDirectory(self, path: str):
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
