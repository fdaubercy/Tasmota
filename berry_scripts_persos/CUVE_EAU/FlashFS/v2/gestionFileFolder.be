# Définition du module
var gestionFileFolder = module("/gestionFileFolder")

# Liste les fichiers présent dans le système de fichier et réparti les fichiers dont le nom est précédé de "SD_"
# dans la carte SD
gestionFileFolder.listeEtRepartitLesFichiers = def()
    import path
    import string
    
    var listFile = path.listdir("/")

    # Crée le dossier html sur carte SD si elle est utilisée
    if path.exists("/sd")
        for nb:0 .. listFile.size() - 1
            var nameFile = listFile[nb]

            # Si extension '.html'
            var filePath = ""
            if string.find(nameFile, ".html") > -1
                path.mkdir("/sd/html")
                filePath = "/sd/html/" + nameFile
            elif string.find(nameFile, ".js") > -1 && string.find(nameFile, ".json") == -1
                path.mkdir("/sd/js")
                filePath = "/sd/js/" + nameFile
            elif string.find(nameFile, ".css") > -1
                path.mkdir("/sd/css")
                filePath = "/sd/css/" + nameFile
            end

            # Recopie le contenu du fichier dans le fichier de destination
            if string.find(nameFile, ".html") > -1 || (string.find(nameFile, ".js") > -1 && string.find(nameFile, ".json") == -1) || string.find(nameFile, ".css") > -1
                var file = open(nameFile, 'r')
                var temp = file.read()
                file.close()

                # Et supprime le fichier d'origine
                path.remove(nameFile)

                var fileDest = open(filePath, 'w')
                fileDest.write(temp)
                fileDest.close()
            end
        end
    # Crée le dossier 'sd'
    else    path.mkdir("/sd")
            gestionFileFolder.listeEtRepartitLesFichiers()
    end
end

gestionFileFolder.readFile = def(chemin)
    import path

    var txt = ""

    # Teste si le fichier existe
    if !path.exists(chemin)
        return false
    end

    # Ouvre le fichier
    var file = open(chemin, 'r')

    # Lit le fichier entier
    txt = file.read()

    # Ferme et efface le buffer
    file.close()
    file.flush()

    return txt
end

gestionFileFolder.writeFile = def(chemin, data)
    # Ouvre le fichier
    var file = open(chemin, 'w')

    # Lit le fichier entier
    file.write(data)

    # Ferme et efface le buffer
    file.close()
    file.flush()
end

gestionFileFolder.readFileByLineAndContentSend = def(chemin)
    import webserver

    var file = open(chemin, 'r')
    var lineBuf = ""
    var offset = 0

    while (offset < file.size())
        lineBuf = file.readline()
        webserver.content_send(lineBuf)

        offset = file.tell()
    end

    file.close()
end

# Supprime les fichiers hors ".bec"
# pour gagner de la place
gestionFileFolder.supprimeBerryFile = def()
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
gestionFileFolder.supprBerryFS = def(folder)
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
				gestionFileFolder.supprBerryFS(nameFile)

                path.rmdir(nameFile)
                log (string.format("CONTROLE_GENERAL: Suppression du dossier '%s' effectuée !", nameFile), LOG_LEVEL_DEBUG)
            end
        end
    end
end

# Charge un fichier ".be" & le supprime si le chargement est OK
gestionFileFolder.loadBerryFile = def(chemin, paramDeleteBe)
    import path
    import string

    # Si le fichier n'est pas nécessaire
    # Si paramDeleteBe=="OFF": Suppression ".be" et pas de chargement
    if (paramDeleteBe == "" || paramDeleteBe == nil)  paramDeleteBe = "ON"    end
    if paramDeleteBe == "OFF"
        path.remove(chemin + ".be")
        log (string.format("LOAD_BERRY_FILE: Supprime le fichier '%s' !", chemin + ".be"), LOG_LEVEL_DEBUG)
        return
    end

    # Compile le fichier "*.be" en "*.bec"
    if path.exists(chemin + ".be")  
        # Si echec de compilation ==> on sort de la fonction sans charger le fichier
        if tasmota.compile(chemin + ".be")
            # Supprime le fichier ".be"
            path.remove(chemin + ".be")
            log (string.format("LOAD_BERRY_FILE: Supprime après compilation le fichier '%s' !", chemin), LOG_LEVEL_DEBUG)
        else
            log (string.format("LOAD_BERRY_FILE: Echec de compilation du fichier '%s' !", chemin), LOG_LEVEL_ERREUR)
            return
        end
    end
    
    # Charge le fichier Berry "*.be" ou "*.bec"
    log (string.format("LOAD_BERRY_FILE: Charge le fichier '%s' !", chemin), LOG_LEVEL_DEBUG)
    load(chemin)
end

# Charge un fichier ".be" & le supprime si le chargement est OK
gestionFileFolder.compileModule = def(chemin, paramDeleteBe)
    import path
    import string

    # Si le fichier n'est pas nécessaire
    # Si paramDeleteBe=="OFF": Suppression ".be" et pas de chargement
    if (paramDeleteBe == "" || paramDeleteBe == nil)  paramDeleteBe = "ON"    end
    if paramDeleteBe == "OFF"
        path.remove(chemin + ".be")
        log (string.format("LOAD_BERRY_FILE: Supprime le fichier '%s' !", chemin + ".be"), LOG_LEVEL_DEBUG)
        return true
    end

    # Compile le fichier "*.be" en "*.bec"
    # print(chemin + " exist=" + str(path.exists(chemin + ".be")))
    if path.exists(chemin + ".be") 
        # Supprime d'abord le fichier *.bec existant
        if path.exists(chemin + ".bec") 
            path.remove(chemin + ".bec")
            log (string.format("LOAD_BERRY_FILE: Supprime avant compilation le fichier '%s' !", chemin + ".bec"), LOG_LEVEL_DEBUG)
        end

        # Si echec de compilation ==> on sort de la fonction sans charger le fichier
        # print(chemin + "compile="+str(tasmota.compile(chemin + ".be")))
        if tasmota.compile(chemin + ".be")
            # Supprime le fichier ".be"
            path.remove(chemin + ".be")
            log (string.format("LOAD_BERRY_FILE: Supprime après compilation le fichier '%s' !", chemin), LOG_LEVEL_DEBUG)
            return true
        else
            log (string.format("LOAD_BERRY_FILE: Echec de compilation du fichier '%s' !", chemin), LOG_LEVEL_ERREUR)
            return false
        end
    else return true
    end
end

# Retourne le module lors de l'importation
return gestionFileFolder