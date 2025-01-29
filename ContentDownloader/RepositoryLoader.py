from .LinkStore import LinkStore
from .Adapters import UTFiles

def load(store: LinkStore):
    UTFiles.init(store)

