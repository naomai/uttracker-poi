class UEPackageDependencies:

    importedPackages = {}

    def parseImports(self, package):
        for imp in package.imports.items:
            importType = imp['class']
            importName = imp['name']
            
            if imp['outer'] != 0:
                    continue
            
            if importType=="Package":
                

                if not importName in self.importedPackages:
                    self.importedPackages[importName] = {
                        'name': importName,
                        'refs': 0,
                        'objects': {},
                    }

            else:
                root = package.getObjectRoot(imp)
                rootName = root['name']

                if not rootName in self.importedPackages:
                    self.importedPackages[rootName] = {
                        'name': rootName,
                        'refs': 0,
                        'objects': {},
                    }

                dependency = self.importedPackages[rootName]
                if not importType in dependency['objects']:
                    dependency['objects'][importType] = []

                dependency['objects'][importType].append(importName)
                dependency['refs'] = dependency['refs'] + 1
        

        for _, dependency in self.importedPackages.items():
            ext = self.guessPackageFileExtension(dependency)
            dependency['filename'] = dependency['name'] + "." + ext


    def guessPackageFileExtension(self, package):
        objectTypes = {
        }

        for className in package['objects'].keys():
            if className == "Sound":
                objectTypes['sound'] = True
            elif className in ["Texture", "FractalTexture", "FireTexture", "IceTexture", \
                    "WaterTexture", "WaveTexture", "WetTexture", "ScriptedTexture"]:
                objectTypes['texture'] = True
            elif className == "Music":
                objectTypes['music'] = True
        
        if len(objectTypes.keys()) != 1:
            return "u"
        
        if "sound" in objectTypes:
            return "uax"
        elif "texture" in objectTypes:
            return "utx"
        elif "music" in objectTypes:
            return "umx"
        else:
            return "u"
