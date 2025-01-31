from ..unreal_engine import ucc
from os import path
import re

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
    
    return out

class UccPackageMissingException(ucc.UccExportException):
    package: str

    def __init__(self, map_file: str, package: str):
        ucc.UccExportException.__init(f"Missing package '{package}'", map_file)
        self.package = package