# Définition du module
var diversFonctions = module("/diversFonctions")

diversFonctions.afficheDateTime = def(sepHoraire, boolAfficheSec, sepDateHeure)
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

# Génère un débit aléatoire
diversFonctions.getRandomInt = def(min, max)
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

# Récupère les template enregistré dans la device Tasmota
# Récupère les componentes
# @template = tableau json enregistré dans _persist.json
# @ Retourne true si l'enregistrement en json doit être effectué
diversFonctions.recupereTemplate = def(template)
    import persist
	import gestionFileFolder
	import json

    var enregistrePersistant = false
    var reponseCMD
    var componentesInverse = {"componentes": {}}

	# Récupère le template (modele)
	log("RECUP_TEMPLATE: Recupere le template du modele !", LOG_LEVEL_DEBUG)
	if str(tasmota.cmd("Template", boolMute)) != str(template)
		template = tasmota.cmd("Template", boolMute)

		# Enregistre le pin du modèle dans persist.json
		enregistrePersistant = true
		log("RECUP_TEMPLATE: Enregistre 'Template' modifié en json !", LOG_LEVEL_DEBUG)
		persist.template = template
		persist.save() 
	end

	# Récupère les componentes existants du modele 
	var componentes = json.load(gestionFileFolder.readFile("/json/componentes.json"))

	reponseCMD = tasmota.cmd("GPIOs", boolMute)
	for cle: reponseCMD.keys()
        if (componentes == nil) 
            componentes = {"componentes": {}}
            log("RECUP_TEMPLATE: Le fichier '/json/componentes.json' est vide !", LOG_LEVEL_DEBUG)
        else
            if (componentes["componentes"].size() == 0 || componentes["componentes"] != reponseCMD[cle])
                if (componentes == nil) 
                    log("RECUP_TEMPLATE: Le fichier '/json/componentes.json' n'existe pas !", LOG_LEVEL_DEBUG)
                end
                log("RECUP_TEMPLATE: Enregistre les componentes en json !", LOG_LEVEL_DEBUG)
            end
        end

        componentes["componentes"] = reponseCMD[cle]
        gestionFileFolder.writeFile("/json/componentes.json", json.dump(componentes))
	end	
	
	# Prépare l'inversion des 'componentes'
	for cle: componentes["componentes"].keys()
		componentesInverse["componentes"].insert(componentes["componentes"][cle], cle)
	end
    gestionFileFolder.writeFile("/json/componentesInverse.json", json.dump(componentesInverse))

    return enregistrePersistant
end

# Affiche les statistiques de mémoire
diversFonctions.statMemory = def()
	import string 

	var stat = tasmota.memory()

	log("STAT_MEMORY: -------------------- divers statMemory -------------------", LOG_LEVEL_DEBUG)
	log(string.format("STAT_MEMORY: Espace programme utilisé = %.1f%%", real(stat["program"] - stat["program_free"]) / real(stat["program"]) * 100.0), LOG_LEVEL_DEBUG)							# value=SINGLE
	if (stat.find("psram", false) && stat.find("psram_free", false))
		log(string.format("STAT_MEMORY: Espace PSRAM utilisé = %.1f%%", real(stat["psram"] - stat["psram_free"]) / real(stat["psram"]) * 100.0), LOG_LEVEL_DEBUG)
	end	
	log(string.format("STAT_MEMORY: Espace Heap libre = %d", stat["heap_free"]), LOG_LEVEL_DEBUG)	
end

# Se charge de joindre 2 json en un tableau
diversFonctions.joinJsonTab = def(*json)
	var json_result = []
        
    for i: 0 .. size(json) - 1
        if (type(json[i]) == 'instance' && json[i] != nil)
            json_result.push(json[i])
        end
    end

	return json_result
end

# Convertit et imprime un nombre en représentation binaire
diversFonctions.printBinaire = def(nombre)
	var binary_string = ''
	
	while (nombre > 0)
	# for nb: 0 .. nb_bytes - 1
		binary_string = str(nombre % 2) + binary_string
		nombre /= 2
	end

	binary_string = "0b" + binary_string
	return binary_string
end

# Retourne le module lors de l'importation
return diversFonctions