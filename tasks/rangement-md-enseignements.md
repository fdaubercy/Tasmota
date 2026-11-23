# Enseignements à remonter dans les références avant archivage des plans

Chantier « rangement des .md », plan `tasks/plans/binomes-berry.md` (A18). Les documents de destination n'existent pas
encore : chaque ligne donne l'enseignement, sa preuve et le document proposé. Aucun n'est recopié ici dans une référence.

Destinations proposées : `outils_docs/environnement/VIGILANCES_BUILD.md` (VB), `outils_docs/reference_berry/SOLIDIFICATION_BERRY.md` (SB),
`outils_docs/guides_outils/build/` (GB). Les autres sont justifiées au cas par cas.

## temps-compilation (plan `tasks/plans/temps-compilation.md`, clos)

| # | Enseignement | Preuve | Destination |
|---|---|---|---|
| 1 | `CFG_HOLDER` ne doit s'incrémenter que si `user_config_override.h` (hors ligne `CFG_HOLDER`) a changé : sinon `tasmota.ino.cpp` et tout Berry (175 fichiers sur la cuve) ne sont jamais repris du cache objet, car `berry_conf.h` inclut `my_user_config.h`. Mesure : 51 min contre 23 min 24 s. | `outils_docs/scripts_python/build/cfg_holder.py::doit_incrementer`, banc `build/test_cfg_holder.py` | VB (déjà résumé dans CLAUDE.md, à reprendre en entier) |
| 2 | `tasmota.ino.cpp` portait en ligne 1 un nom de fichier temporaire aléatoire écrit par `g++ -E` : jamais repris du cache. Un nom fixe fait passer le build de 771 s à 355 s. | `build/ino_stable.py`, banc `build/test_ino_stable.py` (journal `20261101-134632`) | VB |
| 3 | Rendre `tasmota.ino.cpp` reprenable rend `firmware.elf` reprenable : repris du cache, il arrive sans `firmware.map` et `pio-tools/tasmotapiolib.py::get_source_map_path` échoue par `*** [firmware.bin]` sans message. Un retour sur un env refait donc son édition de liens. | commit du correctif du 2026-11-01 (`make_retour`, journal `20261101-181702`), `build/test_scons_cache.py` | VB |
| 4 | `env.Decider("content-timestamp")` et `SetOption("implicit_cache", 1)` ramènent le parcours SCons de ~230 s à ~20 s sans rien compiler ; limite : un nouvel en-tête qui en masque un autre n'est vu qu'à la modification d'un fichier de la chaîne. | `build/test_scons_cache.py`, `build/pre_utilitaires_platformio.py` | VB |
| 5 | Mesurer avant de décider : changer d'env purge `.pio/build` mais le cache objet rend 771 objets sur 772, donc un dossier de build par env ne se justifie pas (à rouvrir si un retour d'env dépasse 10 min de plus qu'un build sans changement). Le chiffre « 655 s pour 1 fichier » venait d'un build échoué : ne jamais conclure d'un journal incomplet. | plan A2 et A11 (journaux de la page du 2026-11-01) | GB (page Build, section performances) |
| 6 | Le lien LTO reste mono-`lto1` malgré `post_lto_parallele.py` et `make` : mesuré sur 5 liens, aucun gain, cause non trouvée. | plan A11, `firmware.bin` identique `11a3f8d574cd6ec3` | VB (section « essais sans effet ») |

## lib-ignore-cuve et lib-ignore-envs (plans clos)

| # | Enseignement | Preuve | Destination |
|---|---|---|---|
| 1 | Le LDF est en mode `chain` : il ne lit pas les `#ifdef`, donc tout `#include` présent tire sa bibliothèque. Un `lib_ignore` bien posé fait passer le scan de la cuve de 21 min 42 à 7 min 36 sans changer le firmware. | plan `lib-ignore-cuve` A1 et A2 (journaux `avant_1.log`, `incremental_3.log`) | VB |
| 2 | Le `lib_ignore` d'un env REMPLACE celui qu'il hérite : repartir de `${env:<base>.lib_ignore}`. Toute modification du cenv change l'empreinte et vide `.pio/build` de tous les envs. | `platformio_tasmota_cenv.ini` (section `[lib_inutiles]`) | VB |
| 3 | Ignorer une bibliothèque dont la fonction est active donne « No such file » ou un échec d'édition des liens : le contrôle se fait au pré-build, avant le scan, contre les defines réels de l'env (préprocesseur croisé et `sdkconfig.h`). | `build/verifie_lib_ignore.py::controle`, `::propose`, banc `build/test_verifie_lib_ignore.py` | GB |
| 4 | Lecture des gardes : retirer les commentaires en un seul passage (`//*****` ouvrait un bloc et effaçait un fichier jusqu'à la ligne 1912) ; une macro inconnue du framework (`ESP_IDF_VERSION_MAJOR`) n'est fausse que si c'est une option Tasmota ; un défaut du contrôle ne bloque jamais le build. | `build/lecture_gardes.py::sans_commentaires`, échecs réels du 2026-10-31 (ESP8266SAM.h, ESPFtpServer.h) | VB |
| 5 | Matter, SendMail et KNX restent actifs : jamais d'`#undef`, ils ne sont ignorés que là où ils sont déjà inactifs. Piscine (ESP8266) hors champ du contrôle. | plan `lib-ignore-envs` Contexte, A2 | GB |

## graphiques-web (plan `tasks/plans/graphiques-web.md`, clos)

| # | Enseignement | Preuve | Destination |
|---|---|---|---|
| 1 | Berry ne peut pas poser d'en-tête de réponse : un fichier compressé se sert par une route qui l'envoie par morceaux, et la page le décompresse (cache localStorage versionné). | `data/fs/graphiquesFonctions.be::envoieFichier` | `outils_docs/reference_berry/PAGES_WEB_CARTES.md` (neuf, à justifier : aucune référence Berry ne couvre les pages servies) |
| 2 | `gestionFileFolder.be::listeEtRepartitLesFichiers` déplace tout fichier dont le nom contient `.js` vers `/sd/js/` en le relisant en mode texte : un `.gz` mal nommé est corrompu. | `data/fs/gestionFileFolder.be::listeEtRepartitLesFichiers` | même document |
| 3 | Les routes à accès privilégié (`/histo`, `/cm`, `/in`, `/cs`) exigent un `Referer` qui désigne la carte, sinon Tasmota coupe sans répondre (curl code 52). Pour les essais : `curl -H "Referer: http://<ip>/"`. Ne pas passer `SetOption128 1`. | `tasmota/tasmota_support/xdrv_01_9_webserver.ino` (contrôle du Referer), plan A1 | même document, et skill `logs-cartes` |
| 4 | Ne pas brancher une page dans un module solidifié (`controleWeb`, `webFonctions`) : chaque retouche imposerait un firmware pour tous les envs. Une page = un fichier de fonctions séparé, non solidifié tant qu'elle évolue. | plan Contexte (décision du 2026-10-18) | SB |
| 5 | Les réglages d'une page (`affichage`, `groupes`, `rafraichissement`, `direct`) vont dans `data/<lieu>/<carte>/graphiques.json` servi sous `/json/`, pas dans le persist (en RAM en permanence). | `data/fs/graphiquesFonctions.be::enregistre`, banc `berry/banc_graphiques.py` | même document |
| 6 | Un collecteur d'historique doit exclure par défaut les mesures internes (température ESP32, RSSI, mémoire) ; `exclues` et `ajouts` règlent les exceptions. Un pas de 5 min n'est livré qu'à son terme : le temps réel passe par `/histo?p=direct`. | `data/fs/historiqueSeries.be`, `historiqueFonctions.be::valeursDirectes` | `outils_docs/guides_outils/` (page graphiques) |

## blocage-trappe-mpu6050 et inclinaison-trappe-mpu6050 (plans clos)

| # | Enseignement | Preuve | Destination |
|---|---|---|---|
| 1 | Lire le MPU6050 en Berry par `wire`, pas par le pilote C `USE_MPU6050` : il ne lit qu'une fois par TelePeriod et se disputerait le capteur ; aucune recompilation. | `data/fs/vrFonctions.be::lireVecteur` (plan `inclinaison-trappe-mpu6050`, Contexte) | `outils_docs/materiel/` (fiche MPU6050, neuve à justifier : seule référence matériel) |
| 2 | Filtre passe-bas du MPU6050 posé au réveil (`0x6B` = 0 puis `0x1A` = `filtre`, 6 par défaut) ; angle par `math.atan2`, moyenne de 4 lectures, hystérésis `marge`. | `vrFonctions.be::lireVecteur`, banc `berry/banc_inclinaison.py` section 2 | même fiche |
| 3 | `CmndShutterStop` coupe le moteur sur-le-champ, alors que `ShutterSetOpen/Close` ne remet que `direction` à 0 : toujours `ShutterStop` AVANT le recalage. `ShutterSetPosition` ne s'applique jamais pendant une course (il remet `direction` à 0 sans couper le moteur). | `xdrv_27_esp32_shutter.ino::CmndShutterStop`, `vrFonctions.be::releveInclinaison`, `::positionReelle` | même fiche, et `outils_docs/reference_berry/` si une page Shutter existe |
| 4 | Détection de blocage (angle figé N s) et de sens inverse : repère posé à chaque début de course et à chaque mouvement d'au moins `blocageDegres` ; jamais de relance automatique après un blocage (danger si quelque chose coince la trappe). | `vrFonctions.be::verifieBlocage`, `::verifieSens`, banc `banc_inclinaison.py` sections 10 et 13 (mutants rouges) | même fiche |
| 5 | Une durée mesurée n'est jamais appliquée seule : `configVRByJson` réécrit `ShutterOpenDuration` et `ShutterCloseDuration` depuis le persist à chaque démarrage ; la page `/volets` ou `ReglageVolets Inclinaison <id>` ne fait que proposer. | `vrFonctions.be::releveInclinaison`, `::texteDurees` | même fiche |

## build-reparations (plan `tasks/plans/build-reparations.md`, clos)

| # | Enseignement | Preuve | Destination |
|---|---|---|---|
| 1 | Cause des `PermissionError ... modules.h` : un processus passager tient le fichier (indexeur C/C++, scons orphelin). Le Restart Manager de Windows nomme le processus, ce qui permet de fermer le bon et lui seul (liste blanche `cpptools-srv.exe`, `cpptools.exe`). | `build_reparations_verrou.py::processus_du_fichier`, `::classe`, `::libere` | VB |
| 2 | Réparer par un catalogue de règles à liste fermée d'actions (`attendre`, `libere_verrou`, `vide_build`), jamais de commande libre ; correspondance sur les 50 dernières lignes du journal, motif validé à l'ajout, signature `règle + dernière ligne` pour ne pas boucler (2 relances au plus). | `build_reparations.py::cherche`, `::Reparateur`, catalogue `outils_docs/schemas/reparations_build.json` | GB |
| 3 | Jamais de relance pour un `upload` ou `erase_upload` par COM ni pour une OTA : seule une compilation, un lien ou un `buildfs` raté se relance ; un `Permission denied` sur un port COM n'entre pas dans le motif. | plan Contexte (contraintes globales), banc `test_build_reparations.py` | GB |
| 4 | Le diagnostic par l'IA passe par `claude -p` en lecture seule, sur un extrait du journal dont les secrets sont filtrés ; une règle proposée est validée comme une règle du catalogue avant d'être appliquée. | `build_reparations_ia.py::diagnostique`, `::valide_proposition`, `build_reparations.py::filtre_secrets` | GB |
| 5 | Un `pio`/`scons`/`python` d'une autre origine n'est jamais fermé : on attend sa fin ; tout autre processus : demande Fermer, Attendre ou Annuler, avec expiration à 10 min (env en échec, série continue). | `build_reparations_verrou.py::classe`, plan Contexte | VB |
