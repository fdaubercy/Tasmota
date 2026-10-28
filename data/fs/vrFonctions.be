# Définition du module
#@ solidify:vrFonctions
var vrFonctions = module("vrFonctions")

# Etat modifiable du module, dans une GLOBALE (solidification 2026-09-27). Un module
# solidifie est constant (en flash) : y ecrire leve "'module' value has no writable
# attribute", et ses listes sont figees. La map est creee au premier appel avec les
# valeurs de depart qu'avaient les anciens attributs du module.
def vrFonctions_etat()
    import global
    if (global._etatVrFonctions == nil)
        global._etatVrFonctions = {}
    end
    return global._etatVrFonctions
end
vrFonctions.etat = vrFonctions_etat


def vrFonctions_log(msg, levelDebug)
    logFonctions.log(msg, levelDebug, "volets")
end
vrFonctions.log = vrFonctions_log

# Aide de la commande ReglageVolets, appelee SEULEMENT par diversFonctions.traiteAide :
# sujet == nil -> [[nom, syntaxe, resume], ...] ; sujet == nom -> lignes de detail, ou nil
def vrFonctions_aideReglageVolets(sujet)
    import string
    if (sujet == nil)
        return [["Inclinaison", "Inclinaison <id volet>", "angle mesure par le MPU6050 du volet, pour regler angleOuvert / angleFerme"],
                ["Apprentissage", "Apprentissage <id volet> ouvert|ferme", "apprend les butees du MPU6050 (axes et angles) en 2 temps"]]
    end
    sujet = string.toupper(sujet)
    if (sujet == "INCLINAISON")
        return ["Lit l'angle du volet (moyenne de 4 lectures) et l'etat qu'il donne, sans recaler le volet.",
                "Repond meme si capteursPosition.inclinaison.activation vaut OFF : sert au calibrage avant activation.",
                "Exemple : ReglageVolets Inclinaison 1"]
    elif (sujet == "APPRENTISSAGE")
        return ["1. Amener le volet en butee OUVERTE (commande habituelle), puis : ReglageVolets Apprentissage 1 ouvert",
                "2. Amener le volet en butee FERMEE, puis : ReglageVolets Apprentissage 1 ferme",
                "Les 2 butees relevees : axes, angleOuvert et angleFerme ecrits dans capteursPosition.inclinaison, persist enregistre.",
                "L'apprentissage ne commande jamais le moteur. Refus (rien d'ecrit) si les butees sont a moins de 10 degres.",
                "Un redemarrage entre les 2 temps efface la 1re butee : recommencer. Marche aussi inclinaison OFF."]
    end
    return nil
end
vrFonctions.aideReglageVolets = vrFonctions_aideReglageVolets

def vrFonctions_reglageVolets(cmd, idx, payload, payload_json)
    import string
    import json
    import persist
    import diversFonctions
    if diversFonctions.traiteAide("ReglageVolets", payload, vrFonctions.aideReglageVolets, true)    return    end


    var fonction = false
    var parametres = []                # liste vide (et non false) : parametres.size() plus bas
    var reponse_cmnd = "reglageVolets: "
    
    # Test   
    vrFonctions.log("REGLAGE_VOLETS: -------------------- reglageVolets -------------------", LOG_LEVEL_DEBUG_PLUS)
    vrFonctions.log("REGLAGE_VOLETS: cmd=" + str(cmd), LOG_LEVEL_DEBUG_PLUS)
    vrFonctions.log("REGLAGE_VOLETS: idx=" + str(idx), LOG_LEVEL_DEBUG_PLUS)
    vrFonctions.log("REGLAGE_VOLETS: payload=" + str(payload), LOG_LEVEL_DEBUG_PLUS)
    vrFonctions.log("REGLAGE_VOLETS: payload_json=" + str(payload_json), LOG_LEVEL_DEBUG_PLUS)

    # Détermine la fonction appelée et ses paramètres
    if string.find(payload, " ") > - 1
        parametres = string.split(payload , " ", 1)
        fonction = parametres.pop(0)
    else fonction = payload
    end

    vrFonctions.log("REGLAGE_VOLETS: fonction=" + str(fonction), LOG_LEVEL_DEBUG_PLUS)
	if (parametres.size() > 0)	vrFonctions.log("REGLAGE_VOLETS: parametre1=" + str(parametres[0]), LOG_LEVEL_DEBUG_PLUS)	end
	if (parametres.size() > 1)	vrFonctions.log("REGLAGE_VOLETS: parametre2=" + str(parametres[1]), LOG_LEVEL_DEBUG_PLUS)	end

    # Calibrage du capteur d'inclinaison : angle mesure, lu meme si l'inclinaison est OFF, sans recalage
    if (string.toupper(str(fonction)) == "APPRENTISSAGE")
        var p = parametres.size() > 0 ? string.split(parametres[0], " ") : []
        reponse_cmnd += vrFonctions.apprend(p.size() > 0 ? int(p[0]) : 0, p.size() > 1 ? string.tolower(p[1]) : "")
        tasmota.resp_cmnd(json.dump(reponse_cmnd))
        return
    end
    if (string.toupper(str(fonction)) == "INCLINAISON")
        var id = parametres.size() > 0 ? int(parametres[0]) : 1
        var incl = vrFonctions.trouveInclinaison(id)
        if (incl == nil)
            reponse_cmnd += string.format("pas de bloc capteursPosition.inclinaison pour le volet %i", id)
        else
            var angle = vrFonctions.lireAngle(id, incl)
            if (angle == nil)
                reponse_cmnd += string.format("volet %i : MPU6050 muet (voir les logs)", id)
            else
                reponse_cmnd += string.format("volet %i : angle %.1f degres, etat %s", id, angle, vrFonctions.etatInclinaison(angle, incl, nil))
            end
        end
        tasmota.resp_cmnd(json.dump(reponse_cmnd))
        return
    end

    # Commande réussie
    # Réponse à la commande
    reponse_cmnd += "aucun reglage disponible"
    tasmota.resp_cmnd(json.dump(reponse_cmnd))
end
vrFonctions.reglageVolets = vrFonctions_reglageVolets

def vrFonctions_configVRByJson()
    import string
    import configGlobal

    var vrJSON = drivers["voletRoulants"]

    # Règle la mise en place et le paramétrage du(des)volet(s) roulant(s)
    if (vrJSON.find("activation", "OFF") == "ON")
        # Paramètre global des volets roulants
        try
            # Active ou nom les volets roulants
            if (configGlobal.testeParam("SetOption80", vrJSON["activation"], "str"))
                vrFonctions.log("CONFIG_VR: Active les volets roulants !", LOG_LEVEL_DEBUG)
            end

            # Paramètre le mode de fonctionnement de tous les volets roulants
            if (configGlobal.testeParam("ShutterMode", vrJSON["mode"], "int"))
                vrFonctions.log(string.format("CONFIG_VR: Paramètre le mode de fonctionnement des volets roulants: Mode %i !", vrJSON["mode"]), LOG_LEVEL_DEBUG)
            end
        except .. as error, message
            vrFonctions.log(string.format("CONFIG_VR_ERREUR: %s -> %s", error, message), LOG_LEVEL_ERREUR)
        end 

        # Paramètre chaque volet roulant
        for cle: vrJSON["environnement"]["VRs"].keys()
            if type(vrJSON["environnement"]["VRs"][cle]) != "instance"   continue    end

            try
                if (vrJSON["environnement"]["VRs"][cle].find("activation", "OFF") == "ON")
                    # Paramètre le relai lié
                    if (configGlobal.testeParam(string.format("ShutterRelay%i", vrJSON["environnement"]["VRs"][cle]["id"]), vrJSON["environnement"]["VRs"][cle]["relais1"], "int"))
                        vrFonctions.log(string.format("CONFIG_VR2: Paramètre le 1er relai du volet roulant %i: Relai %i !", vrJSON["environnement"]["VRs"][cle]["id"], vrJSON["environnement"]["VRs"][cle]["relais1"]), LOG_LEVEL_DEBUG)
                    end

                    # Paramètre le délai de bascule du relai (si Mode=3: Volet Roulant de garage)
                    if (vrJSON["mode"] == 3)
                        if (configGlobal.testeParam(string.format("PulseTime%i", vrJSON["environnement"]["VRs"][cle]["relais1"]), 5, "int"))
                            vrFonctions.log(string.format("CONFIG_VR2: Paramètre le délai de bascule du 1er relai du volet roulant %i: 5s !", vrJSON["environnement"]["VRs"][cle]["id"]), LOG_LEVEL_DEBUG)
                        end
                    # Paramètre l'Interlock entre le relai1 et le suivant
                    elif (vrJSON["mode"] == 1)
                        tasmota.cmd(string.format("Interlock %i,%i", vrJSON['environnement']['VRs'][cle]['relais1'], vrJSON['environnement']['VRs'][cle]['relais1'] + 1), boolMute)
                        tasmota.cmd("Interlock ON", boolMute)
                    end

                    # Paramétre l'aspect et l'ordre des boutons de VR sur webUI
                    if (configGlobal.testeParam(string.format("ShutterInvertWebButtons%i", vrJSON["environnement"]["VRs"][cle]["id"]), 0, "int"))
                        vrFonctions.log(string.format("CONFIG_VR2: Paramètre les icones par défaut du volet roulant %i !", vrJSON["environnement"]["VRs"][cle]["id"]), LOG_LEVEL_DEBUG)
                    end
                    if (configGlobal.testeParam(string.format("ShutterInvert%i", vrJSON["environnement"]["VRs"][cle]["id"]), 1, "int"))
                        vrFonctions.log(string.format("CONFIG_VR2: Paramètre la représentation numérique de l'état du volet roulant %i !", vrJSON["environnement"]["VRs"][cle]["id"]), LOG_LEVEL_DEBUG)
                    end

                    # Paramètre le temps d'ouverture/fermeture du volet roulant
                    if (configGlobal.testeParam(string.format("ShutterOpenDuration%i", vrJSON["environnement"]["VRs"][cle]["id"]), vrJSON["environnement"]["VRs"][cle]["tempsMontee"], "int"))
                        vrFonctions.log(string.format("CONFIG_VR2: Paramètre le temps d'ouverture du volet roulant %i: %is !", vrJSON["environnement"]["VRs"][cle]["id"], vrJSON["environnement"]["VRs"][cle]["tempsMontee"]), LOG_LEVEL_DEBUG)
                    end
                    if (configGlobal.testeParam(string.format("ShutterCloseDuration%i", vrJSON["environnement"]["VRs"][cle]["id"]), vrJSON["environnement"]["VRs"][cle]["tempsDescente"], "int"))
                        vrFonctions.log(string.format("CONFIG_VR2: Paramètre le temps de fermeture du volet roulant %i: %is !", vrJSON["environnement"]["VRs"][cle]["id"], vrJSON["environnement"]["VRs"][cle]["tempsDescente"]), LOG_LEVEL_DEBUG)
                    end

                    # Paramètres les commandes par boutons choisies
                    for cleBTN: vrJSON["environnement"]["VRs"][cle]["boutons"].keys()
                        if (vrJSON["environnement"]["VRs"][cle]["boutons"][cleBTN].find("activation", "OFF") == "ON" && vrJSON["environnement"]["VRs"][cle]["boutons"][cleBTN].find("id", -1) != -1)
                            vrFonctions.log(string.format("CONFIG_VR2: Paramètre le BP %i pour la fonction '%s' !", vrJSON["environnement"]["VRs"][cle]["boutons"][cleBTN]["id"], vrJSON["environnement"]["VRs"][cle]["boutons"][cleBTN]["function"]), LOG_LEVEL_DEBUG)
                            tasmota.cmd(string.format("ShutterButton%i %i %s %i", 
                                                                    vrJSON["environnement"]["VRs"][cle]["id"], vrJSON["environnement"]["VRs"][cle]["boutons"][cleBTN]["id"], 
                                                                    vrJSON["environnement"]["VRs"][cle]["boutons"][cleBTN]["function"], 
                                                                    (vrJSON["environnement"]["VRs"][cle]["boutons"][cleBTN]["mqtt"] == "ON" ? 1 : 0), boolMute))
                        end
                    end
                end
            except .. as error, message
                vrFonctions.log(string.format("CONFIG_VR2_ERREUR: %s -> %s", error, message), LOG_LEVEL_ERREUR)
            end  
        end              
    end
end
vrFonctions.configVRByJson = vrFonctions_configVRByJson

# Règles sur changement d'état lors du démarrage de Tasmota
def vrFonctions_changementEtatDemarrage(value, trigger, msg)
    import string
    import mqtt
    import json
    import gestionFileFolder

	# Test
	vrFonctions.log("VOLETS_CHGT_ETAT_DEMARRAGE: -------------------- Volets changementEtatDemarrage -------------------", LOG_LEVEL_DEBUG_PLUS)
	vrFonctions.log("VOLETS_CHGT_ETAT_DEMARRAGE: value=" + str(value), LOG_LEVEL_DEBUG_PLUS)				# value=SINGLE
	vrFonctions.log("VOLETS_CHGT_ETAT_DEMARRAGE: trigger=" + str(trigger), LOG_LEVEL_DEBUG_PLUS)			# trigger=Button1
	vrFonctions.log("VOLETS_CHGT_ETAT_DEMARRAGE: msg=" + str(msg), LOG_LEVEL_DEBUG_PLUS)					# msg={'Button1': {'Action': SINGLE}}
	
    if (type(value) == "instance")
		for cle: value.keys()
			value = value[cle]
		end
	end

    tasmota.yield()

	# Lorsque la connexion Wi-Fi est change
	if (trigger == "Wifi")
        if msg["WIFI"].find("Connected", 0)
        elif msg["WIFI"].find("Disonnected", 0)
        end
	# Init: Se produit une fois après le redémarrage avant que le Wi-Fi et MQTT ne soient initialisés
    # Boot: Se déclenche après la connexion du Wi-Fi et de MQTT (si activé)
    # Save: Avant redemarrage de tasmota
	elif (trigger == "System")
        if msg[trigger].find("Init", 0)
        elif msg[trigger].find("Boot", 0)
        elif msg[trigger].find("Save", 0)
        end
	# Se déclenche après la connexion MQTT (si activé)
    elif (trigger == "Mqtt")
        if msg["MQTT"].find("Connected", 0)
        elif msg["MQTT"].find("Disconnected", 0)
        end
	# Se déclenche un évènement sur les heures et la synchronisation NTP (si activé)
    elif (trigger == "Time")
        # A chaque fois que le NTP est initialisé et l'heure synchronisée
        if type(msg["Time"]) == "instance"
            if msg["Time"].find("Initialized", 0)
            # A chaque heure, quand le système NTP est synchronisé
            elif msg["Time"].find("Set", 0)
            end
        end
    end
end
vrFonctions.changementEtatDemarrage = vrFonctions_changementEtatDemarrage

# Règles sur changement d'état des capteurs
def vrFonctions_changementEtatCapteur(value, trigger, msg, numRideau, etatRideau)
    import string
    import json
    import persist

	var device

	# Test
	vrFonctions.log("VR_GESTION_CAPTEURS: -------------------- Volets changementEtatCapteur -------------------", LOG_LEVEL_DEBUG_PLUS)
	vrFonctions.log("VR_GESTION_CAPTEURS: value=" + str(value), LOG_LEVEL_DEBUG)							# value=SINGLE
	vrFonctions.log("VR_GESTION_CAPTEURS: trigger=" + str(trigger), LOG_LEVEL_DEBUG)						# trigger=Button1
	vrFonctions.log("VR_GESTION_CAPTEURS: msg=" + str(msg), LOG_LEVEL_DEBUG)								# msg={'Button1': {'Action': SINGLE}}
    vrFonctions.log("VR_GESTION_CAPTEURS: numRideau=" + str(numRideau), LOG_LEVEL_DEBUG)			        # numRideau=1
	vrFonctions.log("VR_GESTION_CAPTEURS: etatRideau=" + str(etatRideau), LOG_LEVEL_DEBUG)			        # etatRideau=ouverture

	if (type(value)) == "instance"
		for cle: value.keys()
			value = value[cle]
		end
	end

	tasmota.yield()

    # Modifie l'état du rideau en fonction du capteur déclenché
    # Croisement VOULU : configVRByJson pose ShutterInvert 1, et Tasmota (ESP32) applique alors
    # 100 - position a ShutterSetClose/Open. ShutterSetClose = volet ouvert : ne pas « corriger ».
    var vrJSON = drivers["voletRoulants"]
    if (etatRideau == "ouverture" && value == "ON")
        # On force l'affichage de l'état 'ouvert' du rideau
        tasmota.cmd(string.format("ShutterSetClose%i", numRideau), boolMute)
        vrFonctions.log(string.format("VR_GESTION_CAPTEURS: Force l'affichage du volet %i en ouverture !", numRideau), LOG_LEVEL_DEBUG)
    elif (etatRideau == "fermeture" && value == "ON")
        # On force l'affichage de l'état 'fermé' du rideau
        tasmota.cmd(string.format("ShutterSetOpen%i", numRideau), boolMute)
        vrFonctions.log(string.format("VR_GESTION_CAPTEURS: Force l'affichage du volet %i en fermeture !", numRideau), LOG_LEVEL_DEBUG)
    end

	# Enregistre les nouvelles valeurs de capteurs en json
	# persist.modules = modules
end
vrFonctions.changementEtatCapteur = vrFonctions_changementEtatCapteur

# Capteur de position VIRTUEL (2026-10-12) : interrupteur d'un esclave ModBus, recopie sur le
# maitre par modBus_TasmotaSlaveModBus. Tasmota n'en fait aucun evenement 'SwitchN#Action', et
# sur le maitre 'SwitchN' designe ses interrupteurs PHYSIQUES : un volet le designe donc par
# "Interrupteur<id>" dans 'capteursPosition'. Appelee a chaque CHANGEMENT d'etat (pas a chaque
# releve : un ShutterSetOpen/Close en plein mouvement fausserait la position). Tous les volets
# qui designent cet interrupteur sont recales, chacun le sien.
def vrFonctions_capteurVirtuel(id, valeur)
    var vrJSON = drivers.find("voletRoulants", {})
    if (vrJSON.find("activation", "OFF") != "ON")    return    end

    var nom = "Interrupteur" + str(id)
    var vrs = vrJSON.find("environnement", {}).find("VRs", {})
    for cle: vrs.keys()
        var vr = vrs[cle]
        if (type(vr) != "instance" || vr.find("activation", "OFF") != "ON")    continue    end
        var capteurs = vr.find("capteursPosition", false)
        if (type(capteurs) != "instance" || capteurs.find("activation", "ON") != "ON")    continue    end

        if (capteurs.find("capteurOuvert") == nom)
            vrFonctions.changementEtatCapteur(valeur, nom, {nom: valeur}, vr["id"], "ouverture")
        end
        if (capteurs.find("capteurFerme") == nom)
            vrFonctions.changementEtatCapteur(valeur, nom, {nom: valeur}, vr["id"], "fermeture")
        end
    end
end
vrFonctions.capteurVirtuel = vrFonctions_capteurVirtuel

# Capteur d'inclinaison MPU6050 (2026-10-28) : l'angle du volet (trappe), lu par l'accelerometre sur
# le bus I2C, sert de capteur de position nomme "Inclinaison" dans 'capteursPosition'. Reglages dans
# 'capteursPosition.inclinaison' du persist ; sans "activation": "ON", rien n'est lu (ni bus, ni
# minuterie). Lu en Berry et pas par le pilote C USE_MPU6050 : celui-ci ne lit qu'une fois par
# TelePeriod et se disputerait le capteur. Une lecture au demarrage, puis toutes les 250 ms en course.

# Le bloc 'inclinaison' d'un volet s'il est actif, sinon nil
def vrFonctions_inclinaison(vr)
    if (type(vr) != "instance" || vr.find("activation", "OFF") != "ON")    return nil    end
    var capteurs = vr.find("capteursPosition")
    if (type(capteurs) != "instance" || capteurs.find("activation", "ON") != "ON")    return nil    end
    var incl = capteurs.find("inclinaison")
    if (type(incl) != "instance" || incl.find("activation", "OFF") != "ON")    return nil    end
    return incl
end
vrFonctions.inclinaison = vrFonctions_inclinaison

# Volets dont l'inclinaison est active (liste vide : le bus I2C n'est jamais touche)
def vrFonctions_inclinaisonsActives()
    var actifs = []
    var vrJSON = drivers.find("voletRoulants", {})
    if (vrJSON.find("activation", "OFF") != "ON")    return actifs    end
    var vrs = vrJSON.find("environnement", {}).find("VRs", {})
    for cle: vrs.keys()
        if (vrFonctions.inclinaison(vrs[cle]) != nil)    actifs.push(vrs[cle])    end
    end
    return actifs
end
vrFonctions.inclinaisonsActives = vrFonctions_inclinaisonsActives

# Suivi d'un volet (dernier etat, course en cours), dans l'etat modifiable du module
def vrFonctions_suiviInclinaison(id)
    var e = vrFonctions.etat()
    if (!e.contains("inclinaison"))    e["inclinaison"] = {}    end
    if (!e["inclinaison"].contains(id))    e["inclinaison"][id] = {"etat": nil, "enCourse": false}    end
    return e["inclinaison"][id]
end
vrFonctions.suiviInclinaison = vrFonctions_suiviInclinaison

# Le bloc 'inclinaison' du volet de numero 'id', ACTIF OU NON (calibrage, apprentissage), sinon nil
def vrFonctions_trouveInclinaison(id)
    for v: drivers.find("voletRoulants", {}).find("environnement", {}).find("VRs", {})
        if (type(v) != "instance" || v.find("id") != id)    continue    end
        var capteurs = v.find("capteursPosition")
        var incl = type(capteurs) == "instance" ? capteurs.find("inclinaison") : nil
        return type(incl) == "instance" ? incl : nil
    end
    return nil
end
vrFonctions.trouveInclinaison = vrFonctions_trouveInclinaison

# Acceleration moyenne [AX, AY, AZ] sur 4 lectures (unites brutes), ou nil + erreur si le capteur ne repond pas
def vrFonctions_lireVecteur(id, incl)
    import string
    var adresse = incl.find("adresse", 0x68)
    var e = vrFonctions.etat()
    if (!e.contains("bus"))    e["bus"] = {}    end
    var w = e["bus"].find(adresse)
    if (w == nil)
        w = tasmota.wire_scan(adresse)
        if (w == nil)
            vrFonctions.log(string.format("VR_INCLINAISON: MPU6050 introuvable a l'adresse 0x%02X (volet %i) !", adresse, id), LOG_LEVEL_ERREUR)
            return nil
        end
        w.write(adresse, 0x6B, 0, 1)        # registre PWR_MGMT_1 : sort le MPU6050 du sommeil
        e["bus"][adresse] = w
    end

    # Juste apres le reveil, les registres valent 0 tant que le 1er echantillon n'est pas pret : un
    # vecteur nul n'est pas une mesure (atan2(0, 0) = 0 degre passerait pour une butee). 8 lectures
    # au plus pour 4 valides, sans delay().
    var a = [0.0, 0.0, 0.0]
    var valides = 0
    for n: 1 .. 8
        var b = w.read_bytes(adresse, 0x3B, 6)      # AX, AY, AZ : int16 signes, gros-boutistes
        if (b == nil || b.size() < 6)
            e["bus"].remove(adresse)                 # prochain essai : nouveau wire_scan
            vrFonctions.log(string.format("VR_INCLINAISON: Le MPU6050 (0x%02X, volet %i) ne repond plus !", adresse, id), LOG_LEVEL_ERREUR)
            return nil
        end
        if (b.get(0, -2) == 0 && b.get(2, -2) == 0 && b.get(4, -2) == 0)    continue    end
        for i: 0 .. 2
            var v = b.get(2 * i, -2)
            a[i] += (v >= 0x8000 ? v - 0x10000 : v) / 4.0
        end
        valides += 1
        if (valides == 4)    return a    end
    end
    e["bus"].remove(adresse)
    vrFonctions.log(string.format("VR_INCLINAISON: Le MPU6050 (0x%02X, volet %i) ne rend que des zeros !", adresse, id), LOG_LEVEL_ERREUR)
    return nil
end
vrFonctions.lireVecteur = vrFonctions_lireVecteur

# Angle en degres, ou nil + erreur. 'axes' : les 2 axes de l'accelerometre dans le plan de rotation
# (atan2 du 1er sur le 2e), choisis par l'apprentissage ou a la main.
def vrFonctions_lireAngle(id, incl)
    import string
    import math
    var axes = str(incl.find("axes", "YZ"))
    var i1 = size(axes) == 2 ? string.find("XYZ", axes[0]) : -1
    var i2 = size(axes) == 2 ? string.find("XYZ", axes[1]) : -1
    if (i1 < 0 || i2 < 0)
        vrFonctions.log(string.format("VR_INCLINAISON: Axes '%s' invalides (volet %i), attendu 2 lettres parmi X, Y, Z !", axes, id), LOG_LEVEL_ERREUR)
        return nil
    end
    var a = vrFonctions.lireVecteur(id, incl)
    if (a == nil)    return nil    end
    return math.atan2(a[i1], a[i2]) * 180 / math.pi
end
vrFonctions.lireAngle = vrFonctions_lireAngle

# Axes et angles deduits des accelerations aux 2 butees, ou un texte d'erreur. L'axe de rotation est
# la composante qui varie le moins ; dans le plan des 2 autres, l'ordre retenu est celui dont l'arc
# ouvert -> ferme ne traverse pas la coupure +-180 degres de atan2, au plus loin de celle-ci.
def vrFonctions_calculeApprentissage(o, f)
    import math
    var k = 0
    for i: 1 .. 2    if (math.abs(o[i] - f[i]) < math.abs(o[k] - f[k]))    k = i    end    end
    var autres = []
    for i: 0 .. 2    if (i != k)    autres.push(i)    end    end
    var retenu = nil
    for ordre: [[autres[0], autres[1]], [autres[1], autres[0]]]
        var ao = math.atan2(o[ordre[0]], o[ordre[1]]) * 180 / math.pi
        var af = math.atan2(f[ordre[0]], f[ordre[1]]) * 180 / math.pi
        var loin = 180 - (math.abs(ao) > math.abs(af) ? math.abs(ao) : math.abs(af))
        if (math.abs(ao - af) < 180 && (retenu == nil || loin > retenu[3]))    retenu = [ordre, ao, af, loin]    end
    end
    if (retenu == nil)    return "l'arc traverse la coupure de l'angle : tourner le capteur d'un quart de tour"    end
    if (math.abs(retenu[1] - retenu[2]) < 10)    return "butees a moins de 10 degres : capteur mal fixe ?"    end
    var arrondi = def (x) return real(int(x * 10 + (x >= 0 ? 0.5 : -0.5))) / 10 end
    return {"axes": "XYZ"[retenu[0][0]] + "XYZ"[retenu[0][1]], "angleOuvert": arrondi(retenu[1]), "angleFerme": arrondi(retenu[2])}
end
vrFonctions.calculeApprentissage = vrFonctions_calculeApprentissage

# Apprentissage en 2 temps (ReglageVolets Apprentissage <id> ouvert|ferme) : releve l'acceleration de la
# butee en RAM ; les 2 connues, ecrit axes et angles dans le persist. Ne commande jamais le moteur.
def vrFonctions_apprend(id, butee)
    import string
    import persist
    var incl = vrFonctions.trouveInclinaison(id)
    if (incl == nil)    return string.format("pas de bloc capteursPosition.inclinaison pour le volet %i", id)    end
    if (butee != "ouvert" && butee != "ferme")    return "syntaxe : Apprentissage <id volet> ouvert|ferme"    end
    if (vrFonctions.suiviInclinaison(id)["enCourse"])    return string.format("volet %i en course : attendre son arret en butee", id)    end
    var v = vrFonctions.lireVecteur(id, incl)
    if (v == nil)    return string.format("volet %i : MPU6050 muet (voir les logs)", id)    end

    var e = vrFonctions.etat()
    if (!e.contains("apprentissage"))    e["apprentissage"] = {}    end
    if (!e["apprentissage"].contains(id))    e["apprentissage"][id] = {}    end
    var appris = e["apprentissage"][id]
    appris[butee] = v
    if (!appris.contains("ouvert") || !appris.contains("ferme"))
        return string.format("volet %i : butee '%s' relevee, amener le volet sur l'autre butee puis relancer", id, butee)
    end

    e["apprentissage"].remove(id)                   # reussite ou refus : la prochaine fois, 2 butees neuves
    var r = vrFonctions.calculeApprentissage(appris["ouvert"], appris["ferme"])
    if (type(r) == "string")
        vrFonctions.log(string.format("VR_INCLINAISON: Apprentissage refuse (volet %i) : %s !", id, r), LOG_LEVEL_ERREUR)
        return string.format("volet %i : apprentissage refuse, %s ; recommencer les 2 butees", id, r)
    end
    for cle: r.keys()    incl[cle] = r[cle]    end
    persist.drivers = drivers
    persist.save(true)                              # true : modif imbriquee, save() seul n'ecrit rien
    vrFonctions.suiviInclinaison(id)["etat"] = nil  # prochain releve : nouvel etat selon les butees apprises
    var msg = string.format("volet %i : appris, axes %s, angleOuvert %.1f, angleFerme %.1f (persist enregistre)", id, r["axes"], r["angleOuvert"], r["angleFerme"])
    vrFonctions.log("VR_INCLINAISON: Apprentissage du " + msg + " !", LOG_LEVEL_INFO)
    return msg
end
vrFonctions.apprend = vrFonctions_apprend

# "ouvert", "ferme" ou "entre" ; 'marge' = hysteresis pour QUITTER une butee (pas de rebond au seuil).
# angleOuvert peut etre inferieur a angleFerme selon le montage du capteur : 's' donne le sens.
def vrFonctions_etatInclinaison(angle, incl, precedent)
    var ouvert = incl.find("angleOuvert", 85)
    var ferme = incl.find("angleFerme", 3)
    var marge = incl.find("marge", 3)
    var s = ouvert >= ferme ? 1 : -1
    if (s * (angle - ouvert) >= (precedent == "ouvert" ? -marge : 0))    return "ouvert"    end
    if (s * (ferme - angle) >= (precedent == "ferme" ? -marge : 0))    return "ferme"    end
    return "entre"
end
vrFonctions.etatInclinaison = vrFonctions_etatInclinaison

# Releve l'angle d'un volet surveille ; au CHANGEMENT d'etat seulement, recale le Shutter comme un
# fin de course (capteurOuvert / capteurFerme = "Inclinaison"). Rend l'angle, ou nil si capteur muet.
def vrFonctions_releveInclinaison(vr)
    import string
    var incl = vrFonctions.inclinaison(vr)
    if (incl == nil)    return nil    end
    var id = vr["id"]
    var angle = vrFonctions.lireAngle(id, incl)
    var suivi = vrFonctions.suiviInclinaison(id)
    suivi["angle"] = angle                          # affiche par la page web (ligneWebInclinaison)
    if (angle == nil)    return nil    end
    var etat = vrFonctions.etatInclinaison(angle, incl, suivi["etat"])
    if (etat == suivi["etat"])    return angle    end

    suivi["etat"] = etat
    vrFonctions.log(string.format("VR_INCLINAISON: Volet %i %s (%.1f degres) !", id, etat, angle), LOG_LEVEL_DEBUG)
    var capteurs = vr["capteursPosition"]
    var nom = "Inclinaison"
    if (etat == "ouvert" && capteurs.find("capteurOuvert") == nom)
        vrFonctions.changementEtatCapteur("ON", nom, {nom: "ON"}, id, "ouverture")
    elif (etat == "ferme" && capteurs.find("capteurFerme") == nom)
        vrFonctions.changementEtatCapteur("ON", nom, {nom: "ON"}, id, "fermeture")
    end
    return angle
end
vrFonctions.releveInclinaison = vrFonctions_releveInclinaison

# Releve toutes les 250 ms tant que le volet est en course ; s'arrete a l'arret du volet ou si le
# capteur ne repond plus (une seule erreur par course, pas une toutes les 250 ms)
def vrFonctions_suitInclinaison(vr)
    var nom = "vrInclinaison" + str(vr["id"])
    tasmota.remove_timer(nom)
    if (vrFonctions.releveInclinaison(vr) == nil)    return    end
    if (vrFonctions.suiviInclinaison(vr["id"])["enCourse"])
        tasmota.set_timer(250, def () vrFonctions.suitInclinaison(vr) end, nom)
    end
end
vrFonctions.suitInclinaison = vrFonctions_suitInclinaison

# Ligne de la page d'accueil : DERNIER angle releve (demarrage, course, arret), sans relire le bus a
# chaque rafraichissement de la page (un capteur muet loguerait une erreur toutes les 2 s)
def vrFonctions_ligneWebInclinaison(vr)
    import string
    var suivi = vrFonctions.suiviInclinaison(vr["id"])
    var nom = vr.find("nom", "Volet " + str(vr["id"]))
    if (suivi.find("angle") == nil)    return string.format("{s}%s : inclinaison{m}capteur muet ou pas encore lu{e}", nom)    end
    return string.format("{s}%s : inclinaison{m}%.1f &deg; (%s){e}", nom, suivi["angle"], str(suivi["etat"]))
end
vrFonctions.ligneWebInclinaison = vrFonctions_ligneWebInclinaison

# Règles sur changement d'état des capteurs
def vrFonctions_changementDirection(value, trigger, msg, numRideau)
    import string
    import json

	# Test
	vrFonctions.log("VR_CHANGEMENT_DIRECTION: -------------------- Volets changementDirection -------------------", LOG_LEVEL_DEBUG_PLUS)
	vrFonctions.log("VR_CHANGEMENT_DIRECTION: value=" + str(value), LOG_LEVEL_DEBUG)							# value=SINGLE
	vrFonctions.log("VR_CHANGEMENT_DIRECTION: trigger=" + str(trigger), LOG_LEVEL_DEBUG)						# trigger=Button1
	vrFonctions.log("VR_CHANGEMENT_DIRECTION: msg=" + str(msg), LOG_LEVEL_DEBUG)								# msg={'Button1': {'Action': SINGLE}}
    vrFonctions.log("VR_CHANGEMENT_DIRECTION: numRideau=" + str(numRideau), LOG_LEVEL_DEBUG)			        # numRideau=1

	if (type(value)) == "instance"
		for cle: value.keys()
			value = value[cle]
		end
	end

    # Teste la valeur (#0: Arrêt / #1: Ouverture en cours / #-1: Fermeture en cours)
    if (value == 0)
        vrFonctions.log(string.format("VR_CHANGEMENT_DIRECTION: Le volet %i est à l'arrêt !", numRideau), LOG_LEVEL_DEBUG)
    elif (value == 1)
        vrFonctions.log(string.format("VR_CHANGEMENT_DIRECTION: Le volet %i est en cours d'ouverture !", numRideau), LOG_LEVEL_DEBUG)
    elif (value == -1)
        vrFonctions.log(string.format("VR_CHANGEMENT_DIRECTION: Le volet %i est en cours de fermeture !", numRideau), LOG_LEVEL_DEBUG)
    end

	tasmota.yield()

    # Modifie l'état de certains relais en fonction de la direction du volet
    # Volet retrouve par son NUMERO (2026-10-12), et non par la cle "VR<n>" : plusieurs volets,
    # dont la cle du persist ne suit pas forcement le numero
    var vrJSON = drivers["voletRoulants"]
    var vr = nil
    for cle: vrJSON["environnement"]["VRs"].keys()
        var v = vrJSON["environnement"]["VRs"][cle]
        if (type(v) == "instance" && v.find("id") == numRideau)    vr = v    break    end
    end
    if (vr == nil)    return    end

    # Capteur d'inclinaison actif : suivi pendant la course, derniere lecture a l'arret
    if (vrFonctions.inclinaison(vr) != nil)
        vrFonctions.suiviInclinaison(numRideau)["enCourse"] = (value != 0)
        vrFonctions.suitInclinaison(vr)
    end

    var activationSiOuvert = vr.find("activationSiOuvert", false)
    var activationSiFerme = vr.find("activationSiFerme", false)

    # Parcours les relais à activer ou désactiver à l'ouverture du volet
    if (value == 1)
        if (activationSiOuvert != false)
            if (activationSiOuvert["activation"] == "ON")   
                for i: 0 .. activationSiOuvert.find("tabRelais", []).size() - 1
                    tasmota.cmd(string.format("Power%i %s", activationSiOuvert["tabRelais"][i], activationSiOuvert["tabEtatRelais"][i]), boolMute)
                    vrFonctions.log(string.format("VR_CHANGEMENT_DIRECTION: %s le relai %i à l'ouverture du volet %i !", (activationSiOuvert["tabEtatRelais"][i] == 1 ? "Active" : "Désactive"), activationSiOuvert["tabRelais"][i], numRideau), LOG_LEVEL_DEBUG)
                end
            end
        end

        if (activationSiFerme != false)
            if (activationSiFerme["activation"] == "ON")
                for i: 0 .. activationSiFerme.find("tabRelais", []).size() - 1
                    tasmota.cmd(string.format("Power%i %i", activationSiFerme["tabRelais"][i], 1 - activationSiFerme["tabEtatRelais"][i]), boolMute)
                    vrFonctions.log(string.format("VR_CHANGEMENT_DIRECTION: %s le relai %i à l'ouverture du volet %i !", (1 - activationSiFerme["tabEtatRelais"][i] == 1 ? "Active" : "Désactive"), activationSiFerme["tabRelais"][i], numRideau), LOG_LEVEL_DEBUG)
                end
            end
        end
    end

    # Parcours les relais à activer ou désactiver à la fermeture du volet
    if (value == -1)
        if (activationSiFerme != false)
            if (activationSiFerme["activation"] == "ON")
                for i: 0 .. activationSiFerme.find("tabRelais", []).size() - 1
                    tasmota.cmd(string.format("Power%i %i", activationSiFerme["tabRelais"][i], activationSiFerme["tabEtatRelais"][i]), boolMute)
                    vrFonctions.log(string.format("VR_CHANGEMENT_DIRECTION: %s le relai %i à la fermeture du volet %i !", (activationSiFerme["tabEtatRelais"][i] == 1 ? "Active" : "Désactive"), activationSiFerme["tabRelais"][i], numRideau), LOG_LEVEL_DEBUG)
                end
            end
        end

        if (activationSiOuvert != false)
            if (activationSiOuvert["activation"] == "ON")   
                for i: 0 .. activationSiOuvert.find("tabRelais", []).size() - 1
                    tasmota.cmd(string.format("Power%i %s", activationSiOuvert["tabRelais"][i],  1 - activationSiOuvert["tabEtatRelais"][i]), boolMute)
                    vrFonctions.log(string.format("VR_CHANGEMENT_DIRECTION: %s le relai %i à la fermeture du volet %i !", (1 - activationSiOuvert["tabEtatRelais"][i] == 1 ? "Active" : "Désactive"), activationSiOuvert["tabRelais"][i], numRideau), LOG_LEVEL_DEBUG)
                end
            end
        end
    end
end
vrFonctions.changementDirection = vrFonctions_changementDirection

# Retourne le module lors de l'importation
return vrFonctions