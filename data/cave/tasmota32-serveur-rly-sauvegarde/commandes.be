import string

def reglageGlobal(cmd, idx, payload, payload_json)
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