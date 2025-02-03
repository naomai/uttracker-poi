import sys
import subprocess
from os import path

__platform = sys.platform
if __platform == "linux":
    __ucc_exec_filename = "ucc-bin"
elif __platform == "win32":
    __ucc_exec_filename = "UCC.exe"

game_path: str


def exec(command: str, *args):
    command_with_args = [__get_ucc_path(), command]
    command_with_args.extend(args)
    result = subprocess.run(command_with_args, 
                            capture_output=True, text=True)
    return result.stdout
    


def __get_ucc_path():
    global __ucc_exec_filename
    return path.realpath(path.join(game_path, "System", __ucc_exec_filename))

class UccExportException(Exception):
    map_file: str
    ucc_output: str

    def __init__(self, message: str, map_file: str, ucc_output: str=None):
        Exception.__init__(self, message)
        self.map_file = map_file
        self.ucc_output = ucc_output
