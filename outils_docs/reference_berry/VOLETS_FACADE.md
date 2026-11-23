# Visuel des volets et réglage de leurs durées

Tiré de `outils_docs/README.md` le 2026-11-23 (plan `binomes-berry`, A20). Aiguillage : `outils_docs/INDEX.md`.

## Visuel des volets et réglage de leurs durées (cartes à volets)

Deux ajouts au driver des volets (`data/fs/controleVoletRoulants.be`), sur les cartes dont le persist décrit une façade : le grenier du RDC, le P4 du garage et le grenier du 2e étage. Le rideau du garage dessine aussi la porte, avec la position lue chez le P4 (§ « La façade du rideau du garage »). Spec : `docs/superpowers/specs/2026-11-11-visuel-volets-reglage-durees-design.md` ; plan : `tasks/plans/visuel-reglage-volets.md`. Maquettes : `outils_docs/volets_visuels/`.

### La façade sous les curseurs

Sur la page d'accueil, sous les curseurs des volets, un dessin de la façade (`data/sd/js/volets.js`, inséré par `data/fs/vrPages.be::accueil`). Aucun pourcentage d'ouverture n'est affiché (retiré le 2026-11-15, sur toutes les façades). Le dessin ne commande rien : les curseurs et boutons natifs restent les seules commandes.

- Il lit la valeur du curseur `s27<n>` que Tasmota met déjà à jour à chaque rafraîchissement : aucune requête de plus. Sur un volet `inverse 1`, le curseur affiche l'inverse du dessin (porte ouverte : curseur à 0, dessin à 100 %). C'est voulu, le dessin montre la position physique.
- Il rejoint la dernière valeur lue à la vitesse du volet (`100 / tempsMontee` %/s en montée, `100 / tempsDescente` en descente), sans la dépasser. Il a donc au plus un rafraîchissement de retard et ne montre jamais une position non atteinte.
- Trappe avec MPU6050 actif : le dessin suit l'angle mesuré (balise `data-vi` de la ligne d'inclinaison, `vrFonctions.be::ligneWebInclinaison`), converti comme `positionReelle`. Capteur muet : retour au curseur. Un blocage ou un sens inverse détecté passe l'ouverture en rouge avec « bloqué » ou « sens inverse ».
- Types d'ouverture : `fenetre`, `porte`, `garage` (tablier à lames), `trappe` (panneau qui se baisse), `trappeEchelle` (panneau, puis échelle posée sur un escalier fixe).

### Décrire la façade dans le persist

Dans le bloc `drivers.voletRoulants` :

```json
"facade": { "activation": "ON", "toit": "deuxPans" },
...
"VR1": { "activation": "ON", "inverse": 0, "facade": { "type": "fenetre", "place": 1 }, ... }
```

- `facade.activation` : `"ON"` pour dessiner. `"OFF"` ou bloc absent : rien n'est dessiné, rien n'est envoyé à la page, et le module `vrPages` n'est pas chargé.
- `facade.toit` : `deuxPans`, `unPan` ou `aucun` (plafond vu de face, sans maison).
- `facade` de chaque VR : `type` (`fenetre`, `porte`, `garage`, `trappe`, `trappeEchelle`) et `place`, rang de gauche à droite. Un VR actif sans cette clé n'est pas dessiné.
- Modèle : `outils_docs/schemas/modele_persist.json`. Exemples : `data/rdc/tasmota32s3-grenier/_persist.json`, `data/garage/tasmota32p4-serveur-modbus/_persist.json`, `data/etage2/tasmota32s3-grenier/_persist.json`.

Les fichiers de la page ne partent que sur les cartes à volets : liste `volets_pages` de `[berry_commun]` dans `platformio_tasmota_cenv.ini` (`vrReglage.be`, `vrPages.be`, `volets.js`, `reglageVolets.html`, `.js`, `.css`), exclue des autres envs. `vrFonctions`, `vrReglage` et `vrPages` sont solidifiés sur les envs à façade : firmware à recompiler par la page Build.

### Décor, fins de course et caméra : les clés du persist (2026-11-13)

Plan `tasks/plans/facade-garage-capteurs.md`. Toutes ces clés sont facultatives : sans elles, le dessin reste celui d'avant.

| Clé | Où | Rôle |
|---|---|---|
| `facade.decor` | bloc du driver | Liste. Garage (toit `unPan`) : `chevrefeuille`, `porte`, `pergola`. Rez-de-chaussée : `maison` (toit, briques, porte d'entrée, boîte aux lettres... ; `toit` est alors ignoré). `finition` : finition de la façade et **nuit** (voile selon le soleil, bouton Auto, Jour, Nuit) ; avec `maison` elle ne pose que le voile, sans cônes ni forêt. |
| `facade.camera` | bloc du driver | `{"module": "<module>", "id": <id du relais>}` : caméra dessinée sur la maison, avec son voyant. Le relais doit être actif dans son module. |
| `facade.lampe` | bloc du driver | `{"module": "<module>", "id": <id du relais>}` : projecteur (lanterne sous le toit, côté pergola) de la façade du garage (toit `unPan`), même mécanisme que la caméra (voyant jaune, clic puis `POST /volets` `action=lampe`). P4 du garage : relais 4 « Caméra de garage » et relais 5 « Projecteur de Garage » (`ModBus_Conn16channel1`). |
| `facade.finsDeCourse` | bloc `facade` d'un VR de type `garage` | `{"module": "<module>", "ouverture": <id>, "fermeture": <id>}` : ids des deux interrupteurs dans `modules.<module>.environnement.interrupteurs`. |
| `facade.place` | bloc `facade` de chaque VR | Avec `maison`, l'abscisse vient du type (fenêtre, trappe, porte) ; `place` ne fixe plus que l'ordre. |

Le rythme de lecture n'est pas une clé du persist : c'est le `WebRefresh` de Tasmota.

Réglages actuels : P4 du garage, `decor: ["chevrefeuille", "porte", "pergola", "finition"]`, `camera: {"module": "garage", "id": 4}`, `lampe: {"module": "garage", "id": 5}` et `finsDeCourse` (ouverture = interrupteur 2, fermeture = interrupteur 1) ; carte du rideau, `decor: ["chevrefeuille", "porte", "finition"]` (garage et porte seuls, avec la nuit, sans portail ni pergola) et `finsDeCourse` ; grenier du RDC, `decor: ["maison", "finition"]` et `camera: {"module": "autres", "id": 7}` (relais CH7 « Caméra de façade »).

**Fins de course** (P4 et carte du rideau). Deux pastilles sur le rail droit du rideau : ouverture en haut, fermeture en bas. Vert : contact fermé (état `ON`) ; rouge : contact ouvert ; gris : état inconnu ou lecture en échec. Un petit levier bascule avec l'état (fondu de 0,3 s). Une pastille clignote si la position du rideau la contredit plus de 6 s.
- Sur le P4, l'état vient des interrupteurs virtuels tenus à jour par ModBus (`modules.garage`), lus par `GET /volets?f=capteurs`. Le P4 ne sait pas si la carte du rideau est muette : la pastille garde le dernier état reçu.
- Sur la carte du rideau, il est lu sur la broche de l'interrupteur (`modules.rideau`, SwitchMode 1 ou 2), sinon dans sa clé `etat`, et arrive dans la réponse de `/rideau?f=position`.
- Changer de capteur : mettre dans `ouverture` ou `fermeture` l'`id` de l'interrupteur (pas son nom). Pastilles inversées (rideau fermé et pastille du haut verte) : échanger les deux ids.

**Caméra de façade** (grenier du RDC). Voyant vert avec halo si le relais est allumé, gris sinon, relu au rythme du rafraîchissement. Un clic sur la caméra demande confirmation puis l'allume ou l'éteint (`POST /volets`, `action=camera`, réservé à un client autorisé par `webserver.check_privileged_access`).
- Le relais d'`id` N est le `Power<N>` de Tasmota. Sur le grenier du RDC, le relais doit aussi être déclaré dans `tca9554.dat` : `230` (Relay7) en 7e position.
- Changer de relais : modifier `facade.camera.id` (et `module`), activer ce relais dans son module, et le déclarer dans `tca9554.dat` s'il passe par l'expandeur.
- Avec `"afficheWeb": "ON"` sur le relais, l'accueil garde aussi le bouton natif de Tasmota.

**Trappe du RDC**. Pas de fins de course : un rapporteur à droite de la trappe montre l'angle mesuré par le MPU6050 (0° fermée, 90° verticale), lu dans la ligne d'inclinaison de l'accueil. Tant que `capteursPosition.inclinaison.activation` vaut `"OFF"`, il affiche « ?° ».

**Nuit** (plan `tasks/plans/facade-garage-portail-commande.md`, A5). Le soleil est lu par `Status 7` toutes les 5 min. Le voile naît et finit par un fondu d'environ 35 min centré sur le coucher et le lever, plus sombre au milieu de la nuit ; réglage commun à toutes les façades par la constante `NUIT` de `volets.js` (`base`, `profonde`, `teinte`). Le bouton Auto, Jour, Nuit est retenu par le navigateur (`localStorage`). Les cônes de la caméra et de la lampe n'apparaissent que la nuit, jusqu'au sol.

**Portail de jardin** (P4 du garage, A3 et A4). Deux ouvertures de type `portail1` (un vantail, le droit) et `portail2` (deux vantaux), portées par deux Shutters en mode 3 sur le P4 (VR2 et VR3). Chaque Shutter pilote un relais virtuel, qui renvoie par ModBus à un relais réel de l'esclave 4 (`TasmotaSlaveModBus3`, id 4) ; ce relais fait une impulsion (clé `impulsion` du VR, en dixièmes de seconde, 5 par défaut, 10 pour 1 s) vers la carte électronique du portail. En « 2 vantaux », le vantail droit part 5 s avant le gauche (constante `PORTAIL_DECALAGE`). Le capteur de fermeture (contact à la masse = fermé) suit le vantail gauche, et un feu orange clignote pendant le mouvement. Un clic sur le portail demande confirmation puis commande.

**Esclave 4 : page du portail seul** (plan `facade-garage-portail-commande`, A8, en cours). Le contact de fermeture est câblé sur l'esclave 4 (interrupteur1, GPIO 47) et remonte au P4 par une entrée virtuelle `ModBus_TasmotaSlaveModBus3`, comme les fins de course du rideau. Sans capteur d'ouverture : contact fermé = portail fermé, sinon portail grand ouvert. Hostname et client `PORTAIL-JARDIN`, topic `jardin/portail`, env `tasmota32s3-garage-portail-jardin-modbus` (inchangés). Le module de la page (`controlePortail.be`, dans le dossier de l'env) ne part que sur cet env ; un env ESP32 de remplacement, `tasmota32-garage-portail-jardin-modbus` (carte Relay x4 sans PSRAM), porte la même identité et son propre `controlePortail.be` : ne jamais faire tourner les deux cartes ensemble.

**Que faut-il renvoyer ?**
- Une clé du persist ou `tca9554.dat` : envoyer le FS de la carte (onglet « Fichiers » de la page Build), puis redémarrer.
- `volets.js` seul : envoyer le FS, sans recompiler.
- `vrPages.be` ou `controleRideau.be` : solidifiés, firmware à recompiler par la page Build (P4 du garage, grenier du RDC, grenier du 2e étage, carte du rideau).
- L'ordre ne casse rien : un ancien firmware ignore les nouvelles clés, un ancien `volets.js` ignore celles qu'il ne connaît pas.

### Régler les durées pas à pas

Page « Configuration » -> bouton **Réglage des volets** (`/volets`, `data/fs/vrReglage.be` et `vrPages.be::route`). Les explications sont aussi sur la page.

1. Préparation : amener le volet en butée basse (fermé) par une commande habituelle. Un seul volet à la fois ; refus si un réglage est déjà en cours, si le volet roule, s'il vient de s'arrêter (moins de `ShutterMotorStop` + 100 ms), ou si un autre volet de la carte roule (le réglage réinitialise tous les volets ; sauf la porte du garage).
2. Choisir le volet, cliquer « Régler les durées ». La carte suspend les boutons natifs de ce volet (les autres gardent les leurs) et autorise une course de 130 s.
3. Un appui : le volet monte, le chronomètre part. Un appui à l'arrivée en haut : arrêt, `tempsMontee` retenu. Un appui : il descend. Un appui à l'arrivée en bas : arrêt, `tempsDescente` retenu.
4. La carte écrit les deux durées (secondes entières) dans son persist, remet les durées et boutons normaux, recale la position (ouvert après la montée, fermé après la descente) et affiche le résultat.

Un appui peut venir du bouton unique, de l'un ou l'autre des deux boutons du volet, ou du bouton « Étape suivante » de la page. Le sens est imposé par l'étape, jamais par la fonction du bouton. Un second appui moins de 1 s après le premier est ignoré. La page demande à chaque départ si le volet va dans le bon sens ; sinon, « Annuler ». Le bouton envoie l'étape qu'il affiche : si l'étape a changé entre-temps (appui physique), la carte répond 409 et la page se resynchronise.

- Annuler : le moteur est arrêté s'il tourne, rien n'est écrit, durées et boutons d'avant remis.
- Délai : 120 s sans appui, même sortie sans rien écrire. Une mesure de moins de 2 s est refusée, de même qu'une arrivée alors que le volet n'a pas bougé (aucun départ rapporté par Tasmota). Si l'écriture du persist échoue, les durées d'avant sont gardées.
- Fins de course et MPU6050 (sauf la porte du garage, en chronomètre : ses fins de course recalent comme d'habitude) : leur recalage et l'arrêt en butée sont coupés pendant la mesure. Le MPU6050 reste garde-fou : un blocage ou un sens inverse coupe le moteur, le réglage s'arrête sans rien écrire et la page donne la cause. S'il a mesuré la course, sa durée s'affiche à côté de la vôtre ; la vôtre est écrite.
- Porte du garage (`mode` 3) : chronomètre seul. La carte ne commande rien. Porte fermée, lancer la porte comme d'habitude (télécommande, curseur) et cliquer « Départ », puis « Arrivée » quand elle est en haut ; même chose pour la descente.
- Un redémarrage pendant le mode le perd sans rien écrire.

### La façade du rideau du garage

Le rideau ne fait pas tourner le driver des volets : c'est le P4 qui pilote la porte. Sa page d'accueil dessine pourtant la même porte (2026-11-12), par `data/garage/tasmota32s3-rideau-garage-modbus/controleRideau.be` et le même `volets.js` :

- Description : la clé `facade` du bloc `drivers.voletRoulants` du persist du rideau et de son VR, comme sur le P4. Ce bloc ne sert qu'à la façade (durées et `capteursPosition`) : il doit suivre celui du P4.
- Position : la page interroge `GET /rideau?f=position&id=1` à chaque rafraichissement (`WebRefresh`), et la carte demande alors `Status 10` au P4 (`serveur.rangeExtender.ipMaitre`). Aucune requête sans page ouverte.
- P4 muet : position tirée des fins de course de la carte (état des interrupteurs désignés par `capteursPosition`, celui que le P4 reçoit par ModBus) : 100 % en butée haute, 0 % en butée basse, « ? » entre les deux. Le dessin est grisé avec « (maître muet) », et une ligne `CONTROLE_RIDEAU_ERREUR` est écrite au passage en muet (une seule, puis une ligne info au retour).
- Pas de page de réglage sur le rideau : les durées se règlent sur le P4.

### Recopier les durées dans le dépôt

Les durées sont écrites dans le persist **de la carte**. Un flash série ou un envoi du FS remet celles du dépôt. La page affiche, en fin de réglage, les deux lignes à recopier dans `data/<lieu>/<carte>/_persist.json` (`drivers.voletRoulants.environnement.VRs.<VR>.tempsMontee` et `tempsDescente`).

### Bancs

- Berry : `python outils_docs/scripts_python/berry/banc_reglage_volets.py` (déroulé complet, annulation, délai, bouton unique en `toggle`, porte en chronomètre ; code 0 = vert) et `python outils_docs/scripts_python/berry/banc_inclinaison.py`.
- Dessin : `node outils_docs/scripts_python/outils_pc/test_volets.mjs` (fonctions pures), puis les sondes Chrome avec le Python de PlatformIO :
  `%USERPROFILE%\.platformio\penv\Scripts\python.exe outils_docs/scripts_python/outils_pc/test_volets_chrome.py` et `.../test_reglage_volets_chrome.py`. Elles arrêtent leur Chrome en fin d'usage ; jamais pendant un build.
- Rideau du garage : `python outils_docs/scripts_python/berry/banc_rideau_facade.py` (route, P4 muet, fins de course ; mutants) ; scénario « rideau » de `test_volets_chrome.py`.
- Démarrage des cartes à façade : `python outils_docs/scripts_python/berry/banc_demarrage.py`.
- Ces bancs ne remplacent pas l'essai sur carte (vrai Shutter, vrais boutons, moteur).

<hr></hr>
