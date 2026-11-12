; Commandes executees a chaque demarrage (autoexec.bat natif de Tasmota : xdrv_50_filesystem.ino::UfsExecuteCommandFile,
; a la 1re connexion MQTT). Lignes de 510 caracteres au plus ; ';' en tete = commentaire.

; Lien avec le Sonoff de la porte de la cave (env tasmota-cave-lumiere-porte, 192.168.0.45), plan envs-grenier-rdc-sonoff-cave A11.
; Relais 3 « LED Machines » (POWER3) <-> lumiere de la cave (POWER1 du Sonoff), par le groupe tasmotas/cave des deux cartes.
; Garde-fou anti-echo : Var1 = dernier etat recu du Sonoff ; un changement n'est renvoye que s'il en differe, donc un etat
; applique sur ordre du Sonoff ne repart pas. Le Sonoff porte la Rule symetrique (USER_RULE2 de sa section du .h).
; Remplace la cle publishMQTT du relai1 du persist (envoi Berry de cmnd/cave/lumiere/POWER1, sans garde-fou), retiree.
Rule1 ON Event#lumPorte DO Backlog Var1 %value%; Power3 %value% ENDON ON Power3#State!=%var1% DO Backlog Var1 %value%; Publish cmnd/tasmotas/cave/Event lumSrv=%value% ENDON
Rule1 1
