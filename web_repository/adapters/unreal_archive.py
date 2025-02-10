from ..manager import RepositoryManager
from ..repository import Repository
import yaml 
import urllib
import glob
from os import path

REPO_URL = "https://github.com/unreal-archive/unreal-archive-data.git"
CACHE_MAX_AGE = 60 * 60 * 24 * 30 # 30 days

__repo: Repository

def init(store: RepositoryManager):
    global __repo
    __repo = store.register_repository("utar")
    __repo.set_adapter_refresh_callback(refresh)

def refresh():
    reload_local_files()

def reload_local_files():
    content_dir = path.join(__repo.cache_dir, "content") 
    map_dirs = glob.glob(pathname="*/Maps/", root_dir=content_dir)
    for dir in map_dirs:
        game_dir = path.join(content_dir, dir) 
        files = glob.glob(pathname="**/*.yml", root_dir=game_dir, recursive=True)
        for file in files:
            file_path = path.join(game_dir, file) 
            try:
                parse_map_file(file_path)
            except Exception:
                pass

def parse_map_file(file_path: str):
    with open(file_path, 'r') as file:
        map = yaml.safe_load(file)

        if map['contentType'] != "MAP":
            return 
        
        map_name = map['name']
        download_filename = map['originalFilename']

        if len(map['downloads'])==0:
            return

        for download_info in map['downloads']:
            if not download_info['direct'] or download_info['state'] != "OK":
                continue
            url = download_info['url']
            break

        for sub_file in map['files']:
            # save references for other files in zip (for dependency lookup)
            sub_filename = sub_file['name']
            sub_package, sub_ext = path.splitext(sub_filename)

            __repo.store_link(url=url, filename=sub_filename,
                              package_name=sub_package, 
                              container_filename=download_filename)
        


def any_constructor(loader, tag_suffix, node):
    if isinstance(node, yaml.MappingNode):
        return loader.construct_mapping(node)
    if isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node)
    return loader.construct_scalar(node)

yaml.add_multi_constructor('', any_constructor, Loader=yaml.SafeLoader)
