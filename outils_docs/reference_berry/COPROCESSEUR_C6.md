# Coprocesseur Wi-Fi ESP32-C6 des P4

Tiré de `outils_docs/README.md` le 2026-11-23 (plan `binomes-berry`, A20). Aiguillage : `outils_docs/INDEX.md`.

## Firmware du coprocesseur Wi-Fi des P4 (ESP32-C6)

Sur le P4, le Wi-Fi passe par un ESP32-C6 (esp_hosted). Son firmware se met à jour à part, par `HostedOta` ; rien ne
le signalait. `data/fs/controleCoprocesseur.be` (solidifié sur le P4, exclu des autres cartes) le fait :

- **Version visée** : celle de la bibliothèque compilée dans le firmware du P4 (champ `Host` de la commande `Hosted`).
  Le C6 doit avoir la même. Le fichier sans numéro de version du serveur n'est pas suivi : il était en 2.12.6 quand
  l'hôte était en 2.12.13 (26/10/2026). La version visée est lue dans `…/coprocessor/v<Host>/network_adapter_<MCU>.bin`.
- **Quand** : au démarrage seulement, car les deux versions ne changent qu'au redémarrage. 20 s après le chargement,
  lecture locale de `Hosted`. C6 à jour : fin, **aucun accès réseau**. C6 en retard : une ligne d'alerte apparaît sur
  l'accueil, puis une seule requête est envoyée 3 min après le démarrage. Elle lit les 512 premiers octets du fichier
  (`Range`), dont l'en-tête d'image donne la version réellement publiée. En cas d'échec réseau, nouvel essai toutes
  les heures, 6 au plus.
- **Page `/coprocesseur`** (lien de la ligne d'alerte) : versions, état sur le serveur, URL. Le bouton « Mettre à jour
  le coprocesseur » (avec confirmation) lance `HostedOta <URL complète>`. Le Wi-Fi du P4 et le point d'accès des
  esclaves sont coupés une à deux minutes, puis le P4 redémarre. L'alerte disparaît si la mise à jour a réussi.
- **Échec et nouvel essai** : le module suit le résultat de `HostedOta` (et de `HostedLoad`, même tapées en console)
  par une règle. Sur `Failed <code>`, la ligne d'accueil indique « échec de la mise à jour ». La page affiche le code et
  sa cause (-1 = téléchargement impossible), puis le bouton revient sous le nom « Réessayer la mise à jour ». Le C6
  garde son firmware et le Wi-Fi marche comme avant. L'échec est journalisé en `erreur`.
- **C6 bloqué (`Failed 5379`)** : `ESP_ERR_OTA_VALIDATE_FAILED`, l'image arrive en entier mais le C6 la refuse. C'est le
  bug [esp-hosted-mcu #143](https://github.com/espressif/esp-hosted-mcu/issues/143) : programme de démarrage d'usine
  en DIO + application 2.1 à 2.8 en QIO reçue par le réseau (cas du P4 du garage, en 2.6.6). Plus aucune mise à jour
  par le réseau ne passe : seul un **flash série du C6** (C6_U0TXD, C6_U0RXD, C6_IO9 à la masse au démarrage, P4 en
  mode téléchargement) avec une version 2.9 ou plus le débloque. Le module note la version bloquée dans le persist
  (`serveur.coprocesseur.bloque`) : ensuite, ni bouton ni requête au serveur, et la ligne d'accueil ne s'affiche que
  pendant la **première minute après le démarrage**. La page `/coprocesseur` (explication, lien du ticket) et le MQTT
  (`"Bloque": true`) gardent l'information. Une autre version lue sur le C6 (flash série fait) efface la clé.
  La clé est **écrite dans le `_persist.json` du dépôt** (P4 du garage, et toute nouvelle carte P4) : une clé
  apprise sur la carte seule serait perdue au flash série suivant, qui réécrit le FS, persist compris.
- **Réglage** : bloc `serveur.coprocesseur` du persist,
  `{"activation": "ON", "url": "https://ota.tasmota.com/tasmota32/coprocessor", "mqtt": "ON"}`.
  Logs sur la cible `general`, préfixe `COPROCESSEUR`.
- **MQTT** (`"mqtt": "ON"`, absent = OFF ; ON sur le P4 du garage) : `tele/<topic>/COPROCESSEUR`, message **retenu**,
  publié à chaque changement d'état (versions lues, réponse du serveur, mise à jour lancée ou ratée) et à chaque
  connexion au broker : `{"MCU": "esp32c6", "Version": "2.6.6", "Attendue": "2.12.13", "AJour": false, "Publiee": true,
  "Lancee": false, "Echec": "Failed 5379", "Bloque": true}` (`Publiee` vaut `null` tant que le serveur n'a pas répondu ;
  `Echec` vaut `null` sans échec). C'est un topic à part : le JSON `SENSOR`, lu par
  Influx et Node-RED sur le Pi et par l'historique, n'est pas modifié.
- **Nouvelle carte P4** : la page « Fichiers Berry par env » pose l'alerte selon la **puce de la base**, quel que soit
  le modèle (`fichiers_berry_coprocesseur.py`). Sur une base P4, elle ajoute le bloc au persist (avec
  `"bloque": "2.6.6"`, ajoutée aussi à un bloc qui ne l'a pas, voir « C6 bloqué »), ajoute la ligne
  `demarrage.charge` à l'autoexec et retire le module des exclusions. Pour une carte d'une autre puce créée depuis le
  P4, elle passe `activation` à `OFF`, retire le module de la solidification et l'exclut du LittleFS. Chaque
  ajustement est annoncé dans la page et visible dans le diff.
- **Banc** : `python outils_docs/scripts_python/berry/banc_coprocesseur.py` (code 0 = vert ; inclut le rendu de la
  page dans Chrome ; `--sans-navigateur` pour la partie Berry seule).

<hr></hr>
