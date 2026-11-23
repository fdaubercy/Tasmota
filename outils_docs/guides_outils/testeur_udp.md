# Testeur UDP maître / esclave

Port : 7400. Cible PlatformIO : `testeur_udp` (Custom). Tâche VS Code : « Outil : testeur UDP maitre/esclave (http://127.0.0.1:7400) ».

## Lancer

Avec le Python de PlatformIO (`pyserial`) :

```
%USERPROFILE%\.platformio\penv\Scripts\python.exe outils_docs/scripts_python/outils_pc/testeur_udp.py --http 7400
```

Options (`testeur_udp.py::lit_options`) :

- `--port-maitre COM11` : port série du maître ModBus (ESP32-P4). Vide = fermé.
- `--port-esclave COM12` : port série de l'esclave (ESP32-S3, cuve ou rideau). Vide = fermé.
- `--vitesse 115200`, `--http 7400`, `--journal fichier.log` (lignes des deux cartes, mot de passe masqué).
- `--persist-maitre <_persist.json>` : persist du maître, d'où vient le réseau Wi-Fi de la bascule en Wi-Fi classique.
- `--local`, `--sans-navigateur`.

Les ports se choisissent aussi depuis la page. `pont:7000` (option ou liste de la page) passe par le pont série, qui garde le port COM. Sinon, fermer le pont ou le moniteur avant.

Pendant un build, lancer le script en Python direct, jamais la cible PlatformIO. Depuis un autre appareil, utiliser le lien à jeton de la console.

## Ce que fait la page

Trois onglets : Essais, Grille ModBus, Aide.

- Essais : ouvre les deux cartes, lit leurs logs, envoie des messages UDP en unicast ou multicast dans les deux sens. Types d'essai : texte libre, trame `ModbusUDP`, push, `ImAlive` (`testeur_udp_essais.py::TYPES`). Chaque essai reçoit un verdict : RECU, EMIS NON RECU, NON EMIS, jugé sur les logs des deux cartes.
- Mode de l'esclave : « Range Extender » (client du point d'accès du maître) ou « Wi-Fi classique » (réseau maison). La page lit et change ce mode par `ReglageGlobal ModeConnexion`. L'esclave redémarre.
- Les niveaux de log `udp` et `modbus` sont posés le temps des essais, puis restaurés à l'arrêt (Ctrl+C) ou par le bouton « Restaurer les logs ».
- Grille ModBus : les sept tests de la grille de `outils_docs/historique/AUDIT_MODBUS_2026-09-29.md` pour un esclave (la cuve par défaut), jugés sur les logs, avec consignes à valider dans la page.
- Aide : raccordement, commandes envoyées, lecture des verdicts.

## Pièges

- Un port série n'accepte qu'un programme : fermer le pont série, le moniteur ou un autre outil avant d'ouvrir le COM ici, ou passer par `pont:7000`.
- Les ports sont ouverts sans basculer DTR/RTS : pas de reset de la carte.
- Le mot de passe Wi-Fi n'apparaît ni dans la page ni dans le journal (remplacé par `***`).
- Tasmota coupe son log série 600 s après son démarrage. Le testeur renvoie `SerialLog` pour le rétablir.
- La bascule de mode redémarre l'esclave et change son réseau : confirmation demandée par la page (`confirme: true`).
- Esclaves derrière le NAPT du maître : leur multicast n'atteint pas le PC sur le Wi-Fi maison.
- Ne jamais émettre vers 224.3.0.1:4000 depuis un essai ou un banc : le vrai maître traiterait un faux push.
- Les POST de la page exigent l'en-tête `X-Testeur: 1`, et `/cmd` envoie une commande libre à une carte.
- Sans `--journal`, rien n'est gardé sur disque (la cible PlatformIO écrit `%TEMP%\testeur_udp.log`).

## Bancs

```
PYPIO outils_docs/scripts_python/outils_pc/test_testeur_udp.py
```

Il inclut ses sous-groupes : `test_testeur_udp_acces.py`, `test_testeur_udp_grille.py`, `test_testeur_udp_muette.py` et `test_testeur_udp_pont.py` (sur le vrai `pont_serie.py` en `loop://`). Ces quatre fichiers ne sont pas autonomes. Les cartes sont simulées par `testeur_udp_sim.py`. Code de sortie 0 = vert.
