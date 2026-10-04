# =============================================================================================
# logFonctions : fonction de log commune, seuil par module, profils de sorties, ReglageLog.
#
# CHARTE DES LOGS BERRY (decidee le 2026-10-04). Copies : CLAUDE.md et outils_docs/README.md,
# a garder alignees avec celle-ci.
#
#   Mot      Constante                  Quand l'utiliser
#   -------  -------------------------  ---------------------------------------------------------
#   erreur   LOG_LEVEL_ERREUR     (1)   Un echec qui demande d'agir : exception, trame rejetee,
#                                       abandon apres N tentatives, fichier absent. TOUJOURS emis.
#   info     LOG_LEVEL_INFO       (2)   Un evenement ou un changement d'etat, UNE ligne par
#                                       evenement. Ce qu'on lit en fonctionnement normal.
#   debug    LOG_LEVEL_DEBUG      (3)   Le deroule d'un traitement : etapes, decisions, valeurs cles.
#   detail   LOG_LEVEL_DEBUG_PLUS (4)   Le brut : trames, JSON complets, parametres recus.
#                                       Emis au niveau 3 du firmware, jamais 4 (pas de BRY: GC).
#
#   Regles d'ecriture :
#   1. Toujours logFonctions.log(msg, niveau [, cible]), jamais log() direct : un log() direct
#      contourne le seuil du module. Sans cible, c'est le seuil "general" qui s'applique.
#   2. Prefixe NOM_MAJ_SNAKE: Message en francais !  -- suffixe _ERREUR dans les except.
#   3. Un echec se logue en erreur, jamais en debug.
#   4. Callback frequent (every_50ms, every_second, reception reseau/serie) : pas d'info.
#   5. Message couteux a construire : if logFonctions.actif(LOG_LEVEL_DEBUG_PLUS, cible) ... end
#      (Berry construit la chaine AVANT d'appeler log(), meme si elle est jetee ensuite).
#
#   Deux filtres successifs :
#   1. le seuil du MODULE : cle "log" du bloc du module dans _persist.json
#      (diverses.logs.general pour la cible "general")
#         ReglageLog <cible> erreur|info|debug|detail
#   2. le seuil de chaque SORTIE (serie, web, mqtt, syslog), donne par le profil actif
#      (diverses.logs.profil + diverses.logs.profils)
#         ReglageLog profil <nom>
#         ReglageLog <sortie> aucun|erreur|info|debug|detail     (modifie le profil actif)
# =============================================================================================
#@ solidify:logFonctions
var logFonctions = module("logFonctions")

# Seuils possibles d'un module : pas de "aucun", les erreurs passent toujours
logFonctions.NIVEAUX_MODULE = {"erreur": 1, "info": 2, "debug": 3, "detail": 4}
# Seuils possibles d'une sortie : "detail" = niveau 4 du firmware (BRY: GC compris)
logFonctions.NIVEAUX_SORTIE = {"aucun": 0, "erreur": 1, "info": 2, "debug": 3, "detail": 4}
logFonctions.MOTS = ["aucun", "erreur", "info", "debug", "detail"]
# Sortie -> commande Tasmota qui en regle le seuil
logFonctions.SORTIES = {"serie": "SerialLog", "web": "WebLog", "mqtt": "MqttLog", "syslog": "SysLog"}
# Cibles connues (une par bloc du persist qui porte une cle "log")
logFonctions.CIBLES = ["general", "serveurWeb", "udp", "tcp", "rangeExtender", "discovery", "modbus",
                       "conn16channels", "slaveModbus", "lorawan", "volets", "es8311"]

# ETAT MUTABLE DU MODULE : dans une GLOBALE, pas dans le module (un module solidifie est
# constant, en flash). Les seuils sont lus une fois depuis le persist, puis mis en cache.
def logFonctions_etat()
    import global
    if (global._etatLogFonctions == nil)
        global._etatLogFonctions = {"seuils": {}}      # cible -> seuil (1 a 4)
    end
    return global._etatLogFonctions
end
logFonctions.etat = logFonctions_etat

# Ou vit le reglage d'une cible dans le persist : [map, cle], ou nil si ce bloc est absent
def logFonctions_lieu(cible)
    import string

    var c = string.tolower(cible)
    var s = (serveur != nil ? serveur : {})
    var d = (drivers != nil ? drivers : {})
    var bloc = nil
    var cle = "log"

    if c == "general"               bloc = (diverses != nil ? diverses.find("logs") : nil)    cle = "general"
    elif c == "serveurweb"          bloc = s
    elif c == "udp"                 bloc = s.find("udp")
    elif c == "tcp"                 bloc = s.find("tcp")
    elif c == "rangeextender"       bloc = s.find("rangeExtender")
    elif c == "discovery"           bloc = s.find("discovery")
    elif c == "modbus"              bloc = d.find("ModBus")
    elif c == "conn16channels"      bloc = d.find("ModBus", {}).find("environnement", {}).find("Conn16channels")
    elif c == "slavemodbus"         bloc = d.find("ModBus", {}).find("environnement", {}).find("TasmotaSlaveModBus")
    elif c == "lorawan"             bloc = d.find("LoRaWan")
    elif c == "volets"              bloc = d.find("voletRoulants")
    elif c == "es8311"              bloc = d.find("I2S", {}).find("environnement", {}).find("ES8311")
    end

    if (type(bloc) != "instance" || bloc.size() == 0)    return nil    end
    return [bloc, cle]
end
logFonctions.lieu = logFonctions_lieu

# Seuil d'une cible (1 a 4). Defaut : info.
# Repli sur l'ancienne cle "debug" tant que le persist de la carte n'est pas migre : ON -> debug, OFF -> info.
def logFonctions_seuil(cible)
    import string

    var seuils = logFonctions.etat()["seuils"]
    var seuil = seuils.find(cible)

    if (seuil == nil)
        seuil = 2
        var lieu = logFonctions.lieu(cible)
        if (lieu != nil)
            var mot = lieu[0].find(lieu[1])
            if (mot == nil)
                var ancien = lieu[0].find("debug")
                if (ancien == "ON")         mot = "debug"
                elif (ancien == "OFF")      mot = "info"
                end
            end
            if (mot != nil)    seuil = logFonctions.NIVEAUX_MODULE.find(string.tolower(str(mot)), 2)    end
        end
        seuils[cible] = seuil
    end

    return seuil
end
logFonctions.seuil = logFonctions_seuil

# LA fonction de log commune. Les erreurs passent toujours ; les autres niveaux passent si le
# seuil de la cible les accepte. "detail" (4) est emis au niveau 3 du firmware.
def logFonctions_log(msg, niveau, cible)
    if (niveau == nil)    niveau = 2    end
    if (niveau > 1)
        if (niveau > logFonctions.seuil(cible == nil ? "general" : cible))    return    end
        if (niveau > 3)    niveau = 3    end
    end
    log(msg, niveau)
end
logFonctions.log = logFonctions_log

# true si un message de ce niveau serait reellement ecrit (seuil du module ET une sortie au moins).
# A utiliser AVANT de construire un message couteux.
def logFonctions_actif(niveau, cible)
    if (niveau > 1 && niveau > logFonctions.seuil(cible == nil ? "general" : cible))    return false    end
    return tasmota.loglevel(niveau > 3 ? 3 : niveau)
end
logFonctions.actif = logFonctions_actif

# Seuil actuel d'une sortie dans Tasmota (nil si illisible).
# SerialLog et SysLog repondent "2 (Active 2)", WebLog et MqttLog un simple nombre.
def logFonctions_niveauSortie(commande)
    import string

    var reponse = tasmota.cmd(commande, boolMute)
    if (reponse == nil)    return nil    end
    var valeur = reponse.find(commande)
    if (valeur == nil)    return nil    end
    return int(string.split(str(valeur), " ")[0])
end
logFonctions.niveauSortie = logFonctions_niveauSortie

# Profil actif du persist (map), ou nil
def logFonctions_profilActif()
    var logs = (diverses != nil ? diverses.find("logs", {}) : {})
    var profil = logs.find("profils", {}).find(logs.find("profil", ""))
    return (type(profil) == "instance" ? profil : nil)
end
logFonctions.profilActif = logFonctions_profilActif

# Applique aux sorties de Tasmota le profil actif du persist.
# Sans profil valide dans le persist, les sorties ne sont pas touchees.
def logFonctions_appliqueProfil()
    import string

    var profil = logFonctions.profilActif()
    if (profil == nil)
        logFonctions.log("APPLIQUE_PROFIL_LOG: aucun profil valide dans diverses.logs, sorties inchangées !", LOG_LEVEL_INFO)
        return false
    end

    for sortie: logFonctions.SORTIES.keys()
        var commande = logFonctions.SORTIES[sortie]
        var niveau = logFonctions.NIVEAUX_SORTIE.find(string.tolower(str(profil.find(sortie, ""))))
        if (niveau != nil && niveau != logFonctions.niveauSortie(commande))
            tasmota.cmd(string.format("%s %i", commande, niveau), boolMute)
            logFonctions.log(string.format("APPLIQUE_PROFIL_LOG: sortie %s réglée à %s !", sortie, logFonctions.MOTS[niveau]), LOG_LEVEL_DEBUG)
        end
    end
    return true
end
logFonctions.appliqueProfil = logFonctions_appliqueProfil

# Cle d'une map dont le nom correspond a 'mot' sans tenir compte de la casse, ou nil
def logFonctions_trouveCle(liste, mot)
    import string
    for cle: liste
        if (string.tolower(cle) == mot)    return cle    end
    end
    return nil
end
logFonctions.trouveCle = logFonctions_trouveCle

# Liste lisible des elements d'un iterable : "a, b, c"
def logFonctions_enTexte(liste)
    var texte = ""
    for element: liste
        texte += (texte == "" ? "" : ", ") + str(element)
    end
    return texte
end
logFonctions.enTexte = logFonctions_enTexte

# Etat complet des reglages : profil actif, sorties reelles, seuil de chaque module configure
def logFonctions_etatReglages()
    var logs = (diverses != nil ? diverses.find("logs", {}) : {})
    var sorties = {}
    var modules = {}
    var profils = []

    for sortie: logFonctions.SORTIES.keys()
        var n = logFonctions.niveauSortie(logFonctions.SORTIES[sortie])
        sorties[sortie] = (n != nil && n >= 0 && n <= 4 ? logFonctions.MOTS[n] : "?")
    end
    for cible: logFonctions.CIBLES
        if (logFonctions.lieu(cible) != nil)    modules[cible] = logFonctions.MOTS[logFonctions.seuil(cible)]    end
    end
    for nom: logs.find("profils", {}).keys()    profils.push(nom)    end

    return {"profil": logs.find("profil", "absent"), "profils": profils, "sorties": sorties, "modules": modules}
end
logFonctions.etatReglages = logFonctions_etatReglages

# Applique un reglage 'quoi mot' et retourne l'etat (map) ou un message d'erreur (chaine)
def logFonctions_regle(quoi, mot)
    import persist

    var logs = (diverses != nil ? diverses.find("logs") : nil)

    # 1. Changement de profil
    if (quoi == "profil")
        var profils = (logs != nil ? logs.find("profils", {}) : {})
        var nom = logFonctions.trouveCle(profils.keys(), mot)
        if (nom == nil)    return "Erreur : profil inconnu '" + mot + "' (profils : " + logFonctions.enTexte(profils.keys()) + ")"    end
        logs["profil"] = nom
        persist.dirty()    persist.save()
        logFonctions.appliqueProfil()
        return logFonctions.etatReglages()
    end

    # 2. Seuil d'une sortie dans le profil actif
    if (logFonctions.SORTIES.contains(quoi))
        if (!logFonctions.NIVEAUX_SORTIE.contains(mot))    return "Erreur : niveau inconnu '" + mot + "' (aucun, erreur, info, debug, detail)"    end
        var profil = logFonctions.profilActif()
        if (profil == nil)    return "Erreur : aucun profil actif dans diverses.logs du persist"    end
        profil[quoi] = mot
        persist.dirty()    persist.save()
        logFonctions.appliqueProfil()
        return logFonctions.etatReglages()
    end

    # 3. Seuil d'un module
    var cible = logFonctions.trouveCle(logFonctions.CIBLES, quoi)
    if (cible == nil)
        return "Erreur : '" + quoi + "' n'est ni 'profil', ni une sortie (" + logFonctions.enTexte(logFonctions.SORTIES.keys()) + "), ni un module (" + logFonctions.enTexte(logFonctions.CIBLES) + ")"
    end
    if (!logFonctions.NIVEAUX_MODULE.contains(mot))    return "Erreur : niveau inconnu '" + mot + "' (erreur, info, debug, detail)"    end
    var lieu = logFonctions.lieu(cible)
    if (lieu == nil)    return "Erreur : le module '" + cible + "' n'est pas configuré sur cette carte"    end
    lieu[0][lieu[1]] = mot
    persist.dirty()    persist.save()
    logFonctions.etat()["seuils"][cible] = logFonctions.NIVEAUX_MODULE[mot]
    return logFonctions.etatReglages()
end
logFonctions.regle = logFonctions_regle

# Commande ReglageLog. Exemples :
# ReglageLog
# ReglageLog profil normal
# ReglageLog modbus detail
# ReglageLog syslog aucun
def logFonctions_reglageLog(cmd, idx, payload, payload_json)
    import string
    import json

    var mots = []
    for m: string.split(string.tolower(payload == nil ? "" : str(payload)), " ")
        if (m != "")    mots.push(m)    end
    end

    var reponse = nil
    if (mots.size() == 0)       reponse = logFonctions.etatReglages()
    elif (mots.size() == 2)     reponse = logFonctions.regle(mots[0], mots[1])
    else                        reponse = "Usage : ReglageLog [profil <nom> | <sortie> <niveau> | <module> <niveau>]"
    end

    tasmota.resp_cmnd(json.dump({"ReglageLog": reponse}))
end
logFonctions.reglageLog = logFonctions_reglageLog

# Retourne le module lors de l'importation
return logFonctions
