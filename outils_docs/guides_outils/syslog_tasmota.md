# Serveur syslog

Port : 7200 (page web). Écoute UDP 514 par défaut. Cible PlatformIO : `syslog_tasmota` (Custom). Tâche VS Code : « Outil : serveur syslog (http://127.0.0.1:7200) ».

## Lancer

Aucune dépendance, tout Python 3.8 ou plus :

```
python outils_docs/scripts_python/outils_pc/syslog_tasmota.py --http 7200 --journal
```

Options (`syslog_tasmota.py::main`) :

- `--port 514` : port UDP. Défaut : `SYS_LOG_PORT` de `tasmota/user_config_override.h`, sinon 514.
- `--ecoute 0.0.0.0` : adresse d'écoute UDP. Pas besoin d'être administrateur sous Windows.
- `--http 7200`, `--historique 5000` (lignes rejouées à l'ouverture de la page).
- `--journal [fichier]` : sans nom de fichier, `%TEMP%\syslog_tasmota.log`. `--journal-max 20` : taille en Mo au-delà de laquelle le journal bascule en `.log.1` (0 : jamais).
- `--local`, `--sans-navigateur`.

Pendant un build, lancer le script en Python direct, jamais la cible PlatformIO. Depuis un autre appareil, utiliser le lien à jeton de la console. Lancé par l'annuaire, le journal sur disque est toujours actif.

## Ce que fait la page

- Reçoit en UDP les lignes de log des cartes (RFC 5424, et les formats plus anciens) et les affiche en direct.
- Filtre par module, sévérité et texte, pause, export.
- Registre des modules vus : IP, nombre de lignes, dernière réception.
- Classement par lieu de travail : la page lit `?lieu=` (route `GET /lieux`).
- Routes de lecture utiles à la ligne de commande : `GET /etat`, `GET /modules`, `GET /flux` (SSE). Aucun POST : la page ne fait que lire.

Une ligne du journal : `AAAA-MM-JJ HH:MM:SS.mmm <ip> <hôte> <SEV> <texte>`. Filtrer par carte avec le nom d'hôte, par module Berry avec le préfixe `NOM_MAJ_SNAKE:` du texte, par niveau avec `ERR`, `WARN`. L'hôte du journal n'est pas le module Berry.

## Pièges

- Les cartes envoient à `SYS_LOG_HOST:SYS_LOG_PORT` : cette adresse doit désigner ce poste, sinon rien n'arrive. Elle se règle à chaud par `LogHost`, `LogPort`, `SysLog`.
- Avant de conclure sur un journal, lire l'horodatage de sa dernière ligne : un journal ancien veut dire syslog arrêté, pas « aucune erreur ».
- Un message passe deux filtres : le seuil du module (`ReglageLog <cible> <niveau>`) et le seuil de la sortie `syslog` du profil actif (`ReglageLog profil <nom>`). `debug` et `detail` sortent tous deux en DEBUG.
- Pas de `SO_REUSEADDR` : un second serveur sur le même port UDP refuse de démarrer. Ne pas en lancer un deuxième.
- Le jeton protège la lecture des logs depuis le réseau.
- Changer un réglage de log envoie une commande à une carte : seulement sur demande.

## Bancs

```
PYPIO outils_docs/scripts_python/outils_pc/test_syslog_acces.py
PYPIO outils_docs/scripts_python/outils_pc/test_syslog_page_chrome.py
```

Le premier couvre l'accès, le second est la sonde Chrome de la page (jamais pendant un build). Aucun banc n'ouvre le port 514. Code de sortie 0 = vert.
