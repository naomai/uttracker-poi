from .manager import Manager

from .adapters import UTFiles

def load(store: Manager):
    UTFiles.init(store)

