from .manager import RepositoryManager

from .adapters import UTFiles, unreal_archive

def load(store: RepositoryManager):
    #UTFiles.init(store)
    unreal_archive.init(store)

