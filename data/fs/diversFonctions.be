# Définition du module
#@ solidify:diversFonctions
var diversFonctions = module("diversFonctions")

def diversFonctions_afficheDateTime(sepHoraire, boolAfficheSec, sepDateHeure)
    import string

	var time_dump = tasmota.time_dump(tasmota.rtc()["local"])
	
	# Paramètres par défaut si absent
	if sepHoraire == "" sepHoraire = "-" end
	if boolAfficheSec == nil boolAfficheSec = false end
	
	var date = (time_dump["day"] < 10 ? "0" + str(time_dump["day"]) : str(time_dump["day"])) + "/" 
		date += (time_dump["month"] < 10 ? "0" + str(time_dump["month"]) : str(time_dump["month"])) + "/" 
		date += str(time_dump["year"]) + (sepDateHeure == "" ? " " : sepDateHeure)
		
	if sepHoraire == ":"
		date += (time_dump["hour"] < 10 ? "0" + str(time_dump["hour"]) : str(time_dump["hour"])) + ":" 
		date += (time_dump["min"] < 10 ? "0" + str(time_dump["min"]) : str(time_dump["min"])) + ":" 
		date += (time_dump["sec"] < 10 ? "0" + str(time_dump["sec"]) : str(time_dump["sec"]))
	else
		date += (time_dump["hour"] < 10 ? "0" + str(time_dump["hour"]) : str(time_dump["hour"])) + "h" 
		date += (time_dump["min"] < 10 ? "0" + str(time_dump["min"]) : str(time_dump["min"]))
		if boolAfficheSec
			date += "min" + (time_dump["sec"] < 10 ? "0" + str(time_dump["sec"]) : str(time_dump["sec"])) + "s" 
		end
	end
		
	return date
end
diversFonctions.afficheDateTime = diversFonctions_afficheDateTime

# Génère un débit aléatoire
def diversFonctions_getRandomInt(min, max)
	import math
	import crypto

	var index_found = true
	var x1 = 0

	min = math.ceil(min);
	max = math.floor(max);

	while (index_found)
		x1 = crypto.random(1)[0]
		if ((x1 >= min) && (x1 <= max))
			index_found = false
		end
	end

	return int(x1);
end
diversFonctions.getRandomInt = diversFonctions_getRandomInt

# Récupère les template enregistré dans la device Tasmota
# Récupère les componentes
# @template = tableau json enregistré dans _persist.json
# @ Retourne true si l'enregistrement en json doit être effectué
def diversFonctions_recupereTemplate(template)
    import persist
	import gestionFileFolder
	import json
	import path

    var enregistrePersistant = false

	# Récupère le template (modele) : un seul appel a 'Template'
	logFonctions.log("RECUP_TEMPLATE: Recupere le template du modele !", LOG_LEVEL_DEBUG)
	var templateActuel = tasmota.cmd("Template", boolMute)
	if str(templateActuel) != str(template)
		# Enregistre le pin du modèle dans persist.json
		enregistrePersistant = true
		logFonctions.log("RECUP_TEMPLATE: Enregistre 'Template' modifié en json !", LOG_LEVEL_DEBUG)
		persist.template = templateActuel
		persist.save()
	end

	# Les 'componentes' (noms des fonctions GPIO -> code) ne dependent QUE DU FIRMWARE
	# (liste compilee), pas du template. Avant, 'GPIOs' (reponse de ~3,7 Ko, 218 entrees),
	# json.load/json.dump et 2 ecritures etaient refaits a CHAQUE boot, en plein creux memoire
	# du demarrage. Ils ne sont plus refaits que si le firmware a change ou si un fichier manque.
	# Marqueur = date de build du firmware, dans un petit fichier a part (lecture peu couteuse).
	var statusFWR = tasmota.cmd("Status 2", boolMute)
	var build = (isinstance(statusFWR, map) && isinstance(statusFWR.find("StatusFWR"), map)) ? str(statusFWR["StatusFWR"].find("BuildDateTime", "")) : ""
	if (build != "" && gestionFileFolder.readFile("/json/componentes.build") == build && path.exists("/json/componentes.json") && path.exists("/json/componentesInverse.json"))
		logFonctions.log("RECUP_TEMPLATE: Firmware inchange, componentes deja a jour !", LOG_LEVEL_DEBUG)
		return enregistrePersistant
	end

	# 'GPIOs' peut publier PLUSIEURS pages ("GPIOs1", "GPIOs2"...) si la liste depasse la taille
	# d'un message ; tasmota.cmd() ne renvoie que la DERNIERE. Aujourd'hui : une seule page.
	var reponseCMD = tasmota.cmd("GPIOs", boolMute)
	if !isinstance(reponseCMD, map)
		logFonctions.log("RECUP_TEMPLATE_ERREUR: Reponse 'GPIOs' invalide, componentes non regeneres !", LOG_LEVEL_ERREUR)
		return enregistrePersistant
	end
	var componentes = {"componentes": {}}
	var componentesInverse = {"componentes": {}}
	for page: reponseCMD.keys()
		for nom: reponseCMD[page].keys()
			componentes["componentes"][nom] = reponseCMD[page][nom]
			componentesInverse["componentes"].insert(reponseCMD[page][nom], nom)	# insert : garde le 1er nom d'un code (comme avant)
		end
	end
	reponseCMD = nil

	logFonctions.log("RECUP_TEMPLATE: Enregistre les componentes en json !", LOG_LEVEL_DEBUG)
	gestionFileFolder.writeFile("/json/componentes.json", json.dump(componentes))
	componentes = nil
	gestionFileFolder.writeFile("/json/componentesInverse.json", json.dump(componentesInverse))
	if (build != "")	gestionFileFolder.writeFile("/json/componentes.build", build)	end

    return enregistrePersistant
end
diversFonctions.recupereTemplate = diversFonctions_recupereTemplate

# Lit le fichier de veille de l'environnement des drivers inactifs (flash, hors RAM) :
# {} s'il n'existe pas, nil s'il est ILLISIBLE (on ne touche alors a rien)
def diversFonctions_litVeille()
	import json
	import path
	import gestionFileFolder

	if !path.exists("/json/driversInactifs.json")		return {}		end
	var veille
	try
		veille = json.load(gestionFileFolder.readFile("/json/driversInactifs.json"))
	except .. as e, m
	end
	return isinstance(veille, map) ? veille : nil
end
diversFonctions.litVeille = diversFonctions_litVeille

# Met en veille l'environnement des drivers INACTIFS : il part dans /json/driversInactifs.json et le persist
# ne garde que 'environnement': {} (le code lit drivers[x]["environnement"].find(...) sans garde).
# Reveille (restaure) l'environnement d'un driver ACTIF dont l'environnement est vide.
# Rien n'est perdu :
#   - le fichier est ecrit (via .tmp relu et verifie) AVANT que le persist ne soit allege ;
#   - un environnement non vide dans le persist fait foi (re-deploiement du _persist.json du depot) ;
#   - au reveil, l'entree du fichier est CONSERVEE (copie perimee sans risque, jamais de perte).
# Le fichier n'est lu que s'il y a quelque chose a faire : en regime etabli, aucun cout au boot.
def diversFonctions_hiberneDriversInactifs()
	import json
	import path
	import persist
	import gestionFileFolder

	var aEndormir = []
	var aReveiller = []
	for nom: drivers.keys()
		var d = drivers[nom]
		if !isinstance(d, map)	continue	end
		var env = d.find("environnement")
		var envVide = !isinstance(env, map) || env.size() == 0
		if (d.find("activation", "OFF") == "ON")
			if (envVide)	aReveiller.push(nom)	end
		elif (!envVide)
			aEndormir.push(nom)
		end
	end
	if (aEndormir.size() == 0 && aReveiller.size() == 0)	return	end

	var fichier = "/json/driversInactifs.json"
	var veille = diversFonctions.litVeille()
	if (veille == nil)
		logFonctions.log("VEILLE_DRIVERS_ERREUR: " + fichier + " illisible : aucune mise en veille !", LOG_LEVEL_ERREUR)
		return
	end

	# Reveil : restaure depuis le fichier (l'entree y reste)
	var nbReveilles = 0
	for nom: aReveiller
		if (veille.contains(nom))
			drivers[nom]["environnement"] = veille[nom]
			nbReveilles += 1
			logFonctions.log("VEILLE_DRIVERS: Reveille l'environnement du driver '" + nom + "' !", LOG_LEVEL_DEBUG)
		end
	end

	# Mise en veille : 1) fichier ecrit et VERIFIE, 2) seulement ensuite, persist allege
	if (aEndormir.size() > 0)
		for nom: aEndormir	veille[nom] = drivers[nom]["environnement"]		end
		var tmp = fichier + ".tmp"
		gestionFileFolder.writeFile(tmp, json.dump(veille))
		var relu = nil
		try relu = json.load(gestionFileFolder.readFile(tmp))	except .. as e, m	end
		var ok = isinstance(relu, map)
		if ok	for nom: aEndormir	ok = ok && relu.contains(nom)	end		end
		relu = nil
		if !ok
			logFonctions.log("VEILLE_DRIVERS_ERREUR: Ecriture de " + tmp + " non verifiee : aucune mise en veille !", LOG_LEVEL_ERREUR)
			path.remove(tmp)
			aEndormir = []
		else
			path.remove(fichier)
			path.rename(tmp, fichier)
			for nom: aEndormir
				drivers[nom]["environnement"] = {}
				logFonctions.log("VEILLE_DRIVERS: Met en veille l'environnement du driver '" + nom + "' !", LOG_LEVEL_DEBUG)
			end
		end
	end
	veille = nil

	if (aEndormir.size() > 0 || nbReveilles > 0)		persist.save(true)		end
end
diversFonctions.hiberneDriversInactifs = diversFonctions_hiberneDriversInactifs

# Rend un driver AVEC son environnement (reinjecte depuis le fichier de veille s'il y dort),
# pour l'affichage web : COPIE superficielle, le persist en RAM n'est pas modifie.
# 'veille' (optionnel) : contenu deja lu du fichier, pour ne le lire qu'une fois sur plusieurs drivers.
def diversFonctions_driverComplet(nom, veille)
	var d = drivers.find(nom)
	if !isinstance(d, map)	return d	end
	var env = d.find("environnement")
	if (d.find("activation", "OFF") == "ON" || (isinstance(env, map) && env.size() > 0))	return d	end
	if (veille == nil)	veille = diversFonctions.litVeille()	end
	if (veille == nil || !veille.contains(nom))		return d	end
	var copie = {}
	for cle: d.keys()	copie[cle] = d[cle]		end
	copie["environnement"] = veille[nom]
	return copie
end
diversFonctions.driverComplet = diversFonctions_driverComplet

# Supprime les listes VIDES de cles connues ('ids', 'modules', 'etatSiON'...) : ~60 octets
# de RAM chacune, et leurs lecteurs utilisent .find(cle, []). Liste FERMEE de cles, jamais
# de suppression generique (une liste vide peut etre remplie ailleurs par .push()).
# Retourne le nombre de listes supprimees.
def diversFonctions_elagueListesVides(noeud)
	var elaguables = ["ids", "modules", "etatSiON", "etatSiOFF", "limites", "topic", "tabRelais", "tabEtatRelais"]
	var nb = 0
	if !isinstance(noeud, map)	return 0	end
	var aSupprimer = []
	for cle: noeud.keys()
		var v = noeud[cle]
		if isinstance(v, map)
			nb += diversFonctions.elagueListesVides(v)
		elif (isinstance(v, list) && v.size() == 0 && elaguables.find(cle) != nil)
			aSupprimer.push(cle)
		end
	end
	for cle: aSupprimer		noeud.remove(cle)	end
	return nb + aSupprimer.size()
end
diversFonctions.elagueListesVides = diversFonctions_elagueListesVides

# Affiche les statistiques de mémoire
def diversFonctions_statMemory()
	import string 

	var stat = tasmota.memory()

	logFonctions.log("STAT_MEMORY: -------------------- divers statMemory -------------------", LOG_LEVEL_DEBUG_PLUS)
	logFonctions.log(string.format("STAT_MEMORY: Espace programme utilisé = %.1f%%", real(stat["program"] - stat["program_free"]) / real(stat["program"]) * 100.0), LOG_LEVEL_DEBUG)							# value=SINGLE
	if (stat.find("psram", false) && stat.find("psram_free", false))
		logFonctions.log(string.format("STAT_MEMORY: Espace PSRAM utilisé = %.1f%%", real(stat["psram"] - stat["psram_free"]) / real(stat["psram"]) * 100.0), LOG_LEVEL_DEBUG)
	end	
	logFonctions.log(string.format("STAT_MEMORY: Espace Heap libre = %d", stat["heap_free"]), LOG_LEVEL_DEBUG)	
end
diversFonctions.statMemory = diversFonctions_statMemory

# Se charge de joindre 2 json en un tableau
def diversFonctions_joinJsonTab(*json)
	var json_result = []
        
    for i: 0 .. size(json) - 1
        if (type(json[i]) == 'instance' && json[i] != nil)
            json_result.push(json[i])
        end
    end

	return json_result
end
diversFonctions.joinJsonTab = diversFonctions_joinJsonTab

# Convertit et imprime un nombre en représentation binaire
def diversFonctions_printBinaire(nombre)
	var binary_string = ''
	
	while (nombre > 0)
	# for nb: 0 .. nb_bytes - 1
		binary_string = str(nombre % 2) + binary_string
		nombre /= 2
	end

	binary_string = "0b" + binary_string
	return binary_string
end
diversFonctions.printBinaire = diversFonctions_printBinaire

# Aide contextuelle des commandes personnalisees (2026-10-04), commune a tous les modules.
# A appeler EN TETE du gestionnaire de commande ; retourne true si la commande est traitee
# (aide affichee, reponse envoyee) -> le gestionnaire doit alors s'arreter (return).
#   'Cmd help|aide|?'           -> liste des sous-commandes (syntaxe + resume)
#   'Cmd help <sous-commande>'  -> detail de la sous-commande
#   'Cmd <inconnue>'            -> liste, si verifieInconnue (commandes a sous-commandes seulement)
#   'Cmd' sans argument         -> false : comportement du gestionnaire inchange
# fnAide(sujet) : fonction d'aide du module, appelee SEULEMENT ici.
#   sujet == nil -> [[nom, syntaxe, resume], ...] ; sujet == nom -> [ligne, ...] ou nil.
# Cout : seul le 1er mot du payload est extrait (pas de split d'un JSON entier a chaque
# commande) ; la liste n'est construite que pour une aide ou une verification d'inconnue.
def diversFonctions_traiteAide(commande, payload, fnAide, verifieInconnue)
	import string
	import json

	var p = (payload == nil ? "" : str(payload))
	if (p == "")	return false	end
	var i = string.find(p, " ")
	var f = string.toupper(i >= 0 ? p[0 .. i - 1] : p)
	var demande = (f == "HELP" || f == "AIDE" || f == "?")
	if (!demande && !verifieInconnue)	return false	end

	var liste = fnAide(nil)
	if !demande
		for e: liste	if (string.toupper(e[0]) == f)	return false	end	end
	end

	# Sujet du detail : 2e mot du payload ('Cmd help BaudrateModbus')
	var sujet = nil
	if (demande && i >= 0)
		var reste = p[i + 1 ..]
		var j = string.find(reste, " ")
		sujet = (j >= 0 ? reste[0 .. j - 1] : reste)
		if (sujet == "")	sujet = nil		end
	end

	var noms = []
	for e: liste	if (e[0] != "")	noms.push(e[0])	end	end
	var reponse = {}
	if (demande && sujet != nil)
		var detail = fnAide(sujet)
		if (detail != nil)
			print(string.format("==================== AIDE %s %s ====================", commande, sujet))
			for e: liste	if (string.toupper(e[0]) == string.toupper(sujet))	print("Syntaxe : " + commande + " " + e[1])	end	end
			for l: detail	print("  " + l)		end
			reponse[commande] = {"Aide": sujet, "Detail": "affiche en console"}
			tasmota.resp_cmnd(json.dump(reponse))
			return true
		end
		print(string.format("%s : sous-commande '%s' inconnue", commande, sujet))
	elif !demande
		print(string.format("%s : sous-commande '%s' inconnue", commande, i >= 0 ? p[0 .. i - 1] : p))
	end

	print(string.format("==================== AIDE %s ====================", commande))
	for e: liste	print(string.format("  %s %s", commande, e[1]))	print("      -> " + e[2])	end
	if (noms.size() > 0)	print(string.format("Detail d'une sous-commande : %s help <sous-commande>", commande))	end
	reponse[commande] = demande ? {"Aide": "affichee en console", "SousCommandes": noms}
	                            : {"Erreur": "sous-commande inconnue", "SousCommandes": noms}
	tasmota.resp_cmnd(json.dump(reponse))
	return true
end
diversFonctions.traiteAide = diversFonctions_traiteAide

# Retourne le module lors de l'importation
return diversFonctions