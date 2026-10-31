---
chantier: ruban-cuve
titre: Ruban WS2812 de la cuve en AUTO/MANUEL et carte cuve v0.2
objectif: Piloter le ruban WS2812 de la cuve en AUTO/MANUEL (bouton et ModBus) et préparer la carte cuve v0.2
statut: actif
cree: 2026-10-18
maj: 2026-10-31
---
# Ruban WS2812 de la cuve en AUTO/MANUEL et carte cuve v0.2

## Contexte
Chantier en 4 lots, mené du 2026-10-13 au 2026-10-15 :
- le ruban WS2812 de la cuve passe en AUTO (suit les niveaux) ou en MANUEL (couleur choisie au bouton) ;
- il se pilote aussi depuis le maître P4 par ModBus : registre 1376, lecture de 5 registres
  `[h, s, bri, animation, mode]` (mode 0 = AUTO, n = minutes de MANUEL, 0xFFFF = MANUEL sans fin),
  écriture `[04, 0]` = couleur suivante, `[05, 0]` = retour AUTO, commande `RubanEsclave<n> etat|auto|suivante` ;
- la carte porteuse de la cuve passe en v0.2 (filtre du bouton GPIO7, placement corrigé).
`ledsFonctions` n'est pas solidifié et n'est pas chargé sur le P4 (garde `rubanGere()`).
Le flash de la nuit du 14 au 15/10 (cuve bloquée après la ligne `HDW:`) est sorti du chantier :
la cuve refonctionne et sa grille ModBus a été validée le 17/10 (plan `modbus-garage`).

## A1 — Lot 1 : module LED renommé
- [x] Module LED RGB renommé `ledsFonctions` / `controleLeds` — preuve : commit 34a56119c
- [x] Bouton web du Relai 2 réaffiché sur le maître P4 — preuve : commit d883d0e5a

## A2 — Lot 2 : ruban en AUTO/MANUEL avec bouton poussoir sur la cuve
- [x] Mode AUTO/MANUEL, palette, bouton, `ReglageLeds`, bloc persist `drivers.leds.environnement.leds.ruban` — preuve : commit 113e3b4c2
- [x] Le bouton du ruban inscrit `eviteResetBTN ON` dans le persist — preuve : commit 6c7624020
- [x] Banc Berry `banc_leds` (ruban, bouton, LED du dev-kit) — preuve : commit 2cbb2bc15
- [ ] Bouton physique de la cuve (GPIO7) essayé sur la carte : appui court = allume/éteint, appui long = couleur suivante (MANUEL), double appui = retour AUTO

## A3 — Lot 3 : pilotage du ruban depuis le maître P4
- [x] Registre 1376 sur 5 registres, codes 0x04 et 0x05, `RubanEsclave`, bouton `rubanMaitre<n>`, curseurs de la page web — preuve : commit eefeb463b
- [x] Banc ModBus, section 29 — preuve : commit eefeb463b (banc_test_modbus vert)
- [x] Retour en AUTO observé sur la carte (relevé mode 0, puis `RubanEsclave1` = AUTO) — preuve : reprise-chantier-modbus-grenier.md:193, grille du 2026-10-17
- [ ] « Couleur suivante » depuis le P4 observée sur la carte (`RubanEsclave1 suivante`, puis relevé du mode MANUEL)
- [ ] Bouton physique du maître (`bouton2`, GPIO22, appui long 15) essayé sur la carte

## A4 — Lot 4 : carte cuve v0.2
- [x] Filtre du bouton : R14 10 kΩ vers 3,3 V, R15 1 kΩ en série, C9 100 nF sur GPIO7 — preuve : commit 0727f1749
- [x] Les 9 erreurs de placement de la v0.1 corrigées — preuve : commit 0727f1749
- [x] Points 1 à 4 de la relecture : R15, C3 sous U1, F1 hors du trajet USB + modèle 3D, R11 180 Ω / R12 560 Ω — preuve : commit 0727f1749
- [x] Routage : DRC parité 0, 0 non connecté, une seule composante de masse — preuve : commit 0727f1749
- [x] Skill pcb-tasmota : `route_net`, `vias_pres`, `connexite_masse.py`, pièges 55-58 — preuve : commit e8eaa1dbb

## A6 — Symbole du mode sur la page et solidification sur les S3
- [x] Ligne « Ruban LED » remplacée par un symbole après le curseur de luminosité (⟳ AUTO, ✋ + minutes MANUEL, clic = retour AUTO) — preuve : banc_leds vert (3 vérifications ajoutées), data/fs/ledsFonctions.be:522
- [x] `ledsFonctions` et `controleLeds` solidifiables — preuve : solidifie_et_compile_berry.py rc 0 pour les deux, contrôle du piège 12 vide
- [x] Liste partagée `berry_commun.leds`, reprise par la cuve, la cave S3, le grenier, le S3 serveur-modbus et le rideau — preuve : ProjectConfig résout les 2 modules dans les 5 envs, CARTE_MODULES_BERRY.md régénérée
- [x] Symbole placé DANS la cellule du curseur (une 3e cellule élargissait la page à toute la fenêtre) — preuve : capture Chrome de la vraie page de la cuve, largeur 1168 px avant, 350 px après (= sans symbole), « ✋ 15 » affiché ; banc_leds vert
- [x] Firmware de la cuve recompilé et téléversé : symbole visible sur la page, clic en MANUEL = retour AUTO — preuve : vu par l'utilisateur le 2026-10-31 (✋ 29) ; relevé par le maître avant le clic MANUEL, reste 29 min, après le clic `ledsFonctions.mode` = AUTO et ligne `ldM` data-m='AUTO' ; modules absents du FS (solidifiés)
- [x] Commit — preuve : commit 91bbae69a

## A5 — Avant de commander la carte
- [x] Identifier le module RS485 réel et adapter son empreinte — preuve : XY-017 confirmé par l'utilisateur le 2026-10-31 ; empreinte `Modules_Tasmota:Module_RS485_Auto_XY-017` debout sous le DevKit, bornier A/B au-dessus du coin bas droit libéré (voies décalées de 10,16 mm), DRC 0
- [x] Corrections de la relecture du 2026-10-31 (v0.3) : voies entrée/0V/+12, JP1 supprimé (RS485 en 3,3 V fixe), bornier J15 du bouton, R16 10 k de rappel sur l'entrée du 74AHCT125, C1 35 V, type de voie sérigraphié — preuve : carte routée, DRC parité 0 / 0 non connecté / 0 violation, ERC 0 erreur, masse en 1 groupe (connexite_masse.py), bilan 2,25 A sans alerte
- [ ] Tension laissée au capteur de niveau (~11 V, ~8 V sur une voie 4-20 mA) vérifiée avec sa référence et sa voie — question à reposer à l'utilisateur
- [ ] Mesurer le DevKit ESP32-S3 et les modules (entraxes des broches)
- [ ] Vérifier la hauteur des fusibles MF-R dans le boîtier
- [ ] Relecture finale par l'agent `relecteur-pcb`
- [ ] Export de fabrication (Gerber, BOM, CPL pour JLCPCB)

## Améliorations restantes
- [ ] [projet] Cuve : PSRAM détectée un démarrage sur deux le 2026-10-14 (même firmware) ; cause non établie (câble, alimentation ou module). La surveiller au prochain démarrage par le pont série.
- [ ] [projet] Cuve : cause du blocage après `HDW:` à la suite du flash du 2026-10-15 non établie.

## Vérification
Étapes sur carte : une ligne de log horodatée (pont série :7000, syslog :7200) ou un relevé `RubanEsclave<n> etat`.
Étapes de code : un commit et le banc concerné (`banc_leds`, `banc_test_modbus`, skill `bancs`).
Étapes PCB : DRC et ERC de kicad-cli, `connexite_masse.py`, relecture `relecteur-pcb`.
Ni commit ni push sans demande ; aucun réglage sur une carte sans accord.
