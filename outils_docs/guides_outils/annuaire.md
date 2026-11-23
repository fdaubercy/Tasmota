# Annuaire des outils

Tiré de `outils_docs/README.md` le 2026-11-23 (plan `binomes-berry`, A20). Aiguillage : `outils_docs/INDEX.md`.

Port : 7600. Cible PlatformIO : `annuaire` (Custom). Tâche VS Code : « Outil : annuaire des outils (http://127.0.0.1:7600) ».

## Lancer

La tâche VS Code démarre l'annuaire toute seule à l'ouverture du dossier (`runOn: folderOpen`) et ouvre sa page dans le navigateur. La première fois, VS Code demande d'autoriser les tâches automatiques (`Tasks: Manage Automatic Tasks`, Allow). Si l'annuaire tourne déjà (deuxième fenêtre), il ouvre seulement la page.

À la main :

```
%USERPROFILE%\.platformio\penv\Scripts\python.exe outils_docs/scripts_python/outils_pc/annuaire_outils.py
```

Options (`annuaire_outils.py::principal`) : `--http 7600`, `--local` (127.0.0.1 seulement), `--sans-navigateur`. Un second lancement sur le même port sort sans rien démarrer.

Pendant un build, ne pas passer par la cible PlatformIO (c'est un `pio run`) : lancer le script en Python direct. Depuis un autre appareil, ouvrir le lien « depuis un autre appareil » affiché par la console : il porte le jeton de la session.

## Ce que fait la page

- Liste les outils PC de `outils_docs/scripts_python/outils_pc/`, rangés par groupes : Bus et cartes, Réseau et journaux, Déploiement, Configuration des cartes, Ateliers, Dépôt et références. Le registre est `annuaire_registre.py::OUTILS`.
- Montre pour chaque outil s'il tourne (fiches de présence sous `%LOCALAPPDATA%\outils_tasmota\presence\`, PID vérifié) et sur quel port.
- Lance un outil avec ses paramètres (port série, vitesse, port de la page). La fenêtre de lancement liste les ports série détectés et dit quel outil tient chacun. Les derniers paramètres choisis sont gardés dans `derniers.json` et reproposés.
- Arrête un outil (bouton Arrêter) : arrêt de tout l'arbre de processus, puis vérification de la mort.
- Affiche la console de l'outil lancé, tant que le panneau est ouvert. Elle est écrite dans `%LOCALAPPDATA%\outils_tasmota\consoles\<id>.log`.
- Une barre « Annuaire » s'ajoute en haut de la page de chaque outil, avec la liste des outils en cours.

## Pièges

- Les outils lancés par l'annuaire s'arrêtent avec lui, même s'il meurt brutalement (Job Object Windows). Exceptions hors du job : la synchro du fork, la page Build et la session FTP des cartes. L'annuaire refuse d'arrêter la synchro pendant un merge, un rebase ou un push, la page Build pendant un lancement, le navigateur FTP pendant une session ouverte.
- Un client de ce PC doit viser `127.0.0.1:<port>`, `localhost:<port>` ou `[::1]:<port>` (403 sinon) : parade contre le DNS rebinding.
- Les POST `/lance` et `/arrete` exigent l'en-tête `X-Annuaire: 1` et une origine autorisée.
- Le jeton est commun : l'annuaire le passe aux outils qu'il lance, et le cookie d'un outil ouvre les autres. Il vaut pour le réseau privé seulement. Ne jamais afficher les fiches de présence : elles contiennent un jeton.
- Une fiche de présence peut être périmée. Se fier à `GET /etat` de l'annuaire, pas aux fichiers.
- Port 7600 pris par un autre programme : l'annuaire sort en code 1 en le disant.
- Pare-feu Windows : autoriser Python sur les réseaux privés au premier lancement, sinon les autres appareils n'atteignent pas la page.

## Bancs

```
PYPIO outils_docs/scripts_python/outils_pc/test_annuaire.py
PYPIO outils_docs/scripts_python/outils_pc/test_annuaire_lanceur.py
PYPIO outils_docs/scripts_python/outils_pc/test_annuaire_securite.py
```

`test_annuaire_cache.py` et la sonde Chrome `test_annuaire_lieux_chrome.py` existent aussi. Le commun d'accès (`acces_web.py`) a son banc `test_acces_web.py` et la sonde `test_acces_repli_chrome.py`. Code de sortie 0 = vert.

## Lieu de travail : annuaire, syslog et sniffeur MQTT

Le lieu (garage, cave, bureau...) vient de la seule table `outils_pc/lieux.py`. Les noms d'hôte, les topics et les adresses IP
des cartes sont lus dans les `_persist.json` du dépôt (`lieux.py::identites`), jamais saisis à la main.

- **Annuaire (7600)** : la rangée de puces « Lieu de travail » (Tous, puis un lieu par puce) ajoute `?lieu=<code>` au lien
  « Ouvrir » des outils qui s'en servent (Build, Fichiers Berry, Assistant persist, Atelier des graphiques, Étiquettes QR, Atelier des écrans,
  Fabrique d'extensions, Atelier des visuels, syslog, sniffeur MQTT, Navigateur FTP des cartes). Rien n'est caché ni arrêté ; le choix est retenu par le navigateur.
- **Syslog (7200)** : des puces de lieu (Tous, un par lieu, Autres) comptent les lignes et les erreurs de chaque lieu et filtrent
  la liste, la barre et la liste des modules. Chaque ligne porte l'étiquette de son lieu, tiré du nom d'hôte (casse ignorée) puis,
  à défaut, de l'IP de l'émetteur ; un hôte inconnu va dans « Autres ». Le lieu choisi n'est pas mémorisé d'une visite à l'autre.
- **Sniffeur MQTT (7100)** : mêmes puces et même étiquette sur les messages (lieu tiré du topic de la carte), sans toucher aux
  abonnements. L'arborescence des topics est rangée par lieu, l'env de la carte entre parenthèses sur son nœud ; les listes de
  cartes des panneaux « Logs » et « Commande » sont groupées par lieu. Le lieu choisi n'est pas mémorisé.
- **Arrivée avec `?lieu=`** : la page ouverte met le lieu en avant une seule fois, avec un bandeau « Lieu : X (depuis l'annuaire) »
  et une croix « Tous les lieux ». La croix retire le paramètre et le bandeau ; sur le syslog et le sniffeur MQTT,
  elle remet aussi la puce « Tous ». Ailleurs, elle ne change aucune liste. Un code inconnu est ignoré.
  Pour la page Build, voir « Arrivée avec `?lieu=` » dans `build_web.md`.

<hr></hr>
