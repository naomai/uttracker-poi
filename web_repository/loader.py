from .manager import RepositoryManager

from .adapters import UTFiles

def load(store: RepositoryManager):
    UTFiles.init(store)

