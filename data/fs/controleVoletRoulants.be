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

var controleVRoulant

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

        if (vrJSON.find("activation", "OFF") == "ON")
            for cle: vrJSON["environnement"]["VRs"].keys()
                if type(vrJSON["environnement"]["VRs"][cle]) != "instance"   continue    end

                if (vrJSON["environnement"]["VRs"][cle].find("activation", "OFF") == "ON")
                    # Rules sur changement d'état des capteurs de position
                    if (vrJSON["environnement"]["VRs"][cle].find("capteursPosition", false) != false)
                        tasmota.add_rule(string.format("%s#Action", vrJSON["environnement"]["VRs"][cle]["capteursPosition"]["capteurOuvert"]), def(value, trigger, msg) vrFonctions.changementEtatCapteur(value, trigger, msg, vrJSON["environnement"]["VRs"][cle]["id"], "ouverture") end, "controleVRoulant_CapteurOuvert")
                        tasmota.add_rule(string.format("%s#Action", vrJSON["environnement"]["VRs"][cle]["capteursPosition"]["capteurFerme"]), def(value, trigger, msg) vrFonctions.changementEtatCapteur(value, trigger, msg, vrJSON["environnement"]["VRs"][cle]["id"], "fermeture") end, "controleVRoulant_CapteurFerme")
                    end

                    # Rules sur changement de direction du volet roulant
                    tasmota.add_rule(string.format("Shutter%i#Direction", vrJSON["environnement"]["VRs"][cle]["id"]), def(value, trigger, msg) vrFonctions.changementDirection(value, trigger, msg, vrJSON["environnement"]["VRs"][cle]["id"]) end, "controleSensVRoulant")
                end
            end
        end

		# Ajoute les commandes personnalisées
		tasmota.add_cmd('ReglageVolets', vrFonctions.reglageVolets)	
    end

    def every_second()
    end

    # Affiche les capteurs du module cuve sur la page web
    def web_sensor()
        # Rien à afficher
    end

    # Ajoute les données des capteurs de rideau de garage à la réponse JSON
    def json_append()
        # Rien à ajouter
    end
end

# Active le Driver de controle global des modules
if (drivers["voletRoulants"].find("activation", "OFF") == "ON")
    for cle: drivers["voletRoulants"]["environnement"]["VRs"].keys()
        import string

        if type(drivers["voletRoulants"]["environnement"]["VRs"][cle]) != "instance"   continue    end

        try
            if (drivers["voletRoulants"]["environnement"]["VRs"][cle].find("activation", "OFF") == "ON")
                controleVRoulant = CONTROLE_VR()
                tasmota.add_driver(controleVRoulant)

                log("CONTROLE_VR: Driver activé !", LOG_LEVEL_DEBUG)

                break
            end
        except .. as error, message
            log(string.format("CONTROLE_VR_ERREUR: %s -> %s", error, message), LOG_LEVEL_ERREUR)
        end
    end
end