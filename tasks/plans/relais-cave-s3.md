---
chantier: relais-cave-s3
titre: Cave — envs ESP32/S3 alignés sur la carte en ligne, audit de l'env S3, carte S3 8 relais de remplacement
statut: actif
cree: 2026-10-31
maj: 2026-10-31
source: concurrent-crafting-knuth.md
objectif: Aligner les envs de la cave sur les broches de la carte en ligne, auditer l'env S3 et choisir une carte ESP32-S3 à 8 relais pour la remplacer
---
# Cave — envs ESP32/S3 alignés sur la carte en ligne, audit S3, carte de remplacement

## Contexte
La carte de la cave en ligne (192.168.0.48) est un ESP32-D0WD-V3 sans PSRAM, 4 Mo, alimenté en
**DC 7-30 V sur bornier**, avec le modèle « ESP32 Relay x8 ». Elle tourne en firmware 13.3.0.3 du
13/01/2024, avec l'ancien code (`data/cave/tasmota32-serveur-rly-sauvegarde/`, autoexec identique
octet pour octet). Son persist et son template ont été relus le 31/10 (`/ufsd?download=`, `/cm?cmnd=Template`) :

| Fonction | GPIO en ligne | Dépôt aujourd'hui |
|---|---|---|
| Relais 1-5 (pompe vide-cave, ventilation, LED machines, pompe cuve, lavage) | 32, 33, 25, 26, 27 | identique (S3 : 5, 6, 7, 16, 17) |
| Boutons 1-3 | 4, 0, 18 | identique |
| LED témoin | 23 | identique (S3 : 21) |
| Thermomètre AM2301 | 22, **ON** | **OFF** dans les deux persists |
| Capteurs de niveau bas / haut | 2 / 15, **OFF**, pas de Switch dans le template | **ON**, Switch1/Switch2 ajoutés au template |

Template en ligne : `[33,1,1,1,32,1,1,1,1,1,1,1,1,1,34,1,1,1,1216,288,1,226,227,228,1,1,1,1,224,225,1,1,1,1,1,1]`.

Décisions prises :
- seules les **broches et les templates** sont alignés ; l'identité (IP .243, topic `-v2`) n'est pas touchée ;
- sur la S3, le GPIO 22 n'existe pas : **AM2301 sur le GPIO 11** (choix de l'utilisateur) ;
- la carte de remplacement est alimentée en DC 7-30 V, comme l'actuelle ;
- l'audit est en **lecture seule** : rapport + plan d'action `en-pause`, rien n'est corrigé ;
- les propositions de cartes sont livrées en **photos PNG**, une par carte, nommées par lettre, avec leurs liens.

Contraintes : un build du P4 (`erase_upload`) tourne → `tasmota/user_config_override.h` n'est édité
qu'après sa fin (un build réécrit ce fichier). Jamais de `pio run` de ma part pendant un build de l'utilisateur.

## A1 — Env ESP32 `tasmota32-cave-serveur-rly` aligné sur la carte en ligne
- [x] Aucun `pio run`/scons en cours juste avant les éditions (garde_build / Win32_Process) — preuve : 10:12:28, 0 processus pio run/scons
- [x] `user_config_override.h` (branche `#else` du `USER_TEMPLATE` de la section cave) : 160 et 161 retirés → template identique octet pour octet à celui de la carte en ligne — preuve : template ESP32 du .h = persist ESP32 = carte en ligne (comparaison scriptée : True)
- [x] `data/cave/tasmota32-serveur-rly/_persist.json` : `pompeVideCave.capteurs.capteur1/2` en `activation: OFF` (broches 2/15 gardées), `Thermo-Hygrometre.thermometre1` en `activation: ON` (GPIO 22, type 1216) ; template du bloc `modele` du persist aligné s'il en porte un ; édition par Edit, texte d'origine conservé (pas de réécriture par `json.dump`) — preuve : git diff du persist (5 valeurs), relance de pompe sans effet sur capteur désactivé (controleGeneral.be::niveauHautActif)
- [x] Contrôle : JSON relu par `json.load` ; template décodé GPIO par GPIO = celui de la carte en ligne (script du scratchpad) — preuve : verif_cave.py « identique a la carte en ligne : True », aucun doublon

## A2 — Env S3 `tasmota32s3-cave-serveur-rly` aligné (même logique, broches S3)
- [x] `user_config_override.h` (branche S3 du `USER_TEMPLATE`) : 160 (GPIO 2) et 161 (GPIO 15) retirés, 1216 (AM2301) posé à l'index du GPIO 11 — preuve : remplacé par le plan cave-s3-waveshare (A3) : template de la Waveshare
- [x] `data/cave/tasmota32s3-serveur-rly/_persist.json` : capteurs de niveau OFF, `thermometre1` ON sur le **pin 11** ; template du bloc `modele` aligné — preuve : verif_cave.py (template S3 38 cases, AM2301 au GPIO 11 ; l'ancien était le tableau ESP32 de 36 cases)
- [x] Commentaire de l'env S3 dans `platformio_tasmota_cenv.ini` mis à jour (AM2301 sur le GPIO 11, capteurs de niveau inactifs comme sur la carte en ligne) — preuve : remplacé par le plan cave-s3-waveshare (A3) : commentaire réécrit pour la Waveshare
- [x] Contrôle : JSON valide ; aucune broche interdite S3 (19-20, 26-37, 43-46) ; aucun doublon de broche dans le persist — preuve : verif_cave.py « interdits S3: [] », « doublons: [] »
- [x] `banc_demarrage.py` (skill `bancs`) : si l'instantané de la cave S3 change, la différence = exactement ces broches, puis instantané mis à jour — preuve : écart règles Switch1/2 -> Tele#AM2301 ; écart « sources 3 -> 1 » antérieur (témoin HEAD identique, référence non réenregistrée depuis 91bbae69a) ; --enregistre puis VERT

## A3 — Audit en lecture seule de l'env S3 relais cave
- [x] Périmètre relu : — preuve : outils_docs/AUDIT_RELAIS_CAVE_S3_2026-10-31.md (cenv, .h, data/cave S3, écarts de fonctions)
  - section du cenv (solidification, `custom_files_exclude`, pages embarquées, partitions N16R8, ports) ;
  - section `#if` du `.h` (identité, Range Extender, options) ;
  - `data/cave/tasmota32s3-serveur-rly/` : autoexec, `controlePompeVideCave.be` comparé à la copie ESP32, persist comparé au modèle du parc ;
  - écarts de fonctions avec la carte en ligne (topic `cave/serveur-rly-cave` contre `-v2`, Node-RED et Telegram, capteurs).
- [x] Rapport `outils_docs/AUDIT_RELAIS_CAVE_S3_2026-10-31.md` : pour chaque point, ce qui est en place, ses avantages, ses inconvénients, une proposition — preuve : P1-P11 ; P2 (COM3) et P5 (UDP/RangeExtender ON sur S3) revérifiés dans le cenv et le persist
- [x] Plan d'action `tasks/plans/audit-relais-cave-s3.md`, statut `en-pause` (l'utilisateur décide) — preuve : fichier créé, 6 actions, aucune cochée
- [x] Aucun fichier de code, de config ni de build modifié par l'audit (`git status` avant/après) — preuve : git status avant/après de l'audit, seuls ses 2 livrables en plus (les autres écarts sont de cette conversation)

## A4 — Cartes ESP32-S3 à 8 relais capables de remplacer la carte en ligne
- [x] Critères écrits — preuve : outils_docs/cartes_relais_cave/README.md § Critères (7 critères)
  - ESP32-S3 avec PSRAM (N16R8 de préférence : c'est la cause du remplacement) ;
  - 8 relais d'au moins 10 A ;
  - alimentation DC qui couvre 7-30 V ;
  - assez d'entrées libres pour 3 boutons, 2 capteurs de niveau et l'AM2301 ;
  - relais pilotés par GPIO direct ou par un expandeur que Tasmota sait piloter (vérifié dans `tasmota/tasmota_xdrv_driver/`) ;
  - fixation et encombrement comparés à la carte actuelle ;
  - prix et disponibilité en France ou dans l'UE.
- [x] Recherche web : au moins 3 candidates — preuve : README, 4 cartes (A Waveshare 8DI-8RO, B variante -C, C KinCony KC868-A8v3 incompatible PCF8575, D LilyGO T-Relay S3 hors critère 6 relais)
- [x] Photos téléchargées dans `outils_docs/cartes_relais_cave/` (`carte-A.png`, `carte-B.png`…), chacune regardée (Read) avant livraison — preuve : carte-A..D.png ouvertes le 2026-10-31, bonne carte sur chacune
- [x] `outils_docs/cartes_relais_cave/README.md` : tableau comparatif selon les critères, lien vers chaque site, recommandation motivée, incompatibilités nommées (expandeur, entrées optocouplées, alimentation) — preuve : README (liens curl 200, sauf 2 OpenELab en 429 signalés) ; driver TCA9554 vérifié : tasmota/tasmota_xdrv_driver/xdrv_69_pca9557.ino (cite la Waveshare 8DI-8RO)

## A5 — Commit
- [ ] `git commit -- <chemins de ce plan seulement>`, message en français sans accents. ⚠️ `user_config_override.h` porte déjà des changements de build (CFG_HOLDER) : les montrer à l'utilisateur avant de les inclure.
- [ ] `git show --stat HEAD` relu

## Améliorations restantes
- [ ] [projet] Une fois la carte choisie : nouveau template, nouvelles broches du persist S3 et section du cenv pour CETTE carte (l'env S3 actuel suppose un DevKit + module relais câblé)
- [ ] [projet] Compiler les deux envs (page build) une fois le build du P4 fini, sur décision de l'utilisateur
- [ ] [projet] Si la S3 remplace la carte en ligne : topic `-v2` contre `cave/serveur-rly-cave` côté Node-RED et Telegram (pris en charge par l'audit)

## Vérification
- Templates : un script du scratchpad décode les tableaux GPIO (ordre ESP32 : 0-5, 9, 10, 12-27, 6-8, 11, 32-39 ; ordre S3 : 0-21, 33-48) et compare celui de l'ESP32 au template relu sur 192.168.0.48.
- Persists : `json.load`, recherche de doublons de `pin` actifs, comparaison des clés `activation/pin/type` avec le persist en ligne (copie dans le scratchpad).
- `banc_demarrage.py` vert, instantanés relus.
- Audit : `git status` identique avant et après.
- Photos : chaque PNG ouvert et regardé ; chaque lien du README répond (curl, code HTTP).
