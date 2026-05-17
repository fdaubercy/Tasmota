# Définition du module
var gestionFileFolder = module("/gestionFileFolder")

# Liste les fichiers présent dans le système de fichier et réparti les fichiers dont le nom est précédé de "SD_"
# dans la carte SD
gestionFileFolder.listeEtRepartitLesFichiers = def()
    import path
    import string
    
    var listFile = path.listdir("/")

    # Crée le dossier contenant les logs
    path.mkdir("/logs")

    # Crée le dossier pour stocker les json
    for nb:0 .. listFile.size() - 1
        var nameFile = listFile[nb]
        var filePath = ""

        if (string.find(nameFile, ".json") > -1 && string.find(nameFile, "_persist.json") == -1)
            path.mkdir("/json")
            filePath = "/json/" + nameFile
        end

        tasmota.yield()

        if (string.find(nameFile, ".json") > -1 && string.find(nameFile, "_persist.json") == -1)
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

            tasmota.yield()

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

    # Crée le dossier '.extensions' pour stocker les extensions tapp
    if path.exists("/.extensions")
        listFile = path.listdir("/")

        for nb:0 .. listFile.size() - 1
            var nameFile = listFile[nb]

            # Si extension '.tapp'
            var filePath = ""
            if string.find(nameFile, ".tapp") > -1
                path.mkdir("/.extensions")
                filePath = "/.extensions/" + nameFile

                tasmota.yield()

                # Recopie le contenu du fichier dans le fichier de destination
                var file = open(nameFile, 'r')
                var temp = file.read()
                file.close()

                # Et supprime le fichier d'origine
                path.remove("/" + nameFile)

                var fileDest = open(filePath, 'w')
                fileDest.write(temp)
                fileDest.close()
            end
        end
    else path.mkdir("/.extensions")
    end
end

# Compte le nombre de fichiers comprenant 'nomFichier' sans l'extension
# Retourne 0: aucun fichier trouvé
# Retourne > 0: indice max des fichiers trouvés 
gestionFileFolder.compteIndiceMaxFileLogs = def(fileChemin)
    import path
    import string
    import re

    var fileName = string.split(fileChemin, "/")[string.count(fileChemin, "/")]
        fileName = string.split(fileName, ".")[0]
    var listFile = path.listdir("/logs")
    var indiceMax = 0

    for nb:0 .. listFile.size() - 1
        if (string.find(listFile[nb], fileName) > -1)
            # Détermine l'indice du fichier
            var result = re.search("[0-9].", listFile[nb])

            # Détermine quel est l'indice max
            if (result[0] != nil && int(result[0]) > indiceMax)
                indiceMax = int(result[0])
            elif (result[0] == nil)
                indiceMax = 0
            end
        end
    end

    return indiceMax
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

    # Ecrit le fichier entier
    file.write(data)

    # Ferme et efface le buffer
    file.close()
    file.flush()
end

# Lit un fichier html ligne par ligne et les envoie par 'webserver.content_send()'
gestionFileFolder.readFileByLineAndContentSend = def(chemin)
    import webserver

    var file = open(chemin, 'r')
    var lineBuf = ""
    var offset = 0

    while (offset < file.size())
        lineBuf = file.readline()
        webserver.content_send(lineBuf)

        tasmota.yield()
        offset = file.tell()
    end

    file.close()
end

# Lit un fichier html ligne par ligne et les envoie par 'webserver.content_send()'
# Remplace les #mots# par des variables
# Pour les pages html webSensor
gestionFileFolder.readFileByLineReplaceAndWebSend = def(chemin, variablesARemplacer, typeSend)
    import re
    import string
    import webserver
    
    var file = open(chemin, 'r')
    var lineBuf = ""
    var offset = 0
        
    while (offset < file.size())
        lineBuf = file.readline()
        
        for key: variablesARemplacer.keys()
            if (string.find(lineBuf, "#" + key + "#") > -1)
                lineBuf = string.replace(lineBuf, "#" + key + "#", str(variablesARemplacer[key]))
            end

            tasmota.yield()
        end

        if (typeSend == "web_send")
            tasmota.web_send(lineBuf)
        elif (typeSend == "content_send")
            webserver.content_send(lineBuf)
        end

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
        tasmota.yield()

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
            log(string.format("CONTROLE_GENERAL: Suppression du fichier '%s' effectuée !", nameFile), LOG_LEVEL_DEBUG)
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
    log(string.format("WEBSERVER: Demande de suppression des fichiers sur %s !", folder), LOG_LEVEL_DEBUG)
    if path.exists(folder)
        listFile = path.listdir(folder)
        for nb:0 .. listFile.size() - 1
            nameFile = folder + "/" + listFile[nb]

            # Teste 
            if (string.find(nameFile, "settings") == -1)
                # Et supprime le fichier
                path.remove(nameFile)
                log(string.format("CONTROLE_GENERAL: Suppression du fichier '%s' effectuée !", nameFile), LOG_LEVEL_DEBUG)
            end

            tasmota.yield()

            # Teste si c'est un dossier
            if (path.isdir(nameFile))
				gestionFileFolder.supprBerryFS(nameFile)

                path.rmdir(nameFile)
                log(string.format("CONTROLE_GENERAL: Suppression du dossier '%s' effectuée !", nameFile), LOG_LEVEL_DEBUG)
            end
        end
    end
end

# Charge un fichier ".be" le supprime si le chargement est OK & que le fichier *.bec est généré
gestionFileFolder.loadBerryFile = def(chemin, paramDeleteBe, compileBe)
    import path
    import string

    # Si le fichier n'est pas nécessaire au programme
    # Si paramDeleteBe=="OFF": 
    #    * Suppression ".be" si le fichier ".bec" existe et pas de chargement
    if (paramDeleteBe == "" || paramDeleteBe == nil)  paramDeleteBe = "ON"    end
    if (compileBe == "" || compileBe == nil)  compileBe = "OFF"    end
    if paramDeleteBe == "OFF" && path.exists(chemin + ".bec") 
        path.remove(chemin + ".be")
        log(string.format("LOAD_BERRY_FILE: Supprime le fichier '%s' !", chemin + ".be"), LOG_LEVEL_DEBUG)
        # return
    end

    # Compile le fichier "*.be" en "*.bec"
    if path.exists(chemin + ".be")  
        # Si compilation du fichier demandée
        if (compileBe == "ON")
            # Si echec de compilation ==> on sort de la fonction sans charger le fichier
            if tasmota.compile(chemin + ".be")
                # Supprime le fichier ".be"
                path.remove(chemin + ".be")
                log(string.format("LOAD_BERRY_FILE: Supprime après compilation le fichier '%s' !", chemin), LOG_LEVEL_DEBUG)
            else
                log(string.format("LOAD_BERRY_FILE: Echec de compilation du fichier '%s' !", chemin), LOG_LEVEL_ERREUR)
                return
            end
        else
            log(string.format("LOAD_BERRY_FILE: Utilisation du fichier '%s' sans compilation !", chemin), LOG_LEVEL_DEBUG)
        end
    end

    # Charge le fichier Berry "*.be" ou "*.bec" Si le fichier est nécessaire au programme
    # if (paramDeleteBe == "OFF")
        log(string.format("LOAD_BERRY_FILE: Charge le fichier '%s' !", chemin), LOG_LEVEL_DEBUG)
        load(chemin)
    # end
end

# Charge un fichier ".be" & le supprime si le chargement est OK & que le fichier *.bec est généré
gestionFileFolder.compileModule = def(chemin, paramDeleteBe)
    import path
    import string

    # Si paramDeleteBe=="OFF": Suppression ".be" si ".bec" existe => pas de chargement
    if (paramDeleteBe == "" || paramDeleteBe == nil)  paramDeleteBe = "ON"    end
    if paramDeleteBe == "OFF" && path.exists(chemin + ".bec") 
        path.remove(chemin + ".be")
        log(string.format("LOAD_BERRY_FILE: Supprime le fichier '%s' !", chemin + ".be"), LOG_LEVEL_DEBUG)
        return true
    end

    # Compile le fichier "*.be" en "*.bec"
    # print(chemin + " exist=" + str(path.exists(chemin + ".be")))
    if path.exists(chemin + ".be") 
        # Supprime d'abord le fichier *.bec existant
        if path.exists(chemin + ".bec") 
            path.remove(chemin + ".bec")
            log(string.format("LOAD_BERRY_FILE: Supprime avant compilation le fichier '%s' !", chemin + ".bec"), LOG_LEVEL_DEBUG)
        end

        # Si echec de compilation ==> on sort de la fonction sans charger le fichier
        # print(chemin + "compile="+str(tasmota.compile(chemin + ".be")))
        if tasmota.compile(chemin + ".be")
            # Supprime le fichier ".be"
            path.remove(chemin + ".be")
            log(string.format("LOAD_BERRY_FILE: Supprime après compilation le fichier '%s' !", chemin), LOG_LEVEL_DEBUG)
            return true
        else
            log(string.format("LOAD_BERRY_FILE: Echec de compilation du fichier '%s' !", chemin), LOG_LEVEL_ERREUR)
            return false
        end
    else return true
    end
end

# Gère l'enregistrement des logs dans un fichier
# Si le fichier existe, on l'ouvre et on ajoute les données à la fin
gestionFileFolder.enregistreLogs = def(fileChemin, modulo, data)
    import json
    import string
    import path

    var fileName = string.split(fileChemin, "/")[string.count(fileChemin, "/")]
        fileName = string.split(fileName, ".")[0]

    tasmota.yield()

    # On est arrivé à l'indiceMax
    if (modulo.indiceLog > modulo.nbLogsFilesMax)
        # On parcours tous les fichiers
        for nb: 1 .. modulo.nbLogsFilesMax + 1
            # On supprime le fichier avec l'indice 1
            if (path.exists(string.replace(fileChemin, ".", str(nb) + ".")))   path.remove(string.replace(fileChemin, ".", str(nb) + "."))  end

            # On décale de -1 le titre des fichiers
            if (path.exists(string.replace(fileChemin, ".", str(nb + 1) + ".")))    path.rename(string.replace(fileChemin, ".", str(nb + 1) + "."), string.replace(fileChemin, ".", str(nb) + "."))     end
        end

        modulo.indiceLog -= 1
    end

    # Prépare les données pour écriture dans le fichier
    data = data     # + "\n"

    # Détermine le nom du fichier à ouvrir
    var filePath = string.replace(fileChemin, ".", str(modulo.indiceLog) + ".")

    # Mode lecture: détermine la taille du fichier
    var file
    var sizeFile = 0

    try
        file = open(filePath, 'r')
        sizeFile = file.size()
    except .. as error, message
        log(string.format("ENREGISTRE_LOGS_ERREUR: %s -> %s", error, message), LOG_LEVEL_ERREUR)
    end
    
    tasmota.yield()

    # Mode lecture-écriture: crée un fichier vide ou ajoute les données à la fin d'un fichier existant.
    file = open(filePath, 'a+')
    tasmota.yield()

    # Si la taille du fichier > (fileLogSize_Ko / 1000 = kO)
    if (sizeFile + size(data) > modulo.fileLogSize_Ko)
        # Ferme et efface le buffer
        file.close()
        file.flush()

        # On passe au fichier avec indice suivant
        modulo.indiceLog += 1

        filePath = string.replace(fileChemin, ".", str(modulo.indiceLog) + ".")
        log(string.format("ENREGISTRE_LOGS: Création du fichier de logs suivants: %s !", filePath), LOG_LEVEL_DEBUG_PLUS)
        file = open(filePath, 'a+')
    end

    # Ecrit les données dans le fichier
    file.write(data + "\n")

    # Ferme et efface le buffer
    file.close()
    file.flush()
end

# Retourne le module lors de l'importation
return gestionFileFolder