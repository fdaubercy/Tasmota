# Pont série

Port : 7000 (TCP brut et page web sur le même port). Cible PlatformIO : `pont_serie` (Custom). Tâche VS Code : « Outil : pont serie (port USB seul, tcp 7000) ».

## Lancer

Avec le Python de PlatformIO (il fournit `pyserial`) :

```
%USERPROFILE%\.platformio\penv\Scripts\python.exe outils_docs/scripts_python/outils_pc/pont_serie.py
```

Options (`pont_serie.py::main`) :

- `--port auto|COM11|loop://|aucun` : `auto` prend le seul port USB présent, sinon le pont démarre port fermé.
- `--vitesse 115200`, `--tcp 7000`, `--journal fichier.log` (copie brute sans couleurs).
- `--sans-couleurs` pour une carte non Tasmota, `--relance-log` pour renvoyer `SerialLog` à la carte.
- `--lister` affiche les ports série et sort. `--local` limite l'écoute à 127.0.0.1. `--sans-navigateur` n'ouvre pas la page.

Pendant un build, ne jamais passer par la cible PlatformIO (c'est un `pio run`) : lancer le script en Python direct. Depuis un autre appareil du réseau, ouvrir le lien « depuis un autre appareil » affiché par la console : il porte le jeton de la session.

## Ce que fait la page

- Ouvre le port série d'une carte et le partage : page web `http://127.0.0.1:7000` et flux TCP brut pour d'autres clients (extension VS Code « Serial Monitor » en mode TCP, PuTTY en Raw).
- Affiche les logs en direct, colorés selon le niveau Tasmota et le module Berry émetteur, avec filtre.
- Bouton Démarrer / Arrêter : Arrêter libère le port (pour un flash) sans fermer la page. Le port et la vitesse se changent depuis la page.
- Envoi en Texte (fin de ligne au choix), en Hex ou en Binaire, avec CRC ModBus en option ; réception affichée en Texte ou en Hex.
- Bouton « + Terminal » : lance un pont secondaire (option `--enfant`) sur le premier port TCP libre, pour suivre plusieurs cartes côte à côte. Il s'arrête avec le pont qui l'a lancé.
- Case « Relancer le log série Tasmota » : Tasmota coupe son log série 600 s après son démarrage, le pont renvoie `SerialLog` à l'ouverture du port et à chaque coupure annoncée. La case est propre à chaque terminal.

## Pièges

- Un port série n'accepte qu'un programme : cliquer Arrêter avant tout flash, et ne jamais ouvrir à côté un COM que le pont tient (lire son flux à la place).
- Le port est ouvert sans basculer DTR/RTS : pas de reset de l'ESP32 à l'ouverture.
- Depuis le réseau, seule la page répond (avec jeton). Une connexion TCP brute venue d'un autre appareil est fermée.
- Chaque POST de la page exige l'en-tête `X-Pont: 1` : `/cmd` et `/envoi` écrivent dans la carte, jamais pour « lire des logs ».
- Port TCP déjà pris : le pont sort avant d'avoir pris le port série. Un autre pont tourne probablement, utiliser `--tcp 7001`.
- Le pont ne crée pas de journal par défaut : sans `--journal`, rien n'est gardé sur disque (la cible PlatformIO écrit `%TEMP%\pont_serie_<env>.log`).
- Le testeur UDP peut passer par le pont avec `pont:7000` au lieu d'un COM.

## Bancs

Depuis la racine du dépôt, avec le Python de PlatformIO (`PYPIO`) :

```
PYPIO outils_docs/scripts_python/outils_pc/test_pont_serie_acces.py
PYPIO outils_docs/scripts_python/outils_pc/test_testeur_udp.py
```

Le premier lance le vrai `pont_serie.py` en `loop://` sur un port TCP libre (accès depuis le réseau, jeton, relance du log) avec des mutants. Le second couvre le groupe « pont ». Code de sortie 0 = vert. Aucun banc n'ouvre un vrai COM ni le port 7000.
