---
chantier: inclinaison-trappe-mpu6050
titre: Capteur d'inclinaison MPU6050 pour les volets (trappe du grenier)
statut: clos
cree: 2026-10-28
maj: 2026-10-28
source: tranquil-sleeping-taco.md
---
# Capteur d'inclinaison MPU6050 pour les volets (trappe du grenier)

## Contexte
La trappe motorisée du grenier est pilotée par le Shutter de Tasmota (position estimée au temps) via
`controleVoletRoulants.be` + `vrFonctions.be`. Un MPU6050 posé sur la trappe donne son angle réel
(accéléromètre, `math.atan2`, vérifié : `be_mathlib.c:169`). Usage : recaler la position (fins de course
logicielles) et connaître la position réelle après un redémarrage.

Décisions prises :
- **Lecture en Berry par `wire`** (`tasmota.wire_scan`, `wire.write`, `wire.read_bytes`, modèle
  `tasmota/berry/drivers/MPU6886_9250.be`), PAS le pilote C `USE_MPU6050` : il ne lit qu'une fois par
  TelePeriod (`xsns_32_mpu6050.ino:262-265`) et se disputerait le capteur. Aucune recompilation.
- **Le MPU est un capteur de position nommé `"Inclinaison"`** dans `capteursPosition.capteurOuvert` /
  `capteurFerme`, sur le modèle de `vrFonctions.capteurVirtuel` : il appelle `changementEtatCapteur`
  au seul CHANGEMENT d'état (recalage `ShutterSetOpen/Close` existant réutilisé).
- **Garde d'activation d'abord** (demande de l'utilisateur) : `controleVoletRoulants` cherche si un volet
  a `capteursPosition.inclinaison.activation == "ON"` ; sinon : ni `wire_scan`, ni minuterie, ni attente
  de données. Les cartes sans MPU ne voient aucune différence.
- **Livré désactivé** : sous-clé `inclinaison` ajoutée avec `"activation": "OFF"` dans les persists,
  `capteurOuvert`/`capteurFerme` inchangés.
- Lecture seulement quand utile : une au démarrage, puis toutes les 250 ms pendant la course
  (début/fin donnés par `Shutter<n>#Direction`, règle déjà posée), moyenne de 4 lectures, hystérésis `marge`.
- `vrFonctions.be:230-237` (ShutterSetClose sur « ouverture ») est JUSTE : `ShutterInvert 1`
  (`vrFonctions.be:121`) + `100 - payload` (`xdrv_27_esp32_shutter.ino:2052`). Décision : garder et commenter.
- Pas de nouveau module Berry : tout dans `vrFonctions.be` (déjà solidifié dans 18 sections du cenv,
  aucune globale nouvelle à ajouter à `globs`). État modifiable dans `vrFonctions.etat()` (module solidifié = constant).

Bloc persist ajouté sous `capteursPosition` :
```json
"inclinaison": {
    "activation": "OFF",
    "adresse": 104,
    "axes": "YZ",
    "angleOuvert": 85,
    "angleFerme": 3,
    "marge": 3
}
```

## A1 — Commentaire de la compensation ShutterInvert
- [x] Vérifier qu'aucun build ne tourne (pas de `scons` / `pio run`) avant toute édition de `data/` (leçon 2026-10-24) — preuve : build cuve (pio run 07:20) attendu, plus aucun scons/pio run à 08:04 avant la recopie dans data/fs
- [x] Commentaire de 2 lignes au-dessus de `vrFonctions.be:230` : ShutterInvert 1 posé par `configVRByJson` -> `ShutterSetClose` = ouvert ; ne pas « corriger » — preuve : `vrFonctions.be::changementEtatCapteur` (commentaire « Croisement VOULU »), décision utilisateur « Garder + commenter »

## A2 — Banc d'abord (comportement attendu, rouge avant le code)
- [x] `outils_docs/scripts_python/berry/banc_inclinaison.{py,be}` sur le modèle de `banc_leds.{py,be}` : vrai `vrFonctions.be` sous `berry.exe`, faux `tasmota.wire_scan` (octets AX/AY/AZ fournis par le test), faux `tasmota.cmd` qui note les `ShutterSet*` — preuve : fichiers créés, faux WireStub/TasmotaStub
- [x] Cas : angles 0°, 45°, 90°, valeurs négatives (int16 signé) ; hystérésis (pas de rebond près du seuil) ; un seul recalage par franchissement — preuve : sections 2 et 4 du banc ; mutant sans hystérésis -> ECHEC (4)
- [x] Témoins : aucun volet `inclinaison` ON -> `wire_scan` JAMAIS appelé ; `wire_scan` rend nil -> log `erreur`, pas d'exception, suivi coupé — preuve : sections 1 et 6 ; mutant sans garde d'activation -> ECHEC (3)
- [x] Banc lancé avant le code : rouge sur les cas nouveaux — preuve : `attribute_error: module 'vrFonctions' has no member 'inclinaisonsActives'`, rc=1

## A3 — Lecture et décision dans vrFonctions.be
- [x] `vrFonctions.inclinaisonsActives()` : volets ON dont `capteursPosition` ON et `inclinaison.activation` ON — preuve : `vrFonctions.be::inclinaisonsActives` + `::inclinaison` ; banc section 1
- [x] `vrFonctions.lireAngle(vr)` : `wire_scan(adresse)` mis en cache dans `etat()`, réveil `0x6B = 0` une fois, `read_bytes(adr, 0x3B, 6)`, int16 signés, `atan2` selon `axes`, moyenne de 4 ; nil + log `erreur` si capteur absent — preuve : `vrFonctions.be::lireAngle(id, incl)` ; banc sections 2 et 6
- [x] `vrFonctions.releveInclinaison(vr)` : état ouvert / fermé / entre avec `marge` ; au changement, `changementEtatCapteur("ON", "Inclinaison", ..., id, "ouverture"|"fermeture")` seulement si `capteurOuvert`/`capteurFerme` vaut `"Inclinaison"` — preuve : `vrFonctions.be::releveInclinaison`, `::etatInclinaison` ; banc sections 4 et 7
- [x] Suivi pendant la course : `changementDirection` démarre une chaîne `tasmota.set_timer(250, ..., "vrInclinaison<id>")` si direction ≠ 0 et volet surveillé ; arrêt + dernière lecture à direction 0 — preuve : `vrFonctions.be::suitInclinaison`, appel dans `::changementDirection` ; banc section 5
- [x] `ReglageVolets Inclinaison <id>` : renvoie angle mesuré et état (calibrage de `angleOuvert`/`angleFerme`) ; entrée dans `aideReglageVolets` — preuve : `vrFonctions.be::reglageVolets`, `::aideReglageVolets` ; banc section 3
- [x] Logs selon la charte (`vrFonctions.log`, pas d'`info` dans la chaîne 250 ms, `detail` gardé par `logFonctions.actif`) — preuve : `verifie_berry.py` : 0 erreur, 0 avertissement de charte ; chaîne 250 ms en debug/erreur seulement

## A4 — Garde d'activation dans controleVoletRoulants.be
- [x] Dans `CONTROLE_VR.init` : `inclinaisonsActives()` ; liste vide -> rien de plus ; sinon une lecture de démarrage par volet + un log `info` « inclinaison active, volet N » — preuve : `controleVoletRoulants.be::CONTROLE_VR.init` (boucle sur `inclinaisonsActives`)

## A5 — Persists et schémas (désactivé)
- [x] Sous-clé `inclinaison` (`activation: "OFF"`) dans `capteursPosition` de chaque `_persist.json` suivi qui le porte, hors `*sauvegarde*` (garage ×4, grenier, cave ×2), fins de ligne de chaque fichier gardées — preuve : 7 persists modifiés (script : 1 remplacement exact par fichier, JSON relu) ; angles en décimaux (85.0, 3.0) pour que le schéma dise `number`
- [x] Même sous-clé dans `outils_docs/schemas/modele_persist.json` ; `persist.schema.json` régénéré par `berry/genere_schema_persist.py` — preuve : `genere_schema_persist.py` (angleOuvert : type number) puis `--valide` : 8 cartes à 0 erreur

## A8 — Apprentissage des butées (2 commandes manuelles)
- [x] Banc d'abord : section « apprentissage » (vecteurs ouvert/fermé simulés, axes et angles déduits, persist.save(true) appelé, témoins : butées trop proches, arc qui traverse la coupure de atan2, une seule butée relevée -> rien écrit) — preuve : section 8 de banc_inclinaison.be rouge (ECHEC 8) avant le code ; mutants sans contrôle de coupure -> ECHEC (1), seuil 1° -> ECHEC (2)
- [x] `ReglageVolets Apprentissage <id> ouvert|ferme` : relève le vecteur moyen (AX, AY, AZ) de la butée, en RAM (`etat()`), lisible même inclinaison OFF ; ne commande jamais le moteur — preuve : `vrFonctions.be::apprend`, `::lireVecteur`, `::trouveInclinaison` ; banc section 8
- [x] Les 2 butées connues : axe de rotation = composante qui varie le moins ; plan = les 2 autres, ordre choisi pour que l'arc ne traverse pas la coupure ±180° de atan2 ; refus si écart < 10° ou si aucun ordre ne convient — preuve : `vrFonctions.be::calculeApprentissage` ; banc section 8 (refus à 5°, refus arc 170° -> -80°)
- [x] Écrit `axes`, `angleOuvert`, `angleFerme` dans `capteursPosition.inclinaison`, puis `persist.drivers = drivers` + `persist.save(true)` ; suivi remis à zéro ; réponse avec les valeurs apprises — preuve : `vrFonctions.be::apprend` ; banc : nb_save + 1, butées relues ouvert / ferme
- [x] Aide `ReglageVolets ?Apprentissage` : déroulé en 2 temps, redémarrage entre les deux = recommencer — preuve : `vrFonctions.be::aideReglageVolets` (sujet APPRENTISSAGE)

## A9 — Inclinaison sur la page web
- [x] `web_sensor` du driver : une ligne `{s}<nom> : inclinaison{m}<angle> ° (<état>){e}` par volet actif, aucune sinon — preuve : `controleVoletRoulants.be::CONTROLE_VR.web_sensor`
- [x] Dernier angle relevé (démarrage, course, arrêt), sans relire le bus à chaque rafraîchissement ; « capteur muet » après une panne — preuve : `vrFonctions.be::ligneWebInclinaison` ; banc section 9

## A6 — Vérifications
- [x] Hook `verifie_berry_edition` sans erreur ni écart de charte sur les deux `.be` — preuve : `verifie_berry.py` sur les 2 fichiers : 0 erreur, 0 avertissement (fichiers recopiés par cp, hook non déclenché : lancé à la main)
- [x] `banc_inclinaison.py` vert, témoins compris — preuve : BANC_INCLINAISON: OK, rc=0 (9 sections) ; 4 mutants détectés
- [x] `berry/solidifie_et_compile_berry.py` sur `vrFonctions.be` et `controleVoletRoulants.be` (chaîne du build, leçon 2026-10-04) — preuve : autorisé par l'utilisateur, aucun build en cours ; `solidified_vrFonctions.h` 157 951 o (21 closures), `solidified_controleVoletRoulants.h` 23 388 o : « LE .h COMPILE », rc=0
- [x] `banc_boot.py` et `banc_demarrage.py` verts (instantanés inchangés : tout est OFF) — preuve : BANC_BOOT: OK ; banc_demarrage VERT (rouge d'abord : `'vrFonctions' undeclared` dans web_sensor, corrigé par `import vrFonctions`)
- [x] Agent `relecteur-berry` sur le diff — preuve : 1 point à corriger (vecteur nul au réveil -> faux « fermé ») corrigé dans `vrFonctions.be::lireVecteur`, + refus de l'apprentissage en course (`::apprend`) ; banc 6b et 8 (témoin rouge avant), bancs boot/démarrage verts

## A7 — Documentation
- [x] `outils_docs/README.md` : paragraphe « Inclinaison d'une trappe (MPU6050) » — câblage I2C, bloc persist, calibrage par `ReglageVolets Inclinaison`, ne pas compiler `USE_MPU6050` en même temps — preuve : section « Inclinaison d'un volet ou d'une trappe (MPU6050) » (+ apprentissage, page web, banc), ligne ReglageVolets des commandes, `verifie_references_docs.py` : 0 défaut

## Améliorations restantes
- [ ] [projet] Essai réel sur la trappe du grenier : SDA/SCL déclarés dans le gabarit, câble court, calibrage, puis activation dans le persist du grenier (décision de l'utilisateur)
- [ ] [projet] Détection de blocage : moteur en marche, angle figé N secondes -> `ShutterStop` + log `erreur`
- [ ] [conversation] Commit sur demande de l'utilisateur (`/commite`)

## Vérification
De bout en bout sur PC : `banc_inclinaison.py` (capteur simulé, témoins), solidification + compilation du `.h`
des deux modules, bancs de démarrage inchangés. Sur carte : rien ne change tant que `inclinaison.activation`
vaut OFF ; l'essai réel est hors de ce plan (améliorations restantes).
