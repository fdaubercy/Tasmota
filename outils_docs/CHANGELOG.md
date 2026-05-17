# Changelog
Liste tous les changements notables sur le paramétrage des scripts BERRY
Et l'ajout de fonctionnalités ou la correction de bugs

## **Voici les étapes de développement en cours :**
#### <ins>Le --/05/2026 à --h--:</ins>
    - Reparamétrage comme la fonction C++ intrasèque à Tasmota ('xdrv_63_modbus_bridge.ino' | 'TasmotaModbus.cpp'):  ✅
        * 'modbusFonctions.decrypteMSG(paramMSG, typeTitre)'
        * 'modbusFonctions.prepareTrame(paramMSG, typeMsg)'

    - Abandon de ModBusUDP: Remplacé par ModBusTCP: ✅
        * Modification des trames adaptées à la voie TCP (Cf. ligne 143 MODBUS.md): A FAIRE 🚩
        * Terminer la gestion des envois automatiques ModBus par l'esclave:  ✅
            . Cf. fonction: 'udpFonctions.lireUDP(typeComm, paramMSG)': ✅
            . A généraliser à la voie TCP: ✅
                --> fontion 'tcpFonctions.lireTCP(typeClient)'
            
        * Paramétrer les réponses automatiques de l'état des capteurs analogiques, thermometres des esclaves de cuve & de rideau:  EN COURS 🚩
            . functionCode = 0x80 | functionCode: ✅
            . Ajoute de 'StartAddress' en 1ere donnée du tableau des données envoyées en automatique: A FAIRE 🚩
            . Les états des boutons, switchs et capteurs seront envoyés automatiquement sur changement d'état: A FAIRE 🚩
            . Les valeurs des capteurs analogiques et températures seront envoyés toutes les 60s (pour éviter trop d'envoi): A FAIRE 🚩

    - Terminer la gestion du rideau de garage: A FAIRE 🚩
        * gestion des capteurs de position
        * envoi des ordres par ModBus
        * Ajout du paramétrage dans la gestion des volets roulants(module vrFonctions'):
            . Le paramètre 'Interlock selon le mode choisi.
            . Le paramétrage du bouton poussoir et de sa fonction pour le volet roulant.

#### <ins>Le 01/05/2026 à 19h15:</ins>
    - Amélioration du support Safeboot et mise à jour de la configuration de build
        * Ajout des cibles de build safeboot pour ESP32, S3, P4, P4R3 dans platformio_override.ini
        * Correction de la carte tasmota32-safeboot : esp32-solo1 → esp32
        * Protection de USE_SENDMAIL et désactivation des hooks pré-build en environnement safeboot
        * Incrémentation de CFG_HOLDER à 1262, désactivation de USE_TASMESH sur tous les environnements
        * Mise à jour de sdkconfig.defaults avec la configuration complète ESP-IDF 5.5.4
        * Détection de l'environnement safeboot dans pre_utilitaires_platformio.py avec contournement
        automatique des fonctions et suppression de USE_CONFIG_OVERRIDE
        * Ajout de variants/tasmota/esp32/pins_arduino.h pour la variante ESP32
        * Synchronisation de tasmota_defines_for_berry avec FIRMWARE_MINIMAL et traductions EN
        * Suppression de CMakeLists.txt et des binaires safeboot obsolètes

#### <ins>Le 18/04/2026 à 21h08:</ins>
    - Ajout d'un Driver BERRY ': 'controleLedTemoin.be'
        * controle une LED selon les données paramétrées en json

#### <ins>Le 18/04/2026 à 12h40:</ins>
    - Correction du module 'vrFonctions'
        * Dans la fonction 'vrFonctions.configVRByJson':
            . Correction d'un bug dans la partie de paramètrage des commandes par boutons choisies

    - Reparamétrage comme la fonction C++ intrasèque à Tasmota ('xdrv_63_modbus_bridge.ino' | 'TasmotaModbus.cpp'):  ✅
        * 'modbusFonctions.decrypteMSG(paramMSG, typeTitre)'
        * 'modbusFonctions.prepareTrame(paramMSG, typeMsg)'

    - Abandon de ModBusUDP: Remplacé par ModBusTCP: ✅
        * Modification des trames adaptées à la voie TCP (Cf. ligne 143 MODBUS.md): A FAIRE 🚩
        * Terminer la gestion des envois automatiques ModBus par l'esclave:  ✅
            . Cf. fonction: 'udpFonctions.lireUDP(typeComm, paramMSG)': ✅
            . A généraliser à la voie TCP: ✅
                --> fontion 'tcpFonctions.lireTCP(typeClient)'
            
        * Paramétrer les réponses automatiques de l'état des capteurs analogiques, thermometres des esclaves de cuve & de rideau:  EN COURS 🚩
            . functionCode = 0x80 | functionCode: ✅
            . Ajoute de 'StartAddress' en 1ere donnée du tableau des données envoyées en automatique: A FAIRE 🚩
            . Les états des boutons, switchs et capteurs seront envoyés automatiquement sur changement d'état: A FAIRE 🚩
            . Les valeurs des capteurs analogiques et températures seront envoyés toutes les 60s (pour éviter trop d'envoi): A FAIRE 🚩

    - Terminer la gestion du rideau de garage: A FAIRE 🚩
        * gestion des capteurs de position
        * envoi des ordres par ModBus
        * Ajout du paramétrage dans la gestion des volets roulants(module vrFonctions'):
            . Le paramètre 'Interlock selon le mode choisi.
            . Le paramétrage du bouton poussoir et de sa fonction pour le volet roulant.

#### <ins>Le 18/04/2026 à 10h01:</ins>
    - Ajout du paramètre '-D UPDATE_IDF55_PLATFORM' dans 'platformio_tasmota_cenv.ini':
        Permet si l'option est activée de lancer la vérification de la version de platform utilisée pour la compilation de tasmota pour ESP32-P4
        Evite les erreurs de compilation sur certains PC Windows
    - Corrections d'erreurs dans les fichiers html perso

    - Création du module 'tasmota32s3-etage2-grenier': Trappe de grenier du 2eme étage  ✅
    - Reparamétrage comme la fonction C++ intrasèque à Tasmota ('xdrv_63_modbus_bridge.ino' | 'TasmotaModbus.cpp'):  ✅
        * 'modbusFonctions.decrypteMSG(paramMSG, typeTitre)'
        * 'modbusFonctions.prepareTrame(paramMSG, typeMsg)'

    - Abandon de ModBusUDP: Remplacé par ModBusTCP: ✅
        * Modification des trames adaptées à la voie TCP (Cf. ligne 143 MODBUS.md): A FAIRE 🚩
        * Terminer la gestion des envois automatiques ModBus par l'esclave:  ✅
            . Cf. fonction: 'udpFonctions.lireUDP(typeComm, paramMSG)': ✅
            . A généraliser à la voie TCP: ✅
                --> fontion 'tcpFonctions.lireTCP(typeClient)'
            
        * Paramétrer les réponses automatiques de l'état des capteurs analogiques, thermometres des esclaves de cuve & de rideau:  EN COURS 🚩
            . functionCode = 0x80 | functionCode: ✅
            . Ajoute de 'StartAddress' en 1ere donnée du tableau des données envoyées en automatique: A FAIRE 🚩
            . Les états des boutons, switchs et capteurs seront envoyés automatiquement sur changement d'état: A FAIRE 🚩
            . Les valeurs des capteurs analogiques et températures seront envoyés toutes les 60s (pour éviter trop d'envoi): A FAIRE 🚩

    - Terminer la gestion du rideau de garage: A FAIRE 🚩
        * gestion des capteurs de position
        * envoi des ordres par ModBus
        * Ajout du paramétrage dans la gestion des volets roulants(module vrFonctions'):
            . Le paramètre 'Interlock selon le mode choisi.
            . Le paramétrage du bouton poussoir et de sa fonction pour le volet roulant.

#### <ins>Le 18/02/2026 à 04h36 :</ins>
    - Création du module 'tasmota32s3-etage2-grenier': Trappe de grenier du 2eme étage  ✅
    - Reparamétrage comme la fonction C++ intrasèque à Tasmota ('xdrv_63_modbus_bridge.ino' | 'TasmotaModbus.cpp'):  ✅
        * 'modbusFonctions.decrypteMSG(paramMSG, typeTitre)'
        * 'modbusFonctions.prepareTrame(paramMSG, typeMsg)'

    - Abandon de ModBusUDP: Remplacé par ModBusTCP: ✅
        * Modification des trames adaptées à la voie TCP (Cf. ligne 143 MODBUS.md): A FAIRE 🚩
        * Terminer la gestion des envois automatiques ModBus par l'esclave:  ✅
            . Cf. fonction: 'udpFonctions.lireUDP(typeComm, paramMSG)': ✅
            . A généraliser à la voie TCP: ✅
                --> fontion 'tcpFonctions.lireTCP(typeClient)'
            
        * Paramétrer les réponses automatiques de l'état des capteurs analogiques, thermometres des esclaves de cuve & de rideau:  EN COURS 🚩
            . functionCode = 0x80 | functionCode: ✅
            . Ajoute de 'StartAddress' en 1ere donnée du tableau des données envoyées en automatique: A FAIRE 🚩
            . Les états des boutons, switchs et capteurs seront envoyés automatiquement sur changement d'état: A FAIRE 🚩
            . Les valeurs des capteurs analogiques et températures seront envoyés toutes les 60s (pour éviter trop d'envoi): A FAIRE 🚩

    - Terminer la gestion du rideau de garage: A FAIRE 🚩
        * gestion des capteurs de position
        * envoi des ordres par ModBus
        * Ajout du paramétrage dans la gestion des volets roulants(module vrFonctions'):
            . Le paramètre 'Interlock selon le mode choisi.
            . Le paramétrage du bouton poussoir et de sa fonction pour le volet roulant.

#### <ins>Le 14/02/2026 à 01h38 :</ins>
    - Création du module 'tasmota32s3-etage2-grenier': Trappe de grenier du 2eme étage
    - Ajout du paramétrage dans la gestion des volets roulants(module vrFonctions'):
        * Le paramètre 'Interlock selon le mode choisi.
        * Le paramétrage du bouton poussoir et de sa fonction pour le volet roulant.
    - Abandon de ModBusUDP: Remplacé par ModBusTCP: ✅
        * Terminer la gestion des envois automatiques ModBus par l'esclave:  ✅
            . Cf. fonction: 'udpFonctions.lireUDP(typeComm, paramMSG)': ✅
            . A généraliser à la voie TCP: ✅
                --> fontion 'tcpFonctions.lireTCP(typeClient)'
        * Paramétrer les réponses automatiques de l'état des capteurs analogiques, thermometres des esclaves de cuve & de rideau:  EN COURS 🚩
            . functionCode = 0x80 | functionCode: ✅
            . Ajoute de 'StartAddress' en 1ere donnée du tableau des données envoyées en automatique
            . Les états des boutons, switchs et capteurs seront envoyées automatiquement sur changement d'état
            . Les valeurs des capteurs analogiques et températures seront envoyées toutes les 60s (pour éviter trop d'envoi)
    - Terminer la gestion du rideau de garage: A FAIRE 🚩
        * gestion des capteurs de position
        * envoi des ordres par ModBus

#### <ins>Le 25/01/2026 à 10h25 :</ins>
    - Paramétrer la fonction 'modBus_TasmotaSlaveModBus.recupereReponseModBus(value, trigger, msg) déclenchée sur réponse d'un esclave par le Maitre: ✅
    - Abandon de ModBusUDP: Remplacé par ModBusTCP: ✅
        * Terminer la gestion des envois automatiques ModBus par l'esclave: EN COURS 🚩
            . Cf. fonction: 'udpFonctions.lireUDP(typeComm, paramMSG)': ✅
            . A généraliser à la voie série et TCP: EN COURS 🚩
                --> fontion 'tcpFonctions.lireTCP(typeClient)'
        * Paramétrer les réponses automatiques de l'état des capteurs analogiques, thermometres des esclaves de cuve & de rideau:  A FAIRE 🚩
            . functionCode = 0x80 | functionCode
            . Ajoute de 'StartAddress' en 1ere donnée du tableau des données envoyées en automatique
            . Les états des boutons, switchs et capteurs seront envoyées automatiquement sur changement d'état
            . Les valeurs des capteurs analogiques et températures seront envoyées toutes les 60s (pour éviter trop d'envoi)
    - Terminer la gestion du rideau de garage: A FAIRE 🚩
        * gestion des capteurs de position
        * envoi des ordres par ModBus

#### <ins>Le 19/01/2026 à 19h53 :</ins>
    - Abandon de ModBusUDP: Remplacé par ModBusTCP: A FAIRE 🚩
    - Pour les messages ModBus:
        * Revoir la fonction 'globalFonctions.changementEtatCapteur(value, trigger, msg, moduleCapteur, cleBouton)':  ✅
        * Revoir la fonction 'controleGlobal.set_power_handler(cmd, idx)':  ✅
    - Reparamétrage des commandes ModBus envoyées : EN COURS 🚩
        * Pour la fonction 0x05 'ECRITURE_COIL_UNIQUE':  ✅
            . Pour les relais:  ✅
        * Pour la fonction 0x06 'ECRITURE_REGISTRE_UNIQUE':  ✅
            . Pour les relais temporisés:  ✅
        * Pour la fonction 0x10 'ECRITURE_REGISTRES_HOLDER':  ✅
            . Pour les leds WS2812B (couleur, saturation, luminosite):  ✅
    - Terminer la gestion des envois automatiques ModBus par l'esclave: EN COURS 🚩
        * la fonction 'globalFonctions.changementEtatCapteur(value, trigger, msg, moduleCapteur, cleBouton)': 0x80 & fonction ModBus  ✅
        * Cf. fonction: 'udpFonctions.lireUDP = def(typeComm, paramMSG)'
        * A généraliser à la voie série et TCP

#### <ins>Le 19/01/2026 à 06h23 :</ins>
    - Adaptation du dépot au nouveau fork
    - Abandon de ModBusUDP: Remplacé par ModBusTCP: A FAIRE 🚩
    - Pour les messages ModBus:
        * Revoir la fonction 'globalFonctions.changementEtatCapteur(value, trigger, msg, moduleCapteur, cleBouton)': A FAIRE 🚩
        * Revoir la fonction 'controleGlobal.set_power_handler(cmd, idx)': A FAIRE 🚩
    - Reparamétrage des commandes ModBus envoyées : EN COURS 🚩
        * Pour la fonction 0x05 'ECRITURE_COIL_UNIQUE': A FAIRE 🚩
            . Pour les relais:  A FAIRE 🚩
        * Pour la fonction 0x06 'ECRITURE_REGISTRE_UNIQUE': A FAIRE 🚩
            . Pour les relais temporisés:  A FAIRE 🚩
        * Pour la fonction 0x10 'ECRITURE_REGISTRES_HOLDER': A FAIRE 🚩
            . Pour les leds WS2812B (couleur, saturation, luminosite): A FAIRE 🚩
            
#### <ins>Le 18/01/2026 à 09h14 :</ins>
    - Abandon de ModBusUDP: Remplacé par ModBusTCP: A FAIRE 🚩
    - Pour les messages ModBus:
        * Revoir la fonction 'globalFonctions.changementEtatCapteur(value, trigger, msg, moduleCapteur, cleBouton)': A FAIRE 🚩
        * Revoir la fonction 'controleGlobal.set_power_handler(cmd, idx)': A FAIRE 🚩
    - Reparamétrage des commandes ModBus envoyées : EN COURS 🚩
        * Pour la fonction 0x04 'LECTURE_REGISTRES_ENTREES':
            . Pour les compteurs: ✅
            . Pour les thermomètres DS18B20 & DHT22: ✅
            . Pour les entrées analogiques: ✅
        * Pour la fonction 0x02 'LECTURE_ENTREES_DISCRETES':
            . Pour les interrupteurs et capteurs: ✅
        * Pour la fonction 0x05 'ECRITURE_COIL_UNIQUE': A FAIRE 🚩
            . Pour les relais:  A FAIRE 🚩
        * Pour la fonction 0x06 'ECRITURE_REGISTRE_UNIQUE': A FAIRE 🚩
            . Pour les relais temporisés:  A FAIRE 🚩
        * Pour la fonction 0x10 'ECRITURE_REGISTRES_HOLDER': A FAIRE 🚩
            . Pour les leds WS2812B (couleur, saturation, luminosite): A FAIRE 🚩
    - Ajout de la commande: 'ReglageModbus ActivationReponseCMD ON|OFF': (Des)active la réponse de l'esclave aux commandes ModBus ✅

#### <ins>Le 11/01/2026 à 06h05 :</ins>
    - Ajout du fichier 'CHANGELOG.md': Liste les modifications effectuées
    - Mise à plat des communications ModBus: ✅
        * Refaire l'ensemble des scripts BERRY pour controleModBus et modbusFonctions: ✅
        * Refaire les scripts BERRY pour les Drivers 'modbus_TasmotaSlaveModBus: ✅
    - Abandon de ModBusUDP: Remplacé par ModBusTCP: A FAIRE 🚩
    - Pour les modules esclaves ModBus:
        * Modification de la fonction 'globalFonctions.changementEtatWS2812()': ✅
            Pour les variations de Dimmer & HSBColor: ✅

#### <ins>Le 04/01/2026 à 15h33 :</ins>
    - Mise à plat du fichier MODBUS.md (déplacé dans le dépot dans le dossier '/outils_docs/Aide/')
    - Dans le driver 'controleDiscovery':
        * Ajout de la fonction 'ReglageDiscovery'
    - Déplacement des paramètres du module Discovery en _persist.json:
        * serveur["discovery"]
    - Gestion ModBus:
        * Arrêt de la fonction timer de récupération de la valeur des capteurs toutes les 60s
        * Conservation de la fonction de pulling au démarrage du module Maitre
        * Pour les modules esclaves:
            . Ils peuvent désormais émettre l'état du capteur (interrupteurs, boutons, capteur d'état) en cas de modification vers le maitre: 
                -> Modification de la fonction 'globalFonctions.changementEtatCapteur()':
                        Pour les interrupteurs, capteurs & boutons ✅
                        Pour les compteurs: A FAIRE ✅
                        Pour les capteurs de T°, entrées analogiques (ADS1115): Le maitre continue a rquêter à intervalle régulier car ces valeurs changent trop souvent ✅

                        Répondre à la question 'Comment connaitre l'ID du capteur chez le maitre ??' dans cette fonction :  ✅
                            !! SOLUTION:
                                Les numéros d'identification des commandes restent les mêmes que selon le protocole officiel
                                Concerne les envois ModBus des esclaves sur modifications de toutes sortes de capteurs, entrées, sorties
                                On identifie ce type d'envoi automatique de l'esclave en mettant le bit 8 (bit de poids fort) à 1: ✅
                                    ex: la commande "Écriture de plusieurs registres (Write Multiple Registers)" = 0x10 (0b0001 0000)
                                            prend comme valeur -> 0x90 (0b1001 0000)
                                    La formule de transformation est réalisé par une opération bit à bit: 0x80(0b1000 0000) OR 0x10(0b0001 0000) = 0x90(0b1001 0000)
                                    La fonction OR bit à bit = '|' en codage BERRY
                                Si le bit8=1: 
                                    le maitre reconnait que c'est un message automatique d'un esclave si: fonction (0x90) AND 0x80 = 0x80
                                    le maitre récupère la valeur de la fonction réelle: fonction reelle (0x10) = fonction (0x90) AND 0x7F = 0x10

                -> Modification de la fonction 'globalFonctions.changementEtatWS2812()': A FAIRE 🚩
                        Pour les variations de Dimmer & HSBColor: A FAIRE 🚩
    - Mise en place des communications TCP Asynchrones:
        * Création du Driver 'controleTCP': ✅
        * Création du Module 'tcpFonctions': ✅

#### <ins>Le 23/12/2025 à 12h29 :</ins>
    - Dans le Driver 'controleDiscovery.be': Correction de la formule de calcul du port pour les boutons de lien vers les devices Tasmota connectés au réseau

#### <ins>Le 23/12/2025 à 09h25 :</ins>
    - Test connexion tcp async impossible entre un maitre et un esclave RangeExtender
    - Création du Driver 'controleES8311.be': pour tenter de faire parler le haut-parleur de la sortie I2S -> OK
        * Cf.discussion en cours: https://github.com/arendst/Tasmota/discussions/16226#discussioncomment-15318199
    
#### <ins>Le 22/12/2025 à 01h52 :</ins>
    - Le bouton vert de 'configuration des module' est décalé sur la page 'Tools'
    - Création du module 'controleDiscovery.be':
        * gère les modules Tasmota connectés sur le réseau Wifi local
        * Affiche un bouton par module Tasmota connecté: 
            . sur l'interface principale
            . permet de retrouver le lien facilement
        * Retrouve les modules par le message MQTT emis sur le topic 'tasmota/discovery/+/config' par chaque module Tasmota
            . subscribe 'tasmota/discovery/+/config' 
            . enregistre le payload dans un fichier '/json/discovery.json'
    - Ajout du paramètre 'serveur["pageDiscovery"]' pour permettre l'affichage de la page et du bouton 'Discovery.html'

#### <ins>Le 20/12/2025 à 09h47 :</ins>
    - Dans le module 'rangeExtenderFonctions':
        * Correction de la fonction 'rangeExtenderFonctions.afficheBoutonsModulesEsclaves()':
            . Affichage des boutons permettant d'ouvrir la page web des modules esclaves associés
    - Dans le module 'udpFonctions':
        * Correction de la fonction 'udpFonctions.reglageUDP':
            . Le maitre envoie le timestamp dès que l'esclave se présente 'ImAlive' pour que maitres & esclaves soient réglés sur la même heure

#### <ins>Le 20/12/2025 à 06h10 :</ins>
    - Pour le Driver 'controleUDP' et le module 'udpFonctions':
        * Paramétrage de ModBusUDP finalisé

#### <ins>Le 18/12/2025 à 08h44 :</ins>
    - Mise à jour des commandes personnalisées de réglage UDP, ModBus, SlaveModBus
        * ReglageModbus logActivation OFF
        * ReglageModbus envoiMessage 0x01 TEST

        * ReglageSlaveModBus1 logActivation OFF   => Active ou désactive les logs du module
        *  ReglageSlaveModBus1 id 0x02   => Change le l'adresse ModBus de l'esclave ModBus_TasmotaSlaveModBus1
        * ReglageConn16Channel logActivation OFF

        * ReglageUDP logActivation OFF
        * ReglageUDP envoiUniCast 192.168.0.43 Salut Ca gaz ! OU ReglageUDP envoiUniCast 192.168.4.3 Salut Ca gaz !
        * ReglageUDP envoiMultiCast Salut Ca gaz ! OU ReglageUDP envoiMultiCast 192.168.4.3 Salut Ca gaz !
        * ReglageUDP forceEnvoiParams ON

#### <ins>Le 14/12/2025 à 11h11 :</ins>
    - Gestion des communications ModBus en UDP: Terminé
        * Utilisation de l'UDP MultiCast pour les communications ModBus UDP & RangeExtender
        * Car l'utilisation des communications TCP ne fonctionnent pas avec le RangeExtender

#### <ins>Le 09/12/2025 à 20h24 :</ins>
    - Correction de la fonction 'modbusFonctions.envoiMsgModbus(paramMSG)':
        * Bug de gestion du flag 'modbusFonctions.attenteReponse'
        * Probleme 'tasmota.set_timer()' avec l'ESP32-P4: remplacé pour l'instant par 'tasmota.add_cron()'
    - Ajout du paramètre activant la transmission UDP d'ordre et réponses ModBus, en _persist.json: 'drivers["ModBus"]["BridgeUDP"]'
        * les commandes ou réponse ModBus sont toutes envoyées en MultiCast sur port UDP

#### <ins>Le 07/12/2025 à 23h35 :</ins>
    - Réfection complète du Driver 'controleUDP' et du module 'udpFonctions':
        * Correction d'un bug sur l'envoi en MultiCast sur le Maitre RangeExtender

#### <ins>Le 01/12/2025 à 07h00 :</ins>
    - Synchronisation du dépot personnel avec le dépot officiel
    - Définition terminée dans 'user_config_override.ini', pour le profil: 'FIRMWARE_ESP32P4_SERVEUR_GARAGE_MODBUS'
    - Fichier du firmware de l'ESP32-C6 Hosted, enregistré dans 'build_output/firmware/network_adapter_esp32c6.bin':
        * Commande pour mettre à jour l'ESP32-C6 de l'ESP32-P4 Wifi6: HostedOTA https://ota.tasmota.com/tasmota32/coprocessor/network_adapter_esp32c6.bin
        * Update du fichier de l'HostedMCU: HostedLoad https://ota.tasmota.com/tasmota32/coprocessor/network_adapter_esp32c6.bin
    - Adaptation du fichier 'user_config_override.h' à l'ESP32-P4
    - Correction d'un bug sur la fonction log en BERRY, la fonction de paramétrage du niveau des logs Serial et Web
    - Révision du programme python 'outils_docs\scripts_python\pre_utilitaires_platformio.py':
        * fonction regex pour transformer l'appelation de l'environnement en un chemin de dossier a téléverser:
            ex: tasmota32p4-garage-serveur-modbus -> data/garage/tasmota32p4-serveur-modbus
        * permet le classement des fichiers BERRY:
            . dossiers pourtous les modules: 'fs, jsson, sd'
            . dossiers spécifiques àchaque module: exemple -> data/garage/tasmota32p4-serveur-modbus
    - Gestion descommunications UDP: Driver 'controleUDP' et module 'udpFonctions':
        * Ajout de la capacité à recevoir des messages UDP UniCast & MultiCast 
        * Ajout de la capacité à envoyer des messages UDP UniCast & MultiCast (souvent Maitre -> tous les esclaves)

#### <ins>Le 23/11/2025 à 14h24 :</ins>
    - Ajout su script 'sauvegarder_fichiers.py': réalise une sauvegarde datee des fichiers importants du dossier Tasmota
    - Réintégration réussie des paramètres dans le fichier 'user_config_override.ini' pour :
        * la partie 'SECTION1' sauf les mots de passe des réseau wifi dans 'user_config_override.ini' pour l'ESP32-P4
        * la partie 'SECTION2'
        * la partie 'USER_CONFIG_OVERRIDE_DEBUG'
        * la partie 'USER_CONFIG_OVERRIDE_SAFE_GUARD'
        * la partie 'USER_CONFIG_OVERRIDE_POST_PROCESS'
        * la partie 'USER_CONFIG_OVERRIDE_MUTUAL_EXCLUDE'
        * la partie 'USER_CONFIG_OVERRIDE_POST_PROCESS_COMPILE_OPTIONS'
        * la partie 'USER_CONFIG_OVERRIDE_FIRMWARES_PERSONNALISES'
        * la partie 'USER_CONFIG_OVERRIDE_PROFILING'
    - Modification du script de paramétrage personnalisés de Platformio: extra_scripts: 'outils_docs/scripts_python/pre_utilitaires_platformio.py'
        . Modification du paramètre dans 'platformio_override.ini':
                extra_scripts           =   pre:outils_docs/scripts_python/pre_utilitaires_platformio.py
                                            ${esp32_defaults.extra_scripts}
    - Ajout du script de sauvegarde et de restauration des fichiers Platformio + Tasmota important lors de refonte du dépot Github: 'outils_docs/scripts_python/sauvegarde_restaure_gui_final.py'
        . Utilise un GUI en python

#### <ins>Le 22/11/2025 à 07h50 :</ins>
    - Mise au point des scripts pour la gestion des fichiers à uploader

#### <ins>Le 19/11/2025 à 08h16 :</ins>
    - Refonte du dépot Fork Tasmota suite à la mise à jour de Tasmota

#### <ins>Le 15/11/2025 à 16h31 :</ins>
    - Création du dossier 'outils_docs', contenant:
        * Le fichier des règles de PEC des ports USB: 'outils_docs/99-platformio-udev.rules'

    - Ajout du fichier 'outils_docs/99-platformio-udev.rules':
        * A copier: sudo sudo cp 'data/99-platformio-udev.rules/99-platformio-udev.rules' /etc/udev/rules.d/99-platformio-udev.rules
        * Permet la reconnaissance des ports USB

        * Enregistrer l'utilisateur dans le groupe 'dialout': sudo usermod -a -G dialout fdaubercy
        * Modifier les droits lecture/ecriture sur ces ports USB: sudo chmod 777 /dev/ttyACM*

    - Nouvelles fonctions:
        * Création du fichier 'tools/gen_tapp.py': Création d'archives TAPP à partir de scripts BERRY
        * Mise à jour des scripts dans les dossiers 'tools' & 'pio-tools'
        * Ajout de la fonction 'def increment_config_holder()' dans 'tools/custom_target.py' pour incrémenter le 'CFG_HOLDER' à chaque compilation
        * Ajout de la fonction 'def change_data_dir_in_platformio_ini(path_tasmota_cenv, new_data_dir)' dans 'tools/custom_target.py':
                pour paramétrer le dossier contenant les fichiers à télécharger lors de la compilation
        * Mise à jour du fichier 'platformio_tasmota_cenv.ini':
            - Permet de changer le dossier contenant les fichiers berry spécifiques à chaque module Tasmota:
                [platformio]
                data_dir = data-tasmota32p4-wifi6
        
    - Test: OK
        * Mise à jour du fichier 'outils_docs/.gitignore'
        * Mise à jour du fichier 'outils_docs/README.md'
        * Mise à jour du dossier 'partitions'
        * Mise à jour du dossier 'boards'
        * Ajout des scripts pythons personnels
        * Mettre à jour la variable pour la gestion des ecritures de bouton
        * Ajout du dossier data/
        * Mise à jour du fichier 'tasmota/user_config_override.h'
        * renommer les commentaires des scripts en francais dans 'tools' & 'pio-tools'
        * Mise à jour du fichier 'platformio_tasmota_cenv.ini':
            - Permet de changer le dossier contenant les fichiers berry spécifiques à chaque module Tasmota
        * Mettre à jour la variable permettant de paramétrer une téléperiode < 10s
        * Tester comment classer les dossier berry pour permettre la fonction 'Build FileSystem Image'
        
#### <ins>Le 13/11/2025 à 12h20 :</ins>
    - Ajout du script de création des fichiers archives *.tapp
        * le script est dans le dossier 'tools': tools\gen_tapp.py

#### <ins>Le 13/11/2025 à 04h26 :</ins>
    - Compilation des firmwares personnalisés pour le garage
    - Tests sur l'envoi de commandes ModBus par MQTT

#### <ins>Le 12/11/2025 à 15h46 :</ins>
    - Mise à jour du firmware et des fichiers binaires de configuration pour les appareils Tasmota ESP32S3 (variantes Modbus)
        Ce commit met à jour tous les fichiers binaires de firmware (.bin, .factory.bin) et de configuration (.map.gz) générés pour les variantes Modbus des Tasmota ESP32S3 Sensors Cuve, Rideau Garage et Server Garage. Ces modifications correspondent à une nouvelle version du firmware et de ses fichiers de configuration associés, garantissant ainsi la disponibilité du code et de la configuration les plus récents pour toutes les cibles matérielles prises en charge.

    - Correction du format de journalisation dans le pilote Berry MODBUS_TASMOTA_SLAVE
        Ce commit corrige le format de journalisation dans la classe du pilote Berry MODBUS_TASMOTA_SLAVE. La correction garantit que l'identifiant du périphérique est correctement concaténé dans le message de journalisation lors de la transmission des requêtes de changement d'état Modbus.

    - Ajout d'une cible serveur OTA personnalisée aux outils Python de PlatformIO
        Introduit la fonction « esp32_creer_server » et une cible PlatformIO personnalisée correspondante dans pio-tools/custom_target.py, permettant ainsi la mise en place d'un serveur de fichiers OTA pour les mises à jour Tasmota ESP32S3. Cette fonction utilise le serveur HTTP intégré de Python et peut être appelée via PlatformIO.

    - Mise à jour des instructions d'utilisation des scripts espupload avec de nouveaux exemples de serveur OTA
        Amélioration de la documentation en haut des fichiers espupload.py et espupload_legacy.py afin d'inclure de nouveaux exemples d'utilisation, reflétant les points de terminaison et les conventions les plus récents pour le chargement du firmware via le serveur OTA.

    - Mise à jour de l’adresse et du point de terminaison du serveur OTA par défaut dans espupload_legacy.py
        Modifie l’adresse IP du serveur OTA par défaut à 192.168.0.43 et met à jour le chemin du point de terminaison à « /u2?fsz » dans espupload_legacy.py, conformément à la dernière configuration du système OTA.

    - Amélioration de la clarté et de la localisation des messages relatifs à la création du système de fichiers dans le script post-compilation ESP32
        Amélioration de la messagerie dans pio-tools/post_esp32.py pour la création du système de fichiers après la compilation du firmware : traduction des messages en français et clarification des actions effectuées, telles que le signalement des fichiers manquants, le renommage et les échecs de téléchargement.

    - Définition de la propriété data_dir dans la configuration PlatformIO
        Ajout de la propriété « data_dir = data » au fichier platformio.ini, définissant l’emplacement du répertoire de données du projet pour les opérations PlatformIO.

    - Mise à jour de upload_port vers le point de terminaison OTA dans la configuration de remplacement PlatformIO
        Modification du paramètre upload_port dans platformio_override.ini pour utiliser le nouveau point de terminaison OTA (192.168.0.43/u2?fsz), facilitant ainsi les mises à jour du firmware via le réseau.

    - Mise à jour de la configuration du script de téléchargement OTA MQTT pour le sujet et les identifiants du garage
        Mise à jour du fichier tools/mqtt-file/upload-ota.py pour utiliser une nouvelle adresse de courtier MQTT, un nouveau mot de passe, un nouveau sujet et un nouveau chemin d’accès au firmware, reflétant les dernières informations de déploiement pour le périphérique Modbus Serveur Garage.

#### <ins>Le 11/11/2025 à 23h19 :</ins>
    - Modification des règles liées aux températures & entrées analogiques:
        * Dans le Driver 'controleGarage':  
            . Dans la fonction 'def json_append()': suppression de l'ajout en json Teleperiod des données de température

        * Dans le module 'configDevices':
            . Dans la fonction 'configDevices.configDevicesByRules = def(modules, nbIOActivesJSON)':
                Les règles des températures virtuelles & compteurs virtues & entrées analogiques virtuelles sont déclenchées par 'Tele-': soit une fréquence = Télépériode = 300ms

        * Dans le Driver 'modBus_TasmotaSlaveModBus':
            . Dans la fonction 'recupereReponseModBus(value, trigger, msg)':
                Ajout dans le json Teleperiod des valeurs de DHT22(Température & Humidite)
                Ajout dans le json Teleperiod des compteurs
            . Dans la fonction 'changementEtatDemarrage(value, trigger, msg)':
                La demande ModBus pour récupérer les valeurs des thermomètres & compteurs & entrées analogiques virtuelles sera réalisé / TéléPeriod (300ms par défaut)

        * Dans le module 'modbusFonctions':
            . Dans la fonction 'modbusFonctions.executeCmdModbus(paramMSG)': envoie la T°+Hum si DHT22
            . Dans la fonction 'modbusFonctions.executeCmdModbus(paramMSG)': envoie la valeur des compteurs

            A TERMINER:
            . Dans la fonction 'modbusFonctions.envoiMsgModbus(paramMSG)':
                dans la section 'if (paramMSG["FunctionName"] == "LECTURE_REGISTRES_ENTREES")':
                    -> compter le nombre de valeurs pour retourner les 2 floats si DHT22
            . Dans 'configDevices.configDevicesByRules(modules, nbIOActivesJSON)': Paramétrer les règles des switchs, capteurs et interrupteurs virtuels

#### <ins>Le 09/11/2025 à 18h07 :</ins>
    - Modification du json ajouté au json 'Teleperiod' lors de la réception d'un message ModBus TasmotaSlaveModBus
    - Réfection des règles paramétrés sur modification des devices dans 'configDevices.configDevicesByRules = def(modules, nbIOActivesJSON)'

#### <ins>Le 31/10/2025 à 07h54 :</ins>
    - Dans le Driver 'controleGarage':
        * Dans la fonction 'init()': Ajout de la fonction recurrente d'envoi d'ordre ModBus pour récupérer l'état d'interrupteurs virtuels
        * Dans la fonction 'modbusFonctions.envoiMsgModbus()':
            . Ajout de la gestion de l'envoi de la trame pour: if (paramMSG["FunctionName"] == "LECTURE_ENTREES_DISCRETES")
        * Dans la fonction 'modbusFonctions.executeCmdModbus()': 
            . Ajout de la gestion de la réponse ModBus à envoyer: if(paramMSG["FunctionName"] == "LECTURE_ENTREES_DISCRETES")
        * Dans la fonction 'modbusFonctions.lireMsgModbus()': 
            . Ajout de le tri des éléments de la demande pour: paramMSG["ModbusReceived"]["FunctionName"] == "LECTURE_ENTREES_DISCRETES"

    - Pour les commandes ModBus: Chaque commande attend que la réponse à la commande précédente soit reçue:
        * Flag: modbusFonctions.attenteReponse = false

    - Ajout de l'environnement de travail pour les ESP32-P4:
        * Dans 'platformio_tasmota_cenv.ini'
        * Dans 'platformio_override.ini'

#### <ins>Le 26/10/2025 à 18h36 :</ins>
    - Mise à jour complète des Drivers 'controleRangeExtender' & 'controleUDP'

#### <ins>Le 05/10/2025 à 19h07 :</ins>
    - Ajout en persist.json des pramètres d'un compteur
    - Ajout du téléchargement des extensions lors de la compilation du programme
        * dans le module 'gestionFileFolder.be':
            . ajout du dossier caché '.extensions'
            . transfère des fichiers .tapp dans le dossier caché '.extensions'
    - Correction de la détection d'activation du bus I2C dans le firmware:
        * Correction des modules: 'i2c_ads1115.be', 'i2c_mcp23017.be' & 'configDevices.be'

#### <ins>Le 30/07/2025 à 04h12 :</ins>
    - Dans le module 'controleGarage':
        * Ajout dans la fonction json_append(): Mis à jour en json teleperiod des valeurs de capteurs analogiques virtuels & thermometres virtuels
        * Ajout du compte des compteurs réels et virtuels en 'nbIOActives.json'
        * Dans le module 'configDevices':
         . Paramétrage de l'affichage de la valeur des compteurs: affichageWebSensor en json

#### <ins>Le 28/07/2025 à 08h05 :</ins>
    - Correction de diverses bugs
    - Dans autoexec.be: modification et suppression du mot 'var' sur les variables globales de LOG pour les rendre globales

#### <ins>Le 12/05/2025 à 06h05 :</ins>
    - Dans 'user_config_override.h':
        * Activation de la passarelle LoRaWan: #define USE_LORAWAN_BRIDGE
    - Ajout des paramètres en '_persist.json':
        * drivers->LoRaWan
    - Ajout du Driver: 'controleLoRaWan.be' & du module: 'loRaWanFonctions.be': 
        * En attente de réception des modules SX1676

#### <ins>Le 08/05/2025 à 08h40 :</ins>
    - Dans le module 'modBus_TasmotaSlaveModBus':
        * Ajout des commandes personnalisées: 
            . 'reglageSlaveModBus(cmd, idx, payload, payload_json)': pour régler le niveau de logs de ce module
                ex: ReglageSlaveModBus logActivation OFF
        * Ajout de la commande personnalisée 'HSBColor' pour les WS2812B virtuelles:
            . fonction retirée de controleGlobal
        * Ajout de la commande personnalisée 'Dimmer' pour les WS2812B virtuelles
            . fonction retirée de controleGlobal

#### <ins>Le 08/05/2025 à 05h33 :</ins>
    - Dans le fichier de paramètres '_persist.json':
        * Ajout dans 'drivers->modBus': des paramètres de l'esclave Tasmota ModBus
            * Pour les relais virtuels 'ModBus_TasmotaSlaveModBus1'
            * Pour les thermomètres DS18B20 virtuels 'ModBus_TasmotaSlaveModBus1'
            * Pour les WS2812B virtuelles 'ModBus_TasmotaSlaveModBus1'
    - Séparation des fichiers 'autoexec.be' dans chacun des dossiers appartenant aux modules
    - Création:
        * du module: 'garageFonctions'
        * du driver 'controleGarage'
    - Ajout de la page des LEDs virtuelles sur le WebUI: 'ledVirtuel.html'
    - Modification du module 'configDevices.be':
        * 'tasmota.global.devices_present' est maintenant calculé dans cette fonction pour ajouter les boutons virtuels 
    - Modification du fichier 'tasmota_types.h':
        * const uint32_t settings_text_size = 800;      //699
        * Permet d'augmenter le nombre de caractères des titres des boutons sur webUI
    - Dans le module 'modbusFonctions':
        * Dans la fonction 'modbusFonctions.lireMsgModbus()': Ajout de la possibilité de réception d'ordre ModBus 0x10: 
            . "Écriture de plusieurs registres (Write Multiple Registers)"     
            . ex= commande d'une LED WS2812B (couleur,intensite, luminosite)
        * Dans la fonction 'modbusFonctions.executeCmdModbus(paramMSG)': Execute la commande "ECRITURE_REGISTRES_HOLDER"
            . Peut modifier la couleur, la saturation, la luminosite d'une LED WS2812B
            . Puis renvoie les 3 valeurs HSBColor[couleur, saturation, luminosite]
    - Dans le module globalFonctions:
        * Ajout de la commande personnalisée 'HSBColor' pour les WS2812B virtuelles
        * Ajout de la commande personnalisée 'Dimmer' pour les WS2812B virtuelles

#### <ins>Le 01/05/2025 à 23h35 :</ins>
    - Correction dans le module 'controleGarage':
        * Dans la fonction 'def web_sensor()':
            . Modification d'un bug lorsque les thermometres n'étaient pas connectés: dans la fonction
    - Dans user_config_override:
        * Ajout de la compétence des websockets: pour le firmware: 'FIRMWARE_ESP32S3_SERVEUR_GARAGE_MODBUS'
        * Cf. PR: https://github.com/arendst/Tasmota/pull/23206
    - Préparation pour le module de Cuve:
        * Il prend en charge le relevé de température d'eau de Cuve par DS18B20 à la place du module de Garage
        * Arrêt de la prise de température par DHT22 par le module de Garage:
            . Compétence conservée dans le paramétrage json et global
            . Modificationdu fichier html pour arrêt de l'affichage web et de la fonction dédiée
        * Il prend en charge la mesure de la hauteur d'eau à la place du module de Garage
        * Il peut se conecter à l'AP de l'iphone pour visualisation
        * Il devient un esclave ModBus:
            . paramétrage des réponses aux ordre ModBus
            . paramétrage des adresses de stockage des données de température d'eau et hauteur de cuve
        * Désactivation de la connexion MQTT & UDP
    - Dans le module 'modbusFonctions':
        * Dans le fonction 'modbusFonctions.executeCmdModbus(paramMSG)':
            . Ajout du traitement de commande '0x04': LECTURE_REGISTRES_ENTREES (Lecture des entrées analogiques, températures (Input Registers))
    - Dans le fichier user_config_override.ini:
        * Ajout du paramètre '#define USE_WEB_STATUS_LINE_WIFI' permettant l'affichage des caractéristiques de la connexion sur le webGUI

#### <ins>Le 14/04/2025 à 20h01 :</ins>
    - Dans le module 'modbusFonctions':
        * Modification de la fonction 'modbusFonctions.envoiMsgModbus = def(paramMSG)':
            . Paramétrage de la reconstruction de la trame au format 'byte()' avec calculCRC avant de l'envoyer pour les functionCode: 0x06

#### <ins>Le 14/04/2025 à 18h54 :</ins>
    - Dans le Driver 'controleGeneral':
        * Modification de la fonction 'set_power_handler(cmd, idx)': Prend en charge l'ordre ModBus envoyé en fonction du type de relai (normal ou inversé)
    - Dans le Driver 'modBus_Conn16channel':
        * Modification de la fonction 'changementEtatDemarrage(value, trigger, msg)': Prend en charge l'ordre ModBus envoyé en fonction du type de relai (normal ou inversé)

#### <ins>Le 14/04/2025 à 01h05 :</ins>
    - Modification du Driver 'controleModbus':
        * La fonction 'every_100ms()' lance la lecture sur le port ModBus régulièrement
        * La fonction 'recupereReponseModBus(value, trigger, msg)': 
            . Si maitre ModBus: Analyse la réponse
            . Si esclave ModBus: 
                -> Analyse l'ordre
                -> Execute la commande
                -> Prépare & Envoie la réponse
    - Transfert de la fonction 'verifRgxClients()' du Driver 'controleUDP' vers le module 'udpFonctions'
    - Transfert de la fonction 'resetClientsConnectes()' du Driver 'controleUDP' vers le module 'udpFonctions'

#### <ins>Le 13/04/2025 à 08h35 :</ins>
    - Correction dans le module 'rangeExtenderFonctions':
        * Mise à jour de la fonction javascript affichant 1 bouton par esclave connecté dans la fonction 'rangeExtenderFonctions.afficheBoutonsModulesEsclaves()'
        * Correction d'un bug dans la fonction de routage RGX dans la fonction 'rangeExtenderFonctions.routageRangeExtender(cmd, idx, payload, payload_json)'
    - Modification du Driver 'controleModbus':
        * Ajout de la fonction 'every_100ms()': gestion des messages ModBus reçus si la device Tasmota est un esclave ModBus (id>0)
    - Modification du module 'modbusFonctions':
        * Reparamétrage de la fonction 'modbusFonctions.lireMsgModbus(): Parse les données reçues si la device Tasmota est un esclave ModBus (id>0)
        * Ajout de la gestion des erreurs:
            . Erreur = 1 -> Adresse esclave incorrecte
            . Erreur = 9 -> CRC incorrecte
        * Ajout du stockage dans un tableau des données envoyées pour les functionCode = 0x03 & 0x06

#### <ins>Le 12/04/2025 à 18h17 :</ins>
    - Modification du Driver 'controleModbus'
        * la fonction 'every_250ms' devient la fonction 'recupereReponseModBus(value, trigger, msg)' utilisée pour le maitre ModBus
    - Modification du module 'gestionFileFolder':
        * Correction d'un bug de passage de ligne doublé dans l'enregistrement des logs
    - Modification du module 'modbusFonctions':
        * Ajout dans la fonction 'configModbusByJson()': 
            . Ajout de l'activation du port série pour la gestion des ordre Modbus recues si la device Tasmota est un esclave Modbus
        * Modification de la fonction 'lireMsgModbus = def(paramMSG)':
            . Changement d'appellation du port série 
    - Modification du Driver 'controleModbus':
        * Réintégration de la fonction 'every_250ms()': lecture et traitement des trames Modbus si la device Tasmota est un esclave Modbus
    - Le module 'i2c_ads1115' devient un Driver
    - Le module 'i2c_mcp23017' devient un Driver
    - Le module 'modBus_Conn16channel' devient un Driver

#### <ins>Le 09/04/2025 à 07h07 :</ins>
    - Correction dans le module 'gestionFileFolder' et sa fonction 'enregistreLogs = def(fileChemin, modulo, data)'
    - Correction de la fonction 'afficheBoutonsModulesEsclaves()' dans le module 'rangeExtenderFonctions'
    - Déplacement du paramétrage des capteurs analogiques virtuels 'I2C_ADS1115' du module 'garageFonctions' vers un module dédié 'i2c_ads1115'
    - Déplacement du paramétrage des relais virtuels 'ModBus_Conn16channel' du module 'garageFonctions' vers un module dédié 'ModBus_Conn16channel'
    - Déplacement du paramétrage des relais virtuels 'I2C_MCP23017' du module 'garageFonctions' vers un module dédié 'i2c_mcp23017'

#### <ins>Le 06/04/2025 à 19h48 :</ins>
    - Dans le fichier de paramétrage '_persist.json':
        * Ajout des relais 6 à 11 (Relais ModBus)
    - Déplacement du paramétrage des relais virtuels 'ModBus_Conn16channel' du module 'garageFonctions' vers un Driver dédié 'ModBus_Conn16channel'
    - Déplacement du paramétrage des relais virtuels 'I2C_MCP23017' du module 'garageFonctions' vers un Driver dédié 'i2c_mcp23017'
    - Dans le fichier 'autoexec.be':
        * Ajout de la compilation forcée ou selon les Drivers activés

#### <ins>Le 06/04/2025 à 02h27 :</ins>
    - Reconstruction complète du Driver 'controleModBus' et du module 'modbusFonctions'
    - Test de compilation OK
    
#### <ins>Le 05/04/2025 à 21h26 :</ins>
    - Dans le module 'configDevices':
        * Correction de la fonction 'configDevicesByRules()'
        * Correction de la fonction 'set_power_handler(cmd, idx)' du Driver 'controleGeneral'
        * Correction de la configuration des relais virtuels ModBus si ils existent et sont paramétrés dans la fonction 'init()' du Driver 'controleGarage'

#### <ins>Le 04/04/2025 à 06h02 :</ins> 
    - Dans le module 'gestionFileFolder': 
        * Ajout de la fonction 'compteIndiceMaxFileLogs(nomFichier)': Compte l'indice maximum contenu dans le nom des fichiers logs
        * Création de la fonction 'enregistreLogs(fileChemin, modulo, data)': Enregistre les données en logs
    - Dans le Driver 'controleGarage':
        * Modification de la fonction 'enregistreLogs(fileChemin)'

#### <ins>Le 31/03/2025 à 00h18 :</ins> 
    - Projet '/data/CUVE-EAU': renommé 'data/GARAGE'
    - Arrêt des logs originaux de Tasmota:
        * dans 'user_config_override.ini':
            // #define FILE_LOG_SIZE       100
            // #define FILE_LOG_COUNT      10                        // Enable with command `FileLog 1..4` or `FileLog 11..14`
            // #define FILE_LOG_NAME       "/logs/fileLog %02d.txt"
    - Ajout de paramètres d'enregistrement de logs en fonction de chaque module:
        * ex dans _persist_json: persist["modules"]["garage"]
			"logs": {
				"nbLogsFiles": 1,
				"fileLogName": "/logs/garage%i.log",
				"fileLogSize": 1000
			}
    - Récupération des mesures et calcul de la formule pour obtenir la hauteur d'eau de cuve du capteur de hauteur d'eau:
        * lien aliexpress: https://fr.aliexpress.com/item/1005008287211948.html?spm=a2g0o.productlist.main.11.3f1c13ceuujsuY&algo_pvid=e1aad01c-251b-4bb1-9208-d9f5604a1ff3&algo_exp_id=e1aad01c-251b-4bb1-9208-d9f5604a1ff3-5&pdp_ext_f=%7B%22order%22%3A%224%22%2C%22eval%22%3A%221%22%7D&pdp_npi=4%40dis%21EUR%2142.49%2142.39%21%21%21325.58%21324.82%21%402103856417432623016415598eba6e%2112000044502826361%21sea%21FR%211679624561%21ACX&curPageLogUid=8URpBp0TgxLt&utparam-url=scene%3Asearch%7Cquery_from%3A
        * Capteur anlogique: 0 à 10V -> 1 à 4m d'eau
        * Cf. fichier: 'data/GARAGE/Conversion analogique Capteur Hauteur Eau.xlsm'
        * Coefficient de conversion: 30mV/cm
        * Paramétrage dans _persist.json
    - Dans le Driver 'controleGarage':
        * Ajout du paramétrage des logs au démarrage du Driver
        * Gestion de l'enregistrement en log du capteur analogique de hauteur de cuve du module 'garage'
        * Récupération des limites d'alertes en fonction de la hauteur d'eau au démarrage du Driver
        * Changement de l'affichage sur page WebUI pour le capteur: 
            . Affichage de la hauteur d'eau et non-plus du voltage
        * Désactivation des entrées analogiques de bornes hautes et basses
    - Dans le module 'diversesFonctions':
        * Ajout de la fonction 'printBinaire(nombre)': convertit un nombre en sa représentation binaire

#### <ins>Le 29/03/2025 à 09h22 :</ins> 
    - Modification de la mission du Driver 'controleModbus':
        * Réactivation et correction de bugs sur ce Driver
        * Activation de la fonction de paramétrage des relais virtuels ModBus 16 channel si activés
    - Dans le Driver 'controleGeneral': 
        * Dans la fonction 'set_power_handler(cmd, idx)':
            . Ajout de la gestion des commandes ModBus pour le module de commande 16 sorties (relais)
    - Modification du fichier 'modBus.help'
    - Suppression du Driver 'controleConn16channelModbus'
    - Modification du _persist.json:
        * Ajout d'un paramètre 'idModBus': correspond à l'id du relais sur la platine 16 relais ModBus
    - Ajout de nouvelles commandes personnalisées dans le Driver 'controleGeneral':
        * ReglageGlobal nbLogsFiles 14: Paramètre le nombre de fichiers de logs (si =0: l'enregistrement des logs est désactivé)
        * ReglageGlobal logLevel 4: Paramètre le niveau des logs sur le port série et l'interface web

#### <ins>Le 27/03/2025 à 02h17 :</ins> 
    - Modification de la mission du Driver 'controleModbus':
        * Chargé de mettre en place une communication entre plusieurs modules ESP32 équipés de Tasmota par liaison ModBus Maitre-Esclaves
        * Capable de lire et d'écrire toutes le commandes ModBus
        * Pour l'instant ne peut que répondre & executer les commandes suivantes qui lui sont envoyées lorsqu'il est esclave ModBus:
            . functioncode=0x05 ==> "ECRITURE_COIL_UNIQUE" ==> ex=Activer 1 relai
            . functioncode=0x06 ==> "ECRITURE_REGISTRE_UNIQUE" ==> ex=Changer une valeur analogique
        * La lecture & l'écriture sur le port ModBus sont réalisées par des fonctions personnalisées.
        * Le Maitre ModBus (id==0):
            . Paramétrage au démarrage des paramètres ModBus selon les fonctions intégrées à Tasmota: ModbusBaudrate/ModbusSerialConfig/ModbusSerialTimeout
            . Ecriture & Lecture des données transmises par les fonctions personnalisées du module
        * L'esclave ModBus (id>0):
            . Paramétrage au démarrage des paramètres ModBus 
            . Ecriture & Lecture des données transmises par les fonctions personnalisées du module

    - Création du Driver 'controleConn16channelModbus':
        * Objectifs:
            . Paramétrer les propriétes de la liaison ModBus entre Tasmota et le module de connexion ModBus 16 sorties
            . Créer les boutons virtuels: Accès de bas niveau aux paramètres et aux variables globales de Tasmota
                -> utilisation de: 'tasmota.global.devices_present' pour créer les boutons virtuels
                -> inspiré du script Berry: 'tasmota/berry/drivers/Shift595.be'
                -> https://tasmota.github.io/docs/Berry/#low-level-access-to-tasmota-globals-and-settings
        * Notes:
            . Seul un Maitre ModBus ne peut commander un module ModBus 16 channels
            . Par défaut: le débit est à 19600 Bauds & 8N1

    - Modification du _persist.json:
        * Apparition des paramètres: 
            . pour le module esclave 16 sorties: ['ModBus']['environnement']['Conn16channel']
            . pour le paramétrage des relais virtuels: ['relai3']['virtuel'] = 'ModBus_Conn16channel'

#### <ins>Le 22/03/2025 à 08h35 :</ins> 
    - Dans le module 'modbusFonctions': 
        * Fonctions ModBus paramétrées:
            . fonction '0x05' (Écriture d’une sortie digitale unique (Coil)) ==> OK
            . fonction '0x06' (Écriture dans un registre (Write Single Register)) ==> OK

#### <ins>Le 22/03/2025 à 08h35 :</ins> 
    - Dans le module 'modbusFonctions': 
        * Fonctions ModBus paramétrées:
            . fonction '0x05' (Écriture d’une sortie digitale unique (Coil)) ==> OK
        * Dans la fonction 'modbusFonctions.configModbusByJson()':
            . Paramétrage du maitre (id=0) au démarrage:
                -> 'ModbusSerialTimeout 2000'
                -> 'ModbusBaudrate 57600'
                -> 'ModbusSerialConfig 8N1'
            . Paramétrage de l'esclave (id>0) au démarrage:

#### <ins>Le 22/03/2025 à 03h00 :</ins> 
    - Dans le module 'modbusFonctions': 
        * Fonctions ModBus paramétrées:
            . fonction '0x05' (Écriture d’une sortie digitale unique (Coil)) ==> OK

#### <ins>Le 22/03/2025 à 02h02 :</ins> 
    - Mise en place de la fonction de lecture de trame ModBus en cas d'esclave ModBus
    - Dans le module 'modbusFonctions': 
        * Ajout de la fonction de lecture de la trame 'lireMsgModbus(paramMSG)' qui décode:
            . l'ID du module cible
            . la fonction recherchée
            . l'adresse de départ en lecture ou écriture
            . le CRC pour le vérifier
            . la longueur de la trame
        * Ajout de la fonction de traitement de l'ordre 'executeCmdModbus(buffer, paramMSG)' & de la préparation de la réponse pour la fonction '0x05':
            . execute l'action sur le relai
            . prépare la réponse

#### <ins>Le 21/03/2025 à 12h17 :</ins> 
    - Ajout des paramètres du DS3231 dans la section "I2C" en _persist.json
    - Dans le driver 'controleGeneral', pour la fonction 'init()': 
        * Ajout du paramètre de des/activation du Driver I2C 22
    - Le réglage de l'heure de la device est réalisé par :
        * connexion à un serveur NTP: diverses["fuseauHoraire"]["typeReglageHeure"] = "NTP"
        * réglage manuel: diverses["fuseauHoraire"]["typeReglageHeure"] = "MANUEL"
        * reglage par module Real Time Clock: diverses["fuseauHoraire"]["typeReglageHeure"] = "RTC"
        * reglage par réception de l'heure par le maitre en UDP: diverses["fuseauHoraire"]["typeReglageHeure"] = "UDP"

#### <ins>Le 19/03/2025 à 04h11 :</ins> 
    - Dans le fichier de configuration: _persist.json
        * Changements des sorties GPIO Serie_RX/TX en ModBr_RX/TX
        * Ajout des fonctionnalités I2C aux esclaves & activation du DS3231
    - Importation de la librairie Partition_Wizard (dans 'autoexec.be')
    - Intégration d'un DS3231 pour le paramétrage de l'heure des esclaves par eux-mêmes

#### <ins>Le 16/03/2025 à 06h45 :</ins> 
        - Ajout du module 'modbusFonctions' & du driver 'controleModbus' & un fichier d'aide 'modBus.help'
        - Changement de la partition avec une partition ota_1
        - Réactivation du driver controleModbus & Test d'utilisation de la commande Tasmota et Recalcul CRC
        - Refonte du fichier 'platformio_tasmota.cenv'

#### <ins>Le 15/03/2025 à 13h01 :</ins> 
        - Dans le module 'controleWeb':
            * Ajout de la recherche de l'existance du module 'controleRangeExtender'
            * Lance l'affichage du bouton
        - Dans le module 'rangeExtenderFonctions':
            * Dans la fonction 'rangeExtenderFonctions.afficheBoutonsModulesEsclaves()':
                . Modification du lien HTML du bouton
                . Réinstallation de la commande personnalisée: 'rangeExtenderFonctions.routageRangeExtender()': 
                    -> Active RgxNAPT
                    -> Ouvre la redirection de port
        - Tests d'intégration du Bluetooth au firmware Tasmota: 'FIRMWARE_ESP32S3_SERVEUR_CUVE_EAU_MODBUS' & 'FIRMWARE_ESP32S3_SLAVE_CUVE_EAU_MODBUS'
        - Dans 'platformio_tasmota_cenv.ini' : ajout des fonctionnalités Bluetooth & Mi32:
        ```
                -D FIRMWARE_BLUETOOTH
                -D USE_MI_EXT_GUI
                -D CONFIG_BT_NIMBLE_NVS_PERSIST=y

                ; Fonctionalités bluetooth & Mi32
                lib_extra_dirs                  = ${env:tasmota32s3.lib_extra_dirs}
                                                    lib/libesp32, lib/libesp32_div, lib/lib_basic, lib/lib_ssl, lib/lib_i2c                     ; bluetooth
                                                    lib/libesp32, lib/libesp32_div, lib/lib_basic, lib/lib_i2c, lib/lib_div, lib/lib_ssl        ; Mi32
                lib_ignore                      = ${env:tasmota32s3.lib_extra_dirs}
                                                    Micro-RTSP
        ```

#### <ins>Le 14/03/2025 à 15h18 :</ins> 
        - Lancement de la synchronisation de l'heure des esclaves :
            * commande 'CommandeUDP Time' lorsque 'Time#Initialized's
        - Modifiction de la structure du json '/json/nbEsclavesUDP.json' complété par chaque esclave:
            * Les adresses IP et MAC sont maintenant reprises de la commande 'Status 5'
            * Elles sont ensuite enregistrées en _persist.json
        - Dans le module 'cuveFonctions':
            * Modification de la fonction 'cuveFonctions.changementEtatCapteur()':
                Ajout du test de l'existence des paramètres 'cuveFonctions.sensorsCuve["voltageMin"]' & cuveFonctions.sensorsCuve["voltageMax"]
        - Dans le driver 'udpFonctions':
            * Debuggage de la fonction 'changementEtatDemarrage()':
                . dans les actions sur 'Time#'
        - Dans le driver 'controleRangeExtender':
            * Ajout de la fonction affichant le bouton de lien en fonction de l'état 'Online' des esclaves:
                fonction 'rangeExtenderFonctions.afficheBoutonsModulesEsclaves()'
        - Dans le driver 'controleRangeExtender':
                correction de la fonction 'rangeExtenderFonctions.afficheBoutonsModulesEsclaves()'

#### <ins>Le 14/03/2025 à 09h00 :</ins> 
        - Mise en place des 2 firmwares : 'FIRMWARE_ESP32S3_SERVEUR_CUVE_EAU_MODBUS' & FIRMWARE_ESP32S3_SLAVE_CUVE_EAU_MODBUS'
            * 1ers test: OK
            * Reset des drivers 'controleUDP' & 'controleRangeExtender'
            * Reset des modules 'udpFonctions' & 'rangeExtenderFonctions'
        - Reparamétrages en commentaires dans les drivers 'controleUDP' & 'controleRangeExtender':
            * des communications UDP entre esclaves & maitres 
            * de la mise en route du RangeExtender et sa dépendance au réseau UDP
	
        - API des messages UDP
            * Les messages sont de la forme respectent l'API MQTT Tasmota
            * toutes les 300 secondes (5min): 
                . le maitre envoi : "cmnd/%topic_groupe_destination%/CommandeUDP Time=%timestamp%, IP=%IP maitre%" (permet le reglage de l'heure des esclaves)
                . les esclaves répondent : "tele/%topic_groupe_destination%/IM_ALIVE"
            * les identifiants :
                . 0 = maitre
                . 1 à 254 = esclaves
                . 255 = broadcast

        - Les communicationsUDP sont réalisées uniquement sur l'IP Wifi principale (pas celle du RangeExtender: 10.99.0.1)
        - Principes de fonctionnement:
            * Dès la connection wifi établie: ##Wifi##Connected
                . Les esclaves enregistrent leurs paramètres dans '/json/nbEsclavesUDP.json': OK
                . les maitres & esclaves établissent la connexion UDPsur le port 2000: OK
            * Dès la connection des esclaves: ##System##Boot
                . Le maitre se rend compte de leur présence (par la commande 'RgxClients') et conserve leur adresse IP & MAC dans un tableau variable (tabClients): OK 
                    -> Le maitre envoie son IP principale & le timestamp aux esclaves pour qu'ils règlent leur heure: OK
                    -> Les esclaves enregistrent ce timestamp et l'adresse IP principale du maitre: OK
                    -> Les esclaves répondent avec leurs paramètres au maitre RangeExtender: OK
                    -> Le maitre les enregistre dans son '/json/nbEsclavesUDP.json': OK
                . Le maitre peut alors autoriser le bouton de lien vers les esclaves sur page web (réalisé sur le driver 'controleRangeExtender'): OK
                    -> sur click sur ce bouton : active le routage NAPT (pdt 5min) + ouvre la page web de l'esclave sur un nouvel onglet: OK
            * Toutes les 300s (5min): Le maitre envoie le timestamp aux esclaves pour qu'ils règlent leur heure: OK

> [!NOTE]
>
>            * Il sert de passerelle pour assurer à ces modules esclaves,uneconnexion au réseua Wifi.
>        - Dans le fichiers json : 'json/nbEsclavesUDP.json', il enregistre les paramètres des modules connectés:
>                nom, adressMAC, routagePort, routageIP, routagePort, routageMaitre, routageMaitrePort, routageMaitreIP
>            * Il enregistre aussi les règles de routage pour chaque module connecté.
>            * Il contient les paramètres pour le maitre et les esclaves.
>        - La transmission initiale entre esclaves & Maitre est réalisée par connexion UDP:
>            * Cette connexion est établie au démarrage sur le port 2000 (driver 'controleuDP'): 
>                s'il est absent une connexion UDP de secours permet la même chose
>            * Le maitre scanne toutes les 300s (5min) à la recherche de clients RangeExtender : rgxclients
>                . Il connait déjà l'adresse mac et IP de chaque module connecté
>                . Il envoie un message de type "cmnd/%topic_groupe_destination%/CommandeUDP TIMESTAMP %timestamp%,%IP du maitre%" à chacun:
>                    -> leur permet de régler leur heure
>                    -> leur permet de répondre par "tele/%topic_groupe_destination%/IM_ALIVE" avec leurs autres paramètres :
>                            nom, adressMAC, routagePort, routageIP, routagePort, topic
>                . Il enregistre les réponses dans le fichier 'json/nbEsclavesUDP.json'
>        - Le routage NAPT est activé tout le temps de la programmation:
>            * Il sera désactiver normalement après la programmation
>            * Il pourra être réactivé par la commande 'ReglageRangeExtender routageNAPT ON'
>            * lors de l'appui sur le bouton de lien sur le routeur pour accéder à chacun des modules esclaves
>                    -> Le maitre peut alors autoriser le bouton de lien vers les esclaves sur page web (réalisé sur le driver 'controleRangeExtender'): OK
>                    -> sur click sur ce bouton : active le routage NAPT (pdt 5min) + ouvre la page web de l'esclave sur un nouvel onglet: OK

#### <ins>Le 14/03/2025 à 07h45 :</ins>
        - Dans 'user_config_override.ini':
	        * Désctivation de la directive: // #define USE_TASMESH
		            Empêche les communications UDP sur l'adresse IP du RangeExtender

#### <ins>Avant le 13/03/2025 :</ins>
        - Dans le module 'udpFonctions':
	        * Ajout de la commande personnalisée : 'ReglageUDP forceEnvoiParams ON'
		        Oblige l'esclave UDP à envoyer ses paramètres au maitre UDP
	        * Déplacement de la fonction d'envoi des paramètres par chaque esclave UDP -> après connexion Wifi :
		        . Chaque esclave envoi le json avec ses paramètres en UDP pour récupérer son horadatage
	        * Création de la commande personnalisée dans le driver 'controleUDP' pour gérer cette réponse côté maitre UDP
	        * Création de la fonction 'lireUniCast(paramMSG)' pour:
		        . décoder le message
		        . savoir s'il est adressé au bon module (reconnaissance par le topic)
			        -> groupTopic = message adressé à tout le monde
			        -> topic du module = message unique adressé à un seul module
	        * Remplacement de 'tasmota.cmd(GroupTopic1')par serveur['mqtt']['GroupTopic1']:
		        . en cas d'inactivation de mqtt, ces commande ne sont plus valides
            * Pour les firmwares : ''FIRMWARE_ESP32S3_SERVEUR_CUVE_EAU_MODBUS' & FIRMWARE_ESP32S3_SLAVE_CUVE_EAU_MODBUS'
	        * Mise à jour du template dans 'user_config_override.ini' & dans '_persist.json'
                . Dans le driver 'controleUDP':	

        - Création d'un script python permettant d'envoyer des message en UDP : 'envoi_message_UDP.py'

------------------------------------------------------------------------------------------------------------------------------------

        - Dans le module 'gestionFileFolder':
            * Modification de la fonction 'listeEtRepartitLesFichiers()':
                Répartit en plus les fichiers json dans un dossier dédié
            * Déplacement de 'nbIO.json' dans /json/nbIO.json
            * Déplacement de 'nbEsclavesUDP.json' dans /json/nbEsclavesUDP.json
        - Dans les modules et drivers utilisant les fichiers json:
            * Lecture du fichier plutôt que de garder les données en variable
            * Déchargement de la variable après utilisation de la fonction

-------------------------------------------------------------------------------------------------------------------------------------

    - Dans 'user_config_override.ini':
        * Activation de la directive: #define USE_TASMESH
    - Dans le driver 'controleUDP':
        * Activation de la règle: 'udpListener_System'
        * Modification de la fonction pour faire un reset du parametre "alive" de chaque esclave
            Puis l'enregistrer en fichier json: 'nbEsclavesUDP.json'
        * Encapsulage dans une fonction gérant l'envoi des paramètres de l'esclave vers le maitre: 'ImAlive()'
            . Reste à ajouter une commande personnalisée dans le driver 'controleUDP' pour gérer cette réponse côté maitre UDP

-------------------------------------------------------------------------------------------------------------------------------------

    - Dans 'user_config_override.ini':
        * Ajout du driver 'Tasmesh'
    - Dans le module 'configGlobal':
        * Dans la fonction 'configGlobalByJson': 
        * Ajoute l'activation / desactivation des comm. MQTT (SetOption3)
    - Dans le driver 'controleUDP':
        * Correction d'un bug sur la tache CRON 'verifClientsConnectes()'
        * Transforme la fonction d'interrogation regulière 'resetClientsConnectes()' (/300s)
    - Dans le module 'udpFonctions':	
        * Au Boot :
            . Chaque esclave envoi le json avec ses paramètres en UDP pour récupérer son horadatage
            . Reste à ajouter une commande personnalisée dans le driver 'controleUDP' pour gérer cette réponse côté maitre UDP
    - Modification du driver50 'xdrv_50_filesystem.ino': 
        * Changement du paramètre 'FILE_LOG_COUNT':
            #ifndef FILE_LOG_COUNT
            #define FILE_LOG_COUNT 16                // Number of log files (max 16 as four bits are reserved for index)
		#endif	

-------------------------------------------------------------------------------------------------------------------------------------

    - Dans 'user_config_override.ini':
        * Modification du chemin des fichiers de logs pour les classer dans un dossier
    - Dans le driver50 'xdrv_50_filesystem.ino': 
        * allongement de la taille du titre du fichier de log
    - Dans _persist.json:
        * ajout de l'ID de cgaque module RangeExtender pour distinguer le maitre des esclaves
            maitre: ID = 0
            esclaves: ID > 0
    - Dans le module 'gestionFileFolder':
        * Création du script de création du dossier 'logs' dans la fonction 'listeEtRepartitLesFichiers()'
    - Dans le driver 'controleUDP':
        * Ajoute une fonction d'interrogation regulière (/300s) des esclaves pour vérifier leur connexion et leur transmettre le timestamp
        * Respecte l'API Tasmota pour les commandes et réponses

<hr></hr>

$\textsf{\color{#f5750e}{Emoji possibles dans README.md}}$  
[Cliquez ici!](https://github.com/ikatyang/emoji-cheat-sheet/blob/github-actions-auto-update/README.md#table-of-contents)

🔴🟠🟡🟢🔵🟣🟤⚫⚪🔘🛑⭕
🟥🟧🟨🟩🟦🟪🟫⬛⬜🔲🔳⏹☑✅❎
❤️🧡💛💚💙💜🤎🖤🤍♥️💔💖💘💝💗💓💟💕❣️♡
🔺🔻🔷🔶🔹🔸♦💠💎💧🧊
🏴🏳🚩🏁
◻️◼️◾️◽️▪️▫️
