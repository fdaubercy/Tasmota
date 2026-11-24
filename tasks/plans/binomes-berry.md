---
chantier: binomes-berry
titre: Binômes Berry autonomes, manifeste unique et persist allégé
objectif: Créer un env ou un persist sans oubli, chaque binôme driver plus module portant sa taille, ses fichiers et ses paramètres
statut: actif
cree: 2026-11-23
maj: 2026-11-24
famille: build
liens: assistant-persist, fichiers-berry-env, lib-ignore-envs
---
# Binômes Berry autonomes, manifeste unique et persist allégé

## Contexte
Conversation du 2026-11-23. Décisions de l'utilisateur :
- un binôme = un driver `controleXxx.be` + un module `xxxFonctions.be` ; il porte ses commandes, règles, pages et
  paramètres ; l'organisation et le contenu de base du driver modèle et du module modèle (paire `controleVoletRoulants.be`
  + `vrFonctions.be`) ne changent pas, tout ajout est additif ;
- ajouter ou retirer une fonctionnalité = `#define` du `user_config_override.h`, fichiers Berry (cenv, autoexec), partie
  JSON du persist ;
- UN seul manifeste : les `blocs` de `outils_docs/schemas/modele_persist.json`, étendus ; les listes du cenv en sont
  générées, avec un contrôle `--verifier` ;
- cibles de log par `logFonctions.declare` (additif, repli sur `CIBLES`/`lieu()`) ;
- `/json` : configuration venue du dépôt, EN LECTURE SEULE sur la carte (descriptions, gabarits, tables, façades), liée
  par une clé explicite du bloc du persist ; restent au persist : états, réglages faits sur une page, identité, clés
  `activation`, blocs lus par plusieurs binômes ;
- premier geste sur le persist : retirer les blocs des fonctionnalités absentes de l'env ;
- un fichier propre à une carte se solidifie si la carte manque de RAM ET qu'il est presque finalisé ou peu modifié ;
- taille de chaque binôme en commentaire GÉNÉRÉ : bloc du couple dans le driver, ligne courte dans le module qui renvoie
  au driver ; mise à jour avant commit ; périmètre `data/fs` ;
- `controlePompeVideCave` : garder la copie la plus récente (celle du S3).
Aucun `.be` autre que la paire volets, aucun `_persist.json`, ni `user_config_override.h` ne se modifie sans accord.

Rangement des .md (A8 à A20), ajouté à la demande de l'utilisateur, conversation du 2026-11-23 : audit en lecture seule
de tous les .md du fork (3 audits + synthèse : `tasks/rangement-md-synthese-2026-11-23.md` ; brouillon du maître :
`tasks/rangement-md-brouillon-INDEX.md`, à archiver une fois A10 et A20 faits). Validé par l'utilisateur : classement, 6 suppressions en bloc, 12 archivages, corrections,
plan de migration. Décisions : push gardé (autorisation du 29/10, toujours derrière `preparateur-push`) ; maître
`outils_docs/INDEX.md` importé dans CLAUDE.md par `@` ; `outils_docs/README.md` découpé en un fichier par outil ;
archives gardées dans le dépôt (`outils_docs/historique/`, `tasks/archive/`) ; `PLC_OPENPLC.md` rangé dans `materiel/`.
Les .md de l'amont (racine sauf CLAUDE.md, `lib/`, `tools/`, `tasmota/`, `.doc_for_ai/`, `.github/`) ne bougent pas.
Chaque action = un commit, précédé de `controleur-secrets`.

## A1 — Mesures de départ
- [x] Taille d'essai de 5 modules en `.be`, `.bec` et solidifié — preuve : conversation du 2026-11-23, volets 62,6 / 32,1 / 22,6 Ko, ModBus 227,9 / 89,9 / 60,5 Ko
- [x] RAM d'un persist chargé, mesurée sur le P4 (texte 22 172 o) — preuve : `Br` sur 192.168.0.43 le 2026-11-23, rechargement 21 840 o (clés partagées) à 51 621 o (clés uniques)
- [ ] Comparer un `.bec` mesuré sur PC à celui d'une carte (ex. `cuveFonctions.bec`)

## A2 — Bloc de taille généré (essai sur la paire volets)
- [x] Script `outils_docs/scripts_python/berry/mesure_binomes.py` (`--ecrire`, `--verifier`, refus pendant un build) — preuve : `--ecrire` rc 0 puis `--verifier` rc 0 sur la paire volets, `git status lib/` propre, 2026-11-23
- [x] Banc `test_mesure_binomes.py` : idempotence, mutant d'un chiffre, séquences interdites absentes du bloc — preuve : 11 OK, 0 échec ; témoin (`retire_generes` neutralisé) : 4 échecs, rc 1
- [x] Bloc écrit dans `controleVoletRoulants.be`, ligne de renvoi dans `vrFonctions.be`, compilés et solidifiables — preuve : `verifie_berry.py` 0 erreur, `solidifie_et_compile_berry.py` « LE .h COMPILE » pour les deux, diff +9/+1 lignes
- [x] Accord de l'utilisateur pour étendre aux autres binômes de `data/fs` — preuve : réponse du 2026-11-23 (« passe le script sur tous les binômes de data/fs », vrReglage et vrPages dans le bloc des volets)
- [ ] Passe sur les 35 groupes de `data/fs`, puis `--verifier` rc 0 et solidification des fichiers modifiés

## A3 — Manifeste unique
- [ ] Champs ajoutés aux `blocs` de `modele_persist.json` : fichiers, pages, defines, lib_ignore, cible, coût, bloc par défaut
- [ ] Blocs manquants ajoutés (liaisonMqtt, emulationHue, qrcode, visuel, energie, page_cuve, pages_graphiques, ecran, ecranSysteme, fsMqtt, LoRaWan, ES8311, coprocesseur)
- [ ] Listes `[berry_commun]` et exclusions générées depuis le manifeste, `--verifier` (code 1 si en retard)
- [ ] Lecteurs branchés : assistant persist, fichiers Berry par env, carte des modules

## A4 — Cibles de log déclarées par le binôme
- [x] Accord pour modifier `logFonctions.be` et les drivers concernés — preuve : réponse du 2026-11-23 (« OK pour logFonctions »)
- [x] `logFonctions.declare(cible, chemin [, description])` additif, repli sur `CIBLES`/`lieu()`, banc — preuve : `banc_log_declare.py` 17 OK + 6 témoins rouges ; `solidifie_et_compile_berry.py` « LE .h COMPILE » ; `banc_test_modbus` OK, `banc_demarrage` VERT
- [ ] Premiers binômes qui déclarent leur cible (pompe, humidité, portail, débits : aucune cible aujourd'hui)
- [ ] Témoin cassé de `banc_ecran_systeme.py` (« cible ecranSysteme absente » : texte cherché périmé depuis `f1dca859d`, avant ce chantier) remis à jour

## A5 — Blocs morts du persist
- [x] Inventaire des lecteurs des 5 ESP32 sans PSRAM — preuve : rapport du sous-agent du 2026-11-23 (scripts `scratchpad/inventaire/`) ; projecteur LED 3 517 o de texte retirables (leds, SD, ecran, KNX, LoRaWan ; squelettes `{"name","activation":"OFF","environnement":{}}` pour I2C et ModBus, `{"activation":"OFF"}` pour serveur.tcp ; `name` exigé par `controleWeb.be`, `activation` par `configModules.be`). CORRECTIF : `diversFonctions::hiberneDriversInactifs` (appelée par `demarrage` à chaque démarrage) range déjà l'`environnement` des drivers OFF dans `/json/driversInactifs.json` et réécrit le persist : en régime établi le gain en RAM n'est que d'environ 350 o par projecteur ; le vrai gain restant est au niveau 3 (`modules.projecteur.environnement`, 3 122 o dont `analogiques` 1 039 o tous OFF), non couvert par l'hibernation
- [ ] Proposition chiffrée par env, validée par l'utilisateur (décidé le 2026-11-23 : `drivers.leds` à ON sans lecteur passé à OFF sur le bureau et la cave ESP32, pas retiré ; PORTAIL ESP32 jugé sur son autoexec CIBLE, pas sur le palier 1 : le P4 le commande par ModBus (relais virtuels 20 et 22 vers l'esclave 4), donc `drivers.ModBus`, `drivers.leds`, `serveur.udp` et `modules.portail` gardés, `modbusFonctions` reste solidifié)
- [ ] Retrait dans le dépôt et déploiement (supprimer persist et autoexec, redémarrer, renvoyer)

## A6 — Paramètres en lecture seule dans `/json`
- [ ] Forme de la clé explicite et lecture à la demande décidées
- [ ] Premier candidat sur une carte sans PSRAM en service (projecteur LED), gain mesuré par `tasmota.gc()`

## A7 — Doublons et règles écrites
- [ ] `controlePompeVideCave` : copie du S3 retenue, sort de l'env ESP32 de la cave décidé
- [ ] Règle de solidification des fichiers de carte écrite dans `SOLIDIFICATION_BERRY.md` §3
- [ ] `nouveau-module.md` (skill Berry) aligné sur la paire de référence

## A8 — Leçons réellement injectées au démarrage
- [x] Script réversible lancé par l'utilisateur (config `~/.claude`) : réserve de `~/.claude/helpers/injecte_lecons.cjs` 3000 -> 1000 o, message « synthèse périmée » au-delà de 20 nouvelles leçons ; limite de la skill `lecons-synthese` 7000 -> 4500 o — preuve : lancé par l'utilisateur le 2026-11-23 ; sauvegarde ~/.claude/_sauvegarde_a8_lecons présente, PEREMPTION dans injecte_lecons.cjs
- [x] `/lecons-synthese` relancé : une règle par thème avec compteur de récidives, `lessons-actives.md` < 4 500 o — preuve : tasks/lessons-actives.md 4 281 o, 12 règles, source_lignes=270 (fichier laissé à l'utilisateur, non commité)
- [x] `node ~/.claude/helpers/test_injecte_lecons.cjs` vert ; sortie du hook < 8 000 o, sans « tronquée » — preuve : 27 réussis, 0 en échec ; sortie du hook 4 352 o, 0 « tronquée » ni « périmée »

## A9 — Contradictions de CLAUDE.md levées
- [x] Push : autorisation du 29/10 écrite dans CLAUDE.md et `/commite`, toujours derrière `preparateur-push` — preuve : commit 81621b5ca
- [x] `tasks/lessons.md` lu par mot-clé, plus « en entier » — preuve : commit 81621b5ca
- [x] Exemption graphify complète (ni pré-commit, ni création de carte) — preuve : commit 81621b5ca
- [x] `c:\Users\fdaub\CLAUDE.md` (doublon du global) réduit à un renvoi — preuve : fichier hors dépôt réécrit le 2026-11-23 : renvoi au global, règles de base

## A10 — Fichier maître `outils_docs/INDEX.md`
- [x] Créé d'après le brouillon : situation -> fichier -> ce qu'il apporte (réussites, pièges), `.doc_for_ai/` compris — preuve : commit 26d23d4c6 (outils_docs/INDEX.md, 120 lignes)
- [x] Ajouté à `DURABLES` de `maintenance/verifie_references_docs.py` ; script code 0, `test_verifie_references_docs.py` vert — preuve : commit 26d23d4c6, verifie_references_docs.py rc 0, test_verifie_references_docs.py VERT
- [x] Importé dans CLAUDE.md par `@outils_docs/INDEX.md` — preuve : commit 26d23d4c6 (CLAUDE.md, démarrage point 6)

## A11 — CLAUDE.md allégé à ~14 Ko
- [x] `outils_docs/verification/EXCEPTIONS_500_LIGNES.md`, `outils_docs/environnement/NOUVEAU_POSTE.md`, `outils_docs/environnement/VIGILANCES_BUILD.md` tirés de CLAUDE.md — preuve : commit 5bf4e3bbc (blocs identiques octet pour octet à HEAD, + environnement/SYNCHRO_FORK.md)
- [x] « Carte des documents » remplacée par un tableau de 12 sujets et la règle « une fonctionnalité nouvelle = une ligne dans INDEX.md » — preuve : commit 5bf4e3bbc : règle « une ligne dans INDEX.md » ; l'import de INDEX.md tient lieu de tableau (pas de seconde table) ; détail dans outils_docs/CARTE_DOCUMENTS.md
- [x] Même commit : règle 4 de `relecteur-docs` remplacée par « chaque `NOM_CIBLE` a son guide et sa ligne dans INDEX.md » ; `/fin-de-session` adapté — preuve : commit 5bf4e3bbc (relecteur-docs.md règle 4, fin-de-session.md)
- [x] `wc -c CLAUDE.md` < 16 000 ; `verifie_references_docs.py` code 0 ; `relecteur-docs` sans bloquant — preuve : CLAUDE.md 15 013 o ; verifie_references_docs.py 39 documents 0 défaut ; relecteur-docs sans bloquant, 3 corrections appliquées

## A12 — Reprises allégées
- [x] `tasks/reprise-modbus-garage.md` (30 lignes : cibles garage, décisions, reste) tiré de `reprise-chantier-modbus-grenier.md` — preuve : commit f87cf7cbe
- [x] Les deux reprises archivées dans `tasks/archive/` ; « reste à solidifier » reporté dans `SOLIDIFICATION_BERRY.md` s'il est encore vrai — preuve : commit f87cf7cbe (tasks/archive/, SOLIDIFICATION_BERRY.md §3, §7, piège 13)
- [x] Démarrage de CLAUDE.md et mémoire `project_chantier_modbus_grenier` repointés ; grep des anciens noms vide dans `.claude`, CLAUDE.md et la mémoire — preuve : commit f87cf7cbe, mémoire réécrite le 2026-11-23

## A13 — `tasks/README.md` court
- [x] `.claude/hooks/index_plans.mjs` : une ligne par plan actif, par famille, sans la seconde copie des gestes ; `test_index_plans.mjs` adapté et vert — preuve : commit a38c6df0f, test_index_plans.mjs rc 0
- [x] `index_plans.mjs --verifier` code 0 ; taille < 12 Ko — preuve : « index_plans : vert » rc 0, tasks/README.md 10 085 o (commit a38c6df0f)

## A14 — Six suppressions (accord en bloc du 2026-11-23)
- [x] Mémoires `project_onglets_fenetre2` et `project_sauvegarde_scripts`, et leurs lignes de MEMORY.md — preuve : fichiers absents, MEMORY.md sans leurs lignes (2026-11-23)
- [x] `tasks/correctif-udp-interface-2026-10-17.diff` — preuve : commit f87cf7cbe (git rm)
- [x] `docs/superpowers/plans/_sauvegarde-avant-solidify/` — preuve : dossier absent (ignoré par git), 2026-11-23
- [x] `.claude/skills/pcb-tasmota/scripts/.claude-flow/` — preuve : dossier absent (ignoré par git), 2026-11-23
- [x] Reliquat de fin de `outils_docs/README.md` (amont obsolète, adresses du réseau local et redirections de la box), APRÈS avoir sauvé les commandes personnalisées (vers `reference_berry/`) et la modification C++ du pied de page ; TODO (Bluetooth/MI32, TasmotaClient, TasmoView) : suppression décidée le 2026-11-23 — preuve : commit be179e6b8 (README 3062 -> 2890 lignes, reference_berry/COMMANDES.md et MODIFICATIONS_FIRMWARE.md)

## A15 — Corrections des documents vivants
- [x] READMEs de maquettes `partitions/`, `build_fin_partitions/`, `sauvegarde_config/` : « réalisé, modèle X, le … » — preuve : commit 068d87078
- [x] Specs `solidification-berry-design`, `annuaire-outils-design`, `page-build-televersement-design` : statut d'une ligne — preuve : commit 068d87078
- [x] `SOLIDIFICATION_BERRY.md` : encadré de tête réécrit (verdict du 2026-07-15) — preuve : commit f87cf7cbe
- [x] `SOUS_AGENTS.md` : tableau réparé, colonnes famille et usage, colonne « modifie » exacte — preuve : commit 068d87078
- [x] En-tête de `HISTORIQUE_SYNCHRO_FORK.md` corrigé dans `synchronise_fork_tasmota.py`, banc de la synchro vert — preuve : commit 068d87078 (script déjà juste), test_synchro_fork_assistant rc 0
- [x] `LIENS_WEB.md` régénéré, `genere_liens_web.py --verifier` code 0 — preuve : commit 068d87078, --verifier rc 0
- [x] `SetOption127 1` du P4 écrit dans son autoexec ou son persist (accord : `data/`) — preuve : commit 26d23d4c6 (autoexec.be du P4, ligne essayée sous berry.exe : 0 -> commande envoyée, 1 -> rien)

## A16 — Garde mécanique des secrets à la lecture
- [x] Lecteur masqué des fichiers à secrets (`_persist.json`, `user_config_override.h`, `tasmota_defines_for_berry.*`, sauvegardes de cartes), motifs repris de `garde_commit.cjs` — preuve : `.claude/hooks/garde_lecture.py::lire` (`--lire`, plus `--cherche-valeurs` et `--public` pour les contrôles) ; persist réel du P4 : 5 lignes masquées, aucune valeur dans la sortie (2026-11-24)
- [x] Hook `PreToolUse` (Read, Grep, Bash, PowerShell) qui refuse leur lecture brute ; banc : refusé, masqué, faux positif — preuve : `python .claude/hooks/test_garde_lecture.py` VERT, 61 cas, 7 mutants tués ; branché dans `.claude/settings.json` ; Read et `cat` d'un faux persist refusés dans la session ET dans un sous-agent, `git status` passe (2026-11-24) ; exception des 500 lignes datée (735 lignes)
- [x] Une ligne dans chaque agent qui a Bash — preuve : 13 fichiers `.claude/agents/*.md` ; procédure `--cherche-valeurs`/`--public` dans `controleur-secrets.md` et `preparateur-push.md` (2026-11-24)

## A17 — Mémoire native rangée
- [x] MEMORY.md en 4 rubriques (préférences, chantiers ouverts, faits matériels et pièges, références), lignes < 150 caractères, < 6 Ko — preuve : MEMORY.md 5 906 o, 0 ligne > 150 caractères (2026-11-23)
- [x] Mémoires périmées réduites à l'état actuel : `project_historique_capteurs`, `project_chantier_modbus_grenier`, `project_statut_cartes`, `project_portail_jardin` — preuve : 4 fichiers réécrits le 2026-11-23
- [x] Doublons avec CLAUDE.md ramenés à un renvoi ; tous les liens de MEMORY.md valides — preuve : 0 lien mort ni orphelin au contrôle du 2026-11-23

## A18 — Plans clos avec bilan
- [x] Section `## Bilan` (marché, raté, règle retenue, cases reportées) ajoutée à `_FORMAT.md` et contrôlée par `index_plans.mjs --verifier` — preuve : commit a38c6df0f
- [x] `sauvegarde-config-cartes`, `energie-differentiel`, `page-build-televersement`, `jauges-cuve` clos avec bilan — preuve : commit a38c6df0f
- [x] `ethernet-p4` clos « remplacé par » `voie-reseau-ethernet` et `rgx-ethernet-uplink` ; `relais-cave-s3`, `audit-relais-cave-s3`, `cave-s3-waveshare` fusionnés (décidé le 2026-11-23) ; `navigateur-ftp-cartes-a5-reprise` lié par `parent:` — preuve : ethernet-p4.md statut clos + ## Bilan ; relais-cave-s3.md 70 cases = 22 + 24 + 24 ; deux plans dans tasks/archive/ ; index --verifier rc 0 (commit des plans du 2026-11-23)
- [ ] Enseignements de `temps-compilation`, `lib-ignore-*`, `graphiques-web`, `*-mpu6050`, `build-reparations` remontés dans les références

## A19 — Rangement des .md libres d'`outils_docs/`
- [x] `git mv` vers `historique/` (ANALYSE_*, AUDIT_*, DIAGNOSTIC_UDP, CHANGELOG), `materiel/` (MODELES_ESP, ECRAN_TACTILE_ESP32P4, PORTAIL_JARDIN, ICONES_BOUTONS_RELAIS, PLC_OPENPLC), `reference_berry/` (PROTOCOLE_MODBUS, `Aide/MODBUS.md` -> MODBUS_MODE_EMPLOI.md, SOLIDIFICATION_BERRY, CARTE_MODULES_BERRY, FICHIERS_DRVSET, EXTENSIONS_TAPP, TASMOTA_VOLETS_ROULANTS), `verification/` (SOUS_AGENTS) — preuve : 22 git mv (rangement A19), Aide/MODBUS.md -> reference_berry/MODBUS_MODE_EMPLOI.md
- [x] Renvois mis à jour : CLAUDE.md, INDEX.md, agents, skills `bancs` et `pcb-tasmota`, constante de `carte_modules_berry.py`, `DURABLES` ; grep des anciens noms vide hors plans et specs — preuve : a19_range.py : renvois réécrits (dont 13 .be de data/, accord du 2026-11-23, blocs de taille refaits) ; git grep des anciens chemins vide hors traces, tasks/lessons.md (ajout seul) et un commentaire du cenv (autre session)
- [x] `carte_modules_berry.py` relancé sans diff ; `verifie_references_docs.py` code 0 — preuve : chemin de sortie corrigé, régénéré sans diff ; verifie_references_docs.py rc 0 ; test_tapp_web, banc_tapp_fsmqtt, test_verifie_references_docs VERT

## A20 — Découpage de `outils_docs/README.md`, un fichier par outil
- [x] Relecture intégrale des 3 063 lignes : carte des sections, destination de chacune, défauts relevés — preuve : `tasks/rangement-md-relecture-readme.md` (3 sous-agents, 29 affirmations périmées, Build en 7 guides, 6 outils sans section), 2026-11-23
- [x] Fiches des fonctions des cartes vers `reference_berry/` — preuve : 12 fiches (LOGS ... EMULATION_HUE), découpage sans perte (a20_decoupe.py), affirmations périmées corrigées (commit du rangement A20)
- [x] Un guide par outil dans `guides_outils/`, nommé d'après son `NOM_CIBLE` (Build en plusieurs fichiers) ; guides manquants écrits — preuve : 31 guides, Build en 7 fichiers, 6 guides neufs ; relecteur-docs : ports et options conformes au code (commit du rangement A20)
- [x] README réduit à un renvoi vers INDEX.md ; renvois de CLAUDE.md, INDEX.md, `.claude/` et de l'en-tête de `logFonctions.be` (accord du 2026-11-23) mis à jour — preuve : outils_docs/README.md 12 lignes ; renvois repointés (a20_renvois.py + 12 fichiers à la main, en-tête de logFonctions.be compris) (commit du rangement A20)
- [x] Contrôle « chaque `NOM_CIBLE` a son guide » ; `grep "README.md §"` vide sur `.claude`, CLAUDE.md, INDEX.md — preuve : 22 NOM_CIBLE, 22 guides et 22 lignes dans INDEX.md ; aucun « README § » restant ; verifie_references_docs.py 91 documents 0 défaut (commit du rangement A20)

## Améliorations restantes
- [ ] [projet] Fichiers de base par puce (ESP8266, ESP32 sans PSRAM, ESP32 avec PSRAM, S3, P4) d'après les coûts mesurés
- [ ] [projet] Registre des voies de relais (`set_power_handler`), après les cibles de log

## Vérification
Mesures relancées par `mesure_binomes.py --verifier` ; RAM réelle par `tasmota.gc()` sur une carte à PSRAM (32 bits, même disposition).
