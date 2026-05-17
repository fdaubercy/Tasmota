; Stocke les commandes qui seront exécutées à chaque démarrage, 
; de manière similaire aux commandes de backlog dans les règles déclenchées à System#Boot.

; Paramétrage du module de Volet Roulant de porte d'entrée
; Affiche la température de l'ESP32
SetOption146 ON

; Evite un reset sur appui long sur un bouton
SetOption1 OFF

; Paramétrage du wifi et de l'IP :
;Backlog WifiPower 17; SSId1 MAISON; Password1 obdormisti-pervigile%.-ficiendus;

; Modèle :
Template {"NAME":"tongou SY2","GPIO":[32,1,9312,1,1,320,1,1,9313,8160,3200,544,1,1,1,1,0,1,1,1,0,0,1,1,0,0,0,0,1,1,4736,1,1,0,0,1],"FLAG":0,"BASE":1}

; Recherche du signal wifi le plus fort :
SetOption56 ON

; Paramétrage le scan de réseaux wifi toutes les 44 min
SetOption57 ON

; Interdit l'affichage du modèle sur la page Web
SetOption141 ON

; Réglage des paramètres locaux :
; Réglage de la latitude et longitude :
Backlog Latitude 50.410931; Longitude 3.085796;

; Réglage du fuseau horaire & heure d'été :
Backlog Timezone 99; TimeStd {"Week": 0, "Month": 10, "Offset": 60, "Day": 1, "Hemisphere": 0, "Hour": 3}; TimeDst {"Hemisphere": 0, "Week": 0, "Month": 3, "Day": 1, "Hour": 2, "Offset": 120};

; Règle le nom du serveur :
DeviceName Disjoncteur Différentiel PC Bureau

; Règle le hostname & Active le serveur mDNS :
Backlog Hostname DISJONCTEUR-DIFFERENTIEL-BUREAU; SetOption55 ON;

; Règle les adresse IP / Masque de sous-reseau / Gateway / DNS Server
Backlog IPAddress1 192.168.0.49; IPAddress2 192.168.0.254; IPAddress3 255.255.255.0; IPAddress4 192.168.0.254;

; Règle les paramètres MQTT :
;Backlog MqttHost 192.168.0.5; MqttPort 1883; MqttClient DISJONCTEUR-DIFFERENTIEL-BUREAU; MqttUser fdaubercy; MqttPassword Lune5676; Topic bureau/pc; GroupTopic1 tasmotas/bureau;

; Active ou non la LED de status et définie son niveau :
Backlog LedPower OFF; SetOption31 OFF; LedState 1;

; Paramètre le niveau des logs (Niveau=LOG_LEVEL_DEBUG) :
Backlog SerialLog 3; WebLog 3;

; Paramètre le pin, le type & le numero des boutons (Button) : 
; Détache les buttons & Active le mutipress :
SetOption73 OFF
; Parametrage du mode du bouton : ON=0 / OFF=1
Backlog SwitchMode1 0; SwitchMode2 0;


Timer1 {"Enable":1,"Mode":0,"Time":"08:00","Window":0,"Days":"1111111","Repeat":1,"Output":1,"Action":1}
Timer2 {"Enable":1,"Mode":0,"Time":"23:30","Window":0,"Days":"1111111","Repeat":1,"Output":1,"Action":0}
Timer3 {"Enable":1,"Mode":0,"Time":"00:00","Window":0,"Days":"1111111","Repeat":1,"Output":1,"Action":0}
Timer3 {"Enable":1,"Mode":0,"Time":"00:00","Window":0,"Days":"1111111","Repeat":1,"Output":1,"Action":0}
Timer4 {"Enable":1,"Mode":0,"Time":"01:00","Window":0,"Days":"1111111","Repeat":1,"Output":1,"Action":0}
Timer5 {"Enable":1,"Mode":0,"Time":"02:00","Window":0,"Days":"1111111","Repeat":1,"Output":1,"Action":0}
Timer6 {"Enable":1,"Mode":0,"Time":"03:00","Window":0,"Days":"1111111","Repeat":1,"Output":1,"Action":0}
Timer7 {"Enable":1,"Mode":0,"Time":"04:00","Window":0,"Days":"1111111","Repeat":1,"Output":1,"Action":0}
Timer8 {"Enable":1,"Mode":0,"Time":"05:00","Window":0,"Days":"1111111","Repeat":1,"Output":1,"Action":0}
Timer9 {"Enable":1,"Mode":0,"Time":"06:00","Window":0,"Days":"1111111","Repeat":1,"Output":1,"Action":0}
Timer10 {"Enable":1,"Mode":0,"Time":"07:00","Window":0,"Days":"1111111","Repeat":1,"Output":1,"Action":0}
Timer11 {"Enable":1,"Mode":0,"Time":"07:30","Window":0,"Days":"1111111","Repeat":1,"Output":1,"Action":0}
