# Deroule commun du DEMARRAGE des cartes (audit Berry P4.2, 2026-10-25), appele par l'autoexec.be de chaque
# carte, qui ne garde que la LISTE ORDONNEE de ses modules :
#     import demarrage
#     if demarrage.prologue()
#         demarrage.importe([...])  demarrage.compileSocle()  demarrage.compile([...], "serveur.udp")
#         demarrage.charge([...])   demarrage.charge([...], "serveur.udp")  demarrage.leds()  demarrage.historique()
#         demarrage.chargeFichier("controleGarage", "modules.garage")
#     end
# SOLIDIFIE (${berry_commun.socle}) : ses fonctions se retrouvent par le nom GLOBAL 'demarrage', cree par
# l'import de niveau fichier de l'autoexec. Elles importent en LOCAL ce qu'elles utilisent : a leur
# compilation (banc), ni logFonctions ni les LOG_LEVEL_* n'existent encore.
# Pas de fonction anonyme (solidification : '_anonymous__closure' redefini), donc pas de chargeModule(nom, def ...) :
# chaque module se charge par son NOM (demarrage.importeUn : un vrai 'import', compile a la volee).
# Une "condition" est le chemin d'un bloc du persist dont la cle "activation" doit valoir "ON"
# ("serveur.udp", "modules.garage", "drivers.voletRoulants"...) ; nil = toujours.
# Logs : prefixe AUTO_EXE garde (meme texte qu'avant la refonte, filtres syslog inchanges).
#@ solidify:demarrage
var demarrage = module("demarrage")

# Globales du demarrage, log, persist allege, fichiers repartis sur la carte SD. Rend true si le persist
# est valide (ses 4 blocs sont des maps) : sinon rien de ce qui le lit ne doit etre execute (audit P10.1, B1).
def demarrage_prologue()
    import global
    import persist
    global.persist = persist
    global.controleGeneral = {}           # remplace par l'instance du driver a son chargement
    global.LOG_LEVEL_ERREUR = 1
    global.LOG_LEVEL_INFO = 2
    global.LOG_LEVEL_DEBUG = 3
    global.LOG_LEVEL_DEBUG_PLUS = 4       # niveau Berry "detail" : logFonctions.log() l'emet au niveau 3 du firmware (sans les BRY: GC)
    var blocs = {"serveur": persist.serveur, "diverses": persist.diverses, "modules": persist.modules, "drivers": persist.drivers}
    var manquants = []
    for c: blocs.keys()
        global.setmember(c, blocs[c])
        if !isinstance(blocs[c], map)    manquants.push(c)    end
    end
    var valide = (size(manquants) == 0)
    global.boolMute = (valide ? persist.diverses.find("cmdMute", false) : true)

    # Log commun AVANT tout le reste : les modules charges ensuite loguent par logFonctions.log()
    demarrage.importe(["logFonctions", "diversFonctions"])
    import logFonctions
    import diversFonctions
    # Allege le persist en RAM : listes vides de cles connues supprimees (lues par .find(cle, [])) ;
    # environnement des drivers inactifs mis en veille dans /json/driversInactifs.json (rien n'est perdu)
    if (valide && diversFonctions.elagueListesVides(persist._p) > 0)    persist.save(true)    end
    if (valide)    diversFonctions.hiberneDriversInactifs()    end

    logFonctions.log("AUTO_EXE: Vérifie les fichiers à transférer sur la carte SD !", 3)
    demarrage.importe(["gestionFileFolder"])
    import gestionFileFolder
    gestionFileFolder.listeEtRepartitLesFichiers()

    if (!valide)
        logFonctions.log("AUTO_EXE: Attention, le fichier de paramétrage est absent ou invalide (bloc(s) manquant(s) : " + manquants.concat(", ") + ") : aucun module chargé !", 1)
    end
    return valide
end
demarrage.prologue = demarrage_prologue

# Importe le module 'nom' par un VRAI 'import', compile a la volee DANS une fonction (sinon '_m' deviendrait une
# globale ; le 3e argument "local" de compile ne suffit pas au berry.exe des bancs) et rend sa valeur : le module, ou ce que rend son
# init() (be_module.c:272, nil pour une LED temoin non configuree). Pas introspect.module : il rend nil aussi
# pour un module ABSENT, sans exception. Module absent -> import_error, comme un 'import' ecrit.
def demarrage_importeUn(nom)
    return compile("return (def () import " + nom + " as _m return _m end)()")()
end
demarrage.importeUn = demarrage_importeUn

# Importe chaque module de la liste ET cree sa globale. Necessaire pour un module SOLIDIFIE dont les
# fonctions retrouvent leur propre module par son nom GLOBAL (GETNGBL) : leur code de niveau fichier ne
# s'execute pas, ce nom n'existe que par un import de niveau fichier... ou par ceci.
def demarrage_importe(noms)
    import global
    for nom: noms
        try
            global.setmember(nom, demarrage.importeUn(nom))
        except .. as e, m
            var msg = "AUTO_EXE_ERREUR: echec de l'import de '" + nom + "' : " + str(e) + " - " + str(m) + " (sa globale n'est pas creee) !"
            if (global.contains("logFonctions"))    global.logFonctions.log(msg, 1)
            else    log(msg, 1)    # logFonctions absent : seul log possible
            end
        end
    end
end
demarrage.importe = demarrage_importe

# Valeur "activation" ("ON"/"OFF") du bloc du persist designe par 'condition' ("serveur.udp") ; nil -> "ON".
# Un bloc absent vaut "OFF" (avant la refonte, serveur["udp"] absent arretait tout l'autoexec).
def demarrage_activation(condition)
    import global
    import string
    if (condition == nil)    return "ON"    end
    var parties = string.split(condition, ".")
    var bloc = global.member(parties[0])
    for i: 1 .. size(parties) - 1
        bloc = isinstance(bloc, map) ? bloc.find(parties[i]) : nil
    end
    return isinstance(bloc, map) ? bloc.find("activation", "OFF") : "OFF"
end
demarrage.activation = demarrage_activation

# Compile en .bec chaque module de la liste si la condition est active (compileModule ne fait rien a "OFF")
def demarrage_compile(noms, condition)
    import gestionFileFolder
    var activation = demarrage.activation(condition)
    if (activation != "ON")    return    end
    for nom: noms    gestionFileFolder.compileModule("/" + nom, activation)    end
end
demarrage.compile = demarrage_compile

# Socle compile sur toutes les cartes ; webFonctions seulement si le serveur web est active
def demarrage_compileSocle()
    demarrage.compile(["configGlobal", "configDevices", "configModules", "gestionFileFolder", "globalFonctions", "diversFonctions", "logFonctions"])
    demarrage.compile(["webFonctions"], "serveur")
end
demarrage.compileSocle = demarrage_compileSocle

# Charge chaque module SOLIDIFIE de la liste, dans l'ordre, si la condition est active. Son init() s'execute
# (be_module.c:285-296) : publie l'instance dans global.controleXxx et fait add_driver ; ne pas le rappeler.
# L'echec d'un module est journalise et n'empeche pas les suivants (audit B2/B5, P10.2).
def demarrage_charge(noms, condition)
    import logFonctions
    if (demarrage.activation(condition) != "ON")    return    end
    for nom: noms
        try
            demarrage.importeUn(nom)
        except .. as e, m
            logFonctions.log("AUTO_EXE_ERREUR: echec du chargement de '" + nom + "' : " + str(e) + " - " + str(m) + " (modules suivants charges quand meme) !", 1)
        end
    end
end
demarrage.charge = demarrage_charge

# Charge un module NON solidifie depuis le LittleFS (controleGarage, controleCuve...) ; loadBerryFile ne
# le charge pas si la condition est a "OFF"
def demarrage_chargeFichier(nom, condition)
    import gestionFileFolder
    import logFonctions
    try
        gestionFileFolder.loadBerryFile("/" + nom, demarrage.activation(condition), "ON")
    except .. as e, m
        logFonctions.log("AUTO_EXE_ERREUR: echec du chargement de '" + nom + "' : " + str(e) + " - " + str(m) + " (modules suivants charges quand meme) !", 1)
    end
end
demarrage.chargeFichier = demarrage_chargeFichier

# LED RGB du dev-kit (drivers.leds.environnement.leds.ledRGB) et ruban WS2812 AUTO/MANUEL avec bouton
# (...leds.ruban) : ledsFonctions et controleLeds compiles et charges SEULEMENT si l'un des deux est active
def demarrage_leds()
    import global
    var leds = global.drivers.find("leds", {})
    var env = leds.find("environnement", {}).find("leds", {})
    if (leds.find("activation", "OFF") == "ON" && (env.find("ledRGB", {}).find("activation", "OFF") == "ON" || env.find("ruban", {}).find("activation", "OFF") == "ON"))
        demarrage.compile(["ledsFonctions", "controleLeds"])
        demarrage.charge(["controleLeds"])
    end
end
demarrage.leds = demarrage_leds

# Historique des mesures (historiqueFonctions.be, S3/P4) : compile en .bec PUIS importe et demarre.
# A appeler AVANT un module qui l'importe (controleGarage, controleCuve) : Berry prefere le .bec au .be
# (be_module.c:181) et garde le module en cache ; importe avant compileModule, c'est l'ANCIEN .bec qui
# tournerait jusqu'au redemarrage suivant (constate sur le P4 le 2026-10-18).
def demarrage_historique()
    import global
    import gestionFileFolder
    import logFonctions
    if (demarrage.activation("diverses.historique") != "ON")    return    end
    gestionFileFolder.compileModule("/historiqueFonctions", "ON")
    try
        var histo = demarrage.importeUn("historiqueFonctions")
        global.historiqueFonctions = histo
        histo.demarre(global.diverses["historique"])
    except .. as e, m
        logFonctions.log("AUTO_EXE_ERREUR: echec du chargement de 'historiqueFonctions' : " + str(e) + " - " + str(m) + " (modules suivants charges quand meme) !", 1)
    end
end
demarrage.historique = demarrage_historique

# NE PAS compiler autoexec.be en .bec : tasmota.compile() compile en contexte LOCAL (tasmota_class.be:480,
# upstream #23457) : ses globales de niveau fichier ('demarrage') deviendraient des locales des le DEUXIEME
# demarrage (constate a la cave le 2026-09-26).

return demarrage
