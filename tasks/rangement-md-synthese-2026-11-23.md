# Synthèse : classement des .md du fork et mémoire de Claude (2026-11-23)

Audit en lecture seule. Rien n'a été modifié, déplacé ni supprimé. Sources : `audit_outils_docs.md`, `audit_tasks_specs.md`,
`audit_config_claude.md` (même dossier), plus des vérifications ponctuelles dans le dépôt (citées entre crochets).
Hors périmètre, ne pas toucher : les .md de la racine sauf `CLAUDE.md`, `lib/**`, `tools/**`, `tasmota/**`,
`info/xdrv_57_tasmesh.md`, `.github/`, `.doc_for_ai/` (amont).

## 0. Ce qui ressort

Le problème n'est pas l'absence de documents mais leur aiguillage. Claude reçoit 163 Ko à chaque session, dont 126 Ko de
`CLAUDE.md` décrivant des fonctionnalités ; il ne reçoit pas les leçons récentes (59 des 65 leçons postérieures au 07/11 ne
sont jamais injectées) ; il doit lire au démarrage deux reprises périmées (62 Ko). Trois choses expliquent les récidives :

1. Le dispositif qui retient les erreurs est tronqué par son propre budget [vérifié : `injecte_lecons.cjs` ligne 12
   `BUDGET = 8000`, ligne 50 réserve jusqu'à 3000 o pour les nouvelles leçons ; la skill `lecons-synthese` fixe la limite de
   la synthèse à « moins de 7 000 octets » (sa ligne 32) ; la synthèse actuelle fait 6 516 o, elle respecte la skill et
   pourtant le hook la coupe, car il ne lui laisse qu'environ 4,7 Ko]. La skill et le hook se contredisent.
2. Ce qui fait grossir `CLAUDE.md` est une règle : l'agent `relecteur-docs` (règle n°4, ses lignes 20 et 36) exige que tout
   outil récent figure dans la « Carte des documents » de `CLAUDE.md`. Alléger `CLAUDE.md` sans changer cette règle ne
   tiendra pas une semaine.
3. La sécurité repose sur des phrases : 12 fuites de secrets dans des sorties d'outils, 10 depuis le 07/11, malgré la règle
   écrite. Le garde `~/.claude/helpers/garde_commit.cjs` ne regarde que les lignes ajoutées d'un commit, pas ce qu'un `grep`
   ou un `Read` affiche dans la conversation.

## 1. Arborescence cible

Principe : on ne déplace que les .md « libres » de la racine d'`outils_docs/` et les fichiers de `tasks/`. Les dossiers que
des outils lisent ou écrivent restent où ils sont (`atelier_ecrans/`, `visuels_accueil/`, `etiquettes_qr/`, `schemas/`,
`Schémas de branchement…/`, `Electronique/`, `chauffage/`, `serveur_pi/`, `organigramme_plans/`) : ils sont indexés, pas
déplacés. Noms de dossiers en minuscules avec soulignés, comme `scripts_python/` et `atelier_ecrans/`.

```
CLAUDE.md                          règles seules, ~14 Ko, importe outils_docs/INDEX.md
outils_docs/
  INDEX.md                         MAÎTRE (neuf) : situation -> fichier -> ce qu'il apporte
  README.md                        transition : inchangé ; à la fin, en-tête + renvoi vers INDEX.md
  HISTORIQUE_SYNCHRO_FORK.md       reste (écrit par synchronise_fork_tasmota.py, lu par 3 scripts et l'annuaire)
  LIENS_WEB.md                     reste (généré à chemin fixe par genere_liens_web.py)
  ICONES_IMAGES_SOURCES.md         reste (5 fichiers à la racine, ce n'est plus du vrac)
  reference_berry/                 PROTOCOLE_MODBUS.md, MODBUS_MODE_EMPLOI.md (ex Aide/MODBUS.md),
                                   SOLIDIFICATION_BERRY.md, CARTE_MODULES_BERRY.md (constante du générateur à changer),
                                   FICHIERS_DRVSET.md, EXTENSIONS_TAPP.md, TASMOTA_VOLETS_ROULANTS.md,
                                   + 12 fichiers tirés du README (l. 65 à 947) : LOGS_BERRY, DISCOVERY, GRAPHIQUES_CARTES,
                                   PAGE_ENERGIE, PAGE_CUVE, DEBITS_NOURRICE, ECRAN_7B, INCLINAISON_MPU6050,
                                   VOLETS_VISUEL_REGLAGE, COPROCESSEUR_C6, VOIE_MQTT, HUE_ALEXA
  guides_outils/                   un fichier par outil, nommé d'après son NOM_CIBLE (build/cible_*.py), port en tête :
                                   build/ (socle, ota_fs, onglets, reparations : 535 lignes coupées en 4),
                                   fichiers_berry, assistant_persist, ftp_cartes, fabrique_tapp, atelier_graphiques,
                                   atelier_ecrans, etiquettes_qr, atelier_visuels, synchro_fork, organigramme_plans,
                                   menage, cartes_simulees, taches_planifiees, sondes, icones_catalogue, sniffeur_i2c,
                                   plan_maison, liens_web, lieux, + 6 guides à écrire depuis CLAUDE.md seul :
                                   sniffeur_modbus, sniffeur_mqtt, syslog, testeur_udp, pont_serie, annuaire
  verification/                    SOUS_AGENTS.md (+ colonnes famille et usage), EXCEPTIONS_500_LIGNES.md (ex CLAUDE.md)
  environnement/                   NOUVEAU_POSTE.md (montage + PermissionError), VIGILANCES_BUILD.md (détail)
  materiel/                        MODELES_ESP.md, ECRAN_TACTILE_ESP32P4.md, PORTAIL_JARDIN_MODULE_ET_ALIMENTATION.md,
                                   ICONES_BOUTONS_RELAIS.md, PLC_OPENPLC.md (si gardé)
  historique/                      ANALYSE_* (4), AUDIT_* (3), DIAGNOSTIC_UDP_2026-10-17.md, CHANGELOG.md
  Electronique/ADS1115/CABLAGE_RUBAN_LED.md -> Electronique/ruban_LED/   (seul déplacement dans un sous-dossier)
tasks/
  README.md                        court (8 à 12 Ko), généré : une ligne par plan actif, par famille
  lessons.md                       journal append-only + index par thème en tête
  lessons-actives.md               une règle par thème, compteur de récidives, sous le budget réel du hook
  reprise-modbus-garage.md         30 lignes (le motif tasks/reprise-*.md est lu par /fin-de-session et
                                   rappel_apres_compactage.sh : garder ce préfixe, pas de sous-dossier reprises/)
  plans/                           inchangé (actifs ET clos : voir §5, pas de clos/)
  archive/                         reprises complètes, exports de passation anciens
docs/superpowers/specs|plans/      inchangé, statut d'une ligne en tête de chaque spec
~/.claude/projects/…/memory/       MEMORY.md par rubriques (voir §5)
```

Familles, lecteurs et moment de lecture :

| Famille | Où | Qui lit | Quand |
|---|---|---|---|
| Règles | `CLAUDE.md` | Claude, injecté | toujours |
| Maître d'index | `outils_docs/INDEX.md` | Claude, importé ; l'utilisateur | toujours (12 Ko) ; l'utilisateur pour s'orienter |
| Mémoire de Claude | `tasks/lessons-actives.md` (injecté), `tasks/lessons.md` (grep), `MEMORY.md` (injecté), `tasks/reprise-*.md` | Claude | à froid ; grep par mot-clé avant de toucher un sujet ; après chaque correction |
| Chantiers | `tasks/README.md`, `tasks/plans/`, `docs/superpowers/specs/` | Claude (bloc suiviPlan injecté) ; l'utilisateur (vue VS Code, organigramme) | à la reprise d'un chantier |
| Référence Berry, drivers, protocoles | `outils_docs/reference_berry/`, `.doc_for_ai/` | Claude à la demande | avant de toucher un module de `data/` |
| Guides des outils | `outils_docs/guides_outils/` | l'utilisateur (depuis la tuile de l'annuaire) ; Claude quand il modifie l'outil | à l'usage |
| Vérification | `outils_docs/verification/`, `.claude/agents/`, skill `bancs` | Claude | avant commit, après modif, devant une panne |
| Environnement | `outils_docs/environnement/` | Claude avant un build ou une synchro ; l'utilisateur au montage d'un poste | rare |
| Matériel | `outils_docs/materiel/` + dossiers de schémas | les deux | à la demande |
| Historique | `outils_docs/historique/`, `tasks/archive/` | personne en routine | pour retrouver un pourquoi |

Un fichier par outil ou par groupe : par outil. Le bloc Build fait déjà 535 lignes à lui seul ; un fichier par groupe
de l'annuaire (Déploiement = Build + tâches + synchro) dépasserait 50 Ko et Claude relirait tout pour un onglet. Le groupe
reste visible dans l'index, et le nom d'après `NOM_CIBLE` permet un contrôle mécanique : chaque `build/cible_*.py` doit avoir
son guide et sa ligne dans l'index.

Le maître : `outils_docs/INDEX.md`, fichier neuf. Pas `README.md` transformé, car il est cité 28 fois par `CLAUDE.md`,
par 45 plans, 14 specs, 6 fichiers de `.claude/` et 2 fichiers de code [comptés par grep] : le convertir en index casserait
tous ces renvois d'un coup. Un fichier neuf se crée sans rien casser. Brouillon complet : `brouillon_INDEX_maitre.md`
(même dossier), écrit sur les chemins d'aujourd'hui pour être juste le jour de sa création.

Ce qui reste dans `CLAUDE.md` (~14 Ko) : démarrage (raccourci, sans les reprises), pas de graphify (exemption complète :
ni pré-commit, ni création de carte), synchro du fork (1 Ko : détecter sans synchroniser), commits, fichiers interdits,
vigilances de build (1,5 Ko de règles), charte des logs (1 Ko, à garder : `data/fs/logFonctions.be` et
`berry/charte_logs.py` déclarent en commentaire qu'une copie est dans `CLAUDE.md`, et `data/fs/*.be` ne se touche pas sans
accord), demandes récurrentes, principe des exceptions de 500 lignes (3 lignes), un tableau de 12 sujets, et la ligne
`@outils_docs/INDEX.md`. La règle d'entretien s'y écrit : « une fonctionnalité nouvelle = une ligne dans INDEX.md ».

## 2. Liste des périmés à soumettre à l'utilisateur

### 2.1 Supprimer (liste courte, sans contenu à sauver)

| Fichier | Preuve | Proposition |
|---|---|---|
| mémoire `project_onglets_fenetre2.md` | relevé d'onglets d'une seule session du 31/10 | supprimer, retirer sa ligne de `MEMORY.md` |
| mémoire `project_sauvegarde_scripts.md` | « état final mai 2026 », descriptif dérivable du code, seul fichier à l'ancien format | supprimer |
| `tasks/correctif-udp-interface-2026-10-17.diff` | `CLAUDE.md` le dit historique, la référence est `udpFonctions.be` ; le diff reste dans git | supprimer |
| `docs/superpowers/plans/_sauvegarde-avant-solidify/` | logs de build et `.ini.avant` de juillet, essai clos | supprimer |
| `.claude/skills/pcb-tasmota/scripts/.claude-flow/` | reste de claude-flow archivé, ignoré par git | supprimer |
| `outils_docs/README.md` l. 2893 à 3063 | liste de « devices » obsolète, modifications C++ du pied de page, aide-mémoire d'emojis ; contient aussi des adresses du réseau local et des redirections de ports de la box dans un dépôt public (valeurs non recopiées ici) | supprimer ; si l'utilisateur tient aux redirections, les garder hors dépôt. L'historique git les conserve de toute façon |

### 2.2 Archiver (contenu juste à sa date, faux ou inutile aujourd'hui)

| Fichier | Preuve | Proposition |
|---|---|---|
| `tasks/reprise-chantier-modbus-grenier.md` (45 Ko) | encadrés « ÉTAT AU » empilés ; « jamais exercé sur un bus réel » contre « grille P4 + cuve VALIDÉE le 17/10 » dans le même fichier ; plan `modbus-garage` clos | extraire 30 lignes vers `tasks/reprise-modbus-garage.md` (cibles garage, décisions, reste : rideau id 3, E4/E5, `seq`, BUS_SERIE_MUET), archiver le reste dans `tasks/archive/` |
| `tasks/reprise-solidification-berry.md` (17 Ko) | « prochaine action du 2026-07-16, dépassée » ; généralisation faite ; mécanisme et pièges dans `SOLIDIFICATION_BERRY.md` | archiver ; reporter « reste à solidifier » dans `SOLIDIFICATION_BERRY.md` si encore vrai |
| `outils_docs/CHANGELOG.md` | dernière entrée 01/05/2026 ; affirme l'abandon de ModBusUDP, faux | archiver, ne plus le présenter comme vivant (`git log` le remplace) |
| `outils_docs/ANALYSE_CLES_MAC_TELEPERIOD_2026-10-27.md` | « décision en vigueur : les clés restent » ; faux depuis `6836a0d29` (28/10) | ajouter « appliqué le 2026-10-28 », archiver |
| `outils_docs/ANALYSE_VOIE_MQTT_2026-11-16.md` | « rien n'est codé » ; plan `voie-mqtt` à 90 %+ | ajouter « codé, voir README et PROTOCOLE §11 », archiver |
| `ANALYSE_DEBITMETRES_CHAUFFAGE_2026-11-08.md`, `ANALYSE_BERRY_MODBUS_DISCOVERY.md`, `AUDIT_MODBUS_2026-09-29.md`, `AUDIT_BERRY_2026-10.md`, `DIAGNOSTIC_UDP_2026-10-17.md` | traces datées, état réel ailleurs | archiver ; une ligne d'état en tête (AUDIT_BERRY : « voir plan actions-audit-berry », chemins du rideau et du différentiel périmés, titre A7 en double) |
| `AUDIT_RELAIS_CAVE_S3_2026-10-31.md` | verdict du 31/10 dépassé par le S3 de remplacement (`3501e194f`) ; plan en pause | archiver après décision sur les 3 plans cave |

### 2.3 Mettre à jour (vivants, mais une affirmation est fausse)

| Fichier | Ce qui est faux | Correction |
|---|---|---|
| `tasks/lessons-actives.md` | 16 jours et 65 leçons de retard, tronqué à l'injection | régénérer sous le budget réel (étape 1) |
| `tasks/README.md` (146 Ko) | 94 lignes répétées mot pour mot, 426 cases recopiées | version courte générée (étape 6) |
| `outils_docs/partitions/README.md`, `build_fin_partitions/README.md`, `sauvegarde_config/README.md` | « rien n'est réalisé » ; les trois onglets existent avec leurs sondes | une ligne « réalisé, modèle X, le … » |
| `CLAUDE.md` | décrit deux fois l'onglet Sauvegarde (« choix en attente » et « modèle B ») | retirer la première au passage de l'étape 4 |
| `outils_docs/SOLIDIFICATION_BERRY.md` | encadré « phase 1 en cours » contre verdict du 2026-07-15 | réécrire l'encadré |
| 3 specs (`solidification-berry-design`, `annuaire-outils-design`, `page-build-televersement-design`) | « non implémenté » | statut d'une ligne |
| `outils_docs/SOUS_AGENTS.md` | une ligne vide coupe le tableau ; colonne « modifie des fichiers : non » alors que `memory: local` donne Write et Edit | corriger, ajouter famille et usage |
| `outils_docs/HISTORIQUE_SYNCHRO_FORK.md` | en-tête cite le script sans `maintenance/` | corriger dans `synchronise_fork_tasmota.py` (il l'écrit) |
| `outils_docs/LIENS_WEB.md` | `genere_liens_web.py --verifier` : en retard | régénérer |
| `outils_docs/README.md` (index) | « 48 plans » (il y en a 64), index « exhaustif » qui oublie 15 documents | remplacé par INDEX.md |
| mémoires `project_historique_capteurs`, `project_chantier_modbus_grenier`, `project_statut_cartes`, `project_portail_jardin` | faits réalisés depuis (12 persist ont l'historique, cave sur le nouveau code, impulsion du portail faite) | réduire à l'état actuel ; la seconde doit pointer vers `reprise-modbus-garage.md` |
| mémoire `project_p4_wifi_veille_modem` | `SetOption127 1` n'est écrit nulle part dans le dépôt : perdu au prochain `erase_upload` | le noter dans l'autoexec ou le persist du P4 (accord : `data/`) |
| `c:\Users\fdaub\CLAUDE.md` | répète le global (3,7 Ko injectés en double) | réduire à un renvoi |
| plans `sauvegarde-config-cartes` (100 %), `energie-differentiel` (99 %), `page-build-televersement` (98 %), `jauges-cuve` (95 %) | actifs alors que finis | clore avec bilan |
| plan `ethernet-p4` (actif, 0/38) | le code Ethernet existe, absorbé par `voie-reseau-ethernet` et `rgx-ethernet-uplink` | clore « remplacé par » (à confirmer) |
| `navigateur-ftp-cartes-a5-reprise` ; `relais-cave-s3`, `audit-relais-cave-s3`, `cave-s3-waveshare` | un chantier, deux ou trois plans | lier par `parent:` ou fusionner |
| `outils_docs/PLC_OPENPLC.md` | cours général sans lien avec le code, aucune adresse vérifiée | à décider : `materiel/` ou suppression |

## 3. Plan de migration (du meilleur rapport gain/risque au plus risqué)

Chaque étape est un commit à part, précédé de `controleur-secrets`. Rien n'est lancé sans l'accord de l'utilisateur.

| # | Étape | Fichiers touchés | Ce qu'elle casse | Vérification | Accord |
|---|---|---|---|---|---|
| 1 | Leçons réellement injectées | `~/.claude/helpers/injecte_lecons.cjs` (réserve 3000 -> 1000 o, message « synthèse périmée » au-delà de 20 nouvelles), `~/.claude/skills/lecons-synthese/SKILL.md` (limite 7000 -> 4500 o, récidives en tête, compteur), puis `/lecons-synthese` | rien | `node ~/.claude/helpers/test_injecte_lecons.cjs` ; exécuter le hook : sortie < 8000 o, sans « tronquée », 5 récidives visibles | oui : config `~/.claude`, sous forme d'un script réversible que l'utilisateur lance lui-même (mémoire `feedback_config_claude_classifieur`) |
| 2 | Lever les contradictions | `CLAUDE.md` (lecture de lessons : grep par mot-clé ; règle de push selon décision ; exemption graphify complète), mémoire `feedback_commit_push_autorise` ou `/commite` | rien | relire les 3 phrases ; `grep -n "en entier" CLAUDE.md` | oui (décision 1) |
| 3 | Créer `outils_docs/INDEX.md` | INDEX.md (neuf, d'après le brouillon), `maintenance/verifie_references_docs.py` (ajouter INDEX.md à `DURABLES`, ligne 33) | rien | `python outils_docs/scripts_python/maintenance/verifie_references_docs.py` code 0 ; `test_verifie_references_docs.py` | oui (décision 2) |
| 4 | Alléger `CLAUDE.md` à ~14 Ko | `CLAUDE.md` ; neufs `verification/EXCEPTIONS_500_LIGNES.md`, `environnement/NOUVEAU_POSTE.md`, `environnement/VIGILANCES_BUILD.md` ; `.claude/agents/relecteur-docs.md` (règle 4 et chiffres des exceptions : vérifier INDEX.md et le nouveau fichier d'exceptions) ; `/fin-de-session` (« voir la carte des documents ») | le contrôle de `relecteur-docs` tant que sa règle 4 n'est pas changée : même commit | `wc -c CLAUDE.md` < 16 000 ; `verifie_references_docs.py` ; lancer `relecteur-docs` ; une session neuve trouve un outil par l'index | oui |
| 5 | Reprises | `tasks/reprise-modbus-garage.md` (neuf, 30 lignes), `tasks/archive/` (les deux reprises), `CLAUDE.md` § démarrage, mémoire `project_chantier_modbus_grenier` | rien si le préfixe `reprise-` est gardé (`fin-de-session.md` ligne 20 et `rappel_apres_compactage.sh` lisent `tasks/reprise-*.md`) ; aucun hook ni agent ne cite les deux noms [vérifié] | `grep -rn "reprise-chantier\|reprise-solidification" .claude CLAUDE.md ~/.claude/projects/*Tasmota*/memory` vide | oui |
| 6 | `tasks/README.md` court | `.claude/hooks/index_plans.mjs` et son banc `test_index_plans.mjs` ; l'agent `verificateur-plans` le lit | l'extension `suivi-plan` régénère par le même script : rien d'autre | `node .claude/hooks/test_index_plans.mjs` ; `node .claude/hooks/index_plans.mjs --verifier` ; taille < 12 Ko | oui |
| 7 | Corrections des « à mettre à jour » (§2.3, hors plans et mémoires) | READMEs de maquettes, specs, SOUS_AGENTS, SOLIDIFICATION_BERRY, générateurs de HISTORIQUE_SYNCHRO_FORK et LIENS_WEB | rien | `genere_liens_web.py --verifier` ; banc de la synchro (`test_synchro_fork_assistant.py`) | non pour les .md ; oui pour le script de la synchro |
| 8 | Garde mécanique des secrets | hook `PreToolUse` (Read, Grep, Bash, PowerShell) qui refuse la lecture brute de `_persist.json`, `user_config_override.h`, `tasmota_defines_for_berry.*`, sauvegardes de cartes, sauf par un filtre de masquage ; motifs repris de `garde_commit.cjs` (constante `SECRETS`) ; une ligne dans chaque agent qui a Bash | des lectures légitimes : prévoir le lecteur masqué avant le refus | banc du hook (cas refusé, cas masqué, faux positif) ; une semaine sans nouvelle leçon « secret » | oui |
| 9 | Mémoire native | `MEMORY.md` par rubriques ; suppressions et réductions du §2.1 et §2.3 | rien | liens de `MEMORY.md` tous valides ; taille < 6 Ko | oui |
| 10 | Clore les plans finis, bilans | 4 plans à 95 %+, `ethernet-p4`, plans cave ; section `## Bilan` ; `index_plans.mjs --verifier` signale un plan clos sans bilan | rien | `node .claude/hooks/index_plans.mjs --verifier` | oui pour `ethernet-p4` et les plans cave |
| 11 | Ranger les .md libres d'`outils_docs/` | `historique/`, `materiel/`, `reference_berry/`, `verification/` ; renvois de `CLAUDE.md`, INDEX, agents (`verificateur-solidification`, `relecteur-docs`, skills `bancs`, `pcb-tasmota`) ; constante de `carte_modules_berry.py` ; `DURABLES` | les renvois des plans et specs (traces datées, laissés tels quels) | `git mv` seulement ; `verifie_references_docs.py` ; `grep -rn "<ancien nom>"` sur `.claude`, `CLAUDE.md`, `outils_docs/scripts_python` vide ; `carte_modules_berry.py` relancé sans diff | oui |
| 12 | Découper `outils_docs/README.md` | `guides_outils/`, `reference_berry/` (12 fichiers), README réduit ; renvois de `CLAUDE.md`, INDEX, 6 fichiers de `.claude/`, 2 en-têtes de code (dont `data/fs/logFonctions.be`) ; plans actifs seulement | 45 plans et 14 specs citent `README.md § …` : laissés comme traces ; l'aide en ligne si une page lie une ancre | `verifie_references_docs.py` ; `grep -rn "README.md §" .claude CLAUDE.md outils_docs/INDEX.md` vide ; contrôle « chaque NOM_CIBLE a son guide » | oui, avec accord séparé pour l'en-tête de `logFonctions.be` |

Non recommandé pour l'instant : découper `PROTOCOLE_MODBUS.md` (17 renvois depuis le code, gain faible : une table de
lecture en tête suffit) ; déplacer les plans clos dans `tasks/plans/clos/` (quatre lecteurs à adapter : `index_plans.mjs`,
mod `suivi-plan` qui rattache les conversations par chemin, extension VS Code, `organigramme_plans.py` ; le statut d'en-tête
et l'index court suffisent à ne plus les voir en vrac).

## 4. Améliorations du dispositif de mémoire

| Proposition | Verdict | Pourquoi |
|---|---|---|
| `lessons-actives.md` sous le budget réel (4,5 Ko), une règle par thème, format `règle \| dernier incident \| récidives` | recommandé, priorité 1 | c'est le seul canal garanti vers une session froide ; aujourd'hui il est coupé |
| Hook qui annonce « synthèse périmée » au-delà de 20 nouvelles leçons | recommandé | la synthèse a 16 jours de retard sans que rien ne le dise |
| Index par thème avec compteur de récidives en tête de `lessons.md` (secrets 12, faux vert 15, build concurrent ~20, sessions parallèles ~15, solidification ~20, affirmation non vérifiée 25+) | recommandé | le grep marche déjà ; l'index dit quels thèmes justifient un contrôle mécanique |
| Découper `lessons.md` en un fichier par thème | non | le hook et le grep supposent un seul fichier append-only ; un index suffit |
| Contrôle mécanique des secrets à la lecture (étape 8) | recommandé, priorité 2 | une 13e phrase n'arrêtera pas la 13e fuite ; les motifs existent déjà dans `garde_commit.cjs` |
| Règle « récidive = contrôle mécanique » : à la 3e occurrence d'un thème, proposer un hook ou un banc plutôt qu'une ligne | recommandé | les thèmes couverts par un garde (`garde_build`, `verificateur-solidification`) ralentissent ; les autres non |
| Section `## Bilan` (marché, raté, règle retenue, cases ouvertes reportées ou abandonnées) obligatoire à la clôture, vérifiée par `index_plans.mjs --verifier` | recommandé | aucun des 64 plans n'a de bilan ; 20 plans clos ont des cases ouvertes sans trace ; le vécu des pannes reste enfoui dans les preuves |
| Remonter avant archivage les enseignements de `temps-compilation`, `lib-ignore-*`, `graphiques-web`, `*-mpu6050`, `build-reparations` | recommandé | sinon ils ne vivent que dans des plans qu'on ne rouvre pas |
| `MEMORY.md` en 4 rubriques (préférences, chantiers ouverts, faits matériels et pièges, références), lignes < 150 caractères | recommandé | aujourd'hui chronologique en vrac, 12 lignes de plus de 250 caractères |
| Mémoire `project_*` supprimée ou réduite à la clôture de son chantier | recommandé | 8 des 11 mémoires de chantier vérifiées portent un fait périmé |
| Encadré de tête standard sur chaque référence et guide (usage, date, état, essayé sur carte oui/non, plan lié) | recommandé | il évite les « rien n'est réalisé » et « phase 1 en cours » trouvés ; contrôlable par `relecteur-docs` |
| `@outils_docs/INDEX.md` importé dans `CLAUDE.md` plutôt que « à lire à la demande » | recommandé | 25 leçons d'affirmations non vérifiées montrent qu'une consigne de lecture ne suffit pas ; 12 Ko contre 126 Ko aujourd'hui |
| Contrôle « chaque `NOM_CIBLE` a son guide et sa ligne dans INDEX » ajouté à `relecteur-docs` | recommandé | remplace la règle 4 qui faisait grossir `CLAUDE.md` |
| Reprises remplacées par l'encadré « SI TU REPRENDS À FROID » en tête du plan actif | recommandé à terme | une reprise et un plan pour le même chantier divergent (cas ModBus) |
| Mémoire locale retirée des agents qui ne l'ont jamais écrite | non | gain nul, coût d'une modification d'agents |
| `relecteur-docs` passé de haiku/low à sonnet | à voir | il portera le contrôle de l'index ; à mesurer sur un passage |
| Archiver `~/.claude/helpers/` de claude-flow (`auto-commit.sh` compris) | recommandé, hors .md | inertes mais trompeurs pour une session qui les découvre |

## 5. Décisions à demander à l'utilisateur

1. Push : garder l'autorisation du 29/10 (mémoire `feedback_commit_push_autorise`), écrite dans `CLAUDE.md` et `/commite`,
   toujours derrière `preparateur-push` (recommandé), ou revenir à « jamais sans demande » et supprimer la mémoire ?
2. Le maître `outils_docs/INDEX.md` est-il importé dans `CLAUDE.md` par `@` (recommandé), ou seulement lu à la demande ?
3. `outils_docs/README.md` est-il découpé en un fichier par outil et par fonction des cartes (recommandé), par groupe de
   l'annuaire, ou laissé entier avec l'index seul ?
4. Les archives restent-elles dans le dépôt (`outils_docs/historique/`, `tasks/archive/`, recommandé : retrouvables par grep
   et citées par les plans), ou sont-elles supprimées en se fiant à l'historique git ?
5. Accordez-vous la suppression des six éléments du §2.1, dont le reliquat du README avec ses données réseau (recommandé : oui
   en bloc), ou les voulez-vous un par un ? Et `PLC_OPENPLC.md` : garder dans `materiel/` (recommandé) ou supprimer ?

## 6. Limites

Je n'ai pas relu ligne par ligne les plans de plus de 30 Ko ni les 280 Ko du README : les plages et tailles viennent des
audits. Les comptes de récidives sont ceux de l'audit des leçons (approximatifs). Le gain de tokens suppose que la liste des
skills et des agents, non mesurée, ne change pas. Aucune commande d'écriture n'a été lancée.
