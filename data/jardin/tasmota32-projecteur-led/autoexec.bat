; Stocke les commandes qui seront executees a chaque demarrage (projecteur du jardin, NOUS B2T, 192.168.0.41).
; Wi-Fi (repeteur KuWFi) et MQTT : par le persist (serveur.wifi, serveur.mqtt), pas ici.

; Evite un reset sur appui long sur un bouton
SetOption1 OFF

; Recherche du signal wifi le plus fort, scan toutes les 44 min
SetOption56 ON
SetOption57 ON

; Interdit l'affichage du modele sur la page Web
SetOption141 ON

; Reglages locaux : position, fuseau horaire et heure d'ete
Backlog Latitude 50.410931; Longitude 3.085796;
Backlog Timezone 99; TimeStd {"Week": 0, "Month": 10, "Offset": 60, "Day": 1, "Hemisphere": 0, "Hour": 3}; TimeDst {"Hemisphere": 0, "Week": 0, "Month": 3, "Day": 1, "Hour": 2, "Offset": 120};

DeviceName Projecteur de jardin

; Hostname et mDNS
SetOption55 ON

; Adresse IP / passerelle / masque / DNS
Backlog IPAddress1 192.168.0.41; IPAddress2 192.168.0.254; IPAddress3 255.255.255.0; IPAddress4 192.168.0.254;

; LED de statut
Backlog LedPower OFF; SetOption31 OFF; LedState 6;

; Logs : la console serie (GPIO1/GPIO3) est prise par la BL0942 -> SerialLog 0
Backlog SerialLog 0; WebLog 3;
