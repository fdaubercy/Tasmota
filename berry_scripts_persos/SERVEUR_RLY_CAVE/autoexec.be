# Déclaration des librairies utilisées
import persist

# Recense toutes les variables globales
var boolMute = true

# Les 2 classes crées
var controleGeneral
var gestionWeb

# Déclaration des variables de LOG
var LOG_LEVEL_ERREUR = 1
var LOG_LEVEL_INFO = 2
var LOG_LEVEL_DEBUG = 3
var LOG_LEVEL_DEBUG_PLUS = 4
var logSerial = LOG_LEVEL_INFO
var logWeb = LOG_LEVEL_INFO

# Vérifie l'intégrité du fichier _persist.json
var parametres = persist.find("parametres", false)
if !parametres
	log ("AUTO_EXE: Crée le _persist.json par défaut !", LOG_LEVEL_DEBUG)
	parametres = {
		"parametres": {
			"diverses": {
				"logs": 3,
				"eviteResetBTN": "ON",
				"leds": {
					"ledLink": {
						"activation": "OFF",
						"pin": -1,
						"type": 17408
					},
					"led": {
						"activation": "OFF",
						"pin": -1,
						"id": 1,
						"type": 9216
					}
				}
			},
			"serveur": {
				"nom": "Serveur ...",
				"hostname": "SERVEUR",
				"mDNS": "ON",
				"IP": {
					"IPAddress": "",
					"IPGateway": "",
					"Subnet": "",
					"DNSServer": ""
				},
				"wifi": {
					"power": 0,
					"selectSignalFort": "ON",
					"reScanBy44": "ON",
					"reseau1": {
						"nomReseauWifi": "",
						"mdpWifi": ""
					},
					"reseau2": {
						"nomReseauWifi": "",
						"mdpWifi": ""
					}
				},
				"localisation": {
					"latitude": "50.410931",
					"longitude": "3.085796"
				},
				"fuseauHoraire": {
					"timezone": 99,
					"TimeStd": {
						"Week": 0,
						"Month": 10,
						"Offset": 60,
						"Day": 1,
						"Hemisphere": 0,
						"Hour": 3
					},
					"TimeDst": {
						"Hemisphere": 0,
						"Week": 0,
						"Month": 3,
						"Day": 1,
						"Hour": 2,
						"Offset": 120
					}
				},
				"mqtt": {
					"activation": "OFF",
					"hote": "",
					"port": 1883,
					"client": "",
					"utilisateur": "",
					"mdp": "",
					"topic": ""
				},
				"pageWeb": {
					"activation": "OFF",
					"CORS": "ON",
					"url_componentes": "http://192.168.0.159/dashboard/componentes.json"
				}
			},
			"modele": {
				"template": {},
				"componentes": {}, 
				"componentesInverse": {}
			},
			"modules": {
				"activation": "ON",
				"Thermo-Hygrometre": {
					"name": "Thermomètre Cave",
					"activation": "ON",
					"environnement": {
						"relais": {
							"relai1": {
								"activation": "ON",
								"nom": "Ventilation Cave",
								"pin": -1,
								"type": 224,
								"id": 2,
								"etat": "OFF",
								"timer": 0
							}
						},
						"thermometres": {
							"thermometre1": {
								"activation": "ON",
								"type": 1216,
								"pin": -1,
								"value": 0,
								"relaisLie": {
									"modules": [],
									"ids": [],
									"limites": [],
									"etatSiON": ["TOGGLE"],
									"etatSiOFF": [""]
								}
							}
						}
					}
				},
				"pompeVideCave": {
					"name": "Pompe",
					"activation": "OFF",
					"environnement": {
						"boutons": {
							"bouton1": {
								"activation": "OFF",
								"id": -1,
								"pin": -1,
								"type": 0,							
								"typeAction": "ON/OFF",
								"etat": "OFF",	
								"relaisLie": {
									"modules": [""],
									"ids": [],
									"etatSiON": ["TOOGLE"],
									"etatSiOFF": [""]
								}
							}
						},
						"relais": {
							"pompe": {
								"activation": "OFF",
								"nom": "Pompe Cave",
								"pin": -1,
								"type": 0,
								"id": -1,
								"etat": "OFF",
								"timer": 0
							}
						},
						"capteursPosition": {
							"capteurNiveauBas": {
								"activation": "OFF",
								"id": -1,
								"pin": -1,
								"type": 0,	
								"etat": "OFF",	
								"relaisLie": {
									"modules": [""],
									"ids": [],
									"etatSiON": ["OFF"],
									"etatSiOFF": [""]
								}
							},
							"capteurNiveauHaut": {
								"activation": "OFF",
								"id": -1,
								"pin": -1,
								"type": 0,	
								"etat": "OFF",	
								"relaisLie": {
									"modules": [""],
									"ids": [],
									"etatSiON": ["ON"],
									"etatSiOFF": [""]
								}
							}
						}
					}
				},
				"autres": {
					"name": "Autres",
					"activation": "ON",
					"environnement": {
						"boutons": {
							"bouton1": {
								"activation": "ON",
								"id": -1,
								"pin": -1,
								"type": 0,
								"typeAction": "ON/OFF",
								"etat": "OFF",
								"relaisLie": {
									"modules": ["autres"],
									"ids": [3],
									"delaiSiON": [0],
									"delaiSiOFF": [0],
									"etatSiON": ["TOGGLE"],
									"etatSiOFF": [""]
								}
							}
						},
						"relais": {
							"relai1": {
								"activation": "ON",
								"nom": "LED Machines",
								"pin": -1,
								"type": 0,
								"id": -1,
								"etat": "OFF",
								"timer": 0,
								"publishMQTT": {
									"topic": ["cmnd/cave/lumiere/POWER1"]
								},
								"timestamp": {
									"ON": 0,
									"OFF": 0, 
									"delai": 0
								}
							},
							"relai2": {
								"activation": "ON",
								"nom": "Pompe Cuve",
								"pin": -1,
								"type": 0,
								"id": -1,
								"etat": "OFF",
								"timer": 0,
								"publishMQTT": {
									"topic": [""]
								},
								"timestamp": {
									"ON": 0,
									"OFF": 0, 
									"delai": 0
								}
							},
							"relai3": {
								"activation": "ON",
								"nom": "Lavage",
								"pin": -1,
								"type": 0,
								"id": -1,
								"etat": "OFF",
								"timer": 0,
								"publishMQTT": {
									"topic": [""]
								},
								"timestamp": {
									"ON": 0,
									"OFF": 0, 
									"delai": 0
								}
							}
						}
					}
				}
			}
		}
	}
			
	persist.parametres = parametres
	persist.save()
end

# Charge les variables & fonctions globales
log ("AUTO_EXE: Charge les fonctions globales !", LOG_LEVEL_DEBUG)
load("globalFonctions.be")
if parametres["serveur"]["web"].find("activation", "OFF") == "ON"
	load("webFonctions.be")
end
load("commandes.be")


# Gère le script BERRY global à lancer
# Charge le Driver de controle global des modules
log ("AUTO_EXE: Lance le Driver 'CONTROLE_GENERAL' !", LOG_LEVEL_DEBUG)
load("controleGlobal.be")

if parametres["serveur"]["web"].find("activation", "OFF") == "ON"
	load("gestionWeb.be")
end
