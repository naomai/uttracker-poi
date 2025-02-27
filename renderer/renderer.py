import subprocess
from os import path, getcwd, chdir
import shlex
import sys
import orchestration

RENDERER_PATH = path.realpath(
    path.join(path.dirname(__file__) , "unrealpoi-php")
)

def process_job(job: dict):
    render(job["levelJson"], job["workDir"])

def render(level_json_path: str, destination_dir: str):
    options = {
        "input": level_json_path, 
        "output": destination_dir,
    }
    try:

        options["projection"]="ort"
        options["fhd"]=False
        __renderer_exec(options)
        options["fhd"]=True
        __renderer_exec(options)


        options["projection"]="iso3"
        options["fhd"]=False
        __renderer_exec(options)
        options["fhd"]=True
        __renderer_exec(options)

        orchestration.queue_add("render_complete", job)
    except RuntimeError as e:
        print(f"Renderer error: {str(e)}")
    
def __renderer_exec(options: dict):
    args = __build_arglist(options)
    output = __php_exec_in_directory(
        "src/Renderer.php", RENDERER_PATH, 
        *args
    )
    is_aborted = output.find("Aborted: ") != -1
    fail_marker = check_fail_marker(options["output"])

    if is_aborted:
        raise RuntimeError("PHP Renderer failed: " + output)
    if fail_marker != None:
        raise RuntimeError("Fail marker found: " + fail_marker)
    return output


def check_fail_marker(directory: str):
    marker_path = path.join(directory, "poly_fail.txt")
    if not path.exists(marker_path):
        return None
    with open(marker_path) as f: 
        fail_message = f.read()
    return fail_message
    
def __php_exec_in_directory(script: str, working_dir: str, *args):
    old_wd = getcwd()
    chdir(working_dir)
    result = __php_exec(script, *args)
    chdir(old_wd)
    return result
    

def __php_exec(script: str, *args):
    command_with_args = ["php", script]
    command_with_args.extend(args)
    result = ""
    with subprocess.Popen(command_with_args, 
                            stdout=subprocess.PIPE,
                            universal_newlines=True
                        ) as process:
        for line in process.stdout:
            print(line, end='')
            result += line

    return result
    
def __build_arglist(arguments: dict):
    # DON'T try to replace it with package
    args_list = []
    for arg_name in arguments:
        arg_val = arguments[arg_name]
        is_bool = isinstance(arg_val, bool)

        if is_bool and not arg_val:
            # skip args with boolean false
            continue

        args_list.append(f"--{arg_name}")

        if not is_bool:
            #append value if not boolean true
            args_list.append(str(arg_val))
    return args_list
        
def __build_argv(arguments: dict):
    args_list = __build_arglist(arguments)
    return shlex.join(args_list)
