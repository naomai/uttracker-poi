import re
import math

def parse_t3d(contents: bytes):
    models = parse_brushes(contents)
    actors = parse_actors(contents)
    assign_actors_brush_models(actors, models)

    return actors

def parse_brushes(contents: bytes) -> dict[str, list]:
    """
    Parse all brushes in T3D file

    Args:
        contents: bytes of T3D file

    Returns:
        dict[str, list]: dictionary of [model_name, list_of_polygons]
    """
    brushes = {}
    brush_regex = re.compile(r"^\s*Begin Brush Name=(.+?)\r?\n(.*?)End Brush$", re.MULTILINE | re.DOTALL)
    for match in brush_regex.finditer(contents):
        brush_name, brush_content = match.groups()
        brush_polys = parse_polylist(brush_content)
        brushes[brush_name] = brush_polys
    return brushes

def parse_actors(contents: bytes):
    actors = []
    actor_regex = re.compile(r"^\s*Begin Actor Class=(.+?) Name=(.+?)\r?\n(.*?)End Actor", re.MULTILINE | re.DOTALL)
    for match in actor_regex.finditer(contents):
        actor_class, actor_name, actor_content = match.groups()
        actor = parse_actor_props(actor_content)

        actor['Class'] = actor_class
        actor['Name'] = actor_name
        actors.append(actor)
    return actors

def assign_actors_brush_models(actors: list, models: dict):
    for actor in actors:
        if not 'Brush' in actor or not 'export' in actor['Brush']:
            continue

        brush_name = actor['Brush']['export']

        if brush_name in models:
            actor['PolyList'] = models[brush_name]


def parse_actor_props(actor_content: str):
    props = {}
    props_regex = re.compile(r"^\s*([a-zA-Z0-9\(\)]+)=(.*)$", re.MULTILINE)
    for match in props_regex.finditer(actor_content):
        prop_name, prop_value = match.groups()

        prop_value_decoded = unserialize(prop_value)
        props[prop_name] = prop_value_decoded
    return props


def parse_polylist(brush_content: str):
    polys = []
    poly_regex = re.compile(r"^\s*Begin Polygon(.*?)\r?\n(.*?)End Polygon$", re.MULTILINE | re.DOTALL)
    poly_row_regex = re.compile(r"^\s*([^\s]+)\s+(.*)$", re.MULTILINE)
    for poly_match in poly_regex.finditer(brush_content):
        poly = {'Vertex': []}
        poly_props_text, poly_content = poly_match.groups()
        poly_props = re.findall("([^\s]+)=(.+?)\s", poly_props_text + " ")
        for prop in poly_props:
            prop_name, prop_value = prop
            poly[prop_name] = prop_value

        for poly_row in poly_row_regex.finditer(poly_content):
            row_type, row_value = poly_row.groups()

            if row_value.find("U=") == 0:
                row_value_decoded = parse_pan(row_value)
            else:
                row_value_decoded = parse_coord(row_value)

            if row_type == "Vertex":
                poly['Vertex'].append(row_value_decoded)
            else:
                poly[row_type] = row_value_decoded
        polys.append(poly)
    return polys
        

def parse_coord(text: str):
    match = re.match("([\+\-][0-9]{5,7}\.[0-9]{6}),([\+\-][0-9]{5,7}\.[0-9]{6}),([\+\-][0-9]{5,7}\.[0-9]{6})",text)
    if not match:
        return None

    return {
        "X": unserialize_float(match[1]),
        "Y": unserialize_float(match[2]),
        "Z": unserialize_float(match[3]),
    }

def parse_pan(text: str):
    match = re.match("U=(-?[0-9]+) V=(-?[0-9])+",text)
    if not match:
        return None
    return {
        "U": unserialize_int(match[1]),
        "V": unserialize_int(match[2]),
    }

def unserialize(text: str):
    val = unserialize_float(text)
    if val:
        return val
    
    val = unserialize_int(text)
    if val:
        return val
    
    val = unserialize_reference(text)
    if val:
        return val
    
    val = unserialize_array(text)
    if val:
        return val
    
    val = unserialize_string(text)
    if val:
        return val
    
    return text
    """
    Profiler hits (two files):
        'float' 7771, 3924
        'int'   7679, 2688
        'ref'   4846, 2010
        'arr'   3773, 2228
        'str'   2820, 1238
        'raw'   1205,  882
    """

def unserialize_reference(text: str):
    match = re.match("([A-Za-z0-9]*)'([^\.]*).([^']*)'",text)

    if not match:
        return None
    return {
        "importType": match[1],
        "package": match[2],
        "export": match[3],
    }

def unserialize_int(text: str):
    try:
        return int(text)
    except ValueError:
        return None
    
def unserialize_float(text: str):
    try:
        result = float(text)
        if math.isinf(result) or math.isnan(result):
            # workaround for JSON lib incorrectly encoding NaNs and Infs
            return None
        return result
    except ValueError:
        return None
    
def unserialize_string(text: str):
    match = re.match("^\"([^\"]*)\"$",text)

    if not match:
        return None
    return match[1]



def unserialize_array(text: str):
    match = re.match("^\((.*)\)$",text)
    if not match:
        return None
    
    props = {}
    prop_name: str = ""
    prop_value: str = ""
    getting_value = False
    array_nesting_level = 0
    string_open = False

    inner_text: str = match[1]
    
    for ch in inner_text:
        if not getting_value:
            if ch == "=":
                getting_value = True
                continue
            else:
                prop_name += ch
        else:
            if ch == "\"":
                string_open = not string_open

            if not string_open:
                if ch == "(":
                    array_nesting_level = array_nesting_level + 1
                elif ch == ")":
                    array_nesting_level = array_nesting_level - 1
                elif ch == "," and array_nesting_level == 0:
                    props[prop_name] = unserialize(prop_value)
                    prop_name = ""
                    prop_value = ""
                    getting_value = False
                    continue
            prop_value += ch

    if prop_name != "":
        props[prop_name] = unserialize(prop_value)

    return props
