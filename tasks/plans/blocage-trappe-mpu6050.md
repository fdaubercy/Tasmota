---
chantier: blocage-trappe-mpu6050
titre: Détection de blocage d'un volet par son inclinaison (MPU6050)
statut: actif
cree: 2026-10-28
maj: 2026-10-29
---
# Détection de blocage d'un volet par son inclinaison (MPU6050)

## Contexte
Suite du plan `inclinaison-trappe-mpu6050` (clos, commit 9676bd2e4). Pendant la course, l'angle est relu
toutes les 250 ms (`vrFonctions.suitInclinaison`). Si le moteur tourne mais que l'angle ne bouge pas
pendant N secondes (trappe coincée, moteur qui force en butée, position estimée fausse), la carte
envoie `ShutterStop<id>` et logue une erreur.

Décisions :
- Repère [angle, millis] posé au début de chaque course (`changementDirection`) puis à chaque mouvement
  d'au moins `blocageDegres` ; blocage si `blocage` secondes passent sans mouvement (`tasmota.time_reached`).
- Clés du bloc `inclinaison` : `"blocage": 5` (secondes, 0 = pas de détection), `"blocageDegres": 1`.
  Valeurs par défaut identiques dans le code (anciens persists). Rien ne change tant que
  `inclinaison.activation` vaut OFF.
- Après `ShutterStop`, la chaîne de 250 ms n'est pas réarmée ; le `Shutter<n>#Direction 0` qui suit fait la
  dernière lecture comme d'habitude.

## A1 — Banc d'abord
- [x] Section 10 de `banc_inclinaison.be` : horloge simulée (`millis`, `time_reached`) ; angle figé 5 s -> `ShutterStop1` + 1 erreur, suivi non réarmé ; volet qui bouge -> rien ; `blocage` 0 -> rien ; nouvelle course -> repère repris — preuve : banc_inclinaison.be section 10 (6 verifications)
- [x] Banc lancé avant le code : rouge sur la section 10 — preuve : sortie du 2026-10-28 : BANC_INCLINAISON: ECHEC (3), section 10

## A2 — Code
- [x] `vrFonctions.verifieBlocage(vr, angle)` appelée par `suitInclinaison` ; repère remis à nil par `changementDirection` — preuve : data/fs/vrFonctions.be::vrFonctions_verifieBlocage, appel dans vrFonctions_suitInclinaison, repere remis a nil dans vrFonctions_changementDirection
- [x] Clés `blocage` / `blocageDegres` dans les 7 persists et `modele_persist.json`, schéma régénéré — preuve : 7 persists + modele_persist.json (JSON relus), genere_schema_persist.py --valide : 0 erreur

## A3 — Vérifications et doc
- [x] `banc_inclinaison.py` vert, mutant (détection retirée) rouge ; `banc_boot.py`, `banc_demarrage.py` verts — preuve : BANC_INCLINAISON: OK ; mutant sans detection ECHEC (3), mutant sans remise du repere ECHEC (1) ; BANC_BOOT: OK ; banc_demarrage VERT
- [x] `solidifie_et_compile_berry.py` sur `vrFonctions.be` : le .h compile — preuve : rc = 0, « LE .h COMPILE », lib/ inchange
- [x] `outils_docs/README.md` § Inclinaison : paragraphe « Détection de blocage » — preuve : § « Détection de blocage » ; verifie_references_docs.py : 0 defaut

## A4 — Arrêt en butée (amélioration 1, 2026-10-29)
Constat dans `xdrv_27_esp32_shutter.ino` : `CmndShutterStop` coupe le moteur sur-le-champ (`ShutterUpdatePosition` ->
`ShutterPowerOff`) ; `ShutterSetOpen/Close` (`CmndShutterSetPosition` -> `ShutterStartInit(i, 0, …)`) met seulement
`direction` à 0. Donc `ShutterStop` AVANT le recalage. `Direction` n'est pas inversé par `ShutterInvert` : 1 = ouverture.
- [x] Banc d'abord (section 11) : arrivée en butée visée -> `ShutterStop1` avant `ShutterSetClose1`, suivi coupé ; déjà en butée et commandé plus loin -> arrêt + recalage immédiats ; départ d'une butée vers l'autre -> rien ; butée non désignée (`Switch2`) -> pas d'arrêt par l'inclinaison — preuve : banc_inclinaison.be section 11 rouge avant le code (ECHEC 12 avec A5/A6), vert apres ; mutant sans arret ECHEC (4)
- [x] `releveInclinaison` : sens mémorisé par `changementDirection` ; volet en course qui atteint la butée de son sens, désignée `"Inclinaison"` -> `ShutterStop` puis recalage (même sans changement d'état) — preuve : data/fs/vrFonctions.be::vrFonctions_releveInclinaison (arret, etat pose avant ShutterStop apres relecture) ; ordre ShutterStop puis ShutterSet* lu dans xdrv_27_esp32_shutter.ino::CmndShutterStop / CmndShutterSetPosition

## A5 — Blocage visible (amélioration 2)
- [x] Banc : après un blocage, ligne web « BLOQUÉ » et publication retenue `tele/<topic>/INCLINAISON<id>` (`"Bloque": true`) ; nouvelle course -> `"Bloque": false` publié, ligne normale — preuve : banc_inclinaison.be section 12 ; mutant « bloque jamais efface » ECHEC (2)
- [x] `verifieBlocage` / `changementDirection` / `ligneWebInclinaison` : état `bloque` dans le suivi, publication au changement seulement — preuve : vrFonctions.be::vrFonctions_publieBlocage, vrFonctions_verifieBlocage, vrFonctions_changementDirection, vrFonctions_ligneWebInclinaison

## A6 — Filtre passe-bas (amélioration 3)
- [x] Banc : au réveil, écrits = `0x6B` = 0 puis `0x1A` = 6 ; clé `filtre` lue — preuve : banc_inclinaison.be section 2 ; mutant sans filtre ECHEC (2)
- [x] `lireVecteur` : `0x1A` (DLPF_CFG) = `filtre` (6 par défaut : ~5 Hz, 19 ms), une fois au réveil — preuve : vrFonctions.be::vrFonctions_lireVecteur

## A7 — Vérifications, doc, commit
- [x] `banc_inclinaison.py` vert + mutants ; `banc_boot.py`, `banc_demarrage.py` verts ; solidification : le .h compile — preuve : BANC_INCLINAISON: OK ; BANC_BOOT: OK ; banc_demarrage VERT ; « LE .h COMPILE », lib/ inchange ; verifie_berry 0 erreur
- [x] Agent `relecteur-berry` sur `vrFonctions.be` (couvre aussi le commit 2a7a35884) — preuve : rien de bloquant ; 2 corrections appliquees avec test rouge puis vert (Direction 0 synchrone : un seul recalage ; butee non designee : arret sans alerte) + repere mis a jour sans allocation
- [x] README § Inclinaison : arrêt en butée, blocage visible, `filtre` — preuve : § Détection de blocage, § Arrêt en butée, cle filtre ; verifie_references_docs : 0 defaut
- [x] Commit et push (demandés par l'utilisateur le 2026-10-29) — preuve : commit 945c016af, poussé sur development

## A8 — Sens inverse (2026-10-29)
- [x] Banc d'abord : angle qui part à l'opposé du sens de course de `sensInverse` degrés (3 par défaut) depuis le départ -> `ShutterStop` + erreur + alerte (ligne web, MQTT `"Cause": "sens inverse"`) ; mouvement dans le bon sens -> rien ; `sensInverse` 0 -> rien — preuve : banc section 13, rouge avant le code puis vert ; mutant sans detection ECHEC (4)
- [x] `vrFonctions.verifieSens` appelée par `suitInclinaison` ; angle de départ noté au 1er relevé de la course ; sens attendu = `sens` × signe(angleOuvert − angleFerme) — preuve : vrFonctions.be::vrFonctions_verifieSens, appel dans vrFonctions_suitInclinaison, depart remis a nil dans vrFonctions_changementDirection

## A9 — Durées de course mesurées
- [x] Banc d'abord : course partie d'une butée et arrivée à l'autre -> durée mémorisée ; `ReglageVolets Inclinaison <id>` la donne avec la proposition `tempsMontee` (ouverture) / `tempsDescente` (fermeture), en secondes entières arrondies au-dessus ; course partie d'entre deux -> pas de mesure — preuve : banc section 14 (12.5 s -> tempsMontee 13) ; mutant duree ECHEC (2)
- [x] Mesure dans `releveInclinaison` (départ : `changementDirection`) ; jamais appliquée seule (`configVRByJson` réécrit ShutterOpen/CloseDuration depuis le persist à chaque démarrage) — preuve : vrFonctions.be::vrFonctions_releveInclinaison, vrFonctions_texteDurees, debut pose par vrFonctions_changementDirection

## A10 — Surveillance à l'arrêt
- [x] Banc d'abord : `surveillance` N s (0 par défaut = rien) -> une lecture toutes les N s volet arrêté, aucune en course ; trappe bougée hors manœuvre -> log info + recalage si butée ; minuterie seulement si l'inclinaison est active — preuve : banc section 15 (+ periode doublee si capteur muet, relecture) ; mutants surv_course ECHEC (1), echecs ECHEC (1)
- [x] `vrFonctions.surveille(vr)` (chaîne `set_timer` `vrSurveillance<id>`), lancée par `CONTROLE_VR.init` après le relevé de démarrage — preuve : vrFonctions.be::vrFonctions_surveille ; controleVoletRoulants.be::CONTROLE_VR.init

## A11 — Position réelle en %
Constat : `ShutterSetPosition` passe par `ShutterStartInit(i, 0, …)`, qui remet `direction` à 0 sans couper le moteur ->
JAMAIS pendant une course. Appliquée à l'arrêt seulement (fin de course, surveillance).
- [x] Banc d'abord : `positionReelle` ON, volet arrêté entre les butées -> `ShutterSetPosition<id> <100 − %ouverture>` (ShutterInvert 1 : `ShutterSetClose` = ouvert) ; écart < 2 % -> rien (pas d'écriture de réglages à chaque relevé) ; en course -> rien ; OFF -> rien — preuve : banc section 16 (+ renvoi apres course, relecture) ; mutants pos_course ECHEC (1), pos_invert ECHEC (3), cache ECHEC (3)
- [x] `vrFonctions.positionReelle(vr, angle)` appelée par `changementDirection` (arrêt) et la surveillance — preuve : vrFonctions.be::vrFonctions_positionReelle, par vrFonctions_commandeArret (differe apres un arret : ShutterWaitForMotorStart boucle sur loop(), relecture) ; mutants immediat ECHEC (3), abandon ECHEC (1)

## A12 — Persists, vérifications, doc, commit
- [x] Clés `sensInverse: 3`, `surveillance: 0`, `positionReelle: "OFF"` dans les 7 persists et le modèle, schéma régénéré — preuve : 7 persists + modele_persist.json (JSON relus) ; genere_schema_persist.py --valide : 8 cartes a 0 erreur
- [x] Bancs inclinaison (+ mutants), boot, démarrage verts ; solidification des 2 `.be` ; `relecteur-berry` — preuve : BANC_INCLINAISON OK, 9 mutants ECHEC ; BANC_BOOT OK ; banc_demarrage VERT ; les 2 .h compilent (apres la fin du build de la cuve, 05:03) ; relecteur : rien de bloquant, 4 points corriges (commandes differees apres arret, cache de position, position en surveillance apres mouvement, periode doublee capteur muet)
- [x] README § Inclinaison ; aide `ReglageVolets Inclinaison` — preuve : § Sens inverse, Durées de course, Surveillance à l'arrêt, Position réelle ; aide INCLINAISON ; verifie_references_docs : 0 defaut
- [ ] Commit et push

## Améliorations restantes
- [ ] [projet] Essai réel sur la trappe du grenier (avec le reste de l'inclinaison)
- [ ] [projet] Accessoire — angle dans le JSON SENSOR (Grafana, historique ; vérifier que `historiqueSeries` n'exclut pas les volets)
- [ ] [projet] Accessoire — température interne du MPU6050 (registre `0x41`) comme capteur du grenier
- Écartés : relance automatique après un blocage (danger si quelque chose coince la trappe) ; apprentissage qui commande le moteur (refusé le 2026-10-28).
- [x] [conversation] Commit sur demande de l'utilisateur — preuve : commit 2a7a35884, poussé sur development
