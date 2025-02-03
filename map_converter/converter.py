from unreal_engine import ucc, t3d
from os import path
import re
from content_downloader import downloader
import shutil

destination_dir = "./Storage/MapContent"

def process_job(job: dict):
    map_name = job['jobData']['mapName']
    map_file = path.join(job['unpackDir'], map_name + ".unr")

    if not path.exists(map_file):
        return

    try:
        map_dir = path.join(destination_dir, map_name)
        polys_tmp = extract_polys(map_file, map_dir)

        with open(polys_tmp) as f:
            t3d.parse_t3d(f.read())

    #except UccPackageMissingException as e:
    finally:
        pass   
    

def extract_polys(map_file: str, target_dir: str):
    out = ucc.exec(
        "BatchExport", path.realpath(map_file), 
        "Level", "t3d", 
        path.realpath(target_dir)
    )
    err_match = re.search("Can't find file for package '(.*)'", out)
    if err_match != None:
        missing_package = err_match.group(1)
        raise UccPackageMissingException(map_file, missing_package)

    output_file = path.join(target_dir, "MyLevel.t3d")
    if not path.exists(output_file):
        raise ucc.UccExportException(f"UCC export failed with message '{out}'", map_file, out)
    
    return path.realpath(output_file)

class UccPackageMissingException(ucc.UccExportException):
    package: str

    def __init__(self, map_file: str, package: str):
        ucc.UccExportException.__init(f"Missing package '{package}'", map_file)
        self.package = package