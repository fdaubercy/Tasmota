---
name: logs-cartes
description: Use when the user asks to read, follow or check the logs of the Tasmota/ESP32 boards of this fork ("regarde les logs", "suis les logs", "les logs des 2 modules", "vérifie les erreurs", console, syslog, MqttLog, stat/<topic>/LOGGING, pont série) — tells where each log source lives (syslog journal, syslog page :7200, MQTT sniffer :7100, serial bridge :7000, tool directory :7600), the exact read-only commands, how to filter by board / Berry module / level, and the traps (serial port already taken, NAPT slaves, log profiles, never a `pio run` during a build).
---

# Lire les logs des cartes (sans voler de port série)

Points d'acces verifies le 2026-10-18 dans `outils_docs/scripts_python/outils_pc/`. Reference
utilisateur : `outils_docs/README.md` (l. 76-125) ; charte des niveaux : CLAUDE.md, « Logs Berry ».

## 1. D'abord : quels outils tournent ?

```
curl -s http://127.0.0.1:7600/etat      # annuaire : outils[] avec id, etat marche/arrete, port
```
Ids : `pont_serie`, `sniffeur_modbus`, `testeur_udp`, `sniffeur_mqtt`, `syslog`, `synchro_fork`.
Les fiches de `%LOCALAPPDATA%\outils_tasmota\presence\` peuvent etre perimees et **contiennent un
jeton : ne jamais les afficher**. Se fier a `/etat` de l'annuaire.

**Ne lancer un outil que sur demande.** Jamais par sa cible PlatformIO pendant un build (c'est un
`pio run`, il peut vider `.pio/build`) : `python outils_docs/scripts_python/outils_pc/<outil>.py`.

## 2. Les sources

| Source | Ce qu'on y voit | Acces (lecture seule) | Prerequis |
|---|---|---|---|
| Journal syslog | tout ce que les cartes envoient en syslog (Tasmota + Berry) | `tail -n 200 "$TEMP/syslog_tasmota.log"` (puis `.log.1`) | `syslog_tasmota.py` lance **avec `--journal`** (la cible PlatformIO et l'annuaire le font, case « Journal sur disque » depuis le 2026-10-31) ; sortie `syslog` du profil ouverte |
| Page syslog :7200 | flux direct, modules vus | `curl -s http://127.0.0.1:7200/etat`, `/modules` (JSON), `/flux` (SSE, `curl -N -m 5`) | syslog lance |
| Sniffeur MQTT :7100 | `stat/<topic>/LOGGING` par carte | `curl -s http://127.0.0.1:7100/logs` (topics), `curl -s "http://127.0.0.1:7100/logs?module=jardin%2Fcuve"` (3000 lignes max, en memoire) | sniffeur lance, broker 192.168.0.5, sortie `mqtt` de la carte ouverte |
| Pont serie :7000 (:7001…) | console serie d'une carte | `curl -s http://127.0.0.1:7000/etat` (port COM), `curl -s -N -m 5 http://127.0.0.1:7000/flux` (SSE, texte JSON avec sequences ANSI) | pont lance ; il **tient** le port COM |
| Consoles des outils | sortie des outils lances par l'annuaire | `curl -s "http://127.0.0.1:7600/console?id=<id>"` | annuaire lance |

Topics MQTT : maitre P4 `garage`, cuve `jardin/cuve`, rideau `garage/rideau` (`user_config_override.h`).
`SYS_LOG_HOST` = 192.168.0.3 (ce PC), port 514.

**Avant de conclure sur un journal, lire l'horodatage de sa derniere ligne** : un journal ancien veut
dire syslog arrete, pas « aucune erreur ».

## 3. Filtrer

Ligne du journal : `AAAA-MM-JJ HH:MM:SS.mmm <ip:15> <hote:24> <SEV:5> <texte>`.
- **Par carte** : `grep " SERVEUR-GARAGE "` (nom d'hote syslog) ou `grep " 192.168.0.43 "` ; en MQTT,
  `module=<topic>` ; pour le pont, un pont par carte (`/etat` donne le COM).
- **Par module Berry** : prefixe `NOM_MAJ_SNAKE:` en tete du texte — `grep "MODBUS_"`, `grep "UDP_"`.
  Le champ « hote » du journal n'est PAS le module Berry.
- **Par niveau** : `grep -E " (ERR|CRIT|WARN) "`. `erreur` Berry = ERR ; `debug` et `detail` sortent tous
  deux en DEBUG (niveau 3), indiscernables dans le journal.

## 4. Si rien n'apparait

Un message passe **deux** filtres : seuil du module (`ReglageLog <cible> <niveau>`) **et** seuil de la
sortie dans le profil actif (`ReglageLog profil <nom>` ; sorties `serie`/`web`/`mqtt`/`syslog`). En profil
`normal`, `mqtt` est a `erreur` : `stat/<topic>/LOGGING` est quasi muet. Changer un reglage de log
envoie une commande a une carte : **seulement sur demande explicite**.

## 5. Pieges

- Ne jamais ouvrir un port COM tenu par le pont : lire `/flux` du pont.
- Esclaves (cuve, rideau) derriere le NAPT du maitre : garder `ReglageLog profil normal` sur eux ;
  `MqttLog` en debug via le NAPT a fait redemarrer la cuve (WDT). Ne pas toucher a `USE_ESP32_WDT`.
- Une sortie a `detail` (niveau 4 firmware) affiche aussi les `BRY: GC`.
- Publier une commande (`POST /publier` du sniffeur MQTT, en-tete `X-Sniffeur: 1` ; `/envoi` et `/cmd`
  du pont, en-tete `X-Pont: 1`) ecrit dans une carte : jamais pour « lire des logs ».
- Depuis ce PC, un GET passe sans jeton ni en-tete (`acces_web.py`, `controle()`).
