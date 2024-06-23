# Liste les fichiers présent dans le système de fichier et réparti les fichiers dont le nom est précédé de "SD_"
# dans la carte SD
def listeEtRepartitLesFichiers(chemin)
    import path
    import string
    
    var listFile = path.listdir("/")

    # Crée le dossier html sur carte SD si elle est utilisée
    if path.exists("/sd")
        for nb:0 .. listFile.size() - 1
            var nameFile = listFile[nb]
        
            # Teste si le nom du fichier commence par 'SD_'
            if string.find(nameFile, "SD_") > -1
                nameFile = string.split(nameFile, "SD_")[1]

                # Si extension '.html'
                var filePath = ""
                if string.find(nameFile, ".html") > -1
                    path.mkdir("/sd/html")
                    filePath = "/sd/html/" + nameFile
                elif string.find(nameFile, ".js") > -1
                    path.mkdir("/sd/js")
                    filePath = "/sd/js/" + nameFile
                elif string.find(nameFile, ".css") > -1
                    path.mkdir("/sd/css")
                    filePath = "/sd/css/" + nameFile
                elif string.find(nameFile, ".js") > -1
                    path.mkdir("/sd/js")
                    filePath = "/sd/js/" + nameFile
                end

                # Recopie le contenu du fichier dans le fichier de destination
                var file = open("SD_" + nameFile, 'r')
                var temp = file.read()
                file.close()

                var fileDest = open(filePath, 'w')
                fileDest.write(temp)
                fileDest.close()

                # Et supprime le fichier d'origine
                path.remove("SD_" + nameFile)
            end
        end
    end
end

def readFile(chemin)
    var file = open(chemin, 'r')
    var txt = ""

    txt = file.read()
    file.close()

    return txt
end

# Supprime les fichiers hors ".bec" & ".json"
# pour gagner de la place
def supprimeBerryFile()
    import path
    import string

    var listFile = path.listdir("/")
    var becExist = false

    # Vérifie si les fichiers '.bec' sont générés
    for nb:0 .. listFile.size() - 1
        var nameFile = listFile[nb]

        if (string.find(nameFile, ".bec") > -1)
            becExist = true
        end
    end

    # On annule la suppression des fichiers '.be' si il n' a pas au moins 1 fichier '.bec'
    if (!becExist)
        return
    end

    # Supprime 1 à 1 les fichiers '.be' 
    for nb:0 .. listFile.size() - 1
        var nameFile = listFile[nb]

        # Teste si le nom du fichier termine par '.be'
        if (string.find(nameFile, ".bec") == -1 && string.find(nameFile, ".json") == -1 && string.find(nameFile, "settings") == -1)
            # Et supprime le fichier d'origine
            log (string.format("CONTROLE_GENERAL: Suppression du fichier '%s' effectuée !", nameFile), LOG_LEVEL_DEBUG)
            path.remove(nameFile)
        end
    end
end

# Supprime tous les fichiers hors "settings" & "_persist.json" en méoire flash et mémoire SD
# pour gagner de la place
def supprBerryFS(folder)
    import path
    import string

    var listFile = ""
    var nameFile = ""

    # Supprime les fichiers sur mémoire SD "/sd" & la mémoire flash "/"
    log (string.format("WEBSERVER: Demande de suppression des fichiers sur %s !", folder), LOG_LEVEL_DEBUG)
    if path.exists(folder)
        listFile = path.listdir(folder)
        for nb:0 .. listFile.size() - 1
            nameFile = folder + "/" + listFile[nb]

            # Teste 
            if (string.find(nameFile, "settings") == -1)
                # Et supprime le fichier
                path.remove(nameFile)
                log (string.format("CONTROLE_GENERAL: Suppression du fichier '%s' effectuée !", nameFile), LOG_LEVEL_DEBUG)
            end

            # Teste si c'est un dossier
            if (path.isdir(nameFile))
				supprBerryFS(nameFile)

                path.rmdir(nameFile)
                log (string.format("CONTROLE_GENERAL: Suppression du dossier '%s' effectuée !", nameFile), LOG_LEVEL_DEBUG)
            end
        end
    end
end
#- test("/") -#
#- test("/sd") -#

# Execute la focntion au démarrage
log ("AUTO_EXE: Vérifie les fichiers à transférer sur la carte SD !", LOG_LEVEL_DEBUG)
listeEtRepartitLesFichiers()