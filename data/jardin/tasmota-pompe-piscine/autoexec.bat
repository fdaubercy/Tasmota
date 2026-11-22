; Reglages de la pompe de piscine (Sonoff S2X, ESP8266 1 Mo, 192.168.0.40), a REJOUER sur un module NEUF.
; Cette carte n'a PAS de systeme de fichiers : ce fichier n'est ni televerse ni lu par la carte. Il se COLLE ligne a ligne
; dans la console Tasmota (http://<ip>/cs), ou s'envoie par http://<ip>/cm?cmnd=<ligne>. Les lignes ';' sont des commentaires.
;
; Procedure pour un module neuf :
;  1. Flasher notre firmware (env tasmota-jardin-pompe-piscine) : OTA en deux temps par le minimal officiel, ou flash serie.
;  2. Console : Reset 1. La carte reprend alors les valeurs compilees de la section de la pompe de tasmota/user_config_override.h
;     (Wi-Fi des deux repeteurs KuWFi, MQTT et son mot de passe, IP .40, topic, module S2X) : ils ne sont donc PAS repetes ici.
;  3. Rejouer les lignes ci-dessous. Ce sont les ecarts mesures le 2026-11-22 entre la config de la pompe restauree et une carte
;     remise a zero (page Build, onglet « Sauvegarde configuration »), plus ce que le fichier compile ne fixe pas.
;  Plus simple : restaurer la sauvegarde outils_docs/sauvegardes_cartes/tasmota-jardin-pompe-piscine/*.dmp par cet onglet
;  (tout est repris d'un coup, mots de passe compris).
;
; Module : Sonoff S2X (numero 8 dans Status 0)
Module 8

; Noms, hostname et mDNS
Backlog DeviceName Pompe de piscine; FriendlyName1 Pompe de piscine;
Backlog Hostname POMPE-PISCINE; SetOption55 ON;

; Adresse IP / passerelle / masque / DNS
Backlog IPAddress1 192.168.0.40; IPAddress2 192.168.0.254; IPAddress3 255.255.255.0; IPAddress4 192.168.0.254;

; MQTT : serveur, client et topics (utilisateur et mot de passe : valeurs compilees)
Backlog MqttHost 192.168.0.5; MqttPort 1883; MqttClient POMPE-PISCINE; Topic jardin/pompe_piscine; GroupTopic tasmotas/jardin;

; Esclave du P4 par MQTT (outils_docs/README.md, « Regler un esclave sans Berry ») : le bouton garde la main sur son relais
; et rien n'est retenu (un ordre retenu serait rejoue a chaque reconnexion).
Backlog SetOption19 0; SetOption73 0; SetOption114 0; ButtonTopic 0; SwitchTopic 0; ButtonRetain 0; SwitchRetain 0; PowerRetain 0;

; Evite un reset sur appui long sur le bouton, recherche du signal Wi-Fi le plus fort, appel de la page sans controle de Referer
Backlog SetOption1 ON; SetOption56 ON; SetOption57 ON; SetOption128 ON;

; Interdit l'affichage du modele (« Sonoff S2X ») sur la page Web
SetOption141 ON

; LED de statut (GPIO13, LED_i1) : LedState 1 = la LED suit l'etat du relais, comme dans la sauvegarde du 2026-11-12
Backlog LedState 1; LedMask 0xFFFF; SetOption31 OFF;

; Emulation Belkin WeMo (Alexa)
Emulation 1

; Reglages locaux : position, fuseau horaire et heure d'ete, serveurs de temps
Backlog Latitude 50.410932; Longitude 3.085796;
Backlog Timezone 99; TimeStd {"Week": 0, "Month": 10, "Offset": 60, "Day": 1, "Hemisphere": 0, "Hour": 3}; TimeDst {"Hemisphere": 0, "Week": 0, "Month": 3, "Day": 1, "Hour": 2, "Offset": 120};
Backlog NtpServer1 pool.ntp.org; NtpServer2 nl.pool.ntp.org; NtpServer3 0.nl.pool.ntp.org;

; Logs : niveau 2 partout (le niveau debug MQTT du fichier compile fait redemarrer certains esclaves), journal syslog sur le PC
Backlog SerialLog 2; WebLog 2; MqttLog 2; LogHost 192.168.0.3; SysLog 2;

; Fonctionnement : telemetrie toutes les 5 minutes, dernier etat du relais conserve au redemarrage
Backlog TelePeriod 300; PowerOnState 3; SetOption0 ON;

; Minuteries : desarmees (Timer1 08:00 ON, Timer2 20:00 OFF), a armer a la main si besoin
Backlog Timers 1; Timer1 {"Enable":0,"Time":"08:00","Days":"1111111","Repeat":0,"Output":1,"Action":1}; Timer2 {"Enable":0,"Time":"20:00","Days":"1111111","Repeat":0,"Output":1,"Action":0};
