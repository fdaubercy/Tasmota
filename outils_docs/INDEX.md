# Index des documents du fork (maître)

Importé par `CLAUDE.md` (`@outils_docs/INDEX.md`), donc lu à chaque session. Un fichier déplacé ou renommé se
corrige ici dans le même commit (plan `tasks/plans/binomes-berry.md`, A19 et A20 : rangement en cours).

Comment s'en servir : chercher la ligne de la situation, lire le fichier indiqué AVANT d'agir, et seulement lui.
Ne jamais lire en entier `tasks/lessons.md` (plus de 120 Ko) : grep. Les guides et fiches sont courts : lire celui de la situation.

Règle d'entretien : une fonctionnalité, un outil ou un document nouveau = UNE ligne ici (chemin, ce qu'il apporte,
banc ou piège principal). Jamais un paragraphe dans `CLAUDE.md`. Contrôle : `relecteur-docs` et
`maintenance/verifie_references_docs.py` (ce fichier est dans sa liste `DURABLES`).

## 1. Mémoire de Claude : ce qui a réussi, ce qui a raté

| Situation | Lire | Ce qu'il apporte |
|---|---|---|
| Début de session | rien à ouvrir : le hook injecte `tasks/lessons-actives.md` | une règle par thème, récidives en tête (secrets, build concurrent, faux vert, sessions parallèles, solidification) |
| Avant de toucher un sujet | `grep -n "<mot-clé>" tasks/lessons.md` | les erreurs datées sur ce sujet ; `persist`, `commit`, `solidif`, `secret`, `témoin` sont les plus fournis |
| Après une correction de l'utilisateur | ajouter une ligne à `tasks/lessons.md` | format `[date] \| ce qui a raté \| règle` ; une récidive s'écrit `RECIDIVE de <date>` |
| Reprendre un chantier à froid | le plan rattaché (bloc suiviPlan injecté), puis `tasks/reprise-*.md` s'il existe | prochaine action, ce qui reste ; une reprise sans plan actif est périmée |
| Décisions et préférences de l'utilisateur | `MEMORY.md` (injecté) | choix tranchés, faits matériels non dérivables du code |
| Pièges de solidification Berry | `outils_docs/reference_berry/SOLIDIFICATION_BERRY.md` §4 | 13 pièges payés ; le vert d'un banc ne prouve pas la solidification |
| Pièges du build | `CLAUDE.md` § Vigilances de build ; détail `outils_docs/environnement/VIGILANCES_BUILD.md` | jamais deux `pio run`, aucune cible PlatformIO pendant un build, `PYTHONIOENCODING=utf-8` |

## 2. Référence Berry, drivers et protocoles (avant de toucher un module de `data/`)

| Sujet | Lire | Ce qu'il apporte |
|---|---|---|
| Langage Berry, API Tasmota, extension C | `.doc_for_ai/BERRY_LANGUAGE_REFERENCE.md`, `BERRY_TASMOTA.md`, `BERRY_C_EXTENSION_REFERENCE.md` (amont) | syntaxe exacte ; le moteur `re` de Berry ignore `{n,m}` |
| Pages web des cartes | `.doc_for_ai/TASMOTA_WEBUI_CODING_GUIDE.md` (amont) | conventions de la WebUI |
| Écrans uDisplay, tactile | `.doc_for_ai/UDISPLAY_UTOUCH_GUIDE.md` (amont), skill `lvgl-haspmota` | `display.ini`, LVGL, HASPmota |
| Quel module sur quelle carte | `outils_docs/reference_berry/CARTE_MODULES_BERRY.md` (généré, ne pas éditer) | solidifié, importé, gardes |
| Logs Berry | `CLAUDE.md` § Logs Berry ; réglages `outils_docs/reference_berry/LOGS.md` ; en-tête de `data/fs/logFonctions.be` | 4 niveaux, `logFonctions.log`, jamais `log()` direct |
| Solidification | `outils_docs/reference_berry/SOLIDIFICATION_BERRY.md` | mécanisme, vérification §5, pièges §4 |
| ModBus : conception, registres, synchro | `outils_docs/reference_berry/PROTOCOLE_MODBUS.md` (§8 registres carte 16 relais, §9 synchro, §11 MQTT) | 3 transports, six pièges de la carte relais |
| ModBus : commandes et trames | `outils_docs/reference_berry/MODBUS_MODE_EMPLOI.md` | mode d'emploi, « Fermeture » contre « Open » |
| Voie MQTT maître/esclaves | `outils_docs/reference_berry/VOIE_MQTT.md` ; `PROTOCOLE_MODBUS.md` §11 | garde-fous G3 à G5 ; esclave sans fiche ModBus = aucun repli |
| Découverte des cartes | `outils_docs/reference_berry/DISCOVERY.md` | ESP32 sans PSRAM : `serveur.discovery` OFF |
| Graphiques, énergie, jauges, débits, écran de la cave, MPU6050, volets, coprocesseur C6, Hue | `outils_docs/reference_berry/GRAPHIQUES.md`, `ENERGIE.md`, `CUVE_PAGE.md`, `DEBITS_PAC.md`, `ECRAN_CAVE.md`, `INCLINAISON_MPU6050.md`, `VOLETS_FACADE.md`, `COPROCESSEUR_C6.md`, `EMULATION_HUE.md` | mode d'emploi de chaque fonction des cartes |
| Commandes Tasmota personnalisées (`ReglageGlobal`, `ReglageLog`, `ReglageUDP`, `ReglageModbus`...) | `outils_docs/reference_berry/COMMANDES.md` | liste vérifiée contre les `add_cmd` de `data/` ; sous-commandes et exemples |
| Modifications du firmware amont (C++ en dur) | `outils_docs/reference_berry/MODIFICATIONS_FIRMWARE.md` | piège de synchro du fork : pied de page de `xdrv_01_9_webserver.ino`, comment le retrouver |
| Volets roulants du firmware | `outils_docs/reference_berry/TASMOTA_VOLETS_ROULANTS.md` | doc Shutters traduite et écarts vérifiés |
| Fichiers `.drvset*` | `outils_docs/reference_berry/FICHIERS_DRVSET.md` | contenu, sauvegarde, effacement |
| Extensions `.tapp` | `outils_docs/reference_berry/EXTENSIONS_TAPP.md` | format, cycle de vie, pièges §7 ; jamais essayé sur carte |
| Écrire du Berry | skill `tasmota-berry` | modèle `controleXxx` + `xxxFonctions`, RAM |
| Coût d'un binôme (driver + module) | bloc `TAILLE DU BINOME` en tête du driver ; `outils_docs/scripts_python/berry/mesure_binomes.py` | .be, .bec et solidifié ; mis à jour avant commit (`--verifier`) |

## 3. Outils de l'annuaire (http://127.0.0.1:7600), par groupe

Un guide par outil dans `outils_docs/guides_outils/<NOM_CIBLE>.md` (doc de l'utilisateur ; Claude le lit quand il modifie l'outil,
avec le plan cité). Détail technique de chaque outil (modules, bancs) : `outils_docs/CARTE_DOCUMENTS.md`, tiré de CLAUDE.md.

| Groupe | Outil (port) | Doc actuelle |
|---|---|---|
| Déploiement | Build et téléversement (7700) | `outils_docs/guides_outils/build_web.md`, puis l'onglet utile : `build_web_compilation`, `_ota`, `_fichiers`, `_memoire_defaut`, `_sauvegardes`, `_reparations` |
| Déploiement | Tâches planifiées, compilations de nuit (7920) | `outils_docs/guides_outils/taches_planifiees.md` |
| Configuration des cartes | Fichiers Berry par env (7800) | `outils_docs/guides_outils/fichiers_berry.md` |
| Configuration des cartes | Assistant persist (7900), onglet autoexec.bat | `outils_docs/guides_outils/assistant_persist.md` |
| Configuration des cartes | Navigateur FTP des cartes (7450) | `outils_docs/guides_outils/ftp_cartes.md` ; fichiers protégés, deux confirmations |
| Ateliers | Graphiques (7950), Écrans (7960), Visuels (7985), Étiquettes QR (7970), Fabrique `.tapp` (7980) | `outils_docs/guides_outils/atelier_graphiques.md`, `atelier_ecrans.md`, `atelier_visuels.md`, `etiquettes_qr.md`, `fabrique_tapp.md` ; consignes des façades `outils_docs/visuels_accueil/CONSIGNES_VISUELS.md` |
| Bus et cartes | Sniffeur ModBus (7300), Sniffeur MQTT (7100), Syslog (7200), Testeur UDP (7400), Pont série (7000) | `outils_docs/guides_outils/sniffeur_modbus.md`, `sniffeur_mqtt.md`, `syslog_tasmota.md`, `testeur_udp.md`, `pont_serie.md` ; onglet Aide de chaque page ; skill `logs-cartes` ; jamais 224.3.0.1:4000 depuis un banc |
| Bus et cartes | Sniffeur I2C (7350), Cartes simulées (7940) | `outils_docs/guides_outils/sniffeur_i2c.md`, `cartes_simulees.md` |
| Maintenance | Synchro du fork (7500) | `outils_docs/guides_outils/synchro_fork.md` ; `outils_docs/environnement/SYNCHRO_FORK.md` |
| Dépôt et références | Organigramme des plans (7990), Ménage (7995), Sondes en cours (7910), Catalogue d'icônes (7930), Liens web | `outils_docs/guides_outils/organigramme_plans.md`, `menage.md`, `sondes.md`, `icones_catalogue.md`, `liens_web.md` |
| Annuaire lui-même | accès, jeton commun, barre | `outils_docs/guides_outils/annuaire.md` ; `CARTE_DOCUMENTS.md` (`acces_web.py`) ; spec `docs/superpowers/specs/2026-10-17-annuaire-outils-design.md` |
| Plan de la maison | page générée | `outils_docs/guides_outils/plan_maison.md` ; plan `tasks/plans/plan-maison-echelle.md` |

## 4. Vérifier : fichiers, commits, bancs, sondes, sous-agents

| Moment | Outil | Ce qu'il évite |
|---|---|---|
| Avant tout commit ou push | agent `controleur-secrets` | 12 fuites de secrets consignées, 10 depuis le 07/11 |
| Avant tout push | `/commite pousse` (agent `preparateur-push`) | commits d'une autre session embarqués |
| Commit qui touche un `.be` de `data/` | agents `verificateur-solidification` puis `relecteur-berry` | panne de solidification du 2026-11-13 |
| Après modif d'un `.py` d'outil, d'une page | agents `relecteur-outils-python`, `relecteur-pages-web` | écriture non atomique, XSS, sonde non hermétique |
| Quel banc lancer | skill `bancs` | banc sur copie, banc Berry sans code de sortie |
| Sondes Chrome | `outils_pc/sonde_hermetique.py` ; arrêter les Chrome `sonde_*` après usage | barre commune réelle, Chrome orphelins |
| Échec de build | agent `analyste-journaux-build` | des milliers de lignes dans la conversation |
| Bug ou comportement inattendu | skill `superpowers:systematic-debugging` | correction sur hypothèse non vérifiée |
| Liste et rôle des agents | `outils_docs/verification/SOUS_AGENTS.md` | lequel lancer, avec quel modèle |
| Renvois des documents | `maintenance/verifie_references_docs.py`, agent `relecteur-docs` | `fichier:ligne` décalé, chemin disparu |
| Cases cochées d'un plan | agent `verificateur-plans` | preuve absente |
| Fichier de plus de 500 lignes | `outils_docs/verification/EXCEPTIONS_500_LIGNES.md` | découpage refusé par l'utilisateur |

## 5. Environnement de travail

| Situation | Lire |
|---|---|
| Nouveau poste, VS Code, PermissionError sur `tasmota.ino.cpp` | `outils_docs/environnement/NOUVEAU_POSTE.md` |
| Retard du fork sur l'amont | `outils_docs/environnement/SYNCHRO_FORK.md` ; agent `diagnostic-synchro-fork` ; journal `outils_docs/HISTORIQUE_SYNCHRO_FORK.md` (généré) |
| Plans : format, index, organigramme | `tasks/plans/_FORMAT.md` ; `tasks/README.md` (généré par `.claude/hooks/index_plans.mjs`) |
| Mods et extension VS Code | `.claude/mods/*/plugin.json` ; `outils_docs/vscode/suivi-plan/LISEZMOI.md` |

## 6. Matériel

| Sujet | Lire |
|---|---|
| Puces Espressif, compatibilité | `outils_docs/materiel/MODELES_ESP.md` |
| Brochage d'une carte | `outils_docs/Schémas de branchement - Attribution des PINS des modules/<lieu>/<env>/` |
| Écran 7B des débits | même dossier, `bureau/tasmota32s3-ecran-debits-pac/WAVESHARE_ESP32-S3-Touch-LCD-7B.md` |
| ADS1115, ruban LED | `outils_docs/Electronique/ADS1115/` (le ruban LED y est rangé par erreur) |
| Portail de jardin | `outils_docs/materiel/PORTAIL_JARDIN_MODULE_ET_ALIMENTATION.md` |
| Cartes relais de la cave | `outils_docs/cartes_relais_cave/README.md` |
| Écran MIPI-DSI sur P4 (recherche, rien essayé) | `outils_docs/materiel/ECRAN_TACTILE_ESP32P4.md` |
| Chauffage, équilibrage | `outils_docs/chauffage/EQUILIBRAGE_CHAUFFAGE_NOURRICE.md` |
| Historique sur le Pi | `outils_docs/serveur_pi/historique_capteurs/README.md` |
| PCB KiCad | skill `pcb-tasmota`, agents `placeur-pcb`, `relecteur-pcb` |
| Icônes, images, licences | `outils_docs/ICONES_IMAGES_SOURCES.md` (glyphes MDI du firmware d'abord) |

## 7. Chantiers en cours

| Quoi | Où |
|---|---|
| Plans actifs, % et prochaine action | `tasks/README.md` (version courte générée) |
| Un plan | `tasks/plans/<nom>.md` ; bilan « ce qui a raté » obligatoire à la clôture |
| Conception d'un chantier | `docs/superpowers/specs/` (clé `spec:` du plan) |
| Choix de maquettes déjà tranchés | `README.md` du dossier de maquettes (`atelier_ecrans/`, `jauges/`, `filtre_lieu/`…) |

## 8. Historique (lire seulement pour retrouver un pourquoi)

Analyses, audits et diagnostics datés, dans `outils_docs/historique/` : `ANALYSE_*.md`, `AUDIT_*.md`, `DIAGNOSTIC_UDP_2026-10-17.md`,
`CHANGELOG.md` (arrêté en mai 2026). Ils gardent leurs numéros de ligne : ce sont des traces. L'état réel est dans la
référence (§2) ou le plan.
