from unreal_engine import ucc, t3d
from os import path
import re
import json
import orchestration
from content_downloader import downloader
from urllib import parse as urlparse

destination_dir = "./Storage/MapContent"

def process_job(job: dict):
    map_name: str = job['mapName']
    map_file = path.join(job['unpackDir'], map_name + ".unr")
    map_dirname = urlparse.quote(map_name.casefold())

    if not path.exists(map_file):
        return

    try:

        map_dir = path.join(destination_dir, map_dirname)
        level_converted_path = path.join(map_dir, "level.json") 

        if not path.exists(level_converted_path):
            level_tmp_path = extract_level(map_file, map_dir)
            with open(level_tmp_path) as f:
                map = t3d.parse_t3d(f.read())
            export_level_json(level_converted_path, map)

        job['levelJson'] = path.realpath(level_converted_path)
        job['workDir'] = path.realpath(map_dir)
        orchestration.queue_add("convert_complete", job)
        

    except UccPackageMissingException as e:
        pass
    finally:
        pass   
    

def extract_level(map_file: str, target_dir: str):
    out = ucc.exec(
        "BatchExport", path.realpath(map_file), 
        "Level", "t3d", 
        path.realpath(target_dir)
    )
    err_match = re.search("Can't find file for package (.*)\.\.", out)
    if err_match != None:
        missing_package = err_match.group(1)
        raise UccPackageMissingException(map_file, missing_package)

    output_file = path.join(target_dir, "MyLevel.t3d")
    if not path.exists(output_file):
        raise ucc.UccExportException(f"UCC export failed with message '{out}'", map_file, out)
    
    return path.realpath(output_file)

def export_level_json(target_path: str, map: list):
    with open(target_path, "w") as f:
        json.dump(obj=map, fp=f)


class UccPackageMissingException(ucc.UccExportException):
    package: str

    def __init__(self, map_file: str, package: str):
        ucc.UccExportException.__init__(self, f"Missing package '{package}'", map_file)
        self.package = package