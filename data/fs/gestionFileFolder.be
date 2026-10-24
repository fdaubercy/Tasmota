# Définition du module
#@ solidify:gestionFileFolder
var gestionFileFolder = module("gestionFileFolder")

# Liste les fichiers présent dans le système de fichier et réparti les fichiers dont le nom est précédé de "SD_"
# dans la carte SD
def gestionFileFolder_listeEtRepartitLesFichiers()
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
gestionFileFolder.listeEtRepartitLesFichiers = gestionFileFolder_listeEtRepartitLesFichiers

# Découpe le chemin d'un fichier de logs : '/logs/cuve.log' -> ["/logs/", "cuve", ".log"]
# Retourne [préfixe dossier avec son '/', nom sans extension, extension avec son '.' ("" si aucune)]
def gestionFileFolder_decoupeCheminLog(fileChemin)
    var posSlash = -1
    var posPoint = -1

    for i: 0 .. size(fileChemin) - 1
        if (fileChemin[i] == "/")       posSlash = i    posPoint = -1
        elif (fileChemin[i] == ".")     posPoint = i
        end
    end

    var fin = (posPoint > -1 ? posPoint : size(fileChemin))
    var prefixe = (posSlash > -1 ? fileChemin[0 .. posSlash] : "")
    var nom = (fin > posSlash + 1 ? fileChemin[posSlash + 1 .. fin - 1] : "")
    var extension = (posPoint > -1 ? fileChemin[posPoint .. size(fileChemin) - 1] : "")

    return [prefixe, nom, extension]
end
gestionFileFolder.decoupeCheminLog = gestionFileFolder_decoupeCheminLog

# Chemin du fichier de logs d'indice 'indice' : ('/logs/cuve.log', 3) -> '/logs/cuve3.log'
def gestionFileFolder_nomFichierLog(fileChemin, indice)
    import gestionFileFolder

    var parties = gestionFileFolder.decoupeCheminLog(fileChemin)
    return parties[0] + parties[1] + str(indice) + parties[2]
end
gestionFileFolder.nomFichierLog = gestionFileFolder_nomFichierLog

# Retourne l'indice max des fichiers '<nom><indice><extension>' du dossier de 'fileChemin'
# Retourne 0: aucun fichier trouvé
# Un fichier qui contient le nom sans indice numérique exact (cuve.log, cuve-old.log, cuve2.log.bak) est ignoré
def gestionFileFolder_compteIndiceMaxFileLogs(fileChemin)
    import path
    import string
    import gestionFileFolder

    var parties = gestionFileFolder.decoupeCheminLog(fileChemin)
    var nom = parties[1]
    var extension = parties[2]
    var dossier = (size(parties[0]) > 1 ? parties[0][0 .. size(parties[0]) - 2] : "/")
    var listFile = path.listdir(dossier)
    var indiceMax = 0

    if (listFile == nil)    return 0    end

    for nameFile: listFile
        var tailleIndice = size(nameFile) - size(nom) - size(extension)

        if (tailleIndice > 0 && string.startswith(nameFile, nom) && string.endswith(nameFile, extension))
            # L'indice doit être fait uniquement de chiffres
            var indice = nameFile[size(nom) .. size(nom) + tailleIndice - 1]
            var chiffres = true
            for i: 0 .. size(indice) - 1
                if (indice[i] < "0" || indice[i] > "9")     chiffres = false    end
            end

            if (chiffres && int(indice) > indiceMax)    indiceMax = int(indice)     end
        end
    end

    return indiceMax
end
gestionFileFolder.compteIndiceMaxFileLogs = gestionFileFolder_compteIndiceMaxFileLogs

# Ne garde que les 'nbGarde' fichiers de logs les plus récents parmi les indices 1 .. indiceMax,
# renumérotés de 1 (le plus ancien) à nbGarde. Les indices absents (coupure pendant un décalage) sont ignorés.
# Parcours croissant : quand le fichier n est renommé en n - nbSuppr, cet indice a déjà été libéré.
def gestionFileFolder_decaleFichiersLogs(fileChemin, indiceMax, nbGarde)
    import path
    import gestionFileFolder

    var nbSuppr = indiceMax - nbGarde
    if (nbSuppr <= 0)   return  end

    for nb: 1 .. indiceMax
        var source = gestionFileFolder.nomFichierLog(fileChemin, nb)

        if (path.exists(source))
            if (nb <= nbSuppr)
                path.remove(source)
            else
                var cible = gestionFileFolder.nomFichierLog(fileChemin, nb - nbSuppr)
                if (path.exists(cible))     path.remove(cible)  end
                path.rename(source, cible)
            end
        end

        tasmota.yield()
    end
end
gestionFileFolder.decaleFichiersLogs = gestionFileFolder_decaleFichiersLogs

def gestionFileFolder_readFile(chemin)
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
gestionFileFolder.readFile = gestionFileFolder_readFile

def gestionFileFolder_writeFile(chemin, data)
    # Ouvre le fichier
    var file = open(chemin, 'w')

    # Ecrit le fichier entier
    file.write(data)

    # Ferme et efface le buffer
    file.close()
    file.flush()
end
gestionFileFolder.writeFile = gestionFileFolder_writeFile

# Lit un fichier html ligne par ligne et les envoie par 'webserver.content_send()'
def gestionFileFolder_readFileByLineAndContentSend(chemin)
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
gestionFileFolder.readFileByLineAndContentSend = gestionFileFolder_readFileByLineAndContentSend

# Lit un fichier html ligne par ligne et les envoie par 'webserver.content_send()'
# Remplace les #mots# par des variables
# Pour les pages html webSensor
def gestionFileFolder_readFileByLineReplaceAndWebSend(chemin, variablesARemplacer, typeSend)
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
gestionFileFolder.readFileByLineReplaceAndWebSend = gestionFileFolder_readFileByLineReplaceAndWebSend

# Supprime les fichiers hors ".bec"
# pour gagner de la place
def gestionFileFolder_supprimeBerryFile()
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
            logFonctions.log(string.format("CONTROLE_GENERAL: Suppression du fichier '%s' effectuée !", nameFile), LOG_LEVEL_DEBUG)
            path.remove(nameFile)
        end
    end
end
gestionFileFolder.supprimeBerryFile = gestionFileFolder_supprimeBerryFile

# Supprime tous les fichiers hors "settings" & "_persist.json" en méoire flash et mémoire SD
# pour gagner de la place
def gestionFileFolder_supprBerryFS(folder)
    import path
    import string

    var listFile = ""
    var nameFile = ""

    # Supprime les fichiers sur mémoire SD "/sd" & la mémoire flash "/"
    logFonctions.log(string.format("WEBSERVER: Demande de suppression des fichiers sur %s !", folder), LOG_LEVEL_DEBUG)
    if path.exists(folder)
        listFile = path.listdir(folder)
        for nb:0 .. listFile.size() - 1
            nameFile = folder + "/" + listFile[nb]

            # Teste 
            if (string.find(nameFile, "settings") == -1)
                # Et supprime le fichier
                path.remove(nameFile)
                logFonctions.log(string.format("CONTROLE_GENERAL: Suppression du fichier '%s' effectuée !", nameFile), LOG_LEVEL_DEBUG)
            end

            tasmota.yield()

            # Teste si c'est un dossier
            if (path.isdir(nameFile))
				gestionFileFolder.supprBerryFS(nameFile)

                path.rmdir(nameFile)
                logFonctions.log(string.format("CONTROLE_GENERAL: Suppression du dossier '%s' effectuée !", nameFile), LOG_LEVEL_DEBUG)
            end
        end
    end
end
gestionFileFolder.supprBerryFS = gestionFileFolder_supprBerryFS

# Charge un fichier ".be" le supprime si le chargement est OK & que le fichier *.bec est généré
def gestionFileFolder_loadBerryFile(chemin, paramDeleteBe, compileBe)
    import path
    import string

    # Si le fichier n'est pas nécessaire au programme
    # Si paramDeleteBe=="OFF": 
    #    * Suppression ".be" si le fichier ".bec" existe et pas de chargement
    if (paramDeleteBe == "" || paramDeleteBe == nil)  paramDeleteBe = "ON"    end
    if (compileBe == "" || compileBe == nil)  compileBe = "OFF"    end
    if paramDeleteBe == "OFF" && path.exists(chemin + ".bec") 
        path.remove(chemin + ".be")
        logFonctions.log(string.format("LOAD_BERRY_FILE: Supprime le fichier '%s' !", chemin + ".be"), LOG_LEVEL_DEBUG)
    end
    # Module desactive (activation OFF) : NI compile NI charge (audit D1/P4.1, 2026-10-24). Avant, le .bec
    # etait charge quand meme et le driver demarrait : controleGarage, controleCuve, controlePompeVideCave
    # n'ont pas d'autre garde que cet argument.
    if (paramDeleteBe == "OFF")
        logFonctions.log(string.format("LOAD_BERRY_FILE: '%s' desactive (activation OFF), non charge !", chemin), LOG_LEVEL_INFO)
        return
    end

    # Compile le fichier "*.be" en "*.bec"
    if path.exists(chemin + ".be")  
        # Si compilation du fichier demandée
        if (compileBe == "ON")
            # Si echec de compilation ==> on sort de la fonction sans charger le fichier
            if tasmota.compile(chemin + ".be")
                # Supprime le fichier ".be"
                path.remove(chemin + ".be")
                logFonctions.log(string.format("LOAD_BERRY_FILE: Supprime après compilation le fichier '%s' !", chemin), LOG_LEVEL_DEBUG)
            else
                logFonctions.log(string.format("LOAD_BERRY_FILE: Echec de compilation du fichier '%s' !", chemin), LOG_LEVEL_ERREUR)
                return
            end
        else
            logFonctions.log(string.format("LOAD_BERRY_FILE: Utilisation du fichier '%s' sans compilation !", chemin), LOG_LEVEL_DEBUG)
        end
    end

    # Charge le fichier Berry "*.be" ou "*.bec" (module active)
    logFonctions.log(string.format("LOAD_BERRY_FILE: Charge le fichier '%s' !", chemin), LOG_LEVEL_DEBUG)
    load(chemin)
end
gestionFileFolder.loadBerryFile = gestionFileFolder_loadBerryFile

# Charge un fichier ".be" & le supprime si le chargement est OK & que le fichier *.bec est généré
def gestionFileFolder_compileModule(chemin, paramDeleteBe)
    import path
    import string

    # Si paramDeleteBe=="OFF": Suppression ".be" si ".bec" existe => pas de chargement
    if (paramDeleteBe == "" || paramDeleteBe == nil)  paramDeleteBe = "ON"    end
    if paramDeleteBe == "OFF" && path.exists(chemin + ".bec") 
        path.remove(chemin + ".be")
        logFonctions.log(string.format("LOAD_BERRY_FILE: Supprime le fichier '%s' !", chemin + ".be"), LOG_LEVEL_DEBUG)
        return true
    end

    # Compile le fichier "*.be" en "*.bec"
    # print(chemin + " exist=" + str(path.exists(chemin + ".be")))
    if path.exists(chemin + ".be") 
        # Supprime d'abord le fichier *.bec existant
        if path.exists(chemin + ".bec") 
            path.remove(chemin + ".bec")
            logFonctions.log(string.format("LOAD_BERRY_FILE: Supprime avant compilation le fichier '%s' !", chemin + ".bec"), LOG_LEVEL_DEBUG)
        end

        # Si echec de compilation ==> on sort de la fonction sans charger le fichier
        # print(chemin + "compile="+str(tasmota.compile(chemin + ".be")))
        if tasmota.compile(chemin + ".be")
            # Supprime le fichier ".be"
            path.remove(chemin + ".be")
            logFonctions.log(string.format("LOAD_BERRY_FILE: Supprime après compilation le fichier '%s' !", chemin), LOG_LEVEL_DEBUG)
            return true
        else
            logFonctions.log(string.format("LOAD_BERRY_FILE: Echec de compilation du fichier '%s' !", chemin), LOG_LEVEL_ERREUR)
            return false
        end
    else return true
    end
end
gestionFileFolder.compileModule = gestionFileFolder_compileModule

# Enregistre la ligne 'data' dans les fichiers de logs tournants du module 'modulo'
#   - fichiers : '/logs/cuve.log' -> /logs/cuve1.log (le plus ancien) ... /logs/cuveN.log (le plus récent)
#   - modulo.nbLogsFilesMax : nombre N de fichiers conservés (0 = pas d'enregistrement)
#   - modulo.fileLogSize_Ko : taille max d'un fichier, en OCTETS malgré le nom de la clé (10000 = ~10 Ko)
#   - modulo.indiceLog      : indice du fichier en cours d'écriture
# Quand le fichier N est plein, le fichier 1 est supprimé, les autres sont décalés d'un cran (2->1 ... N->N-1)
# et l'écriture reprend dans un fichier N vide : il n'y a jamais plus de N fichiers.
def gestionFileFolder_enregistreLogs(fileChemin, modulo, data)
    import string
    import gestionFileFolder

    var nbMax = modulo.nbLogsFilesMax
    if (nbMax == nil || nbMax <= 0)     return  end

    var ligne = data + "\n"
    var file

    try
        # Plus de fichiers que permis (nbLogsFiles diminué dans le persist) : ne garde que les N plus récents
        if (modulo.indiceLog == nil || modulo.indiceLog < 1)    modulo.indiceLog = 1    end
        if (modulo.indiceLog > nbMax)
            logFonctions.log(string.format("ENREGISTRE_LOGS: %i fichiers '%s' pour %i permis, suppression des plus anciens !", modulo.indiceLog, fileChemin, nbMax), LOG_LEVEL_INFO)
            gestionFileFolder.decaleFichiersLogs(fileChemin, modulo.indiceLog, nbMax)
            modulo.indiceLog = nbMax
        end

        # Ouvre en ajout (crée le fichier s'il n'existe pas) et lit sa taille sur le même descripteur
        var filePath = gestionFileFolder.nomFichierLog(fileChemin, modulo.indiceLog)
        file = open(filePath, 'a+')
        var sizeFile = file.size()

        tasmota.yield()

        # Fichier plein (taille en octets) : passe au suivant. Un fichier vide reçoit toujours sa ligne.
        if (sizeFile > 0 && sizeFile + size(ligne) > modulo.fileLogSize_Ko)
            file.close()

            if (modulo.indiceLog >= nbMax)
                # Dernier fichier plein : supprime le plus ancien et décale les autres, l'indice N se libère
                gestionFileFolder.decaleFichiersLogs(fileChemin, modulo.indiceLog, nbMax - 1)
                modulo.indiceLog = nbMax
            else
                modulo.indiceLog += 1
            end

            filePath = gestionFileFolder.nomFichierLog(fileChemin, modulo.indiceLog)
            logFonctions.log(string.format("ENREGISTRE_LOGS: Création du fichier de logs suivant: %s !", filePath), LOG_LEVEL_DEBUG_PLUS)
            file = open(filePath, 'a+')
        end

        file.write(ligne)
        file.close()
    except .. as error, message
        if (file != nil)    file.close()    end
        logFonctions.log(string.format("ENREGISTRE_LOGS_ERREUR: %s -> %s", error, message), LOG_LEVEL_ERREUR)
    end
end
gestionFileFolder.enregistreLogs = gestionFileFolder_enregistreLogs

# Retourne le module lors de l'importation
return gestionFileFolder