import string

# Aide contextuelle des commandes personnalisees (2026-10-04).
# COPIE de diversFonctions.traiteAide (data/fs/diversFonctions.be) pour cet ensemble AUTONOME,
# qui n'utilise pas diversFonctions. Meme contrat, meme sortie.
# A appeler EN TETE du gestionnaire de commande ; retourne true si la commande est traitee
# (aide affichee, reponse envoyee) -> le gestionnaire doit alors s'arreter (return).
#   'Cmd help|aide|?'           -> liste des sous-commandes (syntaxe + resume)
#   'Cmd help <sous-commande>'  -> detail de la sous-commande
#   'Cmd <inconnue>'            -> liste, si verifieInconnue (commandes a sous-commandes seulement)
#   'Cmd' sans argument         -> false : comportement du gestionnaire inchange
# fnAide(sujet) : fonction d'aide de la commande, appelee SEULEMENT ici.
#   sujet == nil -> [[nom, syntaxe, resume], ...] ; sujet == nom -> [ligne, ...] ou nil.
def traiteAide(commande, payload, fnAide, verifieInconnue)
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

# Aide commune aux 4 commandes ReglageGlobal, ReglageDHT22, ReglagePompe et ReglageAutres :
# leurs gestionnaires ci-dessous sont des squelettes (aucune sous-commande implementee), ils
# affichent seulement les arguments recus puis repondent 'Done'. Appelee SEULEMENT par traiteAide.
def aideReglageReserve(sujet)
	if (sujet == nil)
		return [["", "(sans sous-commande)", "commande reservee : affiche ses arguments en console, ne regle rien"]]
	end
	return nil
end

def reglageGlobal(cmd, idx, payload, payload_json)
	if traiteAide("ReglageGlobal", payload, aideReglageReserve, false)	return	end
	var fonction = ""
	var parametre = ""
	
	# Détermine la fonction appelée et ses paramètres
	if string.find(payload, " ") > - 1
		fonction = str(string.split(payload, " ")[0])
		parametre = str(string.split(payload, " ")[1])
		print("payload1=" + str(string.split(payload, " ")[0]))
		print("payload2=" + str(string.split(payload, " ")[1]))
	else 
		fonction = payload
	end
	
	print("cmd=" + str(cmd))
	print("idx=" + str(idx))
	print("fonction=" + str(fonction))
	print("parametre=" + str(parametre))
	print("payload_json=" + str(payload_json))
	
	# Commande réussie
	tasmota.resp_cmnd_done()	
end

def reglageDHT22(cmd, idx, payload, payload_json)
	if traiteAide("ReglageDHT22", payload, aideReglageReserve, false)	return	end
	var fonction = ""
	var parametre = ""
	
	# Détermine la fonction appelée et ses paramètres
	if string.find(payload, " ") > - 1
		fonction = str(string.split(payload, " ")[0])
		parametre = str(string.split(payload, " ")[1])
		print("payload1=" + str(string.split(payload, " ")[0]))
		print("payload2=" + str(string.split(payload, " ")[1]))
	else 
		fonction = payload
	end
	
	print("cmd=" + str(cmd))
	print("idx=" + str(idx))
	print("fonction=" + str(fonction))
	print("parametre=" + str(parametre))
	print("payload_json=" + str(payload_json))
	
	# Commande réussie
	tasmota.resp_cmnd_done()		
end

def reglagePompe(cmd, idx, payload, payload_json)
	if traiteAide("ReglagePompe", payload, aideReglageReserve, false)	return	end
	var fonction = ""
	var parametre = ""
	
	# Détermine la fonction appelée et ses paramètres
	if string.find(payload, " ") > - 1
		fonction = str(string.split(payload, " ")[0])
		parametre = str(string.split(payload, " ")[1])
		print("payload1=" + str(string.split(payload, " ")[0]))
		print("payload2=" + str(string.split(payload, " ")[1]))
	else 
		fonction = payload
	end
	
	print("cmd=" + str(cmd))
	print("idx=" + str(idx))
	print("fonction=" + str(fonction))
	print("parametre=" + str(parametre))
	print("payload_json=" + str(payload_json))
	
	# Commande réussie
	tasmota.resp_cmnd_done()		
end

def reglageAutres(cmd, idx, payload, payload_json)
	if traiteAide("ReglageAutres", payload, aideReglageReserve, false)	return	end
	var fonction = ""
	var parametre = ""
	
	# Détermine la fonction appelée et ses paramètres
	if string.find(payload, " ") > - 1
		fonction = str(string.split(payload, " ")[0])
		parametre = str(string.split(payload, " ")[1])
		print("payload1=" + str(string.split(payload, " ")[0]))
		print("payload2=" + str(string.split(payload, " ")[1]))
	else 
		fonction = payload
	end
	
	print("cmd=" + str(cmd))
	print("idx=" + str(idx))
	print("fonction=" + str(fonction))
	print("parametre=" + str(parametre))
	print("payload_json=" + str(payload_json))
	
	# Commande réussie
	tasmota.resp_cmnd_done()		
end