from .LinkStore import LinkStore
from .Repositories import UTFiles

def load(store: LinkStore):
    UTFiles.init(store)

