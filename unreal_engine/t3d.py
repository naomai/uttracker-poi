import re

def parse_t3d(contents: bytes):
    actors = []

    actor_regex = re.compile(r"^Begin Actor Class=(.+?) Name=(.+?)\r?\n(.*?)End Actor", re.MULTILINE | re.DOTALL)
    for match in actor_regex.finditer(contents):
        actor_class, actor_name, actor_content = match.groups()
        actor = parse_actor_props(actor_content)

        actor['Class'] = actor_class
        actor['Name'] = actor_name

        brush = parse_actor_brush(actor_content)
        actor['Brush'] = brush
        # TODO brush reference (t3dparserVersionWhatever.php:82)


def parse_actor_props(actor_content: str):
    props = {}
    props_regex = re.compile(r"^\s*([a-zA-Z0-9\(\)]+)=(.*)$", re.MULTILINE)
    for match in props_regex.finditer(actor_content):
        prop_name, prop_value = match.groups()
        props[prop_name] = prop_value

        # TODO unserialize (t3dparserVersionWhatever.php:56)
    return props

def parse_actor_brush(actor_content: str):
    brush_declaration_regex = re.compile(r"^\s*Begin Brush Name=(.+)$", re.MULTILINE)
    if not brush_declaration_regex.search(actor_content):
        # brush actor has no model definition (little thing done 
        # by some mappers to save few bytes in their map files)
        return None
    
    return parse_polylist(actor_content)
    
    


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
        "X": match[1],
        "Y": match[2],
        "Z": match[3],
    }

def parse_pan(text: str):
    match = re.match("U=(-?[0-9]+) V=(-?[0-9])+",text)
    if not match:
        return None
    return {
        "U": match[1],
        "V": match[2],
    }
