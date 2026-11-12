---
chantier: ecran-cave-vues-commandes
titre: Écran 7B de la cave, vues, commandes par ModBus, affichage par MQTT, veille et pannes des flotteurs
objectif: Commander les appareils de la cave et voir son état sur l'écran 7B esclave, sans rien changer au comportement des autres cartes
statut: actif
cree: 2026-11-12
maj: 2026-11-12
---
# Écran 7B de la cave : plan de réalisation

> Pour un agent qui exécute ce plan : sous-skill requise, superpowers:subagent-driven-development (recommandée) ou
> superpowers:executing-plans. Cocher chaque étape dès qu'elle est vérifiée, avec « — preuve : … ».

## Contexte

**But.** Sur l'écran 7B de la cave (esclave ModBus id 1), commander lumières, lave-linge, pompe cuve et pompe vide-cave,
redémarrer le serveur, voir T°/HR, ventilation, flotteurs du vide-cave et cuve ; veille ; pannes des flotteurs.

**Conception.** `docs/superpowers/specs/2026-11-12-ecran-cave-vues-commandes-design.md` (validée le 2026-11-12, commit
`de6d66720`). Plan d'origine : `tasks/plans/envs-grenier-rdc-sonoff-cave.md` A9.

**Architecture.**
- Commande : l'écran pousse en UDP (`modbusFonctions.pousseEtat`) un mot par touche sur le registre de son bouton
  virtuel ; le maître ne réagit qu'aux push (`Automatique`), par un crochet générique `global.commandesEsclave` posé
  par un module du seul dossier de la cave.
- Affichage : l'écran s'abonne en MQTT au serveur de la cave et à la cuve, date chaque valeur, grise ce qui est périmé.
- Veille : `ecranFonctions.be` déplacé tel quel dans `data/fs` et partagé avec l'écran des débits.

**Pile.** Berry (Tasmota ESP32-S3), HASPmota, ModBus maison (`data/fs/modbusFonctions.be`), MQTT Berry
(`mqtt.subscribe`), bancs Berry sous `lib/libesp32/berry/berry.exe` pilotés par Python.

### Contraintes globales

- Accord de l'utilisateur sur `data/fs` (2026-11-12) : seulement `modBus_TasmotaSlaveModBus.be`, `globalFonctions.be`,
  `controleGeneral.be` (réactivation des flotteurs) et `ecranFonctions.be` (déplacé), et **tout nouveau comportement
  ne s'active que par une clé du persist absente des autres cartes**. Preuve exigée : `banc_demarrage.py` VERT sans
  `--enregistre` pour toutes les cartes autres que la cave et l'écran ; `banc_test_modbus.py` et `banc_ecran_debits.py`
  VERTS.
- Charte des logs Berry de `CLAUDE.md` (`logFonctions.log`, préfixes `NOM_MAJ:`, pas d'`info` dans un callback fréquent).
- Fichiers de moins de 500 lignes ; renvois au code par `fichier::fonction`.
- Compilation par la page Build (:7700) uniquement ; jamais de `pio run` pendant un build ; `data/`, cenv et `.h` pas
  édités pendant un build.
- Secrets : tout grep d'un persist ou du `.h` filtré par `grep -viE "pass|pwd|mdp|key|token"`.
- Numérotation des touches (choix de Claude, fixée ici) : 1 Lumières (relais 3, module `autres`), 2 Lave-linge
  (relais 5, `autres`), 3 Pompe cuve (relais 4, `autres`), 4 Pompe vide-cave (relais 1, `pompeVideCave`, marche
  manuelle), 5 Redémarrer le serveur.
- Mot poussé par l'écran : `mot = (seq << 1) | (voulu == "ON" ? 1 : 0)`, `seq` de 1 à 127 puis retour à 1, propre à
  chaque touche, jamais 0. Registre : `32 + numero - 1` (type bouton 32).

### Points d'attention (Review Focus)

1. Redémarrage du serveur pendant une marche manuelle : les flotteurs doivent être réactivés au démarrage (A2).
2. Écran qui redémarre, Wi-Fi qui revient, relevé RS485 périodique : aucun relais ne bouge (A4, push seulement, `seq`).
3. Même mot reçu deux fois (relance de l'écran) : une seule action (A4).
4. Broker MQTT absent : valeurs grisées, touche refusée « état inconnu », aucun push (A5, A6).
5. Flotteurs qui bougent pendant un remplissage normal : pas de fausse alerte d'incohérence (anti-rebond, A3).

## A1 — Veille commune : `ecranFonctions.be` dans `data/fs`
Fichiers : déplacer `data/bureau/tasmota32s3-ecran-debits-pac/ecranFonctions.be` -> `data/fs/ecranFonctions.be`
(contenu inchangé) ; `platformio_tasmota_cenv.ini` : nouvelle liste `[berry_commun] ecran = data/fs/ecranFonctions.be`,
ajoutée au `custom_files_exclude` de chaque env SANS écran (modèle : `${berry_commun.page_cuve}`).
Interface produite (inchangée) : `ecranFonctions.bloc` (nom du bloc `modules.<bloc>`), `ecranFonctions.charge(noms)`,
`ecranFonctions.suitVeille()`, `ecranFonctions.regle(cle, n, bornes, differe)`, `ecranFonctions.echantillonne(valeurs)`,
`ecranFonctions.BORNES` (veille, extinction, luminosite). Premier toucher après veille avalé par le voile (déjà fait).
- [x] `banc_ecran_debits.py` VERT AVANT le déplacement (référence), sortie notée — preuve : `banc_ecran_debits.py` VERT avant le déplacement (dernière ligne `BANC_ECRAN_DEBITS (enveloppe): VERT`, 2026-11-12)
- [x] Déplacement (`git mv`) ; le banc trouve encore le module (adapter son chemin s'il est figé) ; `banc_ecran_debits.py` VERT, ses mutants rouges — preuve : `git mv` fait ; chemin du banc adapté (`banc_ecran_debits.py::GENERIQUE`, `.be` ligne 21) ; `banc_ecran_debits.py` VERT après (mutants du générique rouges, enveloppe VERT) ; `verifie_berry.py data/fs/ecranFonctions.be` 0 erreur ; `build/test_interface_ecran.py` VERT
- [x] Liste `ecran` exclue des envs sans écran ; `banc_demarrage.py` VERT sans `--enregistre` — preuve : `${berry_commun.ecran}` ajouté à 16 envs sans écran du cenv ; `banc_demarrage.py` sans `--enregistre` : VERT pour toutes les cartes sauf `tasmota32s3-cave-ecran` (reçoit désormais `/ecranFonctions.be` dans ses sources, attendu : elle garde le module)
- [x] Commit `refactor(ecran): veille commune ecranFonctions deplacee dans data/fs` ; case l.113 — preuve : commit `5c3291884` ; référence `banc_demarrage` de l'écran de la cave mise à jour (`sources (3)` avec `/ecranFonctions.be`) du plan `debits-deux-cartes` mise à jour (déplacement fait, solidification restant à faire là-bas)

## A2 — Pompe vide-cave : marche manuelle sans flotteurs
Fichiers : `data/fs/globalFonctions.be::globalFonctions_commandeRelaisLies` (5e argument de `modifEtatRelai` =
`relaisLie.find("desactiveCapteurs", "OFF") == "ON"` au lieu de `false`) ; `data/fs/globalFonctions.be::globalFonctions_modifEtatRelai`
(quand `boolCapteurs` désactive un capteur, poser aussi `"suspendu": "ON"` ; à la réactivation, retirer la clé) ;
`data/fs/controleGeneral.be` : au passage d'un relais à OFF (bloc « Relance de securite », même endroit que
`acquitteRelance`) et dans `init()`, remettre `activation: "ON"` à tout capteur du module qui porte `"suspendu": "ON"`,
et retirer la clé. Persist de la cave : `"desactiveCapteurs": "ON"` dans le `relaisLie` de `bouton1` et `bouton2` de
`pompeVideCave`. Schéma : `genere_schema_persist.py` régénéré si la clé y est refusée.
Banc neuf : `outils_docs/scripts_python/berry/banc_pompe_cave.py` + `.be` (modèle : `banc_cuve.py`, bouchons dans
`bouchons_berry/pompe_cave/`), code de sortie 0 = VERT.
- [x] Banc rouge d'abord : `appui_bouton_desactive_flotteurs` (bouton1 ON -> capteurs `activation` OFF et `suspendu` ON, relais 1 ON), `flotteur_bas_ignore_en_manuel` (capteur1 OFF pendant la marche -> relais 1 reste ON), `second_appui_reactive` (bouton1 -> relais OFF, capteurs ON, pas de `suspendu`), `minuterie_reactive` (`finTimerRelai` -> capteurs ON), `demarrage_reactive` (persist avec `suspendu` ON -> `init()` les réactive), `sans_cle_inchange` (relaisLie sans `desactiveCapteurs` : capteurs jamais touchés) — preuve : `python outils_docs/scripts_python/berry/banc_pompe_cave.py` avant le code : 4 cas ECHEC (appui_bouton, flotteur_bas, second_appui, minuterie), demarrage_reactive rouge aussi (capteurs OFF/OFF/ON/ON apres init) ; sans_cle_inchange vert d'emblee (garde-fou)
- [x] Code ; banc VERT ; un mutant par cas (ex. `false` remis dans `commandeRelaisLies`) lu rouge — preuve : banc VERT `BANC_POMPE_CAVE: OK (14 controles)` ; mutants lus rouges : `false` remis dans commandeRelaisLies (4 echecs), `true` force (sans_cle rouge), ligne `suspendu` retiree (3), reactivation a OFF retiree (minuterie rouge), boucle d'init retiree (demarrage rouge 2) ; fichiers restaures, verifie_berry.py 0 erreur
- [x] Persist de la cave et schéma ; `genere_schema_persist.py --valide` 0 erreur ; `banc_demarrage.py` VERT (cave réenregistrée seule, avec l'accord déjà donné pour elle) — preuve : `genere_schema_persist.py --valide` : tasmota32s3-serveur-rly 0 erreur (seul KO : tasmota32s3-ecran/ecranCave, persist d'une autre session, hors A2 ; cle acceptee, schema inchange) ; `banc_demarrage.py` VERT sans --enregistre (cave-serveur-rly OK, snapshot inchange, toutes les autres cartes OK) ; banc_test_modbus 386 PASS (le code 1 vient de tasmota32s3-ecran tcp.id=0 != rangeExtender.id=1, autre session) ; banc_boot OK ; banc_ecran_debits VERT
- [ ] Commit `feat(pompe): marche manuelle sans flotteurs, reactives a l'arret et au demarrage`

## A3 — Pannes des flotteurs et état de la pompe publié
Fichier : `data/cave/tasmota32s3-serveur-rly/controlePompeVideCave.be` (dossier de la carte, pas `data/fs`).
Persist de la cave, bloc `pompeVideCave` : `"pannes": {"antiRebond": 5, "maxArretsMinuterie": 3}` (secondes, nombre).
- Incohérence : flotteur haut ON et bas OFF pendant plus de `antiRebond` s -> alerte `incoherence`.
- Cas (a) du flotteur bas : relais 1 coupé par sa minuterie (durée de marche >= `timer` - 1 s) alors que le haut est
  OFF et le bas encore ON -> compteur ; à `maxArretsMinuterie` d'affilée -> alerte `flotteurBas` ; compteur remis à 0
  par un arrêt avec le bas OFF. Rien n'est compté pendant une marche manuelle (capteurs `suspendu`).
- Alerte : même voie que `controleGeneral.be::publieAlerteRelance` (`topicAlerte`, `relai["alerte"]`), effacée par
  `AcquittePompe`.
- Publication : `json_append` du driver ajoute `"PompeVideCave": {"Pompe", "Manuel", "Niveaux": {"Bas", "Haut"}, "Alerte"}`
  (valeurs ON/OFF/"?", texte), lu par l'écran (A6).
- [ ] Banc `banc_pompe_cave` étendu, rouge d'abord : `incoherence_apres_anti_rebond`, `incoherence_breve_ignoree`, `flotteur_bas_apres_n_arrets`, `arret_normal_remet_compteur`, `manuel_ne_compte_pas`, `json_append_porte_pompe_vide_cave`
- [ ] Code ; banc VERT ; mutants rouges ; `verifie_berry.py` 0 erreur
- [ ] Persist (clé `pannes`) ; schéma ; `banc_demarrage.py` VERT
- [ ] Commit `feat(pompe): pannes des flotteurs (incoherence, flotteur bas) et etat publie`

## A4 — Le serveur exécute les touches de l'écran
Fichiers : `data/fs/modBus_TasmotaSlaveModBus.be`, branche `boutons` de la réception : avant la conversion en ON/OFF,
`if (msg.find("Automatique", false) && global.commandesEsclave != nil) global.commandesEsclave.recoit(nameTasmotaSlaveModBus, env[cleEnv][cleDevice]["idModBus"], int(msg["Values"][0])) end`
(une ligne, sur le modèle de `vrFonctions.capteurVirtuel` ; garder `Automatique` lu avant que `push` soit remis à false).
Module neuf du dossier de la cave : `data/cave/tasmota32s3-serveur-rly/controleCommandesEcran.be`, chargé par l'autoexec
de la cave sous la garde `modules.ecranCave` ; il pose `global.commandesEsclave`.
Interface produite : `commandesEsclave.recoit(esclave:string, numero:int, mot:int) -> nil`. Actions : relais
-> `globalFonctions.modifEtatRelai(module, relai, voulu, voulu, manuel == "ON", true, 0)` ; redémarrage -> `Restart 1`
seulement pour `voulu == "ON"`. Dernière `seq` par (esclave, numero) en RAM : même `seq` = ignoré ; `seq` 0 = ignoré.
Persist de la cave, bloc `modules.ecranCave` (activation ON au flash de l'écran, OFF avant) :
`{"activation", "esclave": "ECRAN-CAVE", "actions": {"1": {"module": "autres", "relai": 3}, "2": {"module": "autres", "relai": 5}, "3": {"module": "autres", "relai": 4}, "4": {"module": "pompeVideCave", "relai": 1, "manuel": "ON"}, "5": {"redemarre": "ON"}}, "environnement": {"boutons": …}}`
avec 5 boutons `virtuel: "ModBus_ECRAN-CAVE"`, type 32, `idModBus` 1 à 5, `id` 11 à 15 (hors des boutons physiques 1 à 3).
- [ ] Vérifier d'abord que des boutons virtuels ModBus sur le maître ne créent ni GPIO, ni règle `Button`, ni entrée parasite dans `json_append` de `controleGeneral` (lire `configDevices.be`, banc) ; noter la conclusion ici
- [ ] Banc rouge d'abord (`banc_test_modbus.be` étendu ou `banc_commandes_ecran.{py,be}` neuf) : `push_allume_relai`, `meme_seq_une_seule_action`, `releve_sans_action`, `seq_zero_ignoree`, `numero_inconnu_log_erreur`, `redemarre_seulement_sur_on`, `pompe_manuelle_desactive_flotteurs`, `sans_crochet_comportement_inchange` (garage : `global.commandesEsclave` nil)
- [ ] Code ; bancs VERTS (`banc_test_modbus.py` entier compris) ; mutants rouges
- [ ] Persist de la cave (`ecranCave` OFF), autoexec ; schéma ; `banc_demarrage.py` VERT
- [ ] Commit `feat(modbus): le serveur de la cave execute les touches de l'ecran`

## A5 — L'écran envoie ses touches
Fichiers neufs du dossier de l'écran : `data/cave/tasmota32s3-ecran/ecranCaveFonctions.be` (logique, sans LVGL) et
`controleEcranCave.be` (driver). Persist de l'écran, bloc `modules.ecranCave` : 5 boutons virtuels (type 32, ids 1 à 5,
sans broche) pour répondre au relevé du maître ; `veille`, `extinction`, `luminosite` (clés lues par `ecranFonctions`).
Interface produite : `ecranCaveFonctions.touche(numero:int) -> string` (« envoye », « refuse » ou « inconnu ») ;
`voulu` = inverse de l'état affiché (touche 5 : toujours ON) ; refus si la valeur de l'appareil est périmée (A6) ;
relance du même mot toutes les 2 s, 5 fois au plus, jusqu'à ce que l'état reçu par MQTT égale `voulu`.
- [ ] Vérifier qu'un bouton sans broche ne fait pas planter `changementEtatCapteur` (`device["pin"]` dans un `format %i`) ni le relevé `0x02` du maître ; corriger en `find("pin", -1)` si besoin (dans `globalFonctions.be`, sans autre changement)
- [ ] Banc rouge d'abord : `banc_ecran_cave.{py,be}` (modèle `banc_ecran_debits`) : `touche_pousse_mot`, `seq_avance_jamais_zero`, `refus_si_perime`, `relance_jusqu_a_confirmation`, `abandon_apres_5`, `redemarrer_toujours_on`
- [ ] Code ; banc VERT ; mutants rouges
- [ ] Commit `feat(ecran-cave): envoi des touches par push ModBus`

## A6 — L'écran affiche l'état par MQTT
Fichier : `ecranCaveFonctions.be` (modèle des valeurs) et `controleEcranCave.be` (abonnements). Persist de l'écran :
`modules.ecranCave.sources = {"cave": "cave/serveur-rly-cave-v2", "cuve": "jardin/cuve"}`,
`modules.ecranCave.peremption = {"cave": 900, "cuve": 900}` (secondes, 3 × 300 s).
Abonnements (`mqtt.subscribe`, modèle `fsMqtt.be`) : `tele/<cave>/SENSOR` (AM2301, `PompeVideCave` d'A3),
`tele/<cave>/STATE` et `stat/<cave>/RESULT` (POWER1 à 5), `tele/<cuve>/SENSOR` (`sensorsCuve` : lire
`cuveFonctions.sensorsCuve` pour les noms du taux et du volume). À la connexion MQTT : `cmnd/<cave>/STATE` et
`cmnd/<cave>/STATUS 10` pour ne pas attendre la télémétrie. Chaque valeur garde son heure ; `perime(source) -> bool`.
Interface produite : `ecranCaveFonctions.modele() -> map` (valeurs, `perime` par valeur, alertes) lu par l'interface (A7).
- [ ] Banc rouge d'abord : `sensor_cave_lu`, `power_lu_par_result`, `cuve_lue`, `perime_apres_delai`, `json_invalide_ignore_sans_planter`, `topics_lus_dans_le_persist`
- [ ] Code ; banc VERT ; mutants rouges
- [ ] Commit `feat(ecran-cave): affichage par MQTT, valeurs datees et perimees`

## A7 — Pages HASPmota de l'écran
Description neutre `outils_docs/atelier_ecrans/cartes/tasmota32s3-cave-ecran/ecran.json`, `pages.jsonl` généré par
`outils_pc/atelier_ecrans_haspmota.py::genere`, interface `data/cave/tasmota32s3-ecran/ecranCaveHaspmota.be` (expose
`demarre()` et `affiche(m)` comme `ecranHaspmota.be` ; touches par `tasmota.add_rule("hasp#p<page>b<id>#event", …)`
sur `up` -> `ecranCaveFonctions.touche`). Pages : 1 Accueil (disposition C : capteurs à gauche, appareils à droite),
2 Graphiques T°/HR (`ecranFonctions.echantillonne`), 3 Cuve et vide-cave (jauge, flotteurs, alertes), 4 Réglages écran
(veille, extinction, luminosité par `ecranFonctions.regle`). Menu ☰ en page 0 (fenêtre qui s'ouvre par-dessus) avec
« Redémarrer le serveur » et une confirmation à deux touches. Valeur périmée = grisée, horloge de la barre du haut barrée tant que le broker n'est pas joint ; ventilation = icône animée si
POWER2 ON ; pompe vide-cave « auto » et « manuel » ; alertes des flotteurs en rouge. Polices : celles de `/sd/polices`.
Ressources sous `/sd` (préférence de l'utilisateur).
- [ ] Maquette du rendu (capture de l'aperçu de l'atelier) validée par l'utilisateur avant l'écriture des pages
- [ ] `ecran.json` validé par `atelier_ecrans_description.valide` ; `pages.jsonl` généré
- [ ] `banc_ecran_cave` étendu : chaque objet référencé par `affiche` existe dans `pages.jsonl` ; `confirmation_avant_redemarrage` ; `menu_ouvre_et_ferme`
- [ ] Commit `feat(ecran-cave): pages HASPmota (accueil, graphiques, cuve, reglages, menu)`

## A8 — Intégration, non-régression, compilation
- [ ] Cenv de `tasmota32s3-cave-ecran` : `custom_interface_ecran = haspmota` et ses listes, fichiers du dossier ; autoexec de l'écran (`ecranFonctions`, `ecranCaveFonctions`, `controleEcranCave`, `modules.ecranCave` ON)
- [ ] `banc_demarrage.py` : cave et écran réenregistrés (contenu relu), toutes les autres cartes VERTES SANS réenregistrement
- [ ] `banc_test_modbus.py`, `banc_ecran_debits.py`, `banc_pompe_cave.py`, `banc_ecran_cave.py` VERTS ; `verifie_berry.py` 0 erreur ; `genere_schema_persist.py --valide` 0 erreur
- [ ] Agent `relecteur-berry` sur tous les `.be` touchés ; remarques traitées
- [ ] Compilation par la page Build : cave, écran (et débits, garage si `data/fs` solidifié touché) ; journaux SUCCESS
- [ ] `PROTOCOLE_MODBUS.md` §10 et `outils_docs/README.md` (mode d'emploi de l'écran) ; plan `envs-grenier-rdc-sonoff-cave` A9 coché
- [ ] Commit `feat(ecran-cave): integration et documentation`

## A9 — Essai sur carte (écran branché)
- [ ] Flash de l'écran (USB, effacer puis téléverser) ; `TasmotaSlaveModBus1` et `modules.ecranCave` de la cave à ON, persist renvoyé à chaud
- [ ] Chaque touche commute son relais ; redémarrage après confirmation ; aucune commutation au redémarrage de l'écran ni du serveur (journal syslog)
- [ ] Broker coupé : valeurs grisées, touches refusées ; RS485 seul, puis Wi-Fi seul
- [ ] Marche manuelle de la pompe : flotteurs ignorés, réactivés à l'arrêt et après la minuterie
- [ ] Veille, réveil sans action, luminosité

## Améliorations restantes
- [ ] [projet] Solidifier `ecranFonctions` dans les envs à écran (plan `debits-deux-cartes` A8)
- [ ] [projet] Boutons physiques du serveur à garder ou retirer (plan `envs-grenier-rdc-sonoff-cave` A9)
- [ ] [projet] Topic de la cave à changer au retour en production (A7 du plan d'origine) : seul le persist de l'écran à modifier

## Vérification
Bancs Berry VERTS (`banc_pompe_cave`, `banc_ecran_cave`, `banc_test_modbus`, `banc_ecran_debits`, `banc_demarrage`),
compilation SUCCESS des envs touchés, essai A9 sur carte.
