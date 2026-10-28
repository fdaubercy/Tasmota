---
chantier: blocage-trappe-mpu6050
titre: Détection de blocage d'un volet par son inclinaison (MPU6050)
statut: clos
cree: 2026-10-28
maj: 2026-10-28
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

## Améliorations restantes
- [ ] [projet] Essai réel sur la trappe du grenier (avec le reste de l'inclinaison)
- [ ] [conversation] Commit sur demande de l'utilisateur
