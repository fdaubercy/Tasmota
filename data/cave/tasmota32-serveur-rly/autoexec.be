# Déclaration des librairies utilisées
import persist
# import partition_wizard        # Importe la librairie Partition_Wizard

# Recense toutes les variables globales
var controleGeneral = {}

# Déclaration des variables de LOG
LOG_LEVEL_ERREUR = 1
LOG_LEVEL_INFO = 2
LOG_LEVEL_DEBUG = 3
LOG_LEVEL_DEBUG_PLUS = 4

logSerial = LOG_LEVEL_INFO
logWeb = LOG_LEVEL_INFO

# Execute la fonction au démarrage
log("AUTO_EXE: Vérifie les fichiers à transférer sur la carte SD !", LOG_LEVEL_DEBUG)
import gestionFileFolder
gestionFileFolder.listeEtRepartitLesFichiers()

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

# Vérifie si le persist.json est présent et paramétré
if (persist._p != nil && persist._p.size() != 0)
    # Compile les modules
    gestionFileFolder.compileModule("/configGlobal", "ON")
    gestionFileFolder.compileModule("/configDevices", "ON")
    gestionFileFolder.compileModule("/configModules", "ON")
    gestionFileFolder.compileModule("/gestionFileFolder", "ON")
    gestionFileFolder.compileModule("/globalFonctions", "ON")
    gestionFileFolder.compileModule("/diversFonctions", "ON")
    gestionFileFolder.compileModule("/webFonctions", serveur.find("activation", "OFF"))
    gestionFileFolder.compileModule("/udpFonctions", serveur["udp"].find("activation", "OFF"))
    gestionFileFolder.compileModule("/tcpFonctions", serveur["tcp"].find("activation", "OFF"))
    gestionFileFolder.compileModule("/rangeExtenderFonctions", serveur["rangeExtender"].find("activation", "OFF"))
    # gestionFileFolder.compileModule("/modbusFonctions", drivers["ModBus"].find("activation", "OFF"))
    # gestionFileFolder.compileModule("/loRaWanFonctions", drivers["LoRaWan"].find("activation", "OFF"))
    # gestionFileFolder.compileModule("/vrFonctions")


    # Compile les modules internes à Tasmota
    # gestionFileFolder.compileModule("/leds_panel", "ON")
    # gestionFileFolder.compileModule("/partition_wizard", "ON")

    # Charge les Drivers nécessaires au fonctionnement diu module Tasmota
    # controleGeneral/LedTemoin/Web sont SOLIDIFIES : charges par 'import' (version en
    # FLASH via load_native) + init(), au lieu de loadBerryFile (qui recompile en RAM).
    # init() publie l'instance dans global.controleXxx et fait add_driver, comme avant.
    # Garder controleGeneral AVANT i2c_ads1115 (lit controleGeneral.nbIOActivesJSON).
    import controleGeneral as _ctrl
    _ctrl.init()
    import controleLedTemoin as _ctrl
    _ctrl.init()
    # gestionFileFolder.loadBerryFile("/i2c_ads1115", drivers["I2C"]["environnement"]["ADS1115"].find("activation", "OFF"), "ON")
    # gestionFileFolder.loadBerryFile("/i2c_mcp23017", drivers["I2C"]["environnement"]["MCP23017"].find("activation", "OFF"), "ON")
    # gestionFileFolder.loadBerryFile("/modBus_Conn16channels", drivers["ModBus"]["environnement"]["Conn16channels"].find("activation", "ON"), "ON")
    # gestionFileFolder.loadBerryFile("/modBus_TasmotaSlaveModBus", drivers["ModBus"]["environnement"]["TasmotaSlaveModBus"].find("activation", "ON"), "ON")
    import controleWeb as _ctrl
    _ctrl.init()
    gestionFileFolder.loadBerryFile("/controleUDP", serveur["udp"].find("activation", "OFF"), "ON")
    gestionFileFolder.loadBerryFile("/controleTCP", serveur["tcp"].find("activation", "OFF"), "ON")
    # gestionFileFolder.loadBerryFile("/controleModbus", drivers["ModBus"].find("activation", "OFF"), "ON")
    gestionFileFolder.loadBerryFile("/controleRangeExtender", serveur["rangeExtender"].find("activation", "OFF"), "ON")
    # gestionFileFolder.loadBerryFile("/controleLoRaWan", drivers["LoRaWan"].find("activation", "OFF"), "ON")
    # gestionFileFolder.loadBerryFile("/controleVoletRoulants", drivers.find("voletRoulants", {}).find("activation", "OFF"), "ON")
    gestionFileFolder.loadBerryFile("/controleDiscovery", serveur["discovery"].find("activation", "OFF"), "ON")
    # gestionFileFolder.loadBerryFile("/controleGrenier", modules.find("grenier", {}).find("activation", "OFF"), "ON")

    # Compile autoexec.be
    # gestionFileFolder.compileModule("/autoexec", "ON")
else log("AUTO_EXE: Attention, le fichier de paramétrage est absent !", LOG_LEVEL_ERREUR)
end

