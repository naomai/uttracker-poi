import struct
from .PackageDependencies import UEPackageDependencies

class UEPackageInfo:
    """
    General information about Unreal Engine package
    """
    header = None  
    imports = None
    exports = None
    names = None

    def read(self, fn):
        """
        Load package info from open file reader

        Args:
            fn: Package file reader. Must be at the beginning of 
            header data.
        """
        self.header = UEHeader(fn)        

        fn.seek(self.header.nameOffset)
        self.names = UENameTable(fn, self.header.nameCount)
   
        fn.seek(self.header.importOffset)
        self.imports = UEImportTable(fn, self.header.importCount)
        self.imports.fillNames(self.names)

        fn.seek(self.header.exportOffset)
        self.exports = UEExportTable(fn, self.header.exportCount)
        self.exports.fillNames(self.names)

    def getObjectRoot(self, obj):
        """
        Recursively traverse import/export tree to find 
        topmost entry super to `obj`
        """
        if obj['outer']:
            outerObj = self.getObjectByReference(obj['outer'])
            return self.getObjectRoot(outerObj)
        else:
            return obj
        
    def getObjectByReference(self, value):
        """
        Get object entry from import/export tables by its numeric reference

        Args:
            value: Reference ID from `outer` field. 
            Positive indices point to export table, negative - import.
            Zero value means the topmost (root) entry
        """
        if value==0:
            return None
        elif value > 0:
            return self.exports.items[value-1]
        else:
            return self.imports.items[-value-1]
        
    def getDependencies(self):
        """
        Enumerate external required packages

        Returns:
            list: List of required packages, with their `filename`
            and needed `objects`
        """
        deps = UEPackageDependencies()
        deps.parseImports(self)
        return deps.importedPackages.values()

class UEHeader:
    """
    Unreal Engine package header reader
    """
    importedPackages = []
    exportedPackages = []
    __fn = None
    def __init__(self, fn):
        
        self.__fn = fn

        self.read()


    def read(self):
        self.magic = readDword(self.__fn)
        self.packageVersion = readShort(self.__fn)
        self.licenseeVersion = readShort(self.__fn)
        self.packageFlags = readDword(self.__fn)

        self.nameCount = readDword(self.__fn)
        self.nameOffset = readDword(self.__fn)
        self.exportCount = readDword(self.__fn)
        self.exportOffset = readDword(self.__fn)
        self.importCount = readDword(self.__fn)
        self.importOffset = readDword(self.__fn)

        feat = getPackageFeatures(self.packageVersion)

        if feat['heritage']:
            self.heritageCount = readDword(self.__fn)
            self.heritageOffset = readDword(self.__fn)
            self.heritageItems = []

            currentheaderoffset = self.__fn.tell()
            self.__fn.seek(self.heritageOffset)

            for idx in range(self.heritageCount):
                heritageGuid = readGUID(self.__fn)
                self.heritageItems.append(heritageGuid)
            self.guid = heritageGuid
            self.__fn.seek(currentheaderoffset)
        if feat['guid']:
            self.guid = readGUID(self.__fn)

        if feat['generation']:
            self.generationCount = readDword(self.__fn)
            self.generationItems = []

            for idx in range(self.generationCount):
                generationItem = {
                    'exportCount': readDword(self.__fn),
                    'nameCount': readDword(self.__fn),
                }
                self.generationItems.append(generationItem)

class UENameTable:
    """
    Package name table reader
    
    The name table contains all string identifiers in package.
    This includes names of objects, classes and external packages.
    """
    items = []
    __fn = None
    def __init__(self, fn, count):
        self.__fn = fn
        self.read(count)

    def read(self, count):
        for idx in range(count):
            nameObj = {
                'name': readUEString(self.__fn),
                'nameFlags': readDword(self.__fn),
            }
            self.items.append(nameObj)
    def getNameById(self, nameId):
        return self.items[nameId]['name']

class UEImportTable:
    items = []
    __fn = None
    def __init__(self, fn, count):
        self.__fn = fn
        self.read(count)

    def read(self, count):
        for idx in range(count):
            importObj = {
                'packageIdx': readCompactIndex(self.__fn),
                'classIdx': readCompactIndex(self.__fn),
                'outer': readDword(self.__fn),
                'nameIdx': readCompactIndex(self.__fn),
            }
            self.items.append(importObj)

    def fillNames(self, namesObj):
        for idx, item in enumerate(self.items):
            item['package'] = namesObj.getNameById(item['packageIdx'])
            item['class'] = namesObj.getNameById(item['classIdx'])
            item['name'] = namesObj.getNameById(item['nameIdx'])
            self.items[idx] = item


class UEExportTable:
    items = []
    __fn = None
    def __init__(self, fn, count):
        self.__fn = fn
        self.read(count)

    def read(self, count):
        for idx in range(count):
            exportObj = {
                'classIdx': readCompactIndex(self.__fn),
                'super': readCompactIndex(self.__fn),
                'outer': readDword(self.__fn),
                'nameIdx': readCompactIndex(self.__fn),
                'eFlags': readDword(self.__fn),
                'eSize': readCompactIndex(self.__fn),
            }
            if exportObj['eSize'] > 0:
                exportObj['eOffset'] = readCompactIndex(self.__fn)

            self.items.append(exportObj)

    def fillNames(self, namesObj):
        for idx, item in enumerate(self.items):
            item['class'] = namesObj.getNameById(item['classIdx'])
            item['name'] = namesObj.getNameById(item['nameIdx'])
            self.items[idx] = item

def load(fn):
    """
    Loads Unreal Engine package info from open file stream

    Args:
        fn: Package file stream to read from. 
        Stream pointer must be at the beginning of file.
    """
    package = UEPackageInfo()
    package.read(fn)
    return package

def readCompactIndex(fn):
    """
    Reads Compact Index value from file stream

    Variable-length data type that encodes signed 32-bit values
    to occupy less space for small values.

    Args:
        fn: File stream to read from. 

    Returns:
        int: DWord value obtained from stream
    """
    rawByte=0
    result=0
    
    shift=6
    more=None
    
    rawByte = ord(fn.read(1))
    # first: SIGN | MORE | 6-bit VALUE 
    # next: MORE | next 7 bits
    
    sign = bool(rawByte & 0x80)
    
    result |= (rawByte & 0x3F)
    more = (rawByte & 0x40)

    while more and shift < 32:
        rawByte = ord(fn.read(1))
        result |= (rawByte & 0x7F) << shift
        more = (rawByte & 0x80)
        shift += 7
    
    if sign:
        result = -result
    return result

def readUEString(fn):
    lengthByte = readCompactIndex(fn)
    if lengthByte==0:
        return ""
    length = abs(lengthByte)
    isUnicode = (lengthByte < 0)

    if isUnicode:
        return readUnicodeString(fn, length)
    else:
        return readAsciiString(fn, length)

def readAsciiString(fn, length):
    strRaw = fn.read(length)
    try:
        nullByteOffset = strRaw.index(b'\x00')
        strTrimmed = strRaw[:nullByteOffset]
    except ValueError:
        strTrimmed = strRaw
    return str(strTrimmed, 'ascii')

def readUnicodeString(fn, length):
    strRaw = fn.read(length*2)
    return str(strRaw, "utf-16")

def readGUID(fn):
    return fn.read(16).hex()

class UEVector:
    def __init__(self, fn):
        self.X = readFloat(fn)
        self.Y = readFloat(fn)
        self.Z = readFloat(fn)

class UERotator:
    def __init__(self, fn):
        self.Pitch = readShort(fn)
        self.Yaw = readShort(fn)
        self.Roll = readShort(fn)

class UEColor:
    def __init__(self, fn):
        self.R = readByte(fn)
        self.G = readByte(fn)
        self.B = readByte(fn)
        self.A = readByte(fn)

class UEBoundingBox:
    def __init__(self, fn):
        self.Min = UEVector(fn)
        self.Max = UEVector(fn)
        self.IsValid = UEVector(fn)

class UEBoundingVolume(UEBoundingBox):
    def __init__(self, fn):
        super().__init__(fn) 
        self.Sphere = UEPlane(fn)

class UECoords:
    def __init__(self, fn):
        self.Origin	= UEVector(fn)
        self.XAxis = UEVector(fn)
        self.YAxis = UEVector(fn)
        self.ZAxis = UEVector(fn)

class UEPlane(UEVector):
    def __init__(self, fn):
        super().__init__(fn) 
        self.W = readFloat(fn)

class UEScale:
    def __init__(self, fn):
        self.Scale = UEVector(fn)
        self.SheerRate = readFloat(fn)
        self.SheerAxis = readByte(fn)

def getPackageFeatures(ver):
	feat={
        'names': True,
        'export': True,
        'import': True,
        'heritage': ver < 68,
        'guid': ver >= 68,
        'generation': ver >= 68,
    }
	return feat

def readFloat(fn):
    bytes = fn.read(4)
    return struct.unpack("f", bytes)[0]

def readDword(fn):
    bytes = fn.read(4)
    return struct.unpack("l", bytes)[0]

def readShort(fn):
    bytes = fn.read(2)
    return struct.unpack("h", bytes)[0]

def readByte(fn):
    bytes = fn.read(1)
    return struct.unpack("c", bytes)[0]