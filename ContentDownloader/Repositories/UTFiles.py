from ..LinkStore import LinkRepository, LinkStore

__cacheDir: str
__repo: LinkRepository

def init(store: LinkStore):
    __repo = store.registerRepository("utfi")
    __repo.setRefreshCallback(refreshLinks)

def refreshLinks():
    print("REFRESZ")

