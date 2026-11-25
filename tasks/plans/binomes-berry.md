---
chantier: binomes-berry
titre: Binômes Berry autonomes, manifeste unique et persist allégé
objectif: Créer un env ou un persist sans oubli, chaque binôme driver plus module portant sa taille, ses fichiers et ses paramètres
statut: actif
cree: 2026-11-23
maj: 2026-11-25
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
  générées, avec un contrôle `--verifier` (révisé le 2026-11-24 : contrôle seul, sans génération, lancé par `preparateur-push`) ;
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
- [x] Comparer un `.bec` mesuré sur PC à celui d'une carte (ex. `cuveFonctions.bec`) — preuve : carte cuve (`/ufsd` de 192.168.0.43:8081) `cuveFonctions.bec` 20 716 o, `controleCuve.bec` 8 108 o ; PC (`mesure_binomes.taille_bec`, version du dépôt) 20 793 et 8 124 o, soit +0,4 % et +0,2 % ; versions plus anciennes à 250 o ou plus d'écart, donc la carte porte la version actuelle (2026-11-24)

## A2 — Bloc de taille généré (essai sur la paire volets)
- [x] Script `outils_docs/scripts_python/berry/mesure_binomes.py` (`--ecrire`, `--verifier`, refus pendant un build) — preuve : `--ecrire` rc 0 puis `--verifier` rc 0 sur la paire volets, `git status lib/` propre, 2026-11-23
- [x] Banc `test_mesure_binomes.py` : idempotence, mutant d'un chiffre, séquences interdites absentes du bloc — preuve : 11 OK, 0 échec ; témoin (`retire_generes` neutralisé) : 4 échecs, rc 1
- [x] Bloc écrit dans `controleVoletRoulants.be`, ligne de renvoi dans `vrFonctions.be`, compilés et solidifiables — preuve : `verifie_berry.py` 0 erreur, `solidifie_et_compile_berry.py` « LE .h COMPILE » pour les deux, diff +9/+1 lignes
- [x] Accord de l'utilisateur pour étendre aux autres binômes de `data/fs` — preuve : réponse du 2026-11-23 (« passe le script sur tous les binômes de data/fs », vrReglage et vrPages dans le bloc des volets)
- [x] Passe sur les 35 groupes de `data/fs`, puis `--verifier` rc 0 et solidification des fichiers modifiés — preuve : `--verifier` rc 0 sur les 35 groupes le 2026-11-24 (aucun échec, environ 28 min) ; chaque fichier à directive `#@ solidify:` solidifié par `solidify_all_python.be` et son `.h` compilé (xtensa -Os) dans la même passe ; `controleEcranSysteme` sans directive (non solidifié, voulu) ; `git status lib/ data/fs/` propre

## A3 — Manifeste unique
Décisions du 2026-11-24 : champs AJOUTÉS et optionnels (`fichiers`, `pages`, `defines`, `lib_ignore`, `cible` `{nom, chemin}`,
`defaut`), lus par `.get` ; `solidify`, `exclude_si_inactif` et `h` restent tels quels. Coût : pas dans le manifeste, lu à la
demande dans le bloc TAILLE DU BINOME du driver. Cenv : contrôle seul d'abord (`--verifier`, rien d'écrit), génération plus
tard. Blocs sans clé d'activation (qrcode, visuel, pages_graphiques, fsMqtt, page_cuve) : champ `detection`, hors questions de
l'assistant. LoRaWan, ES8311 et coprocesseur existent déjà (`lorawan`, `i2s`, `coprocesseur`) : 10 blocs manquent, pas 13.
- [x] Champs ajoutés aux `blocs` de `modele_persist.json` : fichiers, pages, defines, lib_ignore, cible, bloc par défaut ; coût lu dans le driver — preuve : 28 blocs portent les 6 champs, `solidify`/`exclude_si_inactif`/`h` intacts, feuilles secrètes identiques à HEAD (comparaison en mémoire) ; `mesure_binomes.py::lit_taille`, `test_mesure_binomes.py` 0 échec (2026-11-24)
- [x] Blocs manquants ajoutés (liaisonMqtt, emulationHue, qrcode, visuel, energie, page_cuve, pages_graphiques, ecran, ecranSysteme, fsMqtt) — preuve : 10 blocs en fin de liste ; 4 questions de l'assistant (liaisonMqtt, emulationHue, energie, ecranSysteme), 6 en `detection` (dont `ecran` : deux clés de métier) ; bancs de l'assistant persist : mêmes KO qu'avant, aucun nouveau (comparaison ligne à ligne) ; création et modification VERT
- [x] Listes `[berry_commun]` comparées au manifeste, `--verifier` (code 1 si écart) — preuve : `outils_pc/verifie_manifeste.py --verifier` rc 0 « ACCORD » ; `test_verifie_manifeste.py` 0 échec, 4 mutants rouges (2026-11-24)
- [x] `exclude_si_inactif` des nouveaux blocs, `test_listes_cuve` adapté — preuve : 8 blocs (liaisonMqtt, emulationHue, energie, ecran, ecranSysteme, visuel, pages_graphiques, page_cuve) + `volets_pages` dans voletRoulants ; qrcode et fsMqtt restent vides (qrcode sur tous les envs depuis `e3865abdd`, fsMqtt au socle) ; `PAGES_AUTRES_CARTES` retiré de `assistant_persist_generation.py` (page énergie gardée quand le bloc energie est coché) ; `test_listes_cuve` recopié sur l'exclusion réelle de la cuve, 8 OK dont le témoin energie ; seuls restent les 2 KO déjà présents (`rejeu_parc`, `autoexec_cuve`), qui ne lisent pas ces listes ; `verifie_manifeste.py --verifier` rc 0 (2026-11-24)
- [x] Génération des listes `[berry_commun]` remplacée par un contrôle mécanique (décision du 2026-11-24 : listes et blocs pas un pour un, `--verifier` détecte déjà tout écart) — preuve : étape 5 de `.claude/agents/preparateur-push.md` (`verifie_manifeste.py --verifier`, code 1 = STOP) ; `--verifier` rc 0 « ACCORD » le 2026-11-24
- [x] Lecteurs branchés : assistant persist, fichiers Berry par env, carte des modules — preuve : `test_mesure_binomes.py` 0 échec (`cout_bloc`, ligne abîmée, fichier non UTF-8) ; `CARTE_MODULES_BERRY.md` régénéré, 77 modules, `test_verifie_references_docs.py` VERT ; `test_assistant_persist_web.py::test_rappel_blocs` 5 OK dont 2 témoins, sonde 7900 « rappel sous la case » OK (KO restants identiques à la ligne de base) ; `test_fichiers_berry_blocs.py` VERT (3 témoins), sonde 7800 VERT ; relectures outils Python et pages web sans bloquant (2026-11-24)
  Décisions du 2026-11-24, tout en lecture : carte des modules = colonnes Bloc et Coût ; assistant (7900) = coût et
  `#define`/`lib_ignore` de chaque bloc, en rappel sous sa case ; page 7800 = fichiers d'un env regroupés par bloc avec son
  coût, actions inchangées. Coût d'un bloc : `mesure_binomes.py::cout_bloc`.

## A4 — Cibles de log déclarées par le binôme
- [x] Accord pour modifier `logFonctions.be` et les drivers concernés — preuve : réponse du 2026-11-23 (« OK pour logFonctions »)
- [x] `logFonctions.declare(cible, chemin [, description])` additif, repli sur `CIBLES`/`lieu()`, banc — preuve : `banc_log_declare.py` 17 OK + 6 témoins rouges ; `solidifie_et_compile_berry.py` « LE .h COMPILE » ; `banc_test_modbus` OK, `banc_demarrage` VERT
- [x] Premiers binômes qui déclarent leur cible : portail (2 envs) et débits (accord du 2026-11-25) — preuve : `logFonctions.declare` en tête de l'init de `controlePortail.be` (×2, copies identiques) et `controleDebits.be`, cible passée à leurs logs (enrobeur `debitsFonctions.log`) ; `modules.portail.log`/`modules.debits.log` déjà au persist ; `verifie_berry.py` 0 erreur ; `banc_debits` et `banc_portail_facade` VERTS avec 2 contrôles nouveaux chacun, ROUGES sur la version HEAD (témoins) (2026-11-25)
- [x] Pompe et humidité déclarent leur cible (demande du 2026-11-25) — preuve : `logFonctions.declare` dans l'init de `controlePompeVideCave.be` (copie S3, retenue ; la copie ESP32 n'a aucun log, son sort reste à A7) et de `controleHumidite.be` (×2, identiques, correctif regex de l'utilisateur compris), cible passée à leurs logs ; `verifie_berry.py` 0 erreur ; `banc_pompe_cave` et `banc_humidite` VERTS avec 2 contrôles nouveaux chacun, ROUGES sur la version HEAD (témoins) (2026-11-25)
- [x] Témoin cassé de `banc_ecran_systeme.py` (« cible ecranSysteme absente » : texte cherché périmé depuis `f1dca859d`, avant ce chantier) remis à jour — preuve : mutant réécrit sur `"ecranSysteme", "liaisonMqtt"` (liste CIBLES actuelle) ; `banc_ecran_systeme.py` rc 0, VERT, témoin « logs : cible ecranSysteme absente » rouge comme attendu (2026-11-25)

## A5 — Blocs morts du persist
- [x] Inventaire des lecteurs des 5 ESP32 sans PSRAM — preuve : rapport du sous-agent du 2026-11-23 (scripts `scratchpad/inventaire/`) ; projecteur LED 3 517 o de texte retirables (leds, SD, ecran, KNX, LoRaWan ; squelettes `{"name","activation":"OFF","environnement":{}}` pour I2C et ModBus, `{"activation":"OFF"}` pour serveur.tcp ; `name` exigé par `controleWeb.be`, `activation` par `configModules.be`). CORRECTIF : `diversFonctions::hiberneDriversInactifs` (appelée par `demarrage` à chaque démarrage) range déjà l'`environnement` des drivers OFF dans `/json/driversInactifs.json` et réécrit le persist : en régime établi le gain en RAM n'est que d'environ 350 o par projecteur ; le vrai gain restant est au niveau 3 (`modules.projecteur.environnement`, 3 122 o dont `analogiques` 1 039 o tous OFF), non couvert par l'hibernation
- [x] Proposition chiffrée par env, validée par l'utilisateur — preuve : réponses du 2026-11-25 : palier 1 appliqué aux 5 ESP32 (18,5 Ko de texte, 0,7 à 0,9 Ko de RAM par carte en régime établi ; I2C et ModBus en squelette, lus en direct par `globalFonctions::changementEtatCapteur` et `configDevices`) ; `drivers.leds` GARDÉ ON sur bureau et cave (décision du 23/11 annulée : lu par `configModules.be::configDevicesByJon`, LedPower/LedState/SetOption31) ; palier 2 (groupes du niveau 3 tous OFF vidés à `{}`, 1,1 à 4 Ko par carte) reporté après un essai sur carte ; `_incertain` du portail ESP32 reporté dans la doc puis retiré. Rapport : scratchpad `inventaire/proposition2_sortie.txt`. Décisions d'origine (2026-11-23 : `drivers.leds` à ON sans lecteur passé à OFF sur le bureau et la cave ESP32, pas retiré ; PORTAIL ESP32 jugé sur son autoexec CIBLE, pas sur le palier 1 : le P4 le commande par ModBus (relais virtuels 20 et 22 vers l'esclave 4), donc `drivers.ModBus`, `drivers.leds`, `serveur.udp` et `modules.portail` gardés, `modbusFonctions` reste solidifié)
- [x] Palier 1 retiré dans le dépôt (5 `_persist.json`) — preuve : persist de HEAD + gestes appliqués en mémoire == fichier écrit, feuilles identiques (secrets compris), fins de ligne inchangées ; texte 14 311 → 8 549 o (LED), 14 328 → 8 566 (barbecue), 13 671 → 9 139 (bureau), 25 723 → 17 793 (cave), 14 927 → 8 342 (portail) ; `banc_demarrage.py --dossier --env` VERT sur les 5, instantané (drivers, règles, commandes, crons, globales, erreurs) identique à celui des persists de HEAD, témoin `drivers.ModBus` à ON : 8 écarts et code 1 ; `_incertain` recopié dans `PORTAIL_JARDIN_MODULE_ET_ALIMENTATION.md` (2026-11-25)
- [ ] Déploiement sur les 5 cartes avec l'utilisateur (supprimer persist et autoexec, redémarrer, renvoyer, garder `/json/driversInactifs.json`), puis RAM relevée par `tasmota.gc()`
- [ ] Palier 2 (groupes du niveau 3 tous OFF vidés à `{}`) : après l'essai du palier 1 sur une carte

## A6 — Paramètres en lecture seule dans `/json`
- [x] Forme de la clé explicite et lecture à la demande décidées — preuve : `SOLIDIFICATION_BERRY.md` §3 bis (clé `"json": "/json/<nom>.json"` lue par `.find` avec le chemin en dur pour défaut, lecture à la demande sur le modèle de `pagesGraphiques_lisDescription`), choix de l'utilisateur du 2026-11-25 (« Fixer la forme, sans candidat »)
- [x] Premier candidat sur une carte sans PSRAM : sans objet — preuve : mesure du 2026-11-25 (scratchpad `a6_tailles.py`, `a6_facade.py`) sur les 5 ESP32 après le palier 1 : persist compact de 5,5 à 10,8 Ko, aucun bloc en lecture seule de taille utile (façade du portail 66 o) ; l'`environnement` porte l'état (`globalFonctions.be`, `device["etat"]`) ; gain reporté au palier 2 d'A5

## A7 — Doublons et règles écrites
- [x] `controlePompeVideCave` : copie du S3 retenue, sort de l'env ESP32 de la cave décidé — preuve : décision du 2026-11-25 (« remplacer par la copie du S3 », puis « active la surveillance des pannes sur l'ESP32 ») ; les deux copies identiques (`cmp`), en-tête rendu commun ; `modules.pompeVideCave.pannes` (5 s, 3 arrêts, valeurs du S3) ajouté au persist ESP32 par insertion, reste du fichier identique ; `verifie_berry.py` 0 erreur, `banc_demarrage` de `tasmota32-cave-serveur-rly` VERT ; retouches de la relecture appliquées aux deux copies (id `pompeVideCave_Bas|Haut` sur les règles `SwitchN#Action`, `tasmota.rtc()` lu seulement en cas d'incohérence) : `banc_pompe_cave` 77 OK dont le contrôle nouveau des id, ROUGE sur la version HEAD (témoin) ; `verificateur-solidification` et `relecteur-berry` sans bloquant (2026-11-25). Fichier solidifié sur l'ESP32 : effet sur la carte au prochain firmware
- [x] Règle de solidification des fichiers de carte écrite dans `SOLIDIFICATION_BERRY.md` §3 — preuve : ligne « Fichier propre à une carte » du tableau du §3 (règle du 2026-11-23 : RAM courte ET fichier presque finalisé), reprise au §7 avec l'état des fichiers de carte solidifiés ou non (relu le 2026-11-25)
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
- [x] Enseignements de `temps-compilation`, `lib-ignore-*`, `graphiques-web`, `*-mpu6050`, `build-reparations` remontés dans les références — preuve : `VIGILANCES_BUILD.md` (sections « Temps de compilation : mesures et decisions » et « lib_ignore : scan des dependances (LDF) »), `GRAPHIQUES.md` (« Choix et pièges »), `INCLINAISON_MPU6050.md`, `NOUVEAU_POSTE.md`, guides `build_web*.md` ; `## Bilan` dans les 7 plans ; `index_plans.mjs --verifier` rc 0, `verifie_references_docs.py` rc 0 (2026-11-25)

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
