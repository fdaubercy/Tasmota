---
name: bancs
description: Use after modifying a Berry module of data/fs (modbusFonctions, ledsFonctions, udpFonctions, discoveryFonctions, rangeExtenderFonctions, logFonctions, globalFonctions) or a Python tool of outils_docs/scripts_python (outils_pc/, maintenance/), or when the user asks to "lance les tests", "lance le banc", "vérifie que rien n'est cassé" — tells which test bench covers the modified file, the exact command, how to read green/red, and the traps (PlatformIO Python for pyserial, Berry benches without exit code, never 224.3.0.1:4000, --reel uses the network, test_rs485_pc is NOT a bench).
---

# Bancs de test du fork Tasmota

Quel banc lancer après une modification, comment le lancer, comment lire le résultat.
Commandes **depuis la racine du dépôt**. `P` = `outils_docs/scripts_python`.

## Règles communes (pièges vérifiés)

- **Python des bancs `outils_pc/`** : celui de PlatformIO, `"$USERPROFILE/.platformio/penv/Scripts/python.exe"`
  (abrégé `PYPIO` ci-dessous). Le Python du PATH n'a pas `pyserial` : `pont_serie`, `sniffeur_modbus*`,
  `testeur_udp*` y échouent sur `import serial`. Les bancs `berry/` et `maintenance/` marchent avec `python`.
- **Bancs Python** : code de sortie 0 = vert, 1 = rouge. Lignes `OK`/`KO` par cas, puis selon le banc
  `VERT` / `ROUGE : N echec(s)`, `BANC_SNIFFEUR: OK|ECHEC (...)`, ou `N verifications reussies, N echec(s)`.
- **Bancs Berry** : `berry.exe` ne pose **pas** de code de sortie. Seule la **dernière ligne** compte
  (`BANC_MODBUS: OK|ECHEC`, `BANC_LEDS: OK|ECHEC`, `TEST_DISCOVERY: OK|ECHEC (N tests...)`). Les enveloppes
  `.py` la traduisent en code 0/1 : les préférer quand elles existent.
- **Témoins** : chaque banc contient des cas qui DOIVENT échouer (règle de `tasks/lessons.md`). Un banc
  modifié pour passer au vert sans témoin ne prouve rien.
- **Aucun banc n'ouvre un vrai port COM ni les ports des outils** (7000, 7001, 7100, 7200, 7300, 514) :
  `loop://` et ports tirés au hasard. Ils peuvent tourner pendant que les outils sont ouverts.
- **Pendant un build** : les bancs ne lancent pas PlatformIO, mais le build solidifie `data/fs`. Pour un
  banc Berry pendant un build, passer une **copie complète** de `data/fs` en argument (une copie partielle
  donne `io_error`).
- **Multicast** : ne JAMAIS viser 224.3.0.1:4000 dans un essai (le vrai maître P4 traiterait un faux push).
  Les bancs utilisent un groupe/port de test en TTL 0 : ne pas « corriger » vers la vraie adresse.
- **`P/outils_pc/test_rs485_pc.py` n'est PAS un banc** : c'est l'outil du bus RS485 réel (convertisseur
  CH343, matériel requis). Ne jamais le lancer comme vérification.
- La syntaxe Berry est déjà vérifiée à chaque édition par le hook `verifie_berry_edition` : un banc
  vérifie le **comportement**, pas la syntaxe.

## Fichier modifié → banc à lancer

| Fichier modifié | Banc | Commande |
|---|---|---|
| `data/fs/modbusFonctions.be`, `logFonctions.be`, `globalFonctions.be` | ModBus (Berry) | `python P/berry/banc_test_modbus.py [dossier_sources]` |
| `data/fs/ledsFonctions.be` | LEDs (Berry) | `python P/berry/banc_leds.py [dossier_sources]` |
| `data/fs/diversFonctions.be` (`hiberneDriversInactifs` : veille des drivers inactifs, ligne 31 des autoexec, LittleFS neuf sans `/json`) | veille des drivers (Berry) | `lib/libesp32/berry/berry.exe P/berry/banc_veille_drivers.be [dossier_sources]` depuis la racine (verdict = dernière ligne `BANC_VEILLE_DRIVERS: OK`) |
| `data/fs/graphiquesFonctions.be`, `historiqueFonctions.be`, `historiqueSeries.be` (séries découvertes, compteurs, route `/graphiques`), `data/sd/js/graphiques.js`, `graphiques_trace.js`, `graphiques_edition.js` (page composable, POST `/graphiques`), `data/sd/html/graphiques.html`, `data/sd/css/graphiques.css`, `graphiques.json` du P4 et de la cuve, `data/sd/js/echarts.min.js.gz`, route `/histo?p=direct`, filtre de `data/garage/tasmota32p4-serveur-modbus/controleGarage.be`, bloc `diverses.historique` du persist du P4, bouton Grafana de `data/fs/controleWeb.be` (`boutonGrafana`) | graphiques (Berry + rendu Chrome) | `python P/berry/banc_graphiques.py` (~2 min 30, ~200 contrôles dont `banc_historique.be` ; `--sans-navigateur` = Berry seul, rendu NON vérifié ; `--garde DOSSIER` garde page et DOM). Copie mutée : `berry.exe P/berry/banc_graphiques.be <sortie> <dossier_sources>` ou `berry.exe P/berry/banc_historique.be <sortie> <dossier_sources>` (copie ENTIÈRE de data/fs) |
| `data/garage/tasmota32p4-serveur-modbus/autoexec.be` et son `_persist.json`, `data/fs/configGlobal.be`, `configDevices.be`, `controleGeneral.be` (dont `surveilleWifi`), `globalFonctions.be` (règles de démarrage, `armeRebootQuotidien`), tout `controleXxx.be` chargé par l'autoexec du P4 | démarrage du P4 (Berry, autoexec ENTIER) | `python P/berry/banc_boot.py [dossier_sources]` (~1,5 s ; 5 cas, un `berry.exe` par cas ; cas 5 = `web_sensor` de `controleGarage.be` sans bloc COUNTER ; `CONNU` = défaut connu non bloquant (`DEFAUTS_CONNUS` en tête du `.be`), `CORRIGE ?` = défaut corrigé, passer son drapeau à `false`) ; copie mutée : copie ENTIÈRE de data/fs en argument |
| `data/fs/udpFonctions.be`, `discoveryFonctions.be`, `rangeExtenderFonctions.be` | discovery (Berry) | `lib/libesp32/berry/berry.exe P/berry/test_discovery.be [dossier_sources] [dossier_bouchons]` puis **lire la dernière ligne** |
| `P/outils_pc/acces_web.py` | **9 bancs** (commun à toutes les pages) | `test_acces_web.py`, puis `test_annuaire.py`, `test_annuaire_securite.py`, `test_pont_serie_acces.py`, `test_sniffeur_mqtt_acces.py`, `test_syslog_acces.py`, `test_sniffeur_modbus.py`, `test_testeur_udp.py`, et `python P/maintenance/test_synchro_fork_web.py` |
| `P/outils_pc/annuaire_*.py` | annuaire | `PYPIO P/outils_pc/test_annuaire.py`, `test_annuaire_lanceur.py`, `test_annuaire_securite.py` |
| `P/outils_pc/sniffeur_modbus*.py`, `decodeur_modbus.py`, `surveillance_modbus.py`, `emulation_modbus.py`, `debit_modbus.py`, `ecoute_udp.py`, `client_mqtt.py` | sniffeur ModBus | `PYPIO P/outils_pc/test_sniffeur_modbus.py` (tous les groupes, dont un fuzz de 20 000 trames) |
| `P/outils_pc/sniffeur_mqtt*.py` | sniffeur MQTT | `PYPIO P/outils_pc/test_sniffeur_mqtt_acces.py` |
| `P/outils_pc/syslog_tasmota*.py` | syslog | `PYPIO P/outils_pc/test_syslog_acces.py` |
| `P/outils_pc/pont_serie*.py` | pont série | `PYPIO P/outils_pc/test_pont_serie_acces.py`, et `test_testeur_udp.py` (groupe pont) |
| `P/outils_pc/testeur_udp*.py` | testeur UDP | `PYPIO P/outils_pc/test_testeur_udp.py` (inclut ses 4 sous-groupes `test_testeur_udp_*.py`, non autonomes) |
| `P/maintenance/synchro_fork_*.py` | synchro du fork | `python P/maintenance/test_synchro_fork_web.py` ; `--reel` seulement avec l'accord de l'utilisateur |

Non autonomes (pas de `__main__`, ne pas lancer seuls) : `test_sniffeur_modbus_acces.py` (appelé par
`test_sniffeur_modbus.py`) et les 4 `test_testeur_udp_{acces,grille,muette,pont}.py`.

## Ce qui n'a pas de banc

- Berry : tous les autres `data/fs/*.be`. Seule la syntaxe est vérifiée (hook). Le dire à l'utilisateur
  plutôt que d'annoncer « testé ».
- Pages et aides HTML/JS des outils (`*_web.py`, `*_aide.py`, `*_panneaux.py`, `annuaire_page.py`,
  `testeur_udp_grille_web.py`) : aucun banc n'exécute leur JavaScript. Une page se vérifie dans un vrai
  navigateur (Chrome headless + sonde, ou DevTools pour les pages à flux SSE : voir `tasks/lessons.md`,
  2026-10-16 et 2026-10-17).
- `synchronise_fork_tasmota.py` / `synchronise_upstream_tasmota.py` : seulement par `--dry-run`
  (ou `test_synchro_fork_web.py --reel`, qui les lance en `--dry-run` ; il accède au réseau).
- `corrige_reglages_vscode.py` : se prouve lui-même par `--verifier`.

## Limites à rappeler en rendant un résultat

- `--reel` (synchro du fork) : vrais scripts en `--dry-run`, mais `git fetch upstream` et appels GitHub.
- Un banc vert ne remplace pas l'essai sur carte : les bancs Berry n'ont ni timing réel, ni bus RS485,
  ni ruban, ni bouton ; `test_discovery` n'émet aucun UDP réel.
