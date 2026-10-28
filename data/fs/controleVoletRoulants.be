#- NOTES Sur le controle des volets roulants
    - En mode de fonctionnement 3 (VR de garage), le volet roulant est commandé par un seul relais.
      Le relai1 (impulsion) active un moteur qui déroule ou enroule le volet roulant.
      Le relai2 n'est utilisé que pour laisser passer ou non l'impulsion du relai1 tant que le volet n'est ni totalement fermé ou ni totalement ouvert.

    - Si les délais d'ouverture et de fermeture sont bien paramétrés, le volet roulant s'arrête automatiquement à la fin du mouvement.
        Donc le relai ne se réactivera pas en fin de course.

    - Les capteurs de fin de course (ouvert/fermé) sont optionnels.
      S'ils sont utilisés:
        * le volet roulant s'arrête automatiquement lorsqu'il atteint la position haute ou basse.
        * Ils désactivent le relai2 pour empêcher l'impulsion systématique de fin de mouvement.
        * Le relai2 se réactivera 5splus tard pour permettre une nouvelle commande.
-#

# Rendu solidifiable (2026-09-27), sur le modele de controleGeneral : la classe est portee
# par le module import-able 'controleVoletRoulants'. autoexec le charge par 'import' (version en FLASH
# via load_native), plus par loadBerryFile (qui recompilait la classe en RAM).
# 'import' appelle AUTOMATIQUEMENT controleVoletRoulants_init(m), en pied de fichier.
#@ solidify:controleVoletRoulants
var controleVoletRoulants = module("controleVoletRoulants")

class CONTROLE_VR : Driver
	# Variables

    def init()
        import vrFonctions
        import string

        # Règle la communication ModBus si activée (Si Eslave ModBus)
        vrFonctions.log("CONTROLE_VR: Enregistre les taches CRON !", LOG_LEVEL_DEBUG)
        # Déclenche une action tous les jours à minuit
        #tasmota.add_cron("0 0 0 * * *", /-> self.majMinuit(), "majMinuit")

        # Configure l'ouverture des ports ModBus (différents s'il s'agit d'un maitre ou d'un esclave)
        vrFonctions.configVRByJson()
        tasmota.yield()

        #-         
            Ajoute les règles lancés selon l'étape de démarrage de la device tasmota :
        -#
        # tasmota.add_rule("Wifi", def(value, trigger, msg) vrFonctions.changementEtatDemarrage(value, trigger, msg) end, "controleVRoulant_System")
        # tasmota.add_rule("Mqtt", def(value, trigger, msg) vrFonctions.changementEtatDemarrage(value, trigger, msg) end, "controleVRoulant_Mqtt") 
        # tasmota.add_rule("System", def(value, trigger, msg) vrFonctions.changementEtatDemarrage(value, trigger, msg) end, "controleVRoulant_Wifi")
        # tasmota.add_rule("Time", def(value, trigger, msg) vrFonctions.changementEtatDemarrage(value, trigger, msg) end, "controleVRoulant_Time")

        #- Parcours tous les modules paramétrés
			* Ajoute les règles sur changement d'état des capteurs si ils sont activés : fonction=changementEtatCapteur
			* Si la règle ne fonctionne par 'add_rule()' => paramétrage de la pseudo règle dans la fonction 'majCapteursJson()' lancée toutes les secondes
					par la fonction 'every_second()'
			* Compte les devices non-virtuelles
			* Compte le nombre de devices activées par type et les range dans un tableau
			* Reset compteur des cycles & timestamp: ex(relai de pompe de cave au démarrage)
			* Détache ou attache les boutons et switchs si activés >= 1
			* Détache ou attache les interrupteurs & capteurs si activés >= 1
		-#
		var vrJSON = drivers["voletRoulants"]

        # Plusieurs volets INDEPENDANTS (2026-10-12) : chaque regle porte le numero de son volet
        # dans son identifiant, pour pouvoir retirer celles d'un seul volet (remove_rule). Les
        # declencheurs differant d'un volet a l'autre, l'ancien identifiant fixe ne provoquait pas
        # de remplacement (add_rule ne remplace qu'a declencheur ET identifiant egaux).
        # Le numero est copie dans une variable LOCALE a l'iteration, capturee par la fonction.
        # Capteur "SwitchN" : interrupteur PHYSIQUE de la carte -> regle 'SwitchN#Action'.
        # Capteur "InterrupteurN" : interrupteur VIRTUEL (esclave ModBus), sans evenement Tasmota :
        # modBus_TasmotaSlaveModBus appelle vrFonctions.capteurVirtuel a chaque changement.
        if (vrJSON.find("activation", "OFF") == "ON")
            for cle: vrJSON["environnement"]["VRs"].keys()
                var vr = vrJSON["environnement"]["VRs"][cle]
                if type(vr) != "instance"   continue    end

                if (vr.find("activation", "OFF") == "ON")
                    var idVR = vr["id"]

                    # Rules sur changement d'état des capteurs de position (physiques seulement)
                    var capteurs = vr.find("capteursPosition", false)
                    if (capteurs != false)
                        var ouvert = str(capteurs.find("capteurOuvert", ""))
                        var ferme = str(capteurs.find("capteurFerme", ""))
                        if (string.find(ouvert, "Switch") == 0)
                            tasmota.add_rule(ouvert + "#Action", def(value, trigger, msg) vrFonctions.changementEtatCapteur(value, trigger, msg, idVR, "ouverture") end, "controleVRoulant_CapteurOuvert" + str(idVR))
                        end
                        if (string.find(ferme, "Switch") == 0)
                            tasmota.add_rule(ferme + "#Action", def(value, trigger, msg) vrFonctions.changementEtatCapteur(value, trigger, msg, idVR, "fermeture") end, "controleVRoulant_CapteurFerme" + str(idVR))
                        end
                    end

                    # Rules sur changement de direction du volet roulant
                    tasmota.add_rule(string.format("Shutter%i#Direction", idVR), def(value, trigger, msg) vrFonctions.changementDirection(value, trigger, msg, idVR) end, "controleSensVRoulant" + str(idVR))
                end
            end

            # Capteur d'inclinaison (MPU6050) : seulement pour les volets qui l'activent dans le persist.
            # Sinon ni bus I2C ni minuterie : une carte sans capteur n'attend aucune donnee.
            for vr: vrFonctions.inclinaisonsActives()
                vrFonctions.log(string.format("CONTROLE_VR: Inclinaison active sur le volet %i !", vr["id"]), LOG_LEVEL_INFO)
                vrFonctions.releveInclinaison(vr)      # position reelle des le demarrage
            end
        end

		# Ajoute les commandes personnalisées
		tasmota.add_cmd('ReglageVolets', vrFonctions.reglageVolets)	
    end

    # Page d'accueil : une ligne « inclinaison » par volet dont le capteur est actif (aucune sinon)
    def web_sensor()
        import vrFonctions
        for vr: vrFonctions.inclinaisonsActives()
            tasmota.web_send_decimal(vrFonctions.ligneWebInclinaison(vr))
        end
    end
end

# Active le Driver de controle global des modules
# Publie la classe dans le module (solidification + import).
controleVoletRoulants.CONTROLE_VR = CONTROLE_VR

# init() : APPELEE AUTOMATIQUEMENT par 'import controleVoletRoulants' (be_module.c:285-296, module_init).
# Ne PAS la rappeler depuis autoexec. Reprend le code d'activation de niveau fichier d'avant.
# Publie aussi le nom GLOBAL 'vrFonctions' : les fonctions de ce module solidifie
# s'appellent entre elles par ce nom, qu'un module natif ne cree pas lui-meme.
def controleVoletRoulants_init(m)
    import global

    import vrFonctions
    global.vrFonctions = vrFonctions

    if (drivers["voletRoulants"].find("activation", "OFF") == "ON")
        for cle: drivers["voletRoulants"]["environnement"]["VRs"].keys()
            import string

            if type(drivers["voletRoulants"]["environnement"]["VRs"][cle]) != "instance"   continue    end

            try
                if (drivers["voletRoulants"]["environnement"]["VRs"][cle].find("activation", "OFF") == "ON")
                    global.controleVRoulant = m.CONTROLE_VR()
                    tasmota.add_driver(global.controleVRoulant)

                    logFonctions.log("CONTROLE_VR: Driver activé !", LOG_LEVEL_DEBUG, "volets")

                    break
                end
            except .. as error, message
                logFonctions.log(string.format("CONTROLE_VR_ERREUR: %s -> %s", error, message), LOG_LEVEL_ERREUR, "volets")
            end
        end
    end
    return m
end
controleVoletRoulants.init = controleVoletRoulants_init

# Rend le module a son import (audit S6/P3.3, 2026-10-25) : sans ce return, un controleXxx charge
# depuis le LittleFS (non solidifie) vaudrait nil et son driver ne demarrerait pas, sans erreur (piege 13).
return controleVoletRoulants
