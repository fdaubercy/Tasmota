# Relecture intégrale de `outils_docs/README.md` (2026-11-23)

Lecture ligne à ligne des 3 063 lignes par trois sous-agents (lecture seule), pour l'action A20 du plan
`tasks/plans/binomes-berry.md`. Les adresses du réseau local sont masquées (`<IP locale>`). À archiver dans
`tasks/archive/` une fois A20 faite.

## Ce qui en ressort pour la suite

- Destinations : une ligne par section dans les tableaux récapitulatifs de chaque partie (plage -> fichier).
- Build (l. 1058-1590) se coupe en 7 guides : `build_web.md`, `_compilation`, `_ota`, `_fichiers`, `_memoire_defaut`,
  `_sauvegardes`, `_reparations` (partie 2).
- Outils sans aucune section : `pont_serie`, `sniffeur_modbus`, `sniffeur_mqtt`, `syslog_tasmota`, `testeur_udp`,
  `annuaire` (guides à écrire d'après CLAUDE.md). `icones_catalogue` est noyé dans l'atelier des écrans (l. 2428-2442).
- Reliquat de fin (l. 2893-3063), à NE PAS supprimer en bloc : garder le bloc des commandes personnalisées
  (l. 2969-3037, vers `reference_berry/`, après correction) et la modification C++ du pied de page (l. 3041-3053, piège
  de synchro) ; le TODO (l. 2954-2967) est à soumettre à l'utilisateur ; la table des redirections de la box est périmée
  (IP absentes des persist, port du rideau faux) : supprimée.
- Affirmations périmées : 10 (partie 1), 6 (partie 2), 13 (partie 3) ; les corriger AU MOMENT du découpage, pas avant.
- Pièges à reporter dans `outils_docs/INDEX.md` : listés à la fin de chaque section.



---

# Partie 1

# Relecture README.md, lignes 1 a 1057 (lecture seule)

Toutes les lignes 1 a 1057 ont ete lues avec Read (4 tranches). Verifications par Grep/Glob/Bash en lecture seule. Aucune valeur sensible recopiee.

Legende nature : U = mode d'emploi utilisateur, I = fonctionnement interne pour Claude, H = historique de chantier, P = pieges et echecs.

---

## 1. En-tete et index (lignes 1-64)

- Nature : 100 % navigation (U), sauf lignes 1-13 (bandeau GitHub amont copie de Tasmota, sans valeur).
- Destination : devient `outils_docs/INDEX.md` (ou reste un README tres court qui renvoie a INDEX.md). Les badges/logo (1-13) sont a supprimer ou a garder dans un README minimal.
- Documents cites (tous existent, verifie) : CLAUDE.md, tasks/lessons.md, les deux reprises, organigramme en ligne, SOLIDIFICATION_BERRY, CARTE_MODULES_BERRY, les 3 docs de conception de la solidification, PROTOCOLE_MODBUS, Aide/MODBUS, ANALYSE_BERRY_MODBUS_DISCOVERY, AUDIT_MODBUS, ANALYSE_VOIE_MQTT, schemas/persist.schema.json, 2 cablages ADS1115, skill et agents PCB, scripts_python/, HISTORIQUE_SYNCHRO_FORK, LIENS_WEB, CHANGELOG, plus 6 ancres internes (logs Berry, MPU6050, graphiques, build, fichiers Berry, synchro, sniffeur I2C, organigramme, liens web : toutes valides).
- Documents OUBLIES (existent dans `outils_docs/`, absents de l'index) : EXTENSIONS_TAPP.md, MODELES_ESP.md, PLC_OPENPLC.md, ECRAN_TACTILE_ESP32P4.md, FICHIERS_DRVSET.md, DIAGNOSTIC_UDP_2026-10-17.md, AUDIT_BERRY_2026-10.md, AUDIT_RELAIS_CAVE_S3_2026-10-31.md, ANALYSE_CLES_MAC_TELEPERIOD_2026-10-27.md, ANALYSE_DEBITMETRES_CHAUFFAGE_2026-11-08.md, ICONES_BOUTONS_RELAIS.md, ICONES_IMAGES_SOURCES.md, PORTAIL_JARDIN_MODULE_ET_ALIMENTATION.md, TASMOTA_VOLETS_ROULANTS.md, SOUS_AGENTS.md, et `chauffage/EQUILIBRAGE_CHAUFFAGE_NOURRICE.md`, `tasks/README.md`, `tasks/plans/` (index des plans), `docs/superpowers/specs/` (26 specs), `outils_docs/SOUS_AGENTS.md`, les dossiers de maquettes (jauges, partitions, volets_visuels, visuels_accueil, etc.). Aucun lien vers les ~13 sections « page web » plus bas (Atelier des ecrans, Etiquettes QR, FTP, Assistant persist, Menage, Cartes simulees, Taches planifiees, Sondes, Plan maison, Fabrique tapp, Atelier visuels, Atelier des graphiques) ni vers « La page Energie », « Les jauges de la cuve », « Debits », « Ecran de la cave », « Voie MQTT », « Hue », « coprocesseur » : l'index ne cite que 6 sections du README sur ~35.
- Affirmations fausses ou perimees de l'index :
  1. L26 : « les 48 plans de `tasks/plans/` » : il y en a 65 (66 fichiers moins `_FORMAT.md`). Perime.
  2. L43 : l'analyse MQTT dit que « l'etat reel est dans § Voie MQTT plus bas » : correct, mais cette section (L846) annonce un etat « au 2026-11-19 » alors que le plan voie-mqtt est a 95 % au 2026-11-21 (voir section 12).
  3. L54 : HISTORIQUE_SYNCHRO_FORK.md est dit *(genere)* : vrai, mais son en-tete cite `outils_docs/scripts_python/synchronise_fork_tasmota.py`, chemin qui n'existe plus (le script est dans `maintenance/`). Defaut du fichier genere, pas de l'index.
  4. L53 : la liste des sous-dossiers de `scripts_python/` est exacte (build, outils_pc, berry, maintenance, sauvegarde, reseau), mais l'index ne cite aucun des 22 outils.
  5. L11 : faute de frappe « developpees » (« developpéespour »), et formulation « devices » vs section L2893 : cosmetique.
  6. L56 : CHANGELOG.md « historique des evolutions » : derniere modification git le 17 mai 2026, soit bien avant tout le travail de ce README. Il est abandonne en pratique ; l'index le presente comme vivant.
- Doublon CLAUDE.md : L22 renvoie a CLAUDE.md, pas de duplication de texte.
- Donnees sensibles : aucune dans 1-64.

---

## 2. Les logs Berry : charte et reglages (L65-152, 88 lignes)

- Nature : U 55 % (commandes `ReglageLog`, exemples), I 30 % (ce que le profil ecrase, `actif()`), P 15 % (SERIALLOG_TIMER, profil ecrase les reglages a la main).
- Destination : `outils_docs/reference_berry/LOGS.md`. Section purement carte, pas d'outil PC (sauf une mention de `syslog_tasmota.py` et `verifie_berry.py`, a laisser en renvoi vers `guides_outils/syslog_tasmota.md`).
- Affirmations verifiees :
  - OK : `logFonctions.SORTIES` = serie/web/mqtt/syslog -> SerialLog/WebLog/MqttLog/SysLog (`data/fs/logFonctions.be`).
  - OK : sous-commandes `profil`, `tous`, `help`, `help niveaux` (`logFonctions_aideReglageLog`).
  - OK : `logFonctions.actif` existe (`logFonctions_actif`) ; `nbLogsFiles` est lu par `configGlobal.be` (L301-303).
  - PERIME (incomplet) L90-93 : la liste des cibles omet `ecranSysteme`, `liaisonMqtt`, `emulationHue` que `logFonctions.CIBLES` contient maintenant (22 cibles dans le code, 19 citees). `lorawan`, `volets`, `es8311`, `garage`, `cuve`, `rideau`, `leds`, `historique`, `ecranCave`, `ecranDebits` y sont bien.
  - Non verifiable sans carte : le chiffre 600 s de `SERIALLOG_TIMER` (c'est un defaut Tasmota amont ; `SERIALLOG_TIMER` n'est pas grepable dans `data/`).
- Doublon CLAUDE.md : FORT. Les 4 niveaux, la regle « `logFonctions.log` jamais `log()` direct », « un echec se logue en `erreur` », « pas d'`info` dans un callback frequent », `logFonctions.actif`, `LOG_LEVEL_*` jamais en chiffre, `verifie_berry.py` en avertissements, les deux filtres successifs : tout cela figure dans la section « Logs Berry : la charte » de CLAUDE.md. Le README est la version « utilisateur » (tableau, commandes, persist) ; CLAUDE.md est la version « regles d'ecriture ». A garder dans `LOGS.md` et reduire CLAUDE.md a un renvoi, ou l'inverse. Les deux divergent deja sur le nombre de cibles.
- Pieges a reporter dans INDEX.md :
  - Un `SerialLog 4` tape a la main est ecrase au redemarrage par le profil ; passer par `ReglageLog serie detail`.
  - La console serie se coupe 600 s apres le demarrage (gardee par choix, ne pas reproposer de la desactiver) ; suivre par MQTT, web ou syslog.
  - `actif()` repond « au moins une sortie » : l'economie de construction depend de la sortie la plus bavarde.
  - Une sortie a `detail` affiche aussi les `BRY: GC` (c'est l'outil de mesure RAM).
- Renvois sortants : aucun fichier.
- Sensible : aucune.

---

## 3. La decouverte des cartes : annonce seule (L154-173, 20 lignes)

- Nature : I 70 % (pourquoi la limite 57 Ko), U 30 % (valeurs `AUTO`/`ON`/`OFF`).
- Destination : `outils_docs/reference_berry/DISCOVERY.md` (a completer plus tard avec l'ANALYSE_BERRY_MODBUS_DISCOVERY). Section carte uniquement.
- Affirmations verifiees :
  - OK : `discoveryFonctions.ecoute` existe (`discoveryFonctions_ecoute`, lit `serveur.discovery.ecoute`, defaut `AUTO`).
  - OK : section 29 de `berry/test_discovery.be` (L1672 : « 29. Mode annonce seule (2026-11-21) »).
  - OK : `data/fs/controleDiscovery.be` existe ; `psram` lu via `tasmota.memory()`.
  - A verifier : « ~14 Ko pour 13 cartes » et « limite Berry ~57 Ko » : mesures non reproductibles par grep.
  - Pas de contradiction trouvee avec la memoire du projet (« Discovery sature un ESP32 simple »).
- Doublon CLAUDE.md : aucun.
- Pieges : un ESP32 sans PSRAM esclave doit avoir `serveur.discovery.activation` a `"ON"` sinon son maitre ne le voit pas ; sans PSRAM, ecoute ON = boucle de redemarrage (constate le 2026-11-02 differentiel, 2026-11-21 projecteur barbecue).
- Sensible : aucune.

---

## 4. Les graphiques des mesures (L175-298, 124 lignes)

Sous-sections : intro et fonctions (L175-220), persist de releve (L221-248), `graphiques.json` (L249-287), Verifier (L288-298).

- Nature : U 60 %, I 35 % (regles de decouverte, filtres), P 5 %.
- Destination : `outils_docs/reference_berry/GRAPHIQUES.md`. Section carte (page `/graphiques` servie par la carte). Attention : l'« Atelier des graphiques » (outil PC, L2095) est une AUTRE section a mettre dans `guides_outils/atelier_graphiques.md` ; ne pas les melanger. Seul renvoi croise a creer.
- Coupure : L175-220 + L288-298 = reference ; L221-287 = schemas de persist (peut rester dans le meme fichier).
- Affirmations verifiees :
  - OK : `historiqueFonctions.be` porte `pasMinutes` 5, `dureeHeures` 24, `moisConserves` 24 (L19, L117-120).
  - OK : limites 8 graphiques, 12 series, titre 1-60 caracteres (`graphiquesFonctions.MAX_GRAPHIQUES`, `MAX_SERIES`, L302).
  - OK : `controleWeb.boutonGrafana` (`data/fs/controleWeb.be` L392), `banc_graphiques.py` existe.
  - OK : ECharts compresse 368 202 octets = « 368 Ko » (`data/sd/js/echarts.min.js.gz`).
  - OK : `rafraichissement` 60 par defaut, 10 au minimum (`graphiquesFonctions.periode`).
  - FAUX (exemple) L235 : l'exemple de `grafana` montre une URL Grafana avec adresse locale. Dans les persist reels, 5 fichiers portent la cle `grafana` (debits PAC x2, cave ecran, P4, cuve) ; celui de l'ecran de la cave la porte vide. Pas contradictoire.
  - A verifier : L285-286 « Cle non posee sur la cave et le bureau (decide le 2026-10-18) » : or `data/cave/tasmota32s3-ecran/_persist.json` et les deux cartes `bureau/...debits-pac` portent `"grafana"` (vide ou non). L'affirmation est perimee pour les cartes de debits (bureau) ; a trancher en regardant la valeur (non recopiee ici).
  - `controleGarage.filtreHistorique` (L296-297) : le Grep n'a trouve aucune definition `filtreHistorique` dans `data/fs` ; il faut chercher dans `data/garage/tasmota32p4-serveur-modbus/controleGarage.be` (non confirme). Soupconne perime.
- Doublon CLAUDE.md : FORT mais bref : CLAUDE.md redecrit `/graphiques`, `graphiquesFonctions.be`, `historiqueSeries.be`, ECharts compresse, `graphiques.json` HORS persist, `diverses.historique.grafana`, bouton `controleWeb.boutonGrafana`. Meme contenu en plus court : candidat a devenir un renvoi.
- Pieges : curl sur `/histo` sans `Referer` : Tasmota coupe sans reponse (`curl: (52)`) ; le persist est charge entier et en permanence en RAM (ne pas y mettre l'affichage) ; un compteur n'est trace qu'une fois regle (`compteurs`) ; sur le P4 une cuve sans capteur donne des trous, pas des zeros.
- Renvois sortants : aucun lien fichier ; cites : `/histo?p=...`, banc.
- Sensible : L235 contient une adresse IP locale (exemple d'URL Grafana) ; a anonymiser lors du decoupage.

---

## 5. La page Energie (L301-351, 51 lignes)

- Nature : U 40 %, I 40 % (calcul, fichiers, calibrage), procedure de portage 20 % (L338-351).
- Destination : `outils_docs/reference_berry/ENERGIE.md`. Carte seulement (la destination « Energie » de l'atelier est a renvoyer vers `guides_outils/atelier_graphiques.md`).
- Affirmations verifiees :
  - OK : `energieFonctions.DEFAUTS_BL0942 = {596, 15187, 251213}` (L48), `DESCRIPTION_MAX = 4096` (L35), `MAX_ARCHIVES`/`MAX_MOIS = 24`, `SEUIL_KO = 16` (16 Ko libres).
  - OK : fichiers `etat.json`, `mois-AAAA-MM.json`, `prix.json`, `courbe.bin` (en-tete de `energieFonctions.be`).
  - OK : routes `f=donnees`, `f=direct`, `f=description`, `f=mois`, `f=tarifs` (`energieFonctions.be` L560).
  - OK : fichiers `energie.html`, `energieTarifs.html`, `energie.css`, `energie.js`, `energieTarifs.js` ; liste `page_energie` du cenv (L80) ; env `tasmota32-bureau-interrupteur-energie` (L1005) ; autoexec contient `demarrage.charge(["controleEnergie"], "diverses.energie")`.
  - OK : tous les bancs cites existent (`banc_energie.py`, `banc_energie_routes.py`, `banc_energie_description.py`, `test_energie_rendu.mjs`).
  - Ecart de forme : L338 dit « aucune autre carte du parc n'en a l'usage au 2026-11-09 » : date figee, a rafraichir ou deplacer en historique.
- Doublon CLAUDE.md : FORT (CLAUDE.md porte un paragraphe d'une quinzaine de lignes sur la page `/energie`, `energieFonctions.be`, `page_energie`, spec, bancs). Candidat a renvoi.
- Pieges : compteur `Total` NON retabli seul (relever avant flash, puis `EnergyTotal <Wh>`) ; un compteur multi-voies donne une page avec compteur illisible et rien d'ecrit ; la description JSON > 4096 octets est ignoree (repli sur la page d'avant) ; le module est solidifie : un envoi du FS seul ne suffit pas.
- Renvois sortants : spec `docs/superpowers/specs/2026-10-31-page-energie-differentiel-design.md` (OK).
- Sensible : aucune.

---

## 6. Les jauges de la cuve (L353-379, 27 lignes)

- Nature : U 50 %, I 50 %.
- Destination : `outils_docs/reference_berry/CUVE_PAGE.md` (ou fusionner avec une future fiche « cuve »). Carte.
- Affirmations verifiees :
  - OK : `cuvePageFonctions.be` (route, page), `data/sd/html/cuve.html`, `css/cuve.css`, `js/cuve.js`, `js/echarts-liquidfill.min.js.gz` (3 429 octets = 3,4 Ko), `liquidfill.js.gz` servi par `/cuve?f=`.
  - OK : liste `page_cuve` du cenv ; `tensionSonde_V` present dans `controleGarage.be`, `controleCuve.be`, `cuveFonctions.be`, `cuve.js`.
  - OK : registre 4708 documente dans `PROTOCOLE_MODBUS.md` (`Calcul_tensionSonde`, id 5).
  - A verifier : L379 « banc `banc_cuve_page.py` » existe.
  - Perime : L355 « Premier essai du 2026-10-31 » : date de chantier, pas un fait d'usage.
- Doublon CLAUDE.md : FORT (paragraphe `Page /cuve` de CLAUDE.md).
- Pieges : sans historique actif la page n'affiche rien ; ECharts vient de `/graphiques?f=echarts.js.gz` (meme cle de cache localStorage, pas de 2e telechargement) ; fichiers embarques uniquement sur cuve et P4.
- Sensible : aucune.

---

## 7. Les debits de la nourrice de chauffage (L383-468, 86 lignes)

- Nature : U 35 %, I 45 % (voies, registres, capteur muet), H 10 % (plans, « pas encore essayees »), commandes 10 %.
- Destination : `outils_docs/reference_berry/DEBITS_PAC.md`. Concerne deux cartes (acquisition + affichage) : coupe possible en L391-425 (affichage et noms) / L426-468 (acquisition). Un seul fichier suffit.
- Affirmations verifiees :
  - OK : dossiers `data/bureau/tasmota32s3-serveur-debits-pac` et `...-ecran-debits-pac` existent avec `debitsFonctions.be`, `controleDebits.be`, `ecranDebitsFonctions.be`, `controleEcranDebits.be`, `equilibrage.html`, `equilibragePage.be`, `equilibrage_carte.js`, `pages.jsonl`.
  - OK : `ReglageDebits k|nom|fenetre|veille|aide` (`debitsFonctions_aideReglageDebits`, exemple `ReglageDebits k 3 11.4`) ; `K_DEFAUT = 11.0` (YF-B2).
  - OK : `ReglageEcranDebits`, `ReglageModbus PeriodeReleve`, `LectureGroupee` (48 occurrences dans 4 fichiers `.be`).
  - OK : noms `analogique1`..`analogique6`, champ `nom` « Debit 1 » a « Debit 6 » dans le persist de l'ecran.
  - OK : `custom_interface_ecran = haspmota` et `custom_interface_ecran_lvgl` du cenv ; `build/interface_ecran.py::applique` et `::retire_exclus` existent.
  - OK : env `tasmota32s3-bureau-serveur-debits-pac` et `...-bureau-ecran-debits-pac` (cenv L1084 et L1129).
  - PERIME : L389 « Pas encore essayees sur des cartes reelles (2026-11-11) » : date figee.
  - Divergence mineure : l'env LVGL de l'ecran de debits a un `ecranLvgl.be` genere (CLAUDE.md dit de ne pas l'editer a la main) ; le README ne le rappelle pas.
- Doublon CLAUDE.md : FORT (CLAUDE.md consacre un long paragraphe aux debits sur deux cartes, avec les memes registres 4704 a 4710, `ReglageEcranDebits`, `ReglageDebits`).
- Pieges : « flasher l'acquisition AVANT l'affichage » ; `ReglageEcranDebits fenetre` a recopier a la main sur l'acquisition ; un depart ferme plus de 10 min est signale « muet » ; `/json/equilibrage.json` est efface par un envoi du FS en image (a reenregistrer) ; un favori vers `/equilibrage` sans Referer donne une page vide qui se recharge.
- Renvois sortants : `ANALYSE_DEBITMETRES_CHAUFFAGE_2026-11-08.md` (OK), `chauffage/EQUILIBRAGE_CHAUFFAGE_NOURRICE.md` (OK), fiche `WAVESHARE_ESP32-S3-Touch-LCD-7B.md` (non verifiee, dans le dossier brochage), plans `debitmetres-chauffage.md` et `debits-deux-cartes.md` (OK).
- Sensible : L396-397 et L399 portent des adresses IP du reseau local (relais `192.168.x.x:8080`) ; L400 aussi un topic MQTT ; a masquer ou deplacer.

---

## 8. L'ecran de la cave (L472-538, 67 lignes)

- Nature : U 55 % (pages, touches, mise en service), I 40 % (pannes flotteurs, grise), H 5 %.
- Destination : `outils_docs/reference_berry/ECRAN_CAVE.md`. Carte.
- Affirmations verifiees :
  - OK : env `tasmota32s3-cave-ecran` (cenv L802) ; fichiers `ecranCaveFonctions.be`, `controleEcranCave.be`, `ecranCaveHaspmota.be`, `pages.jsonl` ; serveur `controleCommandesEcran.be` et `controlePompeVideCave.be` ; bancs `banc_ecran_cave.py`, `banc_commandes_ecran.py`, `banc_pompe_cave.py`.
  - OK : `pannes.antiRebond` = 5 et `maxArretsMinuterie` = 3 ; `peremption` dans le persist de l'ecran.
  - PERIME / FAUX (le plus net) : L527-529 « sur le serveur de la cave, passer a ON `TasmotaSlaveModBus1.activation` et `modules.ecranCave.activation` : tant qu'ils sont a OFF ... ». Dans `data/cave/tasmota32s3-serveur-rly/_persist.json`, `TasmotaSlaveModBus1` est deja `"activation": "ON"` (nom « ECRAN-CAVE (carte a venir) ») et `modules.ecranCave.activation` est deja `"ON"`. La procedure decrit un etat OFF qui n'existe plus au depot.
  - Ambigu : la table touches->relais (touche 1->3, 2->5, 3->4) colle avec `actions` du persist ; touche 4->1 non reverifiee.
  - Doublon de nom : le dossier `data/cave/tasmota32-serveur-rly/` (ESP32 simple) contient aussi `controlePompeVideCave.be` : le README ne precise pas lequel des deux serveurs est vise (S3).
- Doublon CLAUDE.md : aucun (CLAUDE.md n'a pas `ecranCave`).
- Pieges : la touche 5 (redemarrer) n'est JAMAIS relancee (sinon boucle de redemarrage) ; une touche envoie l'etat voulu, jamais une bascule ; valeur grisee = touche refusee apres 15 min sans message ; un esclave ModBus actif sans carte fait tomber le releve en timeout.
- Renvois sortants : plan `ecran-cave-vues-commandes.md` et spec `2026-11-12-ecran-cave-vues-commandes-design.md` (OK), `ICONES_IMAGES_SOURCES.md` (OK), `ecran.json` de l'atelier (dossier `atelier_ecrans/cartes/tasmota32s3-cave-ecran`, OK).
- Sensible : aucune.

---

## 9. Inclinaison d'un volet ou d'une trappe (MPU6050) (L540-683, 144 lignes)

- Nature : U 40 % (apprentissage, commandes), I 50 % (blocage, sens inverse, position reelle, arret en butee), P 10 %.
- Destination : `outils_docs/reference_berry/INCLINAISON_MPU6050.md`. Carte.
- Affirmations verifiees :
  - OK : `vrFonctions.changementEtatCapteur`, `ligneWebInclinaison`, `configBoutons`, `commandeSens`, `enReglage`, `configVRByJson`, `reglageVolets` existent ; log `VR_INCLINAISON: ...` reel (`vrFonctions.be` L468+) ; `ReglageVolets Apprentissage <id> ouvert|ferme` et `Inclinaison <id>` dans l'aide.
  - OK : banc `banc_inclinaison.py` existe.
  - FAUX / PERIME GRAVE (L555-556) : « Lu en Berry ..., PAS par le pilote C de Tasmota : ne pas compiler `USE_MPU6050` ». `tasmota/user_config_override.h` contient maintenant `#define USE_MPU6050` (L1040 et L1635, commentaire du 2026-11-11 : « pilote C du MPU6050 compile (JSON SENSOR a chaque TelePeriod). La lecture rapide en course reste celle de vrFonctions.be »). Le README affirme le contraire de ce qui est compile : le pilote C EST compile, et la bibliotheque « MPU6050 I2C » a ete retiree du `lib_ignore` (liste `sans_mpu6050`). Il faut corriger le paragraphe : double lecture, Berry pour la course, pilote C pour le TelePeriod.
  - Non verifie : constantes 0x6B / 0x3B / filtre 0x1A (non trouves par Grep simple), `blocage` 5 s, `blocageDegres` 1, `sensInverse` 3 : valeurs par defaut a verifier dans `vrFonctions.be`.
  - Non verifie : `ShutterMotorStop` 500 ms (reglage Tasmota amont).
- Doublon CLAUDE.md : PARTIEL (CLAUDE.md mentionne MPU6050 3 fois, dont `banc_inclinaison.py` et la façade).
- Pieges : « Ce n'est pas une securite » (lecture Berry 250 ms au mieux, fins de course physiques indispensables) ; `ShutterSetPosition` jamais pendant une course (remet la direction a 0 sans couper le moteur) ; l'arret passe AVANT le recalage (`ShutterStop` coupe le moteur, `ShutterSetOpen/Close` seul non) ; commandes `Shutter*` moins de `ShutterMotorStop + 100 ms` apres un arret : mises en differe (boucle `loop()` sinon) ; angle fige sur une butee non designee « Inclinaison » = arrivee, pas blocage ; apprentissage refuse si butees a moins de 10 degres ou arc traversant ±180 ; un redemarrage entre les 2 temps de l'apprentissage efface la 1re butee.
- Renvois sortants : aucun lien fichier ; cite `xdrv_27_esp32_shutter.ino`.
- Sensible : aucune.

---

## 10. Visuel des volets et reglage de leurs durees (L685-792, 108 lignes)

Sous-sections : facade (L689-697), persist (L698-713), decor/fins de course/camera/portail (L715-753), regler les durees (L755-770), facade du rideau (L772-779), recopier les durees (L781-783), bancs (L785-792).

- Nature : U 50 %, I 35 %, H 15 % (plans, dates, « en cours »).
- Destination : `outils_docs/reference_berry/VOLETS_FACADE.md` (facade + persist + rideau + portail) et un second fichier possible `outils_docs/reference_berry/VOLETS_REGLAGE_DUREES.md` pour L755-770 (page `/volets`). Si un seul fichier : `VOLETS_FACADE.md`. Le « Portail de jardin » (L745-747) concerne aussi la voie MQTT (section 12) : renvoyer.
- Coupe carte / outil PC : tout est carte ; les sondes Chrome (L788-789) sont des bancs d'outils PC, a laisser en fin de fichier.
- Affirmations verifiees :
  - OK : `vrPages.be::accueil` (L227), `::route` (L254), `RAFRAICHISSEMENT`, `finsDeCourse`, `interrupteur` ; liste `volets_pages` du cenv ; `volets.js` contient `NUIT = {base, profonde, teinte}` et `PORTAIL_DECALAGE = 5` ; `data/sd/js/volets.js` existe.
  - OK : `tca9554.dat` du grenier du RDC = `{"NAME":"TCA9554","GPIO":[224,...,230,0]}` : 230 en 7e position, conforme a L737.
  - OK : persist du grenier RDC `"decor": ["maison","finition"]` et `"camera": {"module":"autres","id":7}` ; P4 `"decor": ["chevrefeuille","porte","pergola","finition"]` et `"camera": {"module":"garage","id":4}` ; rideau `["chevrefeuille","porte","finition"]`.
  - PERIME L729 : « P4 du garage, `decor` avec `pergola` » : le P4 a aussi `chevrefeuille`, `porte`, `finition`, et a une `camera` (module `garage`, id 4) que la phrase ne mentionne pas ; le README parle de la camera uniquement pour le grenier du RDC (L736).
  - PERIME L747 : « Les fichiers de la page ne partiront que sur cet env et seront exclus des autres » (futur) : l'env portail S3 existe deja (`tasmota32s3-garage-portail-jardin-modbus`, cenv L1520), plus l'env ESP32 de remplacement `tasmota32-garage-portail-jardin-modbus` (L1584, carte Relay x4 sans PSRAM, meme identite). Le README ne connait pas le 2e env.
  - PERIME L745 : « deux Shutters en mode 3 sur le P4 » : le commentaire de l'env portail dit « Shutter mode 1 » pour l'esclave ; mode 3 (`"mode": 3` L1545) vaut pour le P4. Coherent, mais ajouter la nuance.
  - Compte de lignes : `volets.js` fait 974 lignes (CLAUDE.md : 971), `vrFonctions.be` 910 (CLAUDE.md : 906) : ecarts de documentation, pas du README.
- Doublon CLAUDE.md : TRES FORT (CLAUDE.md a un paragraphe complet « Visuel des volets » avec les memes modules, bancs, sondes).
- Pieges : refus de reglage si volet en course ou arret recent ou autre volet qui roule (le reglage reinitialise tous les volets, sauf la porte du garage) ; un appui moins de 1 s apres le precedent est ignore ; la porte du garage (mode 3) est en chronometre seul : la carte ne commande rien ; un flash serie ou un envoi du FS remet les durees du depot (recopier dans le `_persist.json`) ; `vrPages.be` et `controleRideau.be` solidifies = firmware a recompiler ; la lecture du rideau dessine « maitre muet » si le P4 ne repond pas.
- Renvois sortants : spec `2026-11-11-visuel-volets-reglage-durees-design.md`, plans `visuel-reglage-volets.md`, `facade-garage-capteurs.md`, `facade-garage-portail-commande.md`, dossier `volets_visuels/` (tous OK) ; `modele_persist.json` (non verifie) ; persist des 3 cartes (OK).
- Sensible : aucune adresse trouvee.

---

## 11. Firmware du coprocesseur Wi-Fi des P4 (ESP32-C6) (L796-842, 47 lignes)

- Nature : U 30 %, I 50 %, P 20 % (bug esp-hosted #143).
- Destination : `outils_docs/reference_berry/COPROCESSEUR_C6.md`. Carte (mais mentionne `fichiers_berry_coprocesseur.py`, L835-840 : renvoi vers `guides_outils/fichiers_berry.md`).
- Coupe : L835-840 (« Nouvelle carte P4 ») = outil PC `fichiers_berry`, a deplacer ou dupliquer en renvoi.
- Affirmations verifiees :
  - OK : constantes `DELAI_LOCAL` 20 000 ms, `DELAI_SERVEUR` 180 000 ms (3 min), `DELAI_ESSAI` 3 600 000 ms (1 h), `ESSAIS_MAX` 6, `CODE_BLOQUE = "Failed 5379"` (`controleCoprocesseur.be` L48-53).
  - OK : persist P4 `serveur.coprocesseur` = activation ON, url, mqtt ON, `bloque` = `"2.6.6"`.
  - OK : `fichiers_berry_coprocesseur.VERSION_BLOQUEE = "2.6.6"`.
  - OK : `banc_coprocesseur.py` existe.
  - A noter : « Range de 512 octets » conforme a l'en-tete du .be.
  - Interne : dans le persist, le bloc coprocesseur n'est donc ni `OFF` ni absent sur le P4 : coherent.
- Doublon CLAUDE.md : FORT (paragraphe « Firmware du coprocesseur Wi-Fi ESP32-C6 des P4 » reprend quasi mot a mot).
- Pieges (ce qui a rate) : `Failed 5379` = `ESP_ERR_OTA_VALIDATE_FAILED`, bug esp-hosted-mcu #143 (bootloader DIO + appli 2.1 a 2.8 QIO) : plus aucune mise a jour reseau ne passe, seul un flash serie du C6 en 2.9 ou plus le debloque ; la cle `bloque` doit vivre dans le `_persist.json` du DEPOT (un flash serie reecrit le FS) ; le fichier sans numero de version du serveur etait en retard (2.12.6 contre hote 2.12.13) : ne pas le suivre ; apres `HostedOta`, Wi-Fi du P4 et point d'acces des esclaves coupes 1 a 2 min.
- Renvois sortants : lien externe esp-hosted-mcu #143 ; plan `alerte-firmware-c6.md` (OK, cite ailleurs).
- Sensible : l'URL du serveur OTA (publique, ota.tasmota.com) : non sensible.

---

## 12. Voie MQTT maitre/esclaves (L846-912, 67 lignes)

- Nature : U 45 % (persist, commandes), I 40 % (garde-fous G3/G4/G5, accuses), P 10 %, H 5 % (etat au 2026-11-19).
- Destination : `outils_docs/reference_berry/VOIE_MQTT.md`. Carte (le sniffeur MQTT est une section d'outil distincte).
- Affirmations verifiees :
  - OK : toutes les cles de garde et leurs defauts (10000, 10, 60, 60000, 300000, 3000, 3, 30000, `ALERTE_MS` 120000) correspondent a `mqttLiaisonFonctions.be` (`static ... _MS`).
  - OK : `drivers.liaisonMqtt` dans le persist du P4 (activation ON, environnement `{}`, log `info`, garde sans `ageEtatMs` ni `alerteBrokerMs`, conforme a L870).
  - OK : liste blanche des commandes `POWER`, `DIMMER`, `CT` (`controleMqttLiaison.be` L19) ; commandes refusees `Restart`, `Backlog`, `Br`, `TOGGLE` (en-tete L7-8) ; `controleMqttLiaison.be::ordonne`, `::recale` existent.
  - OK : `ReglageMqttLiaison` + aide ; relais `relai24`/`25`/`26` dans le persist du P4.
  - PERIME GRAVE L850 : « Etat au 2026-11-19 ... essais sur carte ne sont pas termines. Le re-test du 2026-11-19 a laisse 26 ordres sur 200 non appliques ... correction de la garde commitee mais pas encore eprouvee sur carte ». Le plan `voie-mqtt.md` (maj 2026-11-21, 60/64 etapes, 95 %) enregistre : essais A6 (ordres), A7 (coupure du broker, mesure du 2026-11-20 05:45 et 20:02-20:07), A9 (pompe ESP8266), bouton recale, lignes « perime » faits les 2026-11-20 et 21 ; ne restent que A10 (portail, 5/9). CLAUDE.md contient deja la version a jour (« Essais sur carte (2026-11-20 et 21) »). Le README est en retard de 2 jours et contredit CLAUDE.md. Aussi L850 « Ne pas la presenter comme une voie validee » est un avertissement desormais attenue.
  - Perime (le meme paragraphe) : mention d'une « correction de `GardeMqtt` (ordres rapproches) commitee » : verifier par `git log` si on la garde.
  - Non verifie : « Au plus 5 publish par seconde » (L896).
  - A verifier : « `esclaves.<nom>.topic` unique, sans `+` ni `#` ».
- Doublon CLAUDE.md : FORT (paragraphe « Voie MQTT maitre/esclaves » de CLAUDE.md couvre `mqttLiaisonFonctions.be`, `controleMqttLiaison.be`, G3/G4/G5, `MQTT_<nom>`, `recale`, `ReglageMqttLiaison`, esclaves sans fiche ModBus).
- Pieges / echecs consignes : re-test 100 cycles : 26 ordres sur 200 non appliques en 6 s ; montee intermittente de la memoire Berry du P4 sans cause ; le LWT n'est pas delivre quand le broker lui-meme s'arrete (esclaves restent « en ligne » pendant la coupure) ; `ButtonTopic`/`SwitchTopic` mal poses font publier un `TOGGLE` sans commuter le relais local ; JAMAIS le topic du maitre en `ButtonTopic` (ordre natif hors garde-fous) ; `SetOption19` a 1 supprime les messages `Action` ; un publish lent bloque `loop()` ; ordre « identique » refuse par G3 (rien renvoye) ; un `id` de relais au-dela des autres reste commandable (`configDevices.be`).
- Renvois sortants : `ANALYSE_VOIE_MQTT_2026-11-16.md` (OK), plan `voie-mqtt.md` (OK), `PROTOCOLE_MODBUS.md` § 11 (cite dans CLAUDE.md ; a verifier), journal `/cs`.
- Sensible : aucune dans cette section (topics generiques).

---

## 13. Emulation Hue pour Alexa (L916-946, 31 lignes)

- Nature : U 50 %, I 30 %, P 20 % (limites).
- Destination : `outils_docs/reference_berry/EMULATION_HUE.md`. Carte.
- Affirmations verifiees :
  - OK : `hueFonctions.be::appareils` (L74), `::relaisVolets`, `::refus` ; `controleHue.be::regle` (L147) ; `global.hue_bridge` ; `banc_hue.py` ; liste `berry_commun.emulation_hue = data/fs/hueFonctions.be` du cenv.
  - OK : persist `serveur.emulationHue` = `{"activation": "OFF", "log": "info"}` au depot (P4), present sur 4 persist : cave, etage2 grenier, P4, rdc grenier.
  - OK : cle `alexa` posee : cave (Ventilation, LED des machines), P4 (LED de la cuve, projecteur du garage, du jardin, du barbecue) : correspond a L935 (relais 1, 5, 24, 26 du P4 ; relais 2 et 3 de la cave non reverifies).
  - OK : cible de log `emulationHue` dans `logFonctions.CIBLES`.
  - Ecart de comptage : « Les greniers n'exposent rien » : conforme (aucune cle `alexa` dans les greniers).
  - Non verifie : transport `Emulation 2` (firmware C++).
- Doublon CLAUDE.md : FORT (paragraphe « Emulation Hue pour Alexa » de CLAUDE.md, quasi identique, plus la skill `alexa-developer`).
- Pieges : chaque bascule redemarre la carte une fois (le firmware redemarre a chaque `Emulation`) ; un nouveau `CFG_HOLDER` remet `Emulation` a 0 ; l'API Hue n'a AUCUNE authentification ; fenetre de demarrage : API native sans liste blanche avant le chargement de `controleHue` ; `FriendlyName` gardent leur `$` apres retour a OFF ; un esclave derriere le NAPT d'un maitre n'est pas joignable (SSDP multicast) ; noms vocaux uniques dans toute la maison ; rien essaye sur carte.
- Renvois sortants : aucun lien fichier.
- Sensible : aucune.

---

## 14. Sniffeur I2C (page web) (L948-1033, 86 lignes)

Sous-sections : materiel et cablage, flasher le firmware, lancer la page, vitesse, ce que montre la page, envoi (lire/ecrire un registre), bancs.

- Nature : U 65 %, I 25 % (protocole, 400 kHz), P 10 %.
- Destination : `outils_docs/guides_outils/sniffeur_i2c.md` (NOM_CIBLE existant). Coupe : L948-981 (materiel, firmware) = partie carte/firmware autonome, a garder dans le meme guide ; le firmware `outils_docs/firmware_sniffeur_i2c/` n'est PAS une carte Tasmota.
- Affirmations verifiees :
  - OK : `BROCHE_SDA=4`, `BROCHE_SCL=5` dans `firmware_sniffeur_i2c/platformio.ini` (L19-20) ; `src/machine_i2c.h`, `banc/lance_banc.py` existent.
  - OK : port 7350 (`sniffeur_i2c.py` `--http` defaut 7350) ; `JOURS_JOURNAL = 30` ; tache VS Code « Outil : sniffeur I2C (http://127.0.0.1:7350) » ; cible Custom « Sniffeur I2C (HTTP 127.0.0.1) » (`NOM_CIBLE = "sniffeur_i2c"`) ; groupe « Bus et cartes » (`GROUPES[0]`).
  - OK : decodeur : ADS1115, MCP23017, TCA9554, DS3231, MPU6050, ES8311 (`decodeur_i2c_puces.py`) ; `Br (wire1.detect(...) ? wire1 : wire2).read/write` (`sniffeur_i2c_carte.py`) ; `p.vid in proto.VIDS_SNIFFEUR` (Espressif et Raspberry Pi).
  - OK : bancs `test_sniffeur_i2c.py` et `test_sniffeur_i2c_page_chrome.py`.
  - PERIME L1005 : « ES8311 (noms seuls) » : le decodeur contient bien 3 occurrences ES8311 ; reste plausible.
  - Divergence d'intitule : L985 dit « Tuile Sniffeur I2C de l'annuaire » ; le registre l'intitule « sniffeur I2C » (minuscule) cote id : cosmetique.
  - Cible a surveiller : L973 `pio run -d outils_docs/firmware_sniffeur_i2c -t upload` : le garde `garde_build` le refuse pendant un build (coherent avec CLAUDE.md).
- Doublon CLAUDE.md : FORT (bloc `sniffeur_i2c.py` de la carte des documents, 1 paragraphe).
- Pieges : bus en 3,3 V SEULEMENT (entrees S3 non 5 V) ; GND indispensable ; port « USB natif » (pas « UART ») ; 400 kHz non garanti (si transactions perdues ou tronquees, rester a 100 kHz) ; le coeur 1 coupe le chien de garde des interruptions (cf. `src/main.cpp`) ; `wire1`/`wire2` plutot que `tasmota.wire_scan` (nil pour une puce prise par un pilote C) ; le sniffeur maitre refuse si le bus a vecu dans les 2 dernieres secondes, et seulement sur un composant DEBRANCHE de sa carte ; les trames du decodeur sont « PROVISOIRES » (fiches techniques, pas de capture reelle).
- Renvois sortants : spec `2026-10-31-sniffeur-i2c-design.md` (OK), `firmware_sniffeur_i2c/platformio.ini` (OK).
- Sensible : aucune.

---

## 15. Lieu de travail : annuaire, syslog et sniffeur MQTT (L1037-1054, 18 lignes)

- Nature : U 80 %, I 20 %.
- Destination : MELANGE de trois outils, a COUPER : L1042-1044 (puces de l'annuaire) -> `guides_outils/annuaire.md` ; L1045-1047 (syslog 7200) -> `guides_outils/syslog_tasmota.md` ; L1048-1050 (sniffeur MQTT 7100) -> `guides_outils/sniffeur_mqtt.md` ; L1039-1040 (principe, `lieux.py`) + L1051-1054 (arrivee `?lieu=`) = transversal, a mettre dans un fichier commun `outils_docs/guides_outils/_LIEU_DE_TRAVAIL.md` (ou dans `annuaire.md` avec renvois). Le renvoi L1054 « Pour la page Build, voir Arrivee avec `?lieu=` plus bas » mene a la section Build (L1058+, hors de ma plage).
- Affirmations verifiees :
  - OK : `lieux.py::identites` (L46), `::pour_page_identites` (L78), `puce` (L19), `EXCEPTIONS = {}` (vide), `remplitParLieu` JS ; `annuaire_page_lieux.py` existe, memorise le lieu dans `localStorage` (`annuaire-lieu`) ; `sniffeur_mqtt_lieux.py` et `syslog_tasmota_web.py` appellent `fetch("/lieux")`.
  - PERIME L1043-1044 : liste des outils recevant `?lieu=` = « Build, Fichiers Berry, Assistant persist, Atelier des graphiques, Fabrique d'extensions, syslog, sniffeur MQTT ». Le registre (`annuaire_registre.py` L378-381) y ajoute `etiquettes_qr`, `atelier_ecrans`, `atelier_visuels`, `ftp_cartes` : 4 outils omis dans le README.
  - OK : « Le lieu choisi n'est pas memorise d'une visite a l'autre » pour syslog et sniffeur MQTT (pas de `localStorage` dans ces deux modules) ; la memorisation concerne l'annuaire seulement, et le README le dit pour l'annuaire (« retenu par le navigateur »).
  - OK : bandeau « Lieu : X (depuis l'annuaire) » dans `lieux.py` (L136).
- Doublon CLAUDE.md : FORT (paragraphe « Classement des cartes par lieu » de CLAUDE.md : `lieux.py`, `identites`, `pour_page_identites`, `remplitParLieu`, `lieuDeHote`, puces de l'annuaire, syslog, sniffeur MQTT).
- Pieges : un hote inconnu va dans « Autres » ; nouveau lieu = une ligne dans `lieux.LIEUX`, rien d'autre ; un code de lieu inconnu dans `?lieu=` est ignore ; la croix de bandeau ne change aucune liste hors syslog et sniffeur MQTT.
- Renvois sortants : aucun fichier (renvoi interne vers « Arrivee avec ?lieu= » de la section Build).
- Sensible : le texte parle d'adresses IP des cartes mais n'en cite aucune.

---

## Tableau recapitulatif : plage -> destination

| Plage | Section | Destination proposee | Remarque |
|---|---|---|---|
| 1-13 | Bandeau GitHub amont | supprimer ou README minimal | copie Tasmota |
| 14-63 | Index de la documentation | `outils_docs/INDEX.md` (a refaire, 6 sections sur ~35 citees) | 48 plans -> 65 |
| 65-152 | Logs Berry | `reference_berry/LOGS.md` | cibles incompletes ; doublon CLAUDE.md |
| 154-173 | Decouverte annonce seule | `reference_berry/DISCOVERY.md` | |
| 175-298 | Graphiques S3/P4 | `reference_berry/GRAPHIQUES.md` | IP d'exemple L235 ; `filtreHistorique` a verifier |
| 301-351 | Page Energie | `reference_berry/ENERGIE.md` | procedure de portage L338-351 |
| 353-379 | Jauges cuve | `reference_berry/CUVE_PAGE.md` | |
| 383-468 | Debits PAC | `reference_berry/DEBITS_PAC.md` | IP L396-399 |
| 472-538 | Ecran de la cave | `reference_berry/ECRAN_CAVE.md` | procedure ON/OFF perimee |
| 540-683 | MPU6050 | `reference_berry/INCLINAISON_MPU6050.md` | `USE_MPU6050` FAUX |
| 685-792 | Facade et reglage des volets | `reference_berry/VOLETS_FACADE.md` (+ `VOLETS_REGLAGE_DUREES.md` L755-770) | portail : 2e env ignore |
| 796-842 | Coprocesseur C6 | `reference_berry/COPROCESSEUR_C6.md` | L835-840 = outil fichiers_berry |
| 846-912 | Voie MQTT | `reference_berry/VOIE_MQTT.md` | etat L850 perime |
| 916-946 | Emulation Hue | `reference_berry/EMULATION_HUE.md` | |
| 948-1033 | Sniffeur I2C | `guides_outils/sniffeur_i2c.md` | |
| 1037-1054 | Lieu de travail | coupe en `annuaire.md`, `syslog_tasmota.md`, `sniffeur_mqtt.md` + fichier commun | 3 outils |

---

## Affirmations perimees ou fausses : synthese (les 5 plus graves en tete)

1. L555-556 (MPU6050) : « ne pas compiler `USE_MPU6050` » est faux : `#define USE_MPU6050` est compile dans `tasmota/user_config_override.h` (L1040, L1635).
2. L850 (voie MQTT) : « essais sur carte pas termines, re-test 26/200 non appliques » : le plan `voie-mqtt.md` est a 95 % (maj 2026-11-21), les essais A6/A7/A9 sont faits ; CLAUDE.md est deja a jour.
3. L527-529 (ecran de la cave) : « passer a `ON` `TasmotaSlaveModBus1` et `ecranCave` » : les deux sont deja `ON` dans le persist du depot.
4. L26 (index) : « 48 plans » : il y en a 65.
5. L747 et L745 (volets, portail) : le texte parle d'un env portail « a venir » ; l'env S3 existe, plus un env ESP32 de remplacement (`tasmota32-garage-portail-jardin-modbus`, meme identite) que le README ignore.
6. L90-93 (logs) : liste des cibles de `ReglageLog` incomplete (`ecranSysteme`, `liaisonMqtt`, `emulationHue` manquent).
7. L1043-1044 : liste des outils recevant `?lieu=` incomplete (`etiquettes_qr`, `atelier_ecrans`, `atelier_visuels`, `ftp_cartes` manquent).
8. L285-286 (graphiques) : « cle `grafana` non posee sur la cave et le bureau » : trois persist de cave et bureau la portent.
9. L296-297 : `controleGarage.filtreHistorique` : non retrouve dans `data/fs` ; a verifier dans le P4.
10. L729 : reglages actuels du P4 incomplets (camera du P4, `chevrefeuille`, `porte`, `finition`).
Total : 10 constats perimes ou a corriger (3 certains graves, 4 certains moyens, 3 a verifier).

## Pieges et echecs a reporter dans INDEX.md (une ligne chacun)

- Logs : un reglage `SerialLog` fait a la main est ecrase par le profil au redemarrage ; la console serie se coupe 600 s apres le demarrage (gardee par choix).
- Discovery : un ESP32 sans PSRAM redemarre en boucle si l'ecoute est active ; en esclave il doit avoir `activation` ON.
- Graphiques : `curl /histo` sans `Referer` : connexion coupee sans reponse.
- Energie : le compteur `Total` n'est pas retabli seul apres un flash (releve avant, `EnergyTotal <Wh>` apres) ; module solidifie : firmware a recompiler.
- Debits : flasher l'acquisition AVANT l'affichage ; `/json/equilibrage.json` perdu a l'envoi du FS en image.
- Ecran cave : touche 5 (redemarrer) jamais relancee ; touche = etat voulu, pas bascule.
- MPU6050 : jamais `ShutterSetPosition` pendant une course ; l'arret passe avant le recalage ; commandes Shutter en differe juste apres un arret.
- Volets : un reglage de duree reinitialise tous les volets (hors porte du garage) ; un flash serie remet les durees du depot.
- Coprocesseur C6 : `Failed 5379` = bug esp-hosted #143, seul un flash serie du C6 en 2.9 ou plus debloque ; la cle `bloque` doit etre dans le persist du depot.
- Voie MQTT : 26 ordres sur 200 perdus au re-test du 19/11 ; montee de memoire Berry du P4 sans cause ; LWT non delivre quand le broker s'arrete ; jamais le topic du maitre en `ButtonTopic`.
- Hue : API sans authentification ; chaque bascule redemarre la carte ; fenetre de demarrage sans liste blanche ; rien essaye sur carte.
- Sniffeur I2C : bus 3,3 V seulement ; 400 kHz non garanti ; trames du decodeur PROVISOIRES.
- Lieu : un code de lieu inconnu est ignore ; nouveau lieu = une ligne dans `lieux.LIEUX`.

## Doublons avec CLAUDE.md (Grep de phrases cles)

Forts (a reduire a un renvoi, un seul des deux fichiers garde le detail) : logs Berry (4 niveaux, regles), graphiques, page Energie, jauges cuve, debits PAC, coprocesseur C6, voie MQTT, emulation Hue, visuel des volets, sniffeur I2C, lieu de travail. Partiel : MPU6050. Aucun : discovery annonce seule, ecran de la cave. Recommandation : CLAUDE.md garde une ligne par sujet avec le renvoi vers `reference_berry/<NOM>.md` ; les paragraphes de CLAUDE.md etant plus a jour que le README (voie MQTT), le README doit etre aligne sur eux avant le decoupage.

## Lignes sensibles (valeurs NON recopiees)

- L235 : adresse IP locale dans l'URL Grafana d'exemple.
- L396-397 et L399 : adresses IP locales (relais d'acces `192.168...:8080` et IP de l'affichage), L400 : topic MQTT ; aussi L404 (chemin d'un dossier de brochage) non sensible.
- Aucun mot de passe ni jeton dans 1-1057.


---

# Partie 2

# Relecture README.md lignes 1058 a 1957 (partie 2)

Lecture integrale faite (chaque ligne), lecture seule. Verifications par Grep/Glob sur `outils_docs/scripts_python/outils_pc/`, `build/`, `pio-tools/`, `data/`, `.vscode/tasks.json`.
Aucune valeur sensible recopiee.

Vue d'ensemble : 3 sections `##` (Build 1058-1590 ; Fichiers Berry 1593-1756 ; Assistant persist 1757-1957), 18 `###` + 1 `####` pour Build, 8 `###` pour Fichiers Berry, 8 `###` pour Assistant persist. La ligne 1591 est un `<hr></hr>` separateur (a ne pas reprendre).

Nature globale : ~75 % mode d'emploi utilisateur, ~20 % fonctionnement interne pour Claude (noms de fonctions, garde-fous, protocoles), ~5 % historique/incidents dates ; peu de pieges, mais ils sont denses (voir fin).

---

## A. `## Build et téléversement (page web)` : lignes 1058-1590 (535 lignes)

Intro 1058-1064 : mode d'emploi (resume + liens spec et plan). Liens : `docs/superpowers/specs/2026-10-24-page-build-televersement-design.md` existe ; `tasks/plans/page-build-televersement.md` existe.

Verifications du `##` (6 affirmations) :
- `build_web.py [--http 7700] [--local] [--sans-navigateur]` : conforme (docstring ligne 4, `PORT_DEFAUT = 7700`).
- Cible Custom `NOM_CIBLE = "build_web"` (`build/cible_build_web.py:31`) : conforme.
- Onglets de la page : `build_page.py` en declare 6 (Build, Fichiers, Memoire et partitions, Env par defaut, Sauvegarde configuration, Aide). L'onglet « Aide » n'a aucune section dans le README (texte porte par `build_page_aide.py`, renvoie vers `FICHIERS_DRVSET.md`) : a documenter ou a lier.
- Routes citees ou implicites (`/lancer`, `/arreter`, `/continuer`, `/flux`, `/sortie`, `/memoire`, `/memoire/analyser`, `/partitions/diff|ecrire`, `/defaut(/diff|/ecrire)`, `/fichiers`, `/reparation(s)`, `/cache/purger`) : toutes presentes dans `build_web.py`.
- PERIME : tache VS Code. Le README cite « Outil : build et téléversement (http://127.0.0.1:7700) » avec accents ; `.vscode/tasks.json:203` porte « Outil : build et televersement (...) » sans accents (idem pour « fichiers Berry par env » et « assistant persist » : seul « televersement » differe). Mineur, mais une recherche exacte echoue.

### A1. `### Lancer la page` 1066-1080
- Nature : mode d'emploi 100 %. Destination : `guides_outils/build_web.md` (debut).
- Verifie : options CLI et cible detachee conformes (`cible_build_web.py`, console `consoles\build.log` non reverifiee). Tuile annuaire groupe « Déploiement » : conforme a CLAUDE.md.
- Doublon CLAUDE.md : oui, la carte des documents de CLAUDE.md redit presque tout (tuile, tache, cible detachee, jamais pendant un build).
- Renvoi sortant : annuaire (`guides_outils/annuaire.md`).

### A2. `### Les environnements et les actions` 1081-1111
- Nature : mode d'emploi 85 %, interne 15 % (chemin du `upload_port` herite, solidification controlee).
- Destination : `guides_outils/build_web.md`.
- Verifie : `lieux.py` (`LIEUX`, `EXCEPTIONS = {}`, `puce`) conforme ; `build_solidification.py` (modules.h, « solidification vide ») conforme ; `build_page_lieux.py` gere `?lieu=` conforme. Rien de perime.
- Passage « Classer par » / `?lieu=` (1086-1095) touche aussi `lieux.py` : renvoyer vers `guides_outils/annuaire.md` ou un futur `reference_lieux.md`.
- Doublon CLAUDE.md : partiel (classement par lieu, `lieux.py` dans la carte des documents).

### A3. `### Le port COM : lu, et réécrit dans le .ini` 1112-1125
- Nature : fonctionnement interne + avertissement (piege : reecrire le `.ini` purge `.pio/build`). Destination : `build_web.md`.
- Verifie : `build_envs.py::ecrit_port` (ligne 239) copie bien `.bak` (ligne 245) : conforme. Ecriture hors `Transaction` (contrairement aux onglets Memoire/Defaut) : coherent avec le texte.
- Doublon CLAUDE.md : oui (`Port COM lu ... et REECRIT ... .bak ; change l'empreinte`).

### A4. `### Ce qui fait recompiler (et ce qui ne le fait plus)` 1126-1146
- Nature : fonctionnement interne / explication des couts de build (70 %), historique daté (30 %). Destination : `build_web.md` ou plutot `guides_outils/build_web_compilation.md` (cache, CFG_HOLDER, purge, Defender).
- Verifie : messages « CFG_HOLDER inchangé / incrémenté » existent (`pre_utilitaires_platformio.py:824/831`) ; `purge_cache_build.py` et `exclusions_defender.ps1` existent ; bouton « Purger le cache de compilation » dans `build_page.py:238`, route `/cache/purger`. Conforme. « 17 Go le 2026-11-01 » : chiffre date, a laisser en historique.
- Doublon CLAUDE.md : FORT (section « Vigilances de build » de CLAUDE.md reprend CFG_HOLDER par carte, cache, purge, `implicit_cache`).

### A5. `### Le dossier data_dir : posé avant chaque pio run` 1147-1156
- Nature : interne + incident date (2026-10-26, P4 a recu le FS de la cuve). Destination : `build_web.md`.
- Verifie : `build_envs.py::ecrit_data_dir` (ligne 282) et banc `build/test_data_dir.py` : conformes.
- Doublon CLAUDE.md : oui (carte des documents, « data_dir ... pose sur le dossier de l'env AVANT chaque pio run »).

### A6. `### L'IP de l'OTA` 1157-1184
- Nature : mode d'emploi + interne (Range Extender, Sleep 0). Destination : `guides_outils/build_web_ota.md`.
- Verifie : `build_envs.py::adresse_par_maitre` (8080 + id - 1, id >= 1, activation ON, ipMaitre) conforme ; `build_ota_maitre.py::joint_par_maitre` et `::coupe_sleep` conformes ; `_page_safeboot` dans `build_ota_http.py` conforme ; persist du depot : cuve id 2 -> 8081, rideau id 3 -> 8082, exemples exacts.
- PERIME (leger) : « (cuve, rideau) » ignore le portail de jardin (id 4 -> port 8083), ajoute depuis (persist `data/garage/tasmota32*-portail-jardin-modbus`).
- LIGNE SENSIBLE : 1163 (IP LAN du maitre, deux fois). Ne pas recopier.
- Piege : maitre en `Sleep 50` coupe l'envoi d'un esclave (mesure 2026-10-28, coupe a 3 %), remettre `Sleep 50` a la main si la valeur n'a pas ete restauree.

### A7. `### OTA du firmware` 1185-1194
- Nature : interne (protocole `/up` puis `/u2`, `/u4` safeboot, preuve par `Status 2`). Destination : `build_web_ota.md`.
- Verifie : `build_ota_firmware.py` docstring : `POST /u2`, `GET /up` avant envoi, `0xE9`, `/u4` : conformes. 90 s non reverifie.
- Doublon CLAUDE.md : oui (« OTA du firmware envoyee par la page (/up, /u2, safeboot /u4, preuve par Status 2 »).

### A8. `### OTA du file system` 1195-1229
- Nature : interne 80 % (7 etapes avec garde-fous), incident date (2026-11-09 differentiel, 2026-10-26 P4). Destination : `build_web_ota.md`.
- Verifie : `build_ota_fs.py::verifie_identite`, `::envoie_fs_ota(... fichiers=...)`, appels `UfsFree` et `/ufsd`, `BR_RECHARGE` (`persist.load()`), dossier `%LOCALAPPDATA%\outils_tasmota\build\persist\` : conformes.
- Piege : pas de restauration automatique du persist si la relecture differe (chemin de la sauvegarde affiche).
- Doublon CLAUDE.md : fort.

### A9. `### Onglet « Fichiers » : envoyer quelques fichiers du FS` 1230-1321 (dont `####` 1291-1321 « Arrivée depuis l'atelier des graphiques » et paragraphes MQTT 1271-1290)
- Nature : mode d'emploi 60 %, interne 35 %, cas limites 5 %. Destination : `guides_outils/build_web_fichiers.md`.
- Verifie : `build_ota_fs.py::envoie_fs_ota(fichiers=)` conforme ; `build_page_atelier.py::arriveeAtelier` existe (ligne 55) ; `build_fichiers.py::liste` et `jeton` conformes ; `build_ota_mqtt.py` : `CHARGE = 1896` (~1900 o) conforme ; `data/fs/fsMqtt.be` : `TEMP = "/fsmqtt.tmp"`, controle MD5, efface = `path.format` conformes ; `banc_fsmqtt.py` et `test_build_ota_mqtt.py` existent.
- PERIME 1 : l. 1278-1281 « chargé par l'autoexec de la carte (maître P4 et cuve à ce jour) » : 12 autoexec le chargent maintenant (P4, cuve, rideau, deux portails de jardin, cave S3 et ESP32, ecran cave, deux cartes debits bureau, grenier RDC, plus l'extension `data/extensions/fsMqtt`). Le README se contredit (l. 1922 dit « P4, cuve et rideau »).
- PERIME 2 : titre `####` « Arrivée depuis l'atelier des graphiques » : `build_page_atelier.py::AT_ORIGINES` gere aussi `depuis=qrcode` et `depuis=visuel` (etiquettes QR, atelier des visuels). La section ne parle que de `depuis=atelier`. Passage qui parle d'un AUTRE outil (a deplacer en partie vers `atelier_graphiques.md`, `etiquettes_qr.md`, `atelier_visuels.md` ; garder ici le mecanisme).
- Renvoi sortant : « Atelier des graphiques » (section README ligne 2095, existe) ; `fsMqtt.tapp` (Fabrique d'extensions).
- Piege : « Effacer tout le FS avant l'envoi » (MQTT) formate le FS : si le formatage depasse les 5 s du watchdog la carte redemarre avec un FS vide, sans autoexec ni Berry : la reprendre en HTTP ou par cable. « aucun essai sur carte a ce jour » (1289, a dater).
- Piege : MQTT 14-18 Ko/s contre HTTP 74-102 Ko/s.

### A10. `### Onglet « Mémoire et partitions »` 1322-1357
- Nature : mode d'emploi 70 %, interne 30 % ; contient un avertissement non essaye (4 ou 6 partitions). Destination : `guides_outils/build_web_memoire_defaut.md`.
- Verifie : `build_partitions.py` (pas de 64 Ko `PAS = 0x10000`, `board_build.partitions`, `flash_extra_images`, doublon avec fichier existant, `Transaction`) conforme ; `build_memoire.py` (`Status 4`, `Status 5`, `UfsSize`, `UfsFree`, orange 85 %, rouge 95 %) conforme ; `post_esp32.py::patch_partitions_bin` existe (ligne 112), l'affirmation « suppose 5 partitions » non relue ligne a ligne.
- Doublon CLAUDE.md : partiel (`build_partitions.py` dans la carte des documents).
- Pieges : table a 4/6 partitions « pas encore essayee sur une carte » ; la page ne controle pas un `pio run -t upload` hors d'elle ; apres ecriture, OTA refusee jusqu'au prochain « Effacer puis televerser » (remplace aussi le persist).
- Renvois sortants : plan `tasks/plans/temps-compilation.md` et `build-fin-partitions.md` (existent), maquettes `outils_docs/partitions/` (existent).

### A11. `### Téléversement série : il emporte littlefs.bin` 1358-1373
- Nature : interne (comportement garde par choix) + piege. Destination : `build_web.md`.
- PERIME (grave) : l. 1363 « reconstruit `littlefs.bin` à chaque édition des liens (toujours, puisque `CFG_HOLDER` change à chaque `pio run`) ». Faux depuis le 2026-11-01 : `CFG_HOLDER` n'est plus incremente que si le `.h` change (`cfg_holder.py`, `pre_utilitaires_platformio.py:816-831`, et le README le dit lui-meme l. 1133-1139). La raison actuelle est `env.AlwaysBuild(firmware_bin)` (`pre_utilitaires_platformio.py:843`, confirme par CLAUDE.md « Le pre-script force aussi la refabrication de firmware.bin (AlwaysBuild) »). `post_esp32.py` ne contient pas `CFG_HOLDER`.
- Verifie : `post_esp32.py` ajoute bien `littlefs.bin` (lignes 21, 146, 226).
- Piege (incident 2026-11-01) : en `nobuild` la jointure du FS ne tourne pas, la carte recevait le firmware sans FS (corrige).

### A12. `### Calibrage d'énergie gardé autour d'un flash par câble` 1374-1383
- Nature : interne. Destination : `build_web.md` (ou `build_web_sauvegardes.md`).
- Verifie : `build_drvset.py` (`.drvset003`, `Restart 99`, docstring explique `Restart 1`/EnergySettingsSave) conforme.
- Renvois : `FICHIERS_DRVSET.md` (existe).
- Piege : `Restart 1` reecrirait le calibrage avec la RAM de la carte neuve, d'ou `Restart 99`.

### A13. `### Effacer puis téléverser (erase_upload)` 1384-1402
- Nature : mode d'emploi + avertissement (confirmation). Destination : `build_web.md`.
- Verifie : `build_serie.py` docstring `-t erase_upload` (choix 19, par cable seulement) conforme.
- Doublon CLAUDE.md : partiel (erase_upload dans la carte des documents).
- Piege : persist et reglages de la carte remplaces par ceux du depot, un reglage non reporte est perdu.

### A14. `### Refus, attente, arrêt` 1403-1431
- Nature : mode d'emploi 60 %, interne 40 %. Destination : `build_web.md`.
- Verifie : `.claude/hooks/garde_build.py` existe, `build/test_garde_build.py` existe ; pause « rebranchez la carte » : `build_serie.py` (`nobuild`, `uploadfs`) conforme. Texte « 30 premieres secondes » identique a CLAUDE.md.
- Doublon CLAUDE.md : fort (garde_build, pause « rebranchez la carte », 30 s).
- Piege : arret immediat peut laisser une carte a moitie flashee et des copies temporaires dans `data/<lieu>/<carte>` ; second Ctrl+C force.

### A15. `### Onglet « Env par défaut (Platformio override) »` 1432-1452
- Nature : mode d'emploi. Destination : `build_web_memoire_defaut.md`.
- Verifie : `build_defaut.py` (bloc `default_envs`, `Transaction`), routes `/defaut`, `/defaut/diff`, `/defaut/ecrire` conformes ; `fichiers_berry_creation.py::ajoute_default_envs` cite par CLAUDE.md, non relu ici ; dossier `outils_docs/default_envs/` existe, plan `default-envs-page.md` existe.
- Piege : liste vide refusee (un `pio run` construirait tous les envs) ; enregistrer change l'empreinte.
- Passage sur un AUTRE outil : la case « Ajouter à default_envs » vit dans Fichiers Berry par env et Assistant persist (renvoyer).

### A16. `### Onglet « Sauvegarde configuration »` 1453-1506
- Nature : mode d'emploi 70 %, interne 30 %. Destination : `guides_outils/build_web_sauvegardes.md`.
- Verifie : `build_sauvegarde.py` : `GARDE_NOMBRE, GARDE_JOURS = 5, 90`, `REGLAGES = ".../reglages.json"`, `POSEES`, `reposes()`, `purge()` conformes ; `decode_config.py` : `VERSIONS_VERIFIEES`, version 16.0.0.0, option `--verifier` conformes ; `build_sauvegarde_mqtt.py` (`FileDownload` / `FileUpload`) conforme ; `.gitignore` contient `outils_docs/sauvegardes_cartes/` (ligne 91) conforme.
- Non cite : `build_sauvegarde_esp8266.py` existe (le texte l. 1464-1466 decrit ce comportement sans nommer le module).
- LIGNE SENSIBLE : 1493 (mentionne le mot de passe MQTT, `MQTT_PASS` du `.h`, aucune valeur) ; 1458 (les `.dmp` portent des mots de passe en clair, dossier ignore par git).
- Pieges : au demarrage persist et `autoexec.bat` reposent leurs reglages et l'emportent sur une valeur restauree (marque « ↻ démarrage ») ; table `POSEES` tenue a la main (le banc exige une ligne par commande de `configGlobal.be`) ; decode-config 16.0.0.0 tronque la reserve de textes d'un ESP32 ; restauration refusee pour une autre puce.
- Essai reel : 2026-11-03, differentiel, lecture MQTT en 2 s.

### A17. `### Réparation automatique des pannes` 1507-1540
- Nature : interne 80 % (catalogue, garde-fous), limites 20 %. Destination : `guides_outils/build_web_reparations.md`.
- Verifie : `build_serie.py::Serie._execute_env` existe (ligne 532) ; `build_reparations.py::ACTIONS = attendre/libere_verrou/vide_build`, `LIGNES_FIN = 50`, `RELANCES_MAX = 2`, `CHOIX_DELAI_S = 600` ; `build_reparations_verrou.py::LISTE_BLANCHE = (cpptools-srv.exe, cpptools.exe)` ; `build_reparations_ia.py::diagnostique` et exclusion de `ANTHROPIC_API_KEY`/`ANTHROPIC_AUTH_TOKEN` ; `outils_docs/schemas/reparations_build.json` existe : tous conformes.
- Nuance : README dit « 2 relances au plus par étape et par env » ; le code dit « par etape (env, action, cible) et par serie » : equivalent, formulation a harmoniser.
- Doublon CLAUDE.md : fort (carte des documents « Reparation automatique des pannes de la page Build »).
- Pieges : non essaye sur une vraie serie de production ; les echecs d'envoi OTA/MQTT/serie (port COM tenu) ne sont pas couverts ; pas de reparation pour `upload` ou `erase_upload`.

### A18. `### Journaux, mémoire de la page, fichiers réécrits` 1541-1590
- Nature : mode d'emploi 55 %, interne 45 % (fichiers d'etat). Destination : `build_web.md` (fin).
- Verifie : `derniers.json` (`build_web.py:106-118`), `references.json` (docstring `build_serie.py:60`), `PLATFORMIO_FORCE_ANSI="true"` (`build_serie.py:665`), `build_page_couleurs.py` : conformes ; purge des journaux a 30 jours non relue.
- PERIME (grave) : l. 1583-1585 « Chaque pio run réécrit `platformio_override.ini` et `tasmota/user_config_override.h` (`CFG_HOLDER`) : fichiers à commiter après un lancement ». Le `.h` n'est reecrit que si son contenu (hors ligne `CFG_HOLDER`) a change depuis le dernier increment (`cfg_holder.py`, CLAUDE.md « Vigilances de build »). Contradit les l. 1133-1139 du meme README.
- Renvois : `test_build_*.py`, `build/test_garde_build.py` existent.

---

## B. `## Fichiers Berry par env (page web)` : lignes 1593-1756 (164 lignes)

Nature : mode d'emploi 65 %, interne 30 %, historique 5 %. Destination : `guides_outils/fichiers_berry.md` (taille OK, un seul fichier).
Verifications du `##` (6) : `fichiers_berry_web.py` options `--http 7800`, `PORT_DEFAUT = 7800` ; `cible_fichiers_berry.py` `NOM_CIBLE = "fichiers_berry"` ; tache VS Code `.vscode/tasks.json:214` ; liens spec `2026-10-25-page-fichiers-berry-design.md` et plans `fichiers-berry-env.md`, `fichiers-berry-suppression.md` existent ; les 8 bancs `test_fichiers_berry_{ini,etat,ecriture,creation,suppression,renommage,sauvegarde,web}.py` et la sonde `test_fichiers_berry_page_chrome.py` existent, `build/test_cible_fichiers_berry.py` existe.
- PERIME (mineur, dans le code, pas le README) : `fichiers_berry_web.py:59` et `:64` portent encore un message provisoire « Page en cours d'écriture (action A6) » (repli si `fichiers_berry_page` manque) : commentaire historique.
- Intro 1593-1604 : liste par lieu (`lieux.py`), `?lieu=`. A rapprocher de A2.

### B1. `### Lancer la page` 1605-1619 : mode d'emploi. Verifie : options CLI, cible. Lien « fichiers » depuis la page build (renvoi a `build_web.md`). Doublon CLAUDE.md : fort.
### B2. `### Les trois états` 1620-1647 : mode d'emploi + interne. Verifie : `fichiers_berry_etat.py` (`FIGES = ("autoexec.be",)`, `EXCLUDE_SOLIDIFIES = "custom_files_exclude_solidified"`) conforme ; `fichiers_berry_ini.py` cite `walk_options` (platformio/project/config.py) conforme. Piege : sans `custom_files_exclude_solidified = ON` un fichier solidifie reste AUSSI sur le FS ; « Solidifié » ne verifie rien (lancer `berry/solidifie_et_compile_berry.py`, existe). Renvoi `SOLIDIFICATION_BERRY.md` (existe).
### B3. `### Disposition et enregistrement` 1648-1667 : mode d'emploi. Piege (encadre WARNING) : reecrire le `.ini` change l'empreinte, le build suivant repart de zero. Doublon README A3.
### B4. `### Créer un env à partir d'une carte modèle` 1668-1692 : mode d'emploi + interne. Verifie : `fichiers_berry_creation.py::CHAMPS_IDENTITE` = les 8 champs cites (CODE_IMAGE_STR, PROJECT, WIFI_IP_ADDRESS, WIFI_RGX_SSID, MQTT_CLIENT_ID, MQTT_TOPIC, MQTT_GRPTOPIC, FRIENDLY_NAME) ; define `FIRMWARE_ESP<puce>_<LIEU>_<NOM>` (ligne 65) conforme. Pieges : identite deja portee par une autre carte = avertissement seulement ; `;` dans un champ refuse (commande de plus dans `USER_BACKLOG`) ; mots de passe masques. Touche aussi `fichiers_berry_coprocesseur.py` (non cite ici).
### B5. `### Renommer un env` 1693-1711 : mode d'emploi. Verifie : `fichiers_berry_renommage.py` (`extends`, copie de section). Piege : refus si un autre env reference celui-ci. Doublon CLAUDE.md : partiel.
### B6. `### Supprimer un env` 1712-1733 : mode d'emploi. Verifie : `fichiers_berry_suppression.py::bloc_default_envs`, `dossier_libre(... "-sauvegarde")` conformes. Piege : le dossier est renomme `-sauvegarde`, jamais efface ; une base heritee ne se supprime pas.
### B7. `### Sauvegardes` 1734-1747 : interne + piege. Verifie : `fichiers_berry_sauvegarde.py::Transaction`, `JOURS = 30`, `MARQUE = "en_cours.json"` conformes. Note : « Plus de .bak commun avec la page build » vrai pour cette page, mais `build_envs.py::ecrit_port` ecrit encore un `.bak`. Piege : marque `en_cours.json` restee = bandeau rouge « Opération interrompue ». Doublon CLAUDE.md : fort.
### B8. `### Bancs` 1748-1756 : liste de bancs, tous existants. A mettre en bas du guide ou dans le tableau des bancs de `INDEX.md`.

---

## C. `## Assistant persist (page web)` : lignes 1757-1957 (201 lignes)

Nature : mode d'emploi 55 %, interne 40 %, historique 5 %. Destination : `guides_outils/assistant_persist.md` ; option : couper le `###` « Onglet autoexec.bat » (1861-1937, 77 lignes, grosse table d'avertissements) en `guides_outils/assistant_persist_autoexec.md`.
Verifications du `##` (6) : `assistant_persist_web.py` `PORT_DEFAUT = 7900`, options CLI ; `cible_assistant_persist.py` `NOM_CIBLE = "assistant_persist"` ; routes `/prepare`, `/creation`, `/modification/prepare`, `/modification`, `/suppression/prepare`, `/suppression`, `/parc`, `/env` toutes presentes ; spec `2026-10-27-assistant-persist-design.md` et plan `assistant-persist.md` existent ; `outils_docs/schemas/modele_persist.json` existe ; tache `.vscode/tasks.json:224`.

### C1. `### Lancer la page` 1770-1783 : mode d'emploi. Doublon CLAUDE.md fort. Mentionne `acces_web.py` (renvoi vers le socle commun a decrire une seule fois dans INDEX).
### C2. `### Les étapes de la page` 1784-1803 : mode d'emploi + interne. Verifie : `assistant_persist_elements.py` gere `pinsTechniques`, `debitmetres`, cles `analogique5`, `rxBL0942` conformes ; `configGlobal.be` existe. Piege : un element OFF n'occupe pas sa broche ; refus de doublon de broche, broche prise par ModBus/I2C/LEDs. Renvoi : page Build 7700 et Fichiers Berry 7800.
### C3. `### Les mots de passe` 1804-1811 : interne + securite. Verifie : `assistant_persist_parc.py` (mot de passe tire du reseau par nom de reseau), `assistant_persist_modele.py` (`@secret:wifi1|wifi2|mqtt|ap|ftp`) conformes. LIGNE SENSIBLE (mention de secrets, aucune valeur) : 1806-1810. Piege : deux persists donnent deux mots de passe pour le meme reseau, ou reseau inconnu : creation refusee.
### C4. `### Le modèle modele_persist.json` 1812-1823 : mode d'emploi. Verifie : `a_completer` (`assistant_persist_modele.py`) et bouton « Relue » (`assistant_persist_relue.py`) conformes. Piege : modele casse a la main (JSON invalide) : ni fusion ni creation ; ecriture refusee (409) si l'empreinte du diff a change.
### C5. `### Modifier ou supprimer un env existant` 1824-1860 : interne 70 % (algorithme d'ecart A -> B). Verifie : modules `assistant_persist_texte.py`, `_delta.py`, `_modification.py`, `_page_js_env.py` existent ; routes conformes. Plan `assistant-persist-modification.md` existe. Pieges : ligne retouchee a la main introuvable = TOUTE la modification refusee (409) ; un bloc objet entier retire puis re-ajoute perd sa mise en forme d'origine ; metiers 2 a N non editables ; bloc `rangeExtender` non relu (voulu). Doublon CLAUDE.md : partiel.
### C6. `### Onglet « autoexec.bat »` 1861-1937 : mode d'emploi 55 % (table d'avertissements), interne 45 %. Verifie : `autoexec_analyse.py` `LIMITE = 510` conforme ; `autoexec_gardes.py` (preprocesseur, cache) ; `autoexec_berry.py` (`tasmota.add_cmd`, `demarrage.leds()`, `demarrage.historique()`) conforme ; `autoexec_commandes.py --generer/--verifier` conforme ; `autoexec_envoi.py` (`/ufsu`, `autoexec_cartes/<env>/`, `Sleep 0` du maitre, voie MQTT) conforme ; 6 bancs `test_autoexec_*.py`, `test_assistant_persist_autoexec.py` et la sonde chrome existent ; `banque_autoexec.json` et `commandes_tasmota.json` existent ; spec `2026-11-03-onglet-autoexec-bat-design.md` et plans `autoexec-bat.md`, `autoexec-mqtt-tapp.md` existent.
 - PERIME : l. 1922 « c'est le cas du P4, de la cuve et du rideau (ligne `demarrage.charge(["fsMqtt"])` ... ; le rideau ne l'a qu'après l'envoi de son nouveau FS) » : 12 autoexec chargent `fsMqtt` aujourd'hui (voir A9) ; l'incise du rideau est probablement caduque (son autoexec le charge). L. 1918 « (cuve, rideau) » oublie le portail de jardin.
 - Passages sur un AUTRE outil : « Fabrique d'extensions » (`fsMqtt.tapp`) et la page Build (envoi serie, `Status 5`) : garder le renvoi, deplacer le detail.
 - Pieges : avertissements rouges (redemarrage a repetition `Hostname`, secret en clair meme en commentaire) exigent une case a cocher ; ligne de plus de 510 octets tronquee par le firmware ; « Commande absente » ne sort que si c'est certain (BLE et MI32 jamais signales) ; `SO146` = `SetOption146` mais pas d'autres alias ; carte en refus « répond X à Status 5, pas Y » = persist du depot pas encore envoye ; si l'`autoexec.bat` ne peut pas etre relu en MQTT, rien n'est envoye.
### C7. `### Limites connues` 1939-1949 : interne + pieges. Verifie : `ANALYSE_CLES_MAC_TELEPERIOD_2026-10-27.md` existe. Pieges : edite seulement activation, nom, broche, type ; SD/I2S/Ethernet/LoRa non controles ; plusieurs cartes anciennes du parc refusent la modification (a reprendre a la main) ; cles `adressMAC` retirees et `adresseMAC` ecrite au boot (decision 2026-10-28).
### C8. `### Bancs` 1950-1957 : liste existante (`test_assistant_persist_{modele,parc,elements,generation,creation,fidelite,texte,delta,modification,web}.py` tous presents). `_modification` lent (plusieurs minutes). A integrer au tableau des bancs de INDEX.md.

---

## D. Tableau recapitulatif plage -> destination

| Plage | Titre | Destination proposee |
|---|---|---|
| 1058-1065 | Build, intro | `guides_outils/build_web.md` |
| 1066-1080 | Lancer la page | `guides_outils/build_web.md` |
| 1081-1111 | Environnements et actions | `guides_outils/build_web.md` |
| 1112-1125 | Port COM reecrit | `guides_outils/build_web.md` |
| 1126-1146 | Ce qui fait recompiler | `guides_outils/build_web_compilation.md` (cache, CFG_HOLDER, purge, Defender) |
| 1147-1156 | data_dir | `guides_outils/build_web_compilation.md` |
| 1157-1184 | IP de l'OTA | `guides_outils/build_web_ota.md` |
| 1185-1194 | OTA du firmware | `guides_outils/build_web_ota.md` |
| 1195-1229 | OTA du file system | `guides_outils/build_web_ota.md` |
| 1230-1321 | Onglet Fichiers (+ MQTT, + arrivee atelier) | `guides_outils/build_web_fichiers.md` |
| 1322-1357 | Onglet Memoire et partitions | `guides_outils/build_web_memoire_defaut.md` |
| 1358-1373 | Televersement serie, littlefs.bin | `guides_outils/build_web.md` (a corriger) |
| 1374-1383 | Calibrage d'energie (.drvset003) | `guides_outils/build_web.md` |
| 1384-1402 | Effacer puis televerser | `guides_outils/build_web.md` |
| 1403-1431 | Refus, attente, arret | `guides_outils/build_web.md` |
| 1432-1452 | Onglet Env par defaut | `guides_outils/build_web_memoire_defaut.md` |
| 1453-1506 | Onglet Sauvegarde configuration | `guides_outils/build_web_sauvegardes.md` |
| 1507-1540 | Reparation automatique des pannes | `guides_outils/build_web_reparations.md` |
| 1541-1590 | Journaux, memoire de la page, fichiers reecrits | `guides_outils/build_web.md` (fin) |
| 1591 | `<hr></hr>` | supprimer |
| 1593-1604 | Fichiers Berry, intro | `guides_outils/fichiers_berry.md` |
| 1605-1756 | Lancer, trois etats, disposition, creer, renommer, supprimer, sauvegardes, bancs | `guides_outils/fichiers_berry.md` |
| 1757-1860 | Assistant persist, intro a Modifier/supprimer | `guides_outils/assistant_persist.md` |
| 1861-1937 | Onglet autoexec.bat | `guides_outils/assistant_persist_autoexec.md` (ou meme fichier) |
| 1939-1957 | Limites connues, bancs | `guides_outils/assistant_persist.md` |

Tailles approximatives des fichiers Build issus du decoupage : `build_web.md` ~230 lignes, `build_web_compilation.md` ~30, `build_web_ota.md` ~75, `build_web_fichiers.md` ~92, `build_web_memoire_defaut.md` ~58, `build_web_sauvegardes.md` ~54, `build_web_reparations.md` ~34. Le total (535) depasse la regle des 500 lignes si on ne coupe pas.

## E. Affirmations perimees ou fausses (synthese)

1. l. 1363 : « CFG_HOLDER change a chaque pio run » (faux depuis 2026-11-01 ; cause actuelle `AlwaysBuild(firmware_bin)`, `pre_utilitaires_platformio.py:843`).
2. l. 1583-1585 : « Chaque pio run reecrit user_config_override.h (CFG_HOLDER) » (reecrit seulement si le `.h` a change).
3. l. 1278-1281 : `fsMqtt` charge par « maitre P4 et cuve a ce jour » ; 12 autoexec le chargent (et l. 1922 dit « P4, cuve et rideau » : incoherence interne).
4. l. 1291-1297 : arrivee depuis « l'atelier des graphiques » seulement ; le code gere aussi `qrcode` et `visuel`.
5. l. 1162-1164 et 1918 : « esclaves (cuve, rideau) » ; le portail de jardin (id 4, port 8083) est aussi un esclave.
6. Mineurs : noms de taches VS Code sans accents dans `tasks.json` ; `fichiers_berry_web.py:59` message provisoire A6 ; formulation « par env » des relances.

## F. Pieges et echecs a reporter dans INDEX.md (une ligne chacun)

- Reecrire un `.ini` (port COM, Fichiers Berry, partitions, default_envs) change l'empreinte : le build suivant vide tout `.pio/build` (retour depuis le cache `.cache`).
- Une cible PlatformIO ou un outil `pio run` pendant un build purge `.pio/build` : lancer hors PlatformIO (`python outils_pc/<outil>.py`).
- Esclave derriere le Range Extender en `Sleep 50` du maitre : envoi OTA coupe (3 %) ; la page met `Sleep 0` et le remet (a verifier si l'etape echoue).
- OTA FS : `littlefs_data` n'est pas la source (restes d'anciens builds), utiliser `littlefs.bin` ; contrôle d'identite hostname/topic evite d'envoyer le FS d'une autre carte (incidents 2026-10-26, P4 avec FS de la cuve).
- Fichier plus gros que la place libre : l'ancien est supprime juste avant l'envoi (jamais le persist) ; incident 2026-11-09 differentiel.
- Persist : envoyer le persist puis `persist.load()` AVANT tout redemarrage, sinon la RAM reecrit l'ancien.
- « Effacer tout le FS » par MQTT : formatage > 5 s = watchdog, carte redemarree avec FS vide sans Berry : reprendre en HTTP ou par cable.
- Upload serie du firmware flashe aussi le FS (persist compris) ; `nobuild` ne joint pas le FS (corrige 2026-11-01).
- Calibrage energie : `Restart 99` et non `Restart 1` apres retablissement de `/.drvset003`.
- Solidification vide : `module("X")` sans `#@ solidify:X` = echec d'edition des liens une heure plus tard ; la page arrete pio tout de suite.
- Table de 4 ou 6 partitions : jamais essayee sur carte, upload serie refuse (seul erase_upload), OTA refusee jusqu'au prochain effacement.
- Sauvegardes `.dmp` : mots de passe en clair, dossier ignore par git, depot public ; au demarrage persist/autoexec.bat l'emportent sur une valeur restauree.
- decode-config 16.0.0.0 tronque la reserve de textes d'un ESP32.
- Fichiers Berry : un fichier solidifie reste aussi sur le FS sans `custom_files_exclude_solidified = ON` ; passer a « Solidifie » ne verifie rien.
- Assistant persist : ligne retouchee a la main = modification refusee en bloc ; persists anciens non modifiables ; mots de passe jamais envoyes a la page.
- Autoexec.bat : `Hostname` ou secret en clair (meme en commentaire) = rouge ; ligne > 510 octets tronquee ; « Commande absente » jamais pour BLE/MI32.
- Reparation automatique : non essayee en production, ne couvre ni OTA ni port COM tenu.

## G. Lignes sensibles (numeros de ligne du README, valeurs non recopiees)

- 1163 : adresse IP LAN du maitre (deux occurrences).
- 1458, 1494 : mots de passe Wi-Fi/MQTT dans les `.dmp` ; `MQTT_PASS` du `.h` (nom seulement).
- 1536, 1073, 1612, 1782 : jeton d'acces distant des outils (mention, pas de valeur).
- 1806-1810 : mots de passe Wi-Fi/mqtt/AP/FTP des persists (mention, pas de valeur).
- 1671, 1687-1689 : champs d'identite (IP, topic, client MQTT) cites sans valeur.
Aucune valeur secrete en clair trouvee dans la plage.


---

# Partie 3

# Relecture README.md, lignes 1958 a 3063 (fin) : rapport

Lecture integrale par tranches de 250 lignes, en lecture seule. Verifications par Glob/Grep/Bash contre `outils_docs/scripts_python/`, `data/`, `.vscode/tasks.json`, `.github/workflows/`, `tasks/plans/`, `docs/superpowers/specs/`.

Convention : "perime" = affirmation fausse ou depassee constatee dans le code. "OK" = verifie conforme.

---

## 1. Navigateur FTP des cartes (l. 1958-2053, 96 lignes)

- Nature : mode d'emploi utilisateur 35 %, fonctionnement interne / garde-fous pour Claude 45 %, pieges et limites 20 %.
- Destination : `outils_docs/guides_outils/ftp_cartes.md`.
- Sous-titres : Lancer la page (1965), Ce que montre la page (1976), FTP allume le temps du besoin (2006), Limites connues (2025), bancs (2041), paragraphe sur `sonde_hermetique` (2050-2053, hors sujet FTP : a deplacer vers un guide commun "sondes Chrome" ou vers `reference`/INDEX).
- Verifications :
  - OK `ftp_cartes_liste.py::liste` (l.277), `GENERIQUES` (l.29), `ftp_cartes_chemins.py::cle_fat` (l.32) et `::protege` (l.49), `ftp_cartes_session.py::Session.tic` (l.247), `ESSAIS_EXTINCTION = 5`, `DELAI_ALLUMAGE`, `annuaire_registre.py` `dans_job=False, route_occupe="/execution"`, `annuaire_lanceur.py::_tue_arbre` (l.219), `custom_ftp_cartes_http` dans `build/cible_ftp_cartes.py`, port 7450, `data/fs/globalFonctions.be::regleFTP` (envoie `UFSFTP 0`), 7 bancs `test_ftp_cartes_*` presents plus `faux_ftp_carte.py` (a confirmer : le fichier faux_ftp_carte.py n'est PAS dans le Glob des outils_pc, voir plus bas).
  - PERIME ou a verifier : "les 15 persist du depot qui portent le bloc" : 16 `_persist.json` (hors `*sauvegarde*`) portent `serveurFTP` aujourd'hui (portail S3 ajoute ?). Chiffre a recompter.
  - A VERIFIER : `faux_ftp_carte.py` cite comme faux serveur ; il n'apparait pas dans le listing `ls outils_pc | grep ftp_cartes` (le filtre ne le couvrait pas : nom `faux_ftp_carte`, a controler par Glob avant decoupage).
  - OK tuile groupe "Configuration des cartes" (registre : GROUPES[3]) et tache VS Code "Outil : navigateur FTP des cartes (http://127.0.0.1:7450)" (tasks.json l.334).
- Doublons avec CLAUDE.md : tres forts (CLAUDE.md redit : arret refuse en session, `dans_job=False`, fichiers proteges, `/etat?onglet=`, `sendBeacon`, 90 s, 15 min, `serveur.serveurFTP.activation` OFF). CLAUDE.md garde une copie quasi integrale : a reduire a 3 lignes + renvoi vers le guide.
- Pieges / echecs consignes (pour INDEX.md) :
  1. Arret brutal (gestionnaire de taches, arret de tache VS Code) : `atexit` ne passe pas, le FTP reste allume sur la carte ; remede : rouvrir la carte puis "Deconnecter", ou `UfsFTP 0`.
  2. Un seul client FTP a la fois sur la carte : FileZilla en parallele bloque l'outil.
  3. P4 : `MLSD` ignore le chemin passe (constate sur P4, banc `test_ftp_cartes_session_p4.py`).
  4. `UfsFTP 0` non confirme : plus aucun geste, annuaire refuse d'arreter l'outil, 5 essais puis "Deconnecter" seul.
  5. Noms FAT : casse, points et espaces finaux ; noms 8.3 (`AUTOEX~1.BE`) NON reconnus comme proteges.
  6. Rien essaye sur carte reelle (plan A7) : banc sur faux serveur seulement.
- Renvois sortants : spec `2026-11-20-navigateur-ftp-cartes-design.md` OK, plan `navigateur-ftp-cartes.md` OK (un `navigateur-ftp-cartes-a5-reprise.md` existe aussi, non cite), `outils_docs/navigateur_ftp/maquettes_interfaces.html` existe (non cite).
- Donnees sensibles : l.1973-1974 (jeton, sans valeur), l.2003-2004 (identifiants FTP lus dans `user_config_override.h`, aucune valeur). Aucune valeur recopiee dans le texte.
- A completer dans le guide : rien de manquant, au contraire trop long (le bloc l.1973-2023 est du fonctionnement interne a deplacer en "Pour Claude" en bas du guide).

---

## 2. Fabrique d'extensions (l. 2055-2093, 39 lignes)

- Nature : mode d'emploi 70 %, pieges 25 %, historique 5 %.
- Destination : `outils_docs/guides_outils/fabrique_tapp.md` (NOM_CIBLE `fabrique_tapp`). Fonctionnement des `.tapp` : reste dans `outils_docs/EXTENSIONS_TAPP.md` (a lier dans INDEX.md).
- Titre dit "Quatre etapes" mais la liste en compte CINQ (l.2064 vs 5 items numerotes) : incoherence de redaction.
- Verifications :
  - OK `RE_NOM` 31 caracteres (`tapp_sources.py` l.28-29, justification : chemin Tasmota 49 caracteres), routes `/extensions/extensions.jsonl` et `/extensions/tapp/<nom>.tapp` (`tapp_web.py` l.22-23, 134-136), `data/extensions/fsMqtt` + `fsMqtt.tapp` presents, `berry/gen_tapp.py`, `test_gen_tapp.py`, `banc_tapp_fsmqtt.{py,be}` OK, `NOM_CIBLE = "fabrique_tapp"`, port 7980, tache VS Code OK.
  - PERIME : "Essais ... boutique locale et envoi HTTP ne l'ont pas encore ete" : a revalider (rien trouve de contraire, mais le plan `autoexec-mqtt-tapp.md` est le seul juge).
  - A VERIFIER : `OtaUrl http://<IP locale>:7980/` : IP du PC, voir donnees sensibles.
- Doublons CLAUDE.md : forts (CLAUDE.md redit le piege `LOG_LEVEL_*` avant autoexec dans `gen_tapp.py`, port 7980, boutique `/ext`).
- Pieges :
  1. `LOG_LEVEL_*` nu dans une extension : elle est compilee avant `/autoexec.be`, elle ne se lance pas ; ecrire `global.LOG_LEVEL_INFO` et `import logFonctions` dans la fonction.
  2. `OtaUrl` pointe sur ce PC : casse `Upgrade` par URL pour cette carte (plus de firmware officiel) ; poser carte par carte a la main.
  3. Un `.tapp` n'est pas dans l'image du FS : formatage ou flash serie l'efface.
  4. En MQTT, "Lire la carte" ouvre un echange `fsMqtt` qui annule un transfert en cours.
  5. Pare-feu Windows : autoriser Python en reseau prive, pas `--local`.
- Renvois : `EXTENSIONS_TAPP.md` OK (section 9 citee : a verifier), `tasks/plans/autoexec-mqtt-tapp.md` OK.
- Donnees sensibles : l.2084 (IP du PC dans un exemple `OtaUrl`).

---

## 3. Atelier des graphiques (l. 2095-2284, 190 lignes)

- Nature : mode d'emploi 55 %, fonctionnement interne 20 %, historique de paliers (palier 1, destinations, Energie) 15 %, pieges 10 %.
- Destination : `outils_docs/guides_outils/atelier_graphiques.md`. Cote carte (l.2149-2156 "Cote carte", moteur `pagesGraphiques.be`) : `outils_docs/reference_berry/pagesGraphiques.md`. La sous-section "Destination Energie" (l.2228-2260) : doublon de la section `## La page Energie` (l.301) de la partie 2 du README : a fusionner dans `reference_berry/energie.md` (cote carte) et ne garder dans le guide de l'atelier que le geste "choisir la page Energie". `ReglageCuve simulation` (l.2267-2273) : `outils_docs/reference_berry/cuve.md`. "Premiere page : la cuve" (l.2262-2265) : exemple, a garder dans le guide.
- `###` notables : Lancer (2110), Utilisation (2123), Ce qui est ecrit (2137), Cote carte (2149), Menu Page (2158), Composition carte/depot (2183), Bouton Televerser (2208), Destination Energie (2228), Premiere page cuve (2262), simulation (2267), Bancs (2275).
- Verifications :
  - OK `atelier_graphiques_description.py::valide` (l.274), `atelier_graphiques_graphiques.py::etat_carte` (l.95), `atelier_graphiques_televerse.py::plan` (l.94, signature `plan(racine, env, destination, ecrits, avant, *, get)` conforme), `atelier_graphiques_ecriture.py --exclusions [--ecrit]`, port 7950, tache VS Code (tasks.json l.234), `data/fs/pagesGraphiques.be` et `pagesGraphiquesValidation.be`, `graphiquesFonctions.FICHIERS` (data/fs/graphiquesFonctions.be l.56), `atelier_energie_description.py::valide`, `cas_energie.json`, bancs `test_atelier_graphiques_*`, `test_pages_graphiques.mjs`, `test_pages_graphiques_chrome.py`, `test_atelier_energie_page_chrome.py`.
  - PERIME : `cuveFonctions.be::reglageCuve` et `::releveSimule` cites comme si dans `data/fs` ; ils sont dans `data/garage/tasmota32s3-capteurs-cuve-modbus/cuveFonctions.be` (l.260 et l.69), pas dans `data/fs/`. Le chemin est a preciser.
  - PERIME ou doublon de nom : les bancs `_graphiques.py`, `_televerse.py`, `_web.py` existent ; `_series.py`, `_conseil.py`, `_ecriture.py`, `_description.py` existent aussi ; OK. Mais la liste "mutants `absent`, `archive`, `mobile`, `vol`" n'a pas ete confirmee (non verifie).
  - A noter : `atelier_graphiques_page_compo.py` et `atelier_graphiques_energie.py` existent dans `outils_pc` mais la liste de modules de CLAUDE.md n'en cite qu'une partie : incoherence CLAUDE.md, pas README.
- Doublons CLAUDE.md : moyens (CLAUDE.md redit : port 7950, `pages_graphiques.json`, les deux listes `[berry_commun]`, `ReglageCuve simulation`, destination Graphiques et bouton Televerser). A reduire dans CLAUDE.md.
- Pieges / echecs :
  1. Une tuile de l'atelier ne retire pas sa serie de "Mesures" ; retirer tous les graphiques auto exige d'en garder un non-atelier.
  2. Composition de la carte modifiee sur la carte : choix obligatoire "partir de la carte" (perd les graphiques ecrits non televerses) ou "garder le depot" (ecrase les changements faits sur la carte).
  3. Style `liquide` refuse si `echarts-liquidfill.min.js.gz` est exclu du FS de l'env.
  4. `largeur: demi` sans effet sous `/graphiques`.
  5. Firmware recompile une fois (energieFonctions solidifie) ; carte a l'ancien firmware : `f=description` rend la page HTML en 200, "Televerser" bloque.
  6. JAMAIS d'upload serie du firmware du differentiel : `custom_files_upload` reecrit tout le FS et perd `/energie/` (etat, mois-*.json, courbe.bin, 24 mois d'archives) ; OTA firmware puis fichiers.
  7. Apres ecriture, lancer `berry/banc_demarrage.py` (jamais `--enregistre`).
  8. Un `.json` de la racine de l'image est pose dans `json/` a l'envoi partiel (comme `gestionFileFolder.be` au demarrage).
- Renvois sortants : specs `2026-11-03-atelier-graphiques-design.md`, `2026-11-04-atelier-destinations-televersement-design.md`, `2026-11-08-atelier-energie-differentiel-design.md` OK ; plans `atelier-graphiques.md`, `atelier-destinations.md`, `energie-atelier.md` OK ; `outils_docs/atelier_graphiques/README.md` existe ; renvoi interne "Arrivee depuis l'atelier des graphiques dans la page Build" (l.2225-2226) : section de la partie 1/2, a reporter en lien vers `guides_outils/build_web.md`.
- Donnees sensibles : aucune.

---

## 4. Atelier des ecrans (l. 2286-2500, 215 lignes)

- Nature : mode d'emploi 50 %, fonctionnement interne 30 %, historique 10 %, pieges 10 %.
- Destination : `outils_docs/guides_outils/atelier_ecrans.md`. Candidats a scinder : `### Catalogue d'icones (page web)` (l.2428-2442) est un OUTIL distinct (port 7930, cible `icones_catalogue`) : `outils_docs/guides_outils/icones_catalogue.md`. `### Page "Systeme" construite` et `### Page "QR code" d'une carte a ecran` (l.2388-2410) : cote carte, a mettre dans `outils_docs/reference_berry/ecranSysteme.md` et `ecranDebits.md` (la partie "debits" `## Les debits ...` l.383 est deja une section de la partie 2). `### Images` (2361-2367) : `reference_berry/gestionFileFolder.md`.
- Verifications :
  - OK `atelier_ecrans_catalogue.py --generer` (l.306), `genere_icones_firmware.py [--verifier]`, `build/interface_ecran.py::applique` (l.50), `data/fs/ecranSysteme.be` avec table `ecranSysteme.CHAMPS` (l.17), `controleEcranSysteme.be`, `ecranFonctions.rangePolices` (data/fs/ecranFonctions.be), `gestionFileFolder.be::listeEtRepartitLesFichiers` (l.54), ids 201 a 254 (`atelier_ecrans_navigation.py` : `ID_MAX = 254`), `outils_docs/schemas/{catalogue_ecran,display_ini_parametres,icones_firmware}.json` presents, `icones_firmware.json` compte bien 120 icones, `atelier_ecrans_systeme.py`, `_display.py`, `_import.py`, `_images.py`, `_polices.py`, `_icones.py` presents, port 7960, `ecranDebitsFonctions.qr` (data/bureau/tasmota32s3-ecran-debits-pac/ecranDebitsFonctions.be l.290) OK.
  - PERIME : "Premier palier : sept objets ... label, btn, bar, obj, chart, arc, slider" ; la page decrit ensuite un palier 2 (img, dropdown, roller, switch, qrcode) et la page Systeme : la phrase d'ouverture ne dit pas que le catalogue actuel a 12 objets. Introduction a mettre a jour.
  - PERIME : l.2397 "Pas d'icones pour l'instant (A15 et A18 du plan)" alors que le panneau "Icones" (A15) et le "Catalogue d'icones" (A18) sont decrits plus bas (l.2412-2442) comme faits : contradiction interne.
  - PERIME : l.2409 "La cave n'a pas encore sa page (...son ecran appartient a une autre session)" : formulation datee ; a revalider.
  - A VERIFIER : "120 glyphes Material Design embarques" OK, "Capture `lv.screenshot()` pas encore essayee sur carte" (non verifiable par code).
  - Chemin imprecis : `ecranDebitsFonctions.qr` est dans le dossier de la carte, pas `data/fs`.
- Doublons CLAUDE.md : tres forts (CLAUDE.md redit : port 7960, deux interfaces generees, `custom_interface_ecran`, `build/interface_ecran.py::applique`, A12 a A19, panneau Icones, import PNG, page Systeme). Reduire.
- Pieges / echecs :
  1. Les fichiers de l'interface non choisie sont exclus du FS par `interface_ecran.py::applique` ; changement d'ecran = firmware a recompiler par la page Build.
  2. Dossiers `atelier_ecrans/display/`, `polices/`, `images/<env>/` crees a l'usage : absents d'un depot neuf, normal.
  3. Lignes `brut` d'un `pages.jsonl` importe : reecrites a l'identique, absentes de `ecranLvgl.be`, ni editables ni liees.
  4. Un fichier `.jpg` ou `.bmp` est range mais non affichable (LodePNG seulement PNG).
  5. Module `gestionFileFolder` solidifie : la regle de rangement n'agit qu'apres recompilation.
  6. Une roue (roller) ne prend pas de texte ; une action de liste/roue/interrupteur vaut pour LVGL pur seulement, pas pour `pages.jsonl`.
  7. Polices `.bin` LVGL non importables.
  8. Claude lance par "Traiter les remarques" : lecture seule, hooks coupes, jamais `bypassPermissions`, 10 min au plus, un traitement a la fois.
  9. Le banc de concordance `test_atelier_ecrans_display.py` devient rouge apres une synchro du fork qui ajoute un parametre `display.ini` (piege utile, a mettre dans INDEX).
  10. Une barre de navigation plus large/haute que l'ecran est refusee ; ids 201 a 254 reserves.
- Renvois sortants : spec `2026-11-11-atelier-ecrans-design.md` OK ; plan `atelier-ecrans.md` OK ; `outils_docs/atelier_ecrans/` (README.md, cartes/, maquettes) OK ; skill `lvgl-haspmota` OK ; `ICONES_IMAGES_SOURCES.md` OK.
- Donnees sensibles : aucune.

---

## 5. Etiquettes QR code (l. 2502-2607, 106 lignes)

- Nature : mode d'emploi 65 %, fonctionnement interne 20 %, pieges 15 %.
- Destination : `outils_docs/guides_outils/etiquettes_qr.md`. La partie "Page `/qrcode` de la carte" (l.2544-2550) : `outils_docs/reference_berry/qrcodePage.md`. Partie "Fiche en ligne (mode lien)" (2566-2599) : garder dans le guide, avec renvoi vers `guides_outils/build_web.md` pour la case "Publier les fiches QR a la fin".
- Verifications :
  - OK `etiquettes_qr_modele.CHAMPS` = ("hostname","ip","topic","env","puce","lieu","range_extender") conforme a la liste du texte ; `IMAGE_MAX = 8192` ; 20 lignes max ; texte libre 120 caracteres ; texte avant/apres 20 caracteres ; `etiquettes_qr_filtre_public.py::controle_public` (l.98) ; `build/qrcode_build.py::regenere` (l.17) et `::fiche` (l.54) ; `DELAI_RESEAU = 120` dans `etiquettes_qr_publication.py` ; `data/fs/qrcodePage.be` ; `data/sd/js/qrcode.js` et `qrcode_options.js` presents ; tache VS Code "Outil : etiquettes QR code (http://127.0.0.1:7970)" (tasks.json l.244) ; port 7970.
  - PERIME : le menu "Outils" de la carte, "bouton QR code dans le menu Outils" : non verifiable ici (code C++ / Berry de bouton).
  - A VERIFIER : "Seuils cales le 2026-11-12 : carre de 0,45 mm / 0,40-0,45 mm" (constantes de `etiquettes_qr_verdict.py`, non relues).
- Doublons CLAUDE.md : forts (CLAUDE.md redit : port 7970, publication par branche orpheline `etiquettes`, filtre secrets, badges, `qrcodePage.be`, `qrcode_build.py`, `build_serie.py` +20 lignes).
- Pieges / echecs :
  1. Une seule ligne refusee par le filtre public bloque toute la publication ; faux positifs connus : numero de version a quatre nombres (15.1.0.1), nom de fichier (`autoexec.be`).
  2. Jusqu'a la 1re publication, le QR d'une carte en mode lien mene a une page introuvable (GitHub Pages a activer une fois).
  3. Lien `.local` : ne marche qu'avec `USE_DISCOVERY` + `WEBSERVER_ADVERTISE`, `SetOption55 1` (persist `"mDNS": "ON"`), meme reseau ; un esclave derriere le NAPT n'est pas joignable ainsi.
  4. Imprimer a 100 %, verifier la regle de 50 mm sur le papier.
  5. Une image au centre impose la correction H (code plus gros).
  6. `qrcode.json` n'est range dans `/json/` qu'au demarrage : redemarrage demande apres televersement.
  7. Page publique (depot public) : IPv4 publiques, domaines, jetons, mots de passe filtres ; fiche = donnees publiques.
- Renvois : spec `2026-11-12-etiquettes-qrcode-design.md` OK ; plan `etiquettes-qrcode.md` OK ; `outils_docs/etiquettes_qr/` (README, gabarit.json, impressions.json, cartes/) OK.
- Donnees sensibles : aucune valeur (le texte decrit des filtres).

---

## 6. Atelier des visuels d'accueil (l. 2609-2702, 94 lignes)

- Nature : mode d'emploi 55 %, fonctionnement interne 25 %, pieges/limites 15 %, etude 5 %.
- Destination : `outils_docs/guides_outils/atelier_visuels.md`. "Cote carte" (2677-2686) : `outils_docs/reference_berry/visuelFonctions.md`. "Icone a la place d'un bouton de relais (etude)" (2698-2702) : simple renvoi vers `ICONES_BOUTONS_RELAIS.md` (existe), a garder en une ligne.
- Verifications :
  - OK port 7985 (`PORT_DEFAUT = 7985`), routes `/sources`, `/etat`, `/valide`, `/consignes`, `/consignes/regles`, `/ecriture/prevoit|ecrit|prevoit_retire|retire` (docstring de `atelier_visuels_web_routes.py`), `atelier_visuels_consignes.py::PAR_TYPE` (l.16), seuils poids 40 Ko / 60 Ko esp32 / 200 Ko autres (`atelier_visuels_description.py` l.13-14), `REFRAICHISSEMENT_MIN = 1000`, defaut 2345 ms (`data/sd/js/visuel.js` l.143), `data/fs/visuelFonctions.be`, `controleVisuel.be`, `data/sd/js/visuel.js`, `test_atelier_visuels_formes.mjs`, `berry/banc_visuel.py` (a confirmer : non liste ci-dessus, sa presence n'a pas ete controlee), tuile dans le registre (GROUPES[4] Ateliers), tache VS Code "Outil : atelier des visuels (http://127.0.0.1:7985)" (tasks.json l.264), `build/cible_atelier_visuels.py` et `test_cible_atelier_visuels.py` presents.
  - PERIME (GRAVE) : l.2693 "Pas de tuile d'annuaire, de tache VS Code ni de cible PlatformIO pour l'instant" : FAUX, les trois existent (registre `annuaire_registre.py` l.335, `.vscode/tasks.json` l.264, `build/cible_atelier_visuels.py`) ; et la section l.2619 le dit elle-meme. Contradiction interne du meme chapitre.
  - PERIME : l.2690 "Pas encore essaye sur une carte reelle" : a revalider (CLAUDE.md parle de facade volets sur P4 reels pour la partie volets, pas pour `visuel.json`).
  - A VERIFIER : `modbus_esclave` muet pour la voie serie (limite connue, non verifiable par grep simple).
- Doublons CLAUDE.md : forts (CLAUDE.md redit : port 7985, 7990 pris par l'organigramme, fichiers du moteur, tuile et tache, `CONSIGNES_VISUELS.md`).
- Pieges / echecs :
  1. La description n'est relue qu'au redemarrage de la carte (d'ou `redemarrer=1`).
  2. Fond : avertissement a 40 Ko, refus au-dessus de 60 Ko (ESP32 classique) ou 200 Ko (S3/P4).
  3. Fournisseur IA externe : la photo part chez un tiers, meme via l'abonnement Claude ; avertissement confirme ; cles dans `%APPDATA%\atelier_visuels\config.json` hors depot ; "trop de requetes" met le quota au rouge, jamais retente.
  4. Port 7990 est a l'organigramme : l'atelier a pris 7985.
  5. Un nouvel organe n'est rappele dans le panneau Consignes que s'il est ajoute a `PAR_TYPE`.
  6. `modbus_esclave` (voie serie) reste muet : pas d'horodatage propre cote maitre.
- Renvois : spec `2026-11-13-atelier-visuels-accueil-design.md` OK ; plan `atelier-visuels.md` OK ; `outils_docs/visuels_accueil/` (CONSIGNES_VISUELS.md, FOURNISSEURS_IA.md, README.md) OK ; `ICONES_BOUTONS_RELAIS.md` OK.
- Donnees sensibles : l.2674 chemin de config de cles API (aucune valeur).

---

## 7. Synchro du fork (l. 2704-2765, 62 lignes)

- Nature : mode d'emploi 65 %, fonctionnement interne (ce qu'il ne fait jamais) 30 %, bancs 5 %.
- Destination : `outils_docs/guides_outils/synchro_fork.md` (NOM_CIBLE `synchro_fork`). Doublon massif avec CLAUDE.md section "Synchro du fork" (script, hook, page web, assistant pas a pas) : le guide sera la source, CLAUDE.md garde les regles ("ne jamais merger l'amont dans une branche de chantier", hook qui detecte seulement).
- Verifications :
  - OK `synchro_fork_assistant.py` (git merge-tree --write-tree), `synchro_fork_fusion.py` (`MARQUE = "synchro-fork-assistant"`, `DELAI_PUSH = 120`), `faux_depot_synchro.py`, `liste_blanche_git_synchro.py`, bancs `test_synchro_fork_{assistant,fusion,fusion_suite,web,page_chrome}.py` presents, port 7500 (`PORT_DEFAUT`), tache VS Code "Outil : synchro du fork (http://127.0.0.1:7500)" (tasks.json l.178), `build/cible_synchro_fork.py`.
  - PERIME : l.2713 "Tuile de l'annuaire, groupe Ateliers" : le registre place la tuile dans le groupe "Deploiement" (`GROUPES[2]`, `annuaire_registre.py` l.146).
  - PERIME ou ambigu : `HISTORIQUE_SYNCHRO_FORK.md` cite comme le journal commite : existe dans outils_docs, OK.
  - A VERIFIER : "Pas de `--force`, stash, reset, rebase" : coherent avec `liste_blanche_git_synchro.py` (non relue en detail).
  - Le paragraphe l.2757 ("aucune autre session ne doit commiter ni abandonner le merge") : avertissement valide, absent de CLAUDE.md : a promouvoir dans INDEX.md.
- Pieges / echecs :
  1. Pendant un merge de l'assistant, aucune autre session (Claude ou terminal) ne doit commiter ou abandonner : un commit emporterait le merge a moitie resolu.
  2. Refus pendant un build (et refus aussi si la detection est impossible).
  3. Conflit de suppression : "Garder le fichier" / "Le supprimer" ; "Marquer resolu" refuse s'il reste des marqueurs.
  4. Message de commit sans accents (regle du depot).
  5. Un merge qui n'est pas le sien (pas de marque `.git/synchro-fork-assistant`) : l'assistant n'agit pas.
- Renvois : spec `2026-10-27-assistant-synchro-fork-design.md` OK ; plan `assistant-synchro-fork.md` OK.
- Donnees sensibles : aucune.

---

## 8. Organigramme des plans (l. 2767-2816, 50 lignes)

- Nature : mode d'emploi 80 %, historique 0 %, pieges 20 %.
- Destination : `outils_docs/guides_outils/organigramme_plans.md` (NOM_CIBLE : AUCUNE cible dans `build/` ; proposition de nom `organigramme_plans`, qui est l'identifiant du registre de l'annuaire, port 7990).
- Verifications :
  - OK `maintenance/organigramme_plans.py` options `--verifier`, `--publier` (l.10-13), `organigramme_pptx.mjs`, `outils_pc/organigramme_plans_web.py` (`PORT_DEFAUT = 7990`), `test_organigramme_plans_web.py`, URL publique `https://fdaubercy.github.io/Tasmota/organigramme.html` identique dans le code, branche `etiquettes`.
  - PERIME : la liste des familles ("`build`, `methode`, `modbus-reseau`, `cave`, `debits-energie` ou `graphiques-ecrans`", l.2795) : un plan utilise deja `famille: voie-mqtt` (constate dans `tasks/plans/*.md`) ; repartition actuelle : build 20 (+1 en commentaire), cave 5, debits-energie 7, graphiques-ecrans 10, methode 9, modbus-reseau 13, voie-mqtt 1.
  - OK hook `index_plans_edition.sh` cite (non reverifie ici, vit dans `.claude/hooks/`).
- Doublons CLAUDE.md : forts (CLAUDE.md redit : hook, `famille:`, `parent:`, `liens:`, `spec:`, `--publier`, IPv4 masquees).
- Pieges :
  1. La version en ligne est MANUELLE (elle ne change que si on publie) ; la page peut mettre une minute a refleter.
  2. Le PowerPoint demande Node et `pptxgenjs@3.12.0` hors depot ; son rendu n'a jamais ete verifie visuellement (pas de LibreOffice).
  3. Un plan sans `famille:` n'est pas range dans l'arbre.
  4. Les fiches QR partagent la branche `etiquettes` et gardent `organigramme.html`.
- Renvois : `tasks/plans/_FORMAT.md` OK.
- Donnees sensibles : aucune.

---

## 9. Menage du depot (l. 2818-2832, 15 lignes, tres denses)

- Nature : mode d'emploi 50 %, fonctionnement interne 40 %, pieges 10 %. Les paragraphes l.2824-2832 font 1 a 3 kilo-caracteres chacun : lisibilite tres faible, a decouper en `###`.
- Destination : `outils_docs/guides_outils/menage.md` (NOM_CIBLE `menage`).
- Verifications :
  - OK `menage_web.py` (`PORT_DEFAUT = 7995`, routes `/appliquer/apercu`, `/appliquer`, `/appliquer/annuler`, `/appliquer/derniere`, `/rapports`, `/rapports/ouvrir`), `menage_memoire.py` (`garde.json`), `menage_lancement.py` (`MODELES = ("sonnet","opus","haiku")`, `EFFORTS = ("low","medium","high","max")`, defaut sonnet/max, `CLES_API` retirees, `--output-format stream-json`), `menage_application.py::annule` (l.280), `menage_verification.py`, `menage_page_rapports.py`, `menage_rapport.py`, bancs `test_menage_*.py`, `outils_docs/schemas/menage_rapport.schema.json`, tache VS Code (tasks.json l.284), `build/cible_menage.py`.
  - A VERIFIER : "Compter une dizaine de secondes de plus (jusqu'a une minute)" : non mesurable ici.
- Doublons CLAUDE.md : forts (CLAUDE.md redit l'essentiel : 7995, agent `auditeur-menage`, `menage_application.py`, `menage_page_rapports.py`, `garde.json`).
- Pieges / echecs :
  1. Le lot "Appliquer" ne commite jamais ; `git rm` / `git mv` un fichier a la fois, jamais `-f` ni `-r`.
  2. Annuler refuse apres un commit (utiliser `git revert`), pendant un build, ou si le fichier a ete retouche.
  3. La pile des applications est en memoire : apres redemarrage de l'outil le bouton "Annuler" disparait (`applications.jsonl` garde la trace, `git restore` a la main reste possible).
  4. L'aperçu est refuse pendant une application (git prend le verrou d'index meme avec `-n`).
  5. La verification ne voit pas un renvoi construit dynamiquement (listes `custom_files_*` de l'ini, motifs generiques).
  6. `ANTHROPIC_API_KEY` / `ANTHROPIC_AUTH_TOKEN` retirees de l'environnement de `claude` : l'audit passe par l'abonnement, jamais par une cle API heritee.
  7. Refus : build en cours, dossier entier, `.git*`, `.claude`, `.vscode` et leurs noms courts Windows.
- Renvois : plans `menage-page.md` et `menage-appliquer.md` (existent ; non cites dans cette section, cites dans CLAUDE.md).
- Donnees sensibles : aucune.

---

## 10. Cartes simulees (l. 2834-2840, 7 lignes)

- Nature : mode d'emploi 60 %, limites 40 %.
- Destination : `outils_docs/guides_outils/cartes_simulees.md` (NOM_CIBLE `cartes_simulees`).
- Verifications :
  - OK port 7940 (`PORT_DEFAUT`), refus 409 documente (`cartes_simulees_web.py` l.16 : "409 (deja lancee, carte en ligne, port occupe)"), `berry/simule_carte_rideau.be`, `bouchons_berry/rideau`, port 8082 du rideau (id 3 dans son persist : 8080 + 3 - 1 = 8082 OK), `cartes_simulees_reseau.py` formule `8080 + id - 1`, tache VS Code (tasks.json l.314), `build/cible_cartes_simulees.py`, `test_cible_cartes_simulees.py`.
  - A VERIFIER : "Les 12 autres cartes n'ont que leur identite reseau et un accueil generique" ; "le P4 en <IP locale>" ; le P4 est bien en <IP locale> dans son persist (verifie par Grep de l'IP) mais le texte porte une IP : voir donnees sensibles.
- Trop maigre par rapport a CLAUDE.md : CLAUDE.md ajoute (plan `tasks/plans/cartes-simulees.md`, `cartes_simulees.py`, `cartes_simulees_reseau.py`, `cartes_simulees_page.py`, panneau de scenario `/__sim` de `simule_carte_rideau.be` avec "position du P4, fins de course", scenarios nommes dont "incoherent", `URL_MAITRE` de test, serveur local `127.0.0.1` seulement, "Rien n'est ecrit dans le depot", "pas d'alias d'IP"). A completer dans le guide : comment lancer sans l'annuaire, le panneau `/__sim` et ses scenarios (code : `simule_carte_rideau.be` l.37-42), l'option `--port`, ce qui est rejoue (`controleRideau.be`), comment ajouter une carte simulee (a ecrire).
- Pieges :
  1. Une carte qui repond sur le reseau n'est jamais simulee (409) ; le P4 en fait partie.
  2. MQTT jamais connecte : un second client du meme nom ferait tomber la vraie carte.
  3. Pas d'alias d'IP ; pages natives C++ (Configuration, Console) en 404.
  4. "Arreter" n'apparait dans l'annuaire que si l'outil est lance par sa tuile ou la cible Custom.
- Renvois : aucun explicite ; plan `tasks/plans/cartes-simulees.md` existe (non cite ici).
- Donnees sensibles : l.2840 (IP du P4).

---

## 11. Compilations de nuit et taches planifiees (l. 2842-2853, 12 lignes denses)

- Nature : mode d'emploi 55 %, fonctionnement interne 30 %, pieges 15 %.
- Destination : `outils_docs/guides_outils/taches_planifiees.md` (NOM_CIBLE `taches_planifiees`) ; le script `compilation_nuit.py` s'y decrit aussi.
- Verifications :
  - OK `maintenance/compilation_nuit.py`, `compilation_nuit_tache.py` (sous-commandes `etat|creer [HH:MM]|active|desactive|supprime`, tache `Tasmota-CompilationNuit`, creee desactivee), `matrice_github.py`, `outils_docs/compilations_nuit/envs_github.json` (cle `exclus`), `.github/workflows/build_custom.yml` (`name: Build_custom`, cron `0 2 * * *` en UTC, job `choix` qui lance `matrice_github.py`), code de sortie 3 "desactive" present (`return 3, {**resultat, "refus": "desactive"}`), bancs `test_compilation_nuit*.py`, `test_matrice_github.py`, tache VS Code (tasks.json l.294), port 7920 (`PORT_DEFAUT`), `build/cible_taches_planifiees.py`.
  - PERIME : "la serie complete (25 envs)" : `platformio_tasmota_cenv.ini` compte aujourd'hui 27 sections `[env:`. Chiffre a recompter (et il peut inclure des bases non compilees).
  - A VERIFIER : "Les safeboot ne sont plus compiles (echec amont `be_constobj.h`)".
- Doublons CLAUDE.md : moyens (une ligne pour `compilation_nuit.py`, une pour `taches_planifiees_web.py` avec les memes gestes et les memes bancs).
- Pieges / echecs :
  1. GitHub desactive les workflows d'un fork apres une synchro de l'amont ET `actions/permissions` repond quand meme `enabled: true` : seul l'age du dernier run planifie (rouge au-dela de 36 h) le revele ; remede : bouton "I understand my workflows, go ahead and re-enable them" sur la page Actions du fork.
  2. "Arreter la voie PC" arrete la serie en cours de la page Build meme lancee a la main.
  3. Le bouton "Ecrire, commiter et pousser" refuse si la branche n'est pas `development`, si des commits sont non pousses ou en retard, ou si le fichier est deja modifie ; si le push echoue, le commit reste local.
  4. GitHub prouve que le code compile avec `platformio_override_sample.ini`, pas que le FS ni le cache sont ceux du PC.
  5. Les gestes n'ont ete essayes qu'avec de faux `gh` et `schtasks`.
  6. Pas de synchro nocturne du fork (decision du 2026-11-15).
  7. La serie complete depasse une nuit ; la page refuse (409) la tache suivante tant qu'elle tourne.
- Renvois : plan `compilations-nuit.md` OK.
- Donnees sensibles : aucune.

---

## 12. Sondes en cours (l. 2855-2861, 7 lignes)

- Nature : mode d'emploi 50 %, fonctionnement interne 40 %, pieges 10 %.
- Destination : `outils_docs/guides_outils/sondes.md` (NOM_CIBLE `sondes`).
- Verifications :
  - OK port 7910 (`PORT_DEFAUT`), route `GET /detail?pid=N` (`sondes_web.py` l.11 et l.117), en-tete `X-Sondes: 1` (`sondes_page.py`), `suivi_sondes.suit_si_script_test` (l.252), variable `SUIVI_SONDES=0` (l.234), `sondes_historique.json` (l.50), `build/cible_sondes.py`, `test_cible_sondes.py`, tache VS Code (tasks.json l.304).
  - PERIME (GRAVE) : l.2857 "Les bancs `test_*.py` et `banc_*.py` de `scripts_python` appellent tous `suit_si_script_test()`" : mesure faite : 199 fichiers sur 247 (`test_*.py` et `banc_*.py` hors dossier racine) l'appellent, soit environ 80 %, pas "tous". Ecart de 48 bancs a lister.
  - A VERIFIER : "les 33 sondes Chrome qui importent `test_build_page_chrome.py`" : 39 fichiers `test_*chrome*.py` contiennent la chaine `test_build_page_chrome` (dont le module lui-meme et ses variantes) ; le chiffre exact est a recompter.
  - A VERIFIER : "un releve PowerShell prend 11 a 24 s sous charge" (mesure non reproductible ici).
- Trop maigre par rapport a CLAUDE.md : CLAUDE.md ajoute `sondes_scan.py`, `sondes_actions.py`, `sondes_page.py`, "orphelins signales", bancs `test_suivi_sondes.py`, `test_sondes_scan.py`, `test_sondes_web.py`, sonde `test_sondes_page_chrome.py`. A completer : usage de `suivi_sondes.suit(total=)`, comment lancer l'outil sans l'annuaire, formes du fichier `<pid>.json`, regle "arret = pid du dernier releve seulement".
- Pieges :
  1. Un banc sans total prend celui de la derniere execution sans echec ("12 / ~46").
  2. Un Chrome de sonde dont le banc parent a disparu est "orphelin" (bouton "Arreter les orphelines") ; le memo utilisateur impose de verifier et arreter les Chrome headless `sonde_*` apres usage.
  3. Arret : deux clics, uniquement pour un numero present dans le dernier releve.
  4. Limite : le releve PowerShell peut etre retarde sous charge.
- Renvois : plan `sondes-en-cours.md` OK.
- Donnees sensibles : aucune.

---

## 13. Plan de la maison (l. 2865-2879, 15 lignes)

- Nature : mode d'emploi 55 %, fonctionnement interne (derivation des liens) 40 %, pieges 5 %.
- Destination : `outils_docs/guides_outils/plan_maison.md` (NOM_CIBLE : AUCUNE cible dans `build/` ; proposition `plan_maison`, identifiant du registre, port 7915).
- Verifications :
  - OK `outils_docs/plan_maison/genere_plan_maison.py`, `placement.json` avec cles `niveaux, cartes, ip_cartes, etiquettes, liens_manuels, broker, wifi, chauffage` (+ `wifi.appareils, defaut_ssid, wifi_manuel, re_hotes`), `outils_pc/plan_maison_web.py` (`PORT_DEFAUT = 7915`, route `GET /debits`, `Status 10`), `test_plan_maison_web.py`, `test_plan_maison_page_chrome.py`, `outils_docs/plan_maison/test_plan_maison.py`, `propositions_faisceau.html`, rattachement Wi-Fi `reseau1`/`reseau2` et SSID `-GATEWAY` dans `genere_plan_maison.py`.
  - PERIME : l.2878 "Banc : `python outils_docs/plan_maison/test_plan_maison.py`" OK existe ; mais l.2873 cite `python outils_docs/scripts_python/outils_pc/test_plan_maison_page_chrome.py` OK existe. Pas d'ecart. En revanche le texte ne parle ni de `mesures_a_saisir.md` (present dans le dossier) ni du plan `plan-maison-echelle.md` (plan actif a 3 %, "plan a l'echelle, etage par etage, avec editeur web") : a ajouter en lien.
  - Marque "📶 RE ×N" : emoji dans le texte (l.2873), a garder tel quel (c'est un libelle de l'outil).
- Doublons CLAUDE.md : moyens (une entree a la fin de la carte des documents).
- Pieges :
  1. Une carte de `data/` sans placement, un lien orphelin, une piece qui deborde ou une IP ambigue : signales sur stderr a la generation.
  2. MAISON est diffusee par plusieurs points d'acces : le persist ne dit pas lequel ; la Freebox Server est le defaut, `wifi.wifi_manuel` corrige.
  3. L'affectation des debits 1 a 6 aux pieces est encore inconnue (traits pointilles).
  4. Aucun appel reseau a la generation ; le bouton "Tester les cartes" interroge au clic seulement ; jamais pendant un build.
  5. Pour que le test fonctionne, la page doit etre ouverte par l'annuaire (route `/debits`).
- Renvois : plan `plan-maison.md` OK.
- Donnees sensibles : aucune valeur (les IP vivent dans `placement.json`, pas dans le texte).

---

## 14. Liens web (l. 2881-2891, 11 lignes)

- Nature : mode d'emploi 70 %, fonctionnement interne 30 %.
- Destination : `outils_docs/guides_outils/liens_web.md` (NOM_CIBLE : AUCUNE ; proposition `liens_web`, port 7905). Ce `##` n'a AUCUNE entree dans CLAUDE.md (carte des documents) : a ajouter.
- Verifications :
  - OK `genere_liens_web.py` avec `--verifier`, `liens_web.py`, `liens_web_web.py` (`PORT_DEFAUT = 7905`, en-tete `X-Liens`, routes `/ajouter`, `/retirer`, `/archiver`, `/regenere`), `liens_web_page.py`, `test_liens_web.py`, `outils_docs/liens_web/liens_ajoutes.json` et `archives/`, `.gitignore` contient `outils_docs/liens_web/archives/`, `outils_docs/LIENS_WEB.md` existe.
  - OK "Pas encore de cible PlatformIO ni de tache VS Code" : vrai (aucune `cible_liens_web.py` dans `build/`, aucune tache `liens` dans `tasks.json`).
  - A VERIFIER : "ports 7000 a 7995" : les ports reels vont de 7000 a 7995 (+ 7450 du FTP), coherent.
- Pieges :
  1. Archive PDF : Chrome de `Program Files` requis ; 40 Mo, 90 s, hotes publics seulement (hote local, prive ou a identifiant refuse, redirections comprises, anti-SSRF) ; archives IGNOREES par git (depot public : droits d'auteur et poids).
  2. Seul un lien ajoute se retire depuis la page ; un lien cite dans un fichier se corrige dans ce fichier.
  3. Le fichier `LIENS_WEB.md` est GENERE : ne pas l'editer a la main.
- Renvois : `LIENS_WEB.md` OK.
- Donnees sensibles : aucune.

---

## 15. Reliquat herite de l'amont : "Les devices Tasmota developpees" jusqu'a la fin (l. 2893-3063, 171 lignes)

Decision deja prise : A SUPPRIMER. Lecture complete faite. Contenu et verdict par bloc :

| Lignes | Contenu | Utile a sauver ? |
|---|---|---|
| 2893-2906 | Liste de 6 "devices" (serveur garage, trappe, cave, SONOFF porte, TV, VR) | NON. Perimee : le parc reel est dans `data/` et `outils_docs/plan_maison/`. Aucun `_persist.json` avec "sonoff". |
| 2908-2911 | `[!WARNING]` generique "Urgent info" (texte-modele GitHub, vide) | NON, a supprimer. |
| 2913-2950 | `[!CAUTION]` Freebox : table IP + redirections de ports TCP externes par module | OUI (info reseau, pas dans le code) mais SENSIBLE et en partie FAUSSE : 11 entrees. Voir ci-dessous. |
| 2954-2967 | `[!IMPORTANT]` TODO : Bluetooth/MI32, TasmotaClient dans `udpFonctions`, TasmoView | TODO anciens : a verifier avec l'utilisateur ; Bluetooth/MI32 et TasmotaClient ne figurent dans aucun plan actif (grep `.superpowers`, `tasks/plans/autoexec-mqtt-tapp.md` seulement pour MI32). `tools/fw_TasmotaClient_arduino` : aucun dossier du meme nom ne repond a `ls` (n'est pas dans le depot : lien mort). |
| 2969-3037 | `[!TIP]` Liste des commandes Tasmota personnalisees (`ReglageGlobal`, `ReglageLog`, `ReglageLeds`, `RubanEsclave1`, `ReglageUDP`, `RoutageRangeExtender1`, `ReglageCuve`, `ReglageAna`, `ReglageModbus`, `ReglageSlaveModBus1`, `HSBCOLOR/DIMMER`, `SCHEME`, `EtatPompe`, `AcquittePompe`, `ReglageVolets`, et commandes sans sous-commande) | OUI, c'est la seule liste de commandes du depot qui parle francais : A SAUVER vers `outils_docs/reference_berry/commandes.md` apres controle (voir ci-dessous). |
| 3041-3053 | Modifications C++ en dur de `xdrv_01_9_webserver.ino` (pied de page "Au Bonheur des Asturies") | OUI, A SAUVER : modification du firmware qui entrera en conflit a chaque synchro de l'amont (a lier dans la partie "pieges de synchro" / `HISTORIQUE_SYNCHRO_FORK.md`). |
| 3055-3063 | Memo emoji (lien ikatyang, lignes d'emojis) et formule LaTeX de couleur | NON. |

Verifications des affirmations sauvables :
- Commandes : toutes les 20 commandes de premier niveau citees (`ReglageGlobal`, `ReglageLog`, `ReglageLeds`, `RubanEsclave1`, `ReglageUDP`, `RoutageRangeExtender`, `ReglageCuve`, `ReglageAna`, `ReglageModbus`, `ReglageSlaveModBus`, `EtatPompe`, `AcquittePompe`, `ReglageVolets`, `ReglageGarage`, `ReglageDiscovery`, `ReglageRangeExtender`, `ReglageConn16Channel`, `ReglageTCP`, `ReglageLoRaWan`, `SCHEME`) apparaissent dans au moins un `.be` de `data/` hors sauvegarde. Sous-commandes confirmees par Grep (comptes de fichiers > 0) : `afficheMemoire`, `nbLogsFiles`, `heureReboot`, `VoieReseau`, `timerRebootSansWifi`, `rubanAuto`, `rubanDuree`, `rubanAppuiLong`, `rubanBouton`, `envoiUniCast`, `envoiMultiCast`, `forceEnvoiParams`, `etalonnageCapteur`, `hauteurCuve`, `voltageMax`, `seuilMin`, `cablage`, `BaudrateModbus`, `RecupereBaudrateConn16channels`, `TesteDebitConn16channels`, `VerifieConn16channels`, `ActivationReponseCMD`, `RelaisPushMQTT`, `Apprentissage`, `Inclinaison`, `envoiMessageUDP`, `envoiMessagTCP`.
- PERIME : `ReglageUDP telePeriodClients 300` : le texte `telePeriodClients` n'apparait dans AUCUN `.be` de `data/` hors sauvegarde (compte 0), alors que `telePeriod` apparait ailleurs dans `udpFonctions.be` ; la sous-commande a ete renommee ou supprimee. A corriger ou retirer.
- PERIME : les deux lignes `ReglageGlobal ...` et `RubanEsclave1` sont repetees (`RubanEsclave1` apparait deux fois, l.2994 et l.3030).
- PERIME : `RoutageRangeExtender1 : ... => RgxPort tcp, 8080, 10.99.0.2, 80` : la commande enregistree est `RoutageRangeExtender` (sans suffixe, `controleRangeExtender.be` l.109) ; le "1" est un index d'esclave a verifier.
- Redirections de ports (l.2913-2950), verifications faites par Grep des IP dans les `_persist.json` (hors sauvegarde) :
  - <IP locale>, .42, .44, .45 : AUCUN persist ne porte cette IP (cartes retirees ou renommees, dossiers `data/base/tasmota-tv-salon` etc. sans IP en dur).
  - <IP locale> : portee par SIX persist du garage (P4, S3 serveur, cuve, rideau, deux portails) : "Serveur de Garage", "Capteurs de cuve d'eau" et "Rideau de Garage" repetent la meme IP avec des redirections vers `:8080` et `:8081`. Le texte (rideau en :8081) contredit le code : le rideau a l'id 3, donc le port NAPT est 8082 (8080 + 3 - 1), ce que dit la section Cartes simulees du meme README. Donc la table est PERIMEE et en contradiction avec la section "Cartes simulees".
  - Capteurs de cuve d'eau "IP: <IP locale>" : adresse AP du Range Extender de l'esclave, le diagnostic UDP du 2026-10-17 a justement conclu que ce plan d'adressage etait le defaut ; a confirmer avec l'utilisateur.
  - <IP locale> (projecteur-led), .46 (rdc grenier), .47 (etage2 grenier), .48 (cave), .49 (differentiel) : IP effectivement portees par les persist correspondants. Le mapping nom -> IP est donc partiellement vrai ; mais "Prise de piscine .41" et "Volet roulant d'entree .46" ne correspondent plus aux dossiers (.41 = projecteur-led, .46 = grenier RDC).
  - Verdict : table de redirections a archiver dans `outils_docs/historique/` avec la mention "etat 2026 de la Freebox, non verifie"; ne pas la laisser dans un document public.
- Pied de page C++ : OK partiellement : `xdrv_01_9_webserver.ino` l.429 contient bien "Au Bonheur des Asturies" et l.1244 `WSContentSend_P(HTTP_END, TasmotaGlobal.version)`. Le texte dit "deux appels" ; le Grep n'en trouve qu'un (l.1244) : un second appel a ete peut-etre retire ou reorganise par une synchro. A revalider.
- Donnees sensibles : l.2915-2950 (11 adresses IP locales, redirections de ports externes, numeros de ports 10040 a 10049 et 18123 : topologie d'acces distant a la maison dans un depot PUBLIC), l.2997 (deux IP dans un exemple de commande), l.3003 (IP du reseau interne du Range Extender), l.2959-2967 (liens externes, sans risque).

**A sauver du reliquat** : (1) le bloc `[!TIP]` des commandes (l.2969-3037) vers `reference_berry/commandes.md` apres correction de `telePeriodClients` et du doublon `RubanEsclave1` ; (2) la modification C++ du pied de page (l.3041-3053) vers un fichier "modifications firmware en dur" ; (3) les TODO (l.2954-2967) seulement apres decision de l'utilisateur ; (4) la table Freebox archivee SANS les IP (garder seulement "redirections 100xx vers les modules, voir routeur"). Tout le reste : supprimer.

---

## Outils de la liste NOM_CIBLE sans AUCUNE section dans tout le README

Verification : `grep -nE "^## "` sur tout le fichier (31 titres `##`). Sections presentes : sniffeur I2C (l.948), Lieu de travail annuaire / syslog / sniffeur MQTT (l.1037), Build (l.1058), Fichiers Berry (l.1593), Assistant persist (l.1757), FTP, Fabrique, Atelier des graphiques, Atelier des ecrans, Etiquettes QR, Atelier des visuels, Synchro, Cartes simulees, Taches planifiees, Sondes, Menage, Catalogue d'icones (sous-section de l'atelier des ecrans), Organigramme, Plan de la maison, Liens web.

Outils SANS section `##` propre :
- `pont_serie` : 2 mentions seulement dans tout le README (comptage Grep), aucun mode d'emploi. Guide a ecrire.
- `sniffeur_modbus` : 1 mention seulement. Guide a ecrire (CLAUDE.md contient un long paragraphe, source possible).
- `testeur_udp` : 0 mention (chaine exacte "Testeur UDP" absente). Guide a ecrire (CLAUDE.md : long paragraphe + groupe "Grille ModBus").
- `sniffeur_mqtt` : 1 mention seulement (et le `##` "Lieu de travail" est consacre aux lieux, pas a l'outil). Guide a ecrire.
- `syslog_tasmota` : couvert seulement a travers le chapitre "Lieu de travail" (12 mentions du mot "syslog") ; pas de mode d'emploi propre. Guide a ecrire.
- `annuaire` : 43 mentions du mot, mais aucun `##` dedie (seul `## Lieu de travail : annuaire, syslog ...` y touche par les lieux). Guide a ecrire (jeton commun, barre commune, registre `annuaire_registre.py`).
- `icones_catalogue` : a une `###` (l.2428), pas de `##` : fichier propre a creer (`guides_outils/icones_catalogue.md`).
- `organigramme_plans`, `plan_maison`, `liens_web` : ont une section mais PAS de cible dans `build/` (pas de `cible_organigramme*.py`, `cible_plan_maison*.py`, `cible_liens_web*.py`). Noms de guide proposes : `organigramme_plans.md`, `plan_maison.md`, `liens_web.md`.
- Hors liste mais manquants : `acces_web.py` / `sonde_hermetique.py` (communs a tous les outils, paragraphes dans CLAUDE.md) : `guides_outils/_commun_acces_web.md` conseille.

---

## Tableau recapitulatif plage -> destination

| Plage | Section | Nature dominante | Destination proposee |
|---|---|---|---|
| 1958-2048 | Navigateur FTP des cartes | mode d'emploi + interne | `outils_docs/guides_outils/ftp_cartes.md` |
| 2050-2053 | sondes Chrome hermetiques (`sonde_hermetique`) | piege commun | `outils_docs/guides_outils/_commun_sondes_chrome.md` (ou INDEX) |
| 2055-2093 | Fabrique d'extensions | mode d'emploi | `outils_docs/guides_outils/fabrique_tapp.md` |
| 2095-2226 | Atelier graphiques (hors Energie) | mode d'emploi + interne | `outils_docs/guides_outils/atelier_graphiques.md` |
| 2149-2156 | Cote carte du moteur de pages | fonctionnement carte | `outils_docs/reference_berry/pagesGraphiques.md` |
| 2228-2260 | Destination Energie | doublon avec `## La page Energie` l.301 | fusion dans `outils_docs/reference_berry/energie.md` + 5 lignes dans le guide de l'atelier |
| 2267-2273 | `ReglageCuve simulation` | commande carte | `outils_docs/reference_berry/cuve.md` |
| 2275-2284 | Bancs graphiques | bancs | fin de `guides_outils/atelier_graphiques.md` |
| 2286-2427, 2444-2500 | Atelier des ecrans | mode d'emploi | `outils_docs/guides_outils/atelier_ecrans.md` |
| 2388-2410 | Pages Systeme et QR code d'une carte a ecran | cote carte | `outils_docs/reference_berry/ecranSysteme.md` et `ecranDebits.md` |
| 2428-2442 | Catalogue d'icones | outil distinct | `outils_docs/guides_outils/icones_catalogue.md` |
| 2502-2607 | Etiquettes QR code | mode d'emploi | `outils_docs/guides_outils/etiquettes_qr.md` (+ `reference_berry/qrcodePage.md` pour l.2544-2550) |
| 2609-2702 | Atelier des visuels d'accueil | mode d'emploi | `outils_docs/guides_outils/atelier_visuels.md` (+ `reference_berry/visuelFonctions.md` pour l.2677-2686) |
| 2704-2765 | Synchro du fork | mode d'emploi + interne | `outils_docs/guides_outils/synchro_fork.md` |
| 2767-2816 | Organigramme des plans | mode d'emploi | `outils_docs/guides_outils/organigramme_plans.md` |
| 2818-2832 | Menage du depot | mode d'emploi + interne | `outils_docs/guides_outils/menage.md` |
| 2834-2840 | Cartes simulees | mode d'emploi (maigre) | `outils_docs/guides_outils/cartes_simulees.md` (a completer) |
| 2842-2853 | Compilations de nuit / taches planifiees | mode d'emploi + interne | `outils_docs/guides_outils/taches_planifiees.md` |
| 2855-2861 | Sondes en cours | mode d'emploi (maigre) | `outils_docs/guides_outils/sondes.md` (a completer) |
| 2863 | `<hr></hr>` | decor | supprimer |
| 2865-2879 | Plan de la maison | mode d'emploi + interne | `outils_docs/guides_outils/plan_maison.md` |
| 2881-2891 | Liens web | mode d'emploi | `outils_docs/guides_outils/liens_web.md` |
| 2893-2906 | Devices Tasmota developpees | perime | supprimer |
| 2908-2911 | `[!WARNING]` vide | decor | supprimer |
| 2913-2950 | Redirections Freebox (IP + ports) | sensible et perime | archiver SANS IP dans `outils_docs/historique/`, ou supprimer |
| 2954-2967 | TODO (Bluetooth, TasmotaClient, TasmoView) | ancien | decision utilisateur ; sinon `outils_docs/historique/` |
| 2969-3037 | Commandes Tasmota personnalisees | utile, a corriger | `outils_docs/reference_berry/commandes.md` |
| 3041-3053 | Modifs C++ en dur (pied de page) | piege de synchro | `outils_docs/reference_berry/modifications_firmware_en_dur.md` |
| 3055-3063 | Memo emojis | inutile | supprimer |

---

## Synthese des affirmations perimees (par gravite)

1. L.2693 : "Pas de tuile d'annuaire, de tache VS Code ni de cible PlatformIO" pour l'atelier des visuels : FAUX (les trois existent), contredit l.2619.
2. L.2857 : "les bancs `test_*.py` et `banc_*.py` appellent tous `suit_si_script_test()`" : 199 sur 247 seulement.
3. L.2913-2950 : table de redirections Freebox : plusieurs IP absentes de tout persist, doublon <IP locale>, rideau en `:8081` alors que le code donne 8082.
4. L.2713 : Synchro du fork dans le groupe "Ateliers" : le registre dit "Deploiement".
5. L.2999 : `ReglageUDP telePeriodClients 300` : sous-commande absente de `data/` (`telePeriodClients` : 0 occurrence).
6. (suite) L.2397 vs 2412-2442 : "Pas d'icones pour l'instant (A15 et A18)" contredit par le panneau Icones et le Catalogue d'icones du meme chapitre.
7. L.2795 : liste des familles de plans sans `voie-mqtt` (1 plan l'utilise).
8. L.2846 : "(25 envs)" alors que le cenv en compte 27.
9. L.2021 : "15 persist portent `serveurFTP`" : 16 aujourd'hui.
10. L.2064 : "Quatre etapes" suivi de 5 etapes (Fabrique d'extensions).
11. L.2269 : `cuveFonctions.be` cite sans son vrai dossier (`data/garage/tasmota32s3-capteurs-cuve-modbus/`, pas `data/fs`).
12. L.2288-2293 : "Premier palier : sept objets" alors que le catalogue en a 12.
13. L.3003 : `RoutageRangeExtender1` (la commande enregistree est `RoutageRangeExtender`) ; L.3044 : "deux appels `WSContentSend_P(HTTP_END ...)`" alors qu'un seul est trouve (l.1244).

## Aucun renvoi sortant casse constate dans la plage, sauf :
- `tools\fw_TasmotaClient_arduino\TasmotaClient\examples` (l.2965) : dossier introuvable.
- Liens vers `tasks/plans/*.md`, `docs/superpowers/specs/*.md`, `outils_docs/*.md` : tous trouves.

## Donnees sensibles (lignes seulement)
- 2084 (IP du PC dans un exemple `OtaUrl`), 2840 (IP du P4), 2915-2950 (11 IP locales + redirections de ports + ports externes), 2997 (deux IP), 3003 (IP du reseau interne du Range Extender), 1973-1974 et 2003-2004 (jetons et identifiants FTP, sans valeur), 2674 (chemin du fichier de cles API, sans valeur).
