---
chantier: facade-garage-capteurs
titre: Façade du garage (P4 et carte du rideau) : fins de course animées, porte, chèvrefeuille, pergola et jasmin
objectif: Voir sur la façade de l'accueil du P4 et de la carte du rideau l'état réel des deux fins de course, dans un dessin fidèle au garage
statut: actif
cree: 2026-11-13
maj: 2026-11-13
---
# Façade du garage : fins de course et décor

## Contexte
Demande de l'utilisateur du 2026-11-13, maquette validée le même jour (copie de travail :
scratchpad `maquette_garage/maquette.html`, d'après sa photo du garage). Façade de l'accueil du P4 (192.168.0.43),
dessinée par `data/sd/js/volets.js` d'après `vrPages.be::facade` (SOLIDIFIÉ sur le P4).

Décisions :
- Fins de course sur le rail droit du rideau : « Capteur Ouverture » en haut, « Capteur Fermeture » en bas ; vert = contact
  fermé (état `ON` du persist, comme `controleRideau.be::positionCapteurs`), rouge = contact ouvert ; fondu 0,3 s ; petit levier
  qui bascule ; clignotement si l'état contredit la position du rideau plus de 6 s (options validées par l'utilisateur).
- État lu sur le P4 dans `modules.garage.environnement.interrupteurs.*.etat` (interrupteurs virtuels mis à jour par ModBus),
  par une nouvelle lecture `GET /volets?f=capteurs`, au rythme du rafraichissement de la façade. Pastilles grisées si la
  lecture échoue ou si l'état est inconnu. Le P4 ne sait pas dire si la carte du rideau est muette (pas d'horodatage par
  esclave) : la pastille garde le dernier état reçu.
- Décor déclaré dans le persist (`drivers.voletRoulants.facade.decor`), fins de course dans le bloc `facade` du volet
  (`finsDeCourse`) : sans ces clés, aucune autre façade ne change (greniers, carte du rideau).
- Carte du rideau `tasmota32s3-garage-rideau-garage-modbus` aussi (demande du 2026-11-13) : façade construite par
  `controleRideau.be` ; états de ses vrais interrupteurs (`modules.rideau`) ajoutés à la réponse de `/rideau?f=position`,
  déjà lue par la façade (une seule requête).
- Rien n'est écrit dans `data/` pendant la série de compilation en cours : travail dans une copie, recopie à la fin.
- Façade du rez-de-chaussée (`tasmota32s3-rdc-grenier`, demande du 2026-11-13, d'après une photo de la maison) : briques,
  toit en appentis vu de face (tuiles sombres, partie droite orange), arcs de briques, appui à plantes, porte blanche à vitrage,
  numéro, boîte aux lettres, compteur, applique, petite fenêtre, banc, marches ; sans voiture, poteau ni mur au-dessus du toit.
  Trappe du grenier gardée à sa place d'origine (au plancher, invisible sur la photo), SANS fins de course : indicateur
  de son inclinaison réelle (MPU6050, rapporteur et degrés). Maquette proposée avant tout remplacement.
- À l'issue de ce plan : revenir au plan `ecran-cave-vues-commandes` (A8 compilation, A9 essai sur carte) (demande du 2026-11-13).

## A1 — Code dans une copie de travail, bancs d'abord
- [x] Bancs rouges d'abord sur la copie : `test_volets.mjs` (décor dessiné seulement s'il est déclaré, pastilles et couleurs,
  incohérence), `banc_reglage_volets` (facade() porte decor et finsDeCourse, route ?f=capteurs) — preuve : sur l'origine,
  test_volets.mjs « KO window.Volets porte … etatsCapteurs », banc_reglage_volets « ECHEC ?f=capteurs sans finsDeCourse » (2026-11-13)
- [x] `volets.js` : décor (chèvrefeuille sur treillis, porte, pergola et jasmin), pastilles à levier, fondu, lecture
  périodique de `?f=capteurs`, clignotement d'incohérence, grisé — preuve : copie scratchpad, test_volets.mjs « 0 echec(s) sur 100 »
- [x] `vrPages.be` : facade() transmet decor et finsDeCourse ; route `?f=capteurs` ; module solidifiable (aucun état) — preuve :
  banc_reglage_volets « BANC_REGLAGE_VOLETS: OK », solidifie_et_compile_berry « LE .h COMPILE »
- [x] `controleRideau.be` : window.VOLETS transmet decor et finsDeCourse ; `/rideau?f=position` ajoute les capteurs ;
  banc `banc_rideau_facade` étendu — preuve : `banc_rideau_facade.py --sources <copie>` « VERT » (11 mutants rouges), origine « ROUGE »
- [x] Bancs VERTS sur la copie, témoins rouges ; sonde Chrome `test_volets_chrome.py` verte ; rendu vu en navigateur — preuve :
  sonde « VERT » sur la copie, « ROUGE » sur l'origine ; captures facade_p4_decor_capteurs.png, facade_rideau_capteurs.png

## A1b — Façade du rez-de-chaussée (maison)
- [x] Maquette validée par l'utilisateur (scratchpad `maquette_maison/maquette.html`) — preuve : « OK je valide l'image » (2026-11-13), caméra comprise
- [x] Décor de la maison dans `volets.js` (déclaré par `decor` du persist du RDC), indicateur d'inclinaison de la trappe
  (angle lu comme aujourd'hui par `data-angle`), bancs étendus, témoins rouges — preuve : copie scratchpad, sonde « VERT »
  (scénario maison, caméra comprise), témoin « ROUGE : 13 echec(s) », capture facade_maison_camera.png
- [ ] Caméra de façade sur le relais CH7 (choix de l'utilisateur du 2026-11-13) : `modules.autres.relai1` du persist du RDC
  renommé « Caméra de façade » et activé ; voyant vert avec halo si allumée, gris sinon ; clic sur la caméra dessinée =
  allumer ou éteindre après confirmation (commande Power7, garde check_privileged_access) ; bancs — preuve : persist du RDC
  (relai1 « Caméra de façade », ON) et `tca9554.dat` (230 en 7e position, sinon Power7 n'existe pas) posés ; banc_reglage_volets
  groupe 17c « BANC_REGLAGE_VOLETS: OK » (mutant sans branche caméra : ECHEC (3)) ; sonde Chrome VERT (2026-11-13)

## A2 — Dans le dépôt, après la série de compilation
- [x] Recopie dans `data/` ; persists du P4, de la carte du rideau et du RDC : `decor` (et `finsDeCourse` pour le garage)
  posés par ancre de texte (accord de l'utilisateur) — preuve : git diff des 3 persists et de tca9554.dat, JSON valides,
  genere_schema_persist --valide 0 erreur (2026-11-13)
- [ ] `banc_demarrage`, bancs des volets, relecteurs (Berry, pages web) ; README (façade du garage)
- [x] README § « Visuel des volets » : comment chaque façade est paramétrée (clés du persist) et comment changer le relais
  ou les capteurs liés (clé, id, à recompiler ou à renvoyer seulement) (demande de l'utilisateur du 2026-11-13) — preuve :
  outils_docs/README.md § « Décor, fins de course et caméra : les clés du persist »
- [ ] Commit

## A3 — Sur la carte
- [ ] Compilation par la page Build : P4 (vrPages solidifié), carte du rideau, RDC, et les trois envs du plan
  `ecran-cave-vues-commandes` (écran de la cave, serveur de la cave, écran des débits) ; prévenir l'utilisateur avant
- [ ] Rideau fermé : capteur de fermeture vert ; ouvert : capteur d'ouverture vert ; sinon correspondance ON/OFF inversée à corriger
- [ ] Pastilles qui changent pendant une manœuvre ; clignotement si un capteur ne suit pas

## A4 — Retour au plan initial
- [ ] Reprendre le plan `ecran-cave-vues-commandes` (A8 compilation, A9 essai sur carte) : `/suivi suivre ecran-cave-vues-commandes`

## Améliorations restantes
- [ ] [projet] Horodatage du dernier contact par esclave ModBus, pour griser les pastilles quand la carte du rideau est muette

## Vérification
Bancs `outils_pc/test_volets.mjs`, `outils_pc/test_volets_chrome.py`, `berry/banc_reglage_volets.py`, `berry/banc_demarrage.py`.
