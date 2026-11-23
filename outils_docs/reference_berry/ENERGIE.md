# Page Énergie du différentiel

Tiré de `outils_docs/README.md` le 2026-11-23 (plan `binomes-berry`, A20). Aiguillage : `outils_docs/INDEX.md`.

## La page Énergie (page `/energie`, différentiel du bureau)

Bouton **Énergie** de l'accueil, page gardée par la carte elle-même, sans le Pi. En haut : puissance, courant, facteur
de puissance en cadran, fréquence (relus toutes les 10 s, mêmes précisions que l'accueil). Puis, en barres, les
consommations **d'aujourd'hui par heure**, **du mois par jour**, des **12 derniers mois**, chacune avec son total en kWh
(en Wh sous 1 kWh) et son coût ; enfin la courbe de puissance sur 24 h. En bas, en petit, l'endroit où régler le prix.

- **Calcul** : écart de `ENERGY.Total` à chaque changement d'heure locale ; l'heure en cours est ajoutée à l'affichage
  (le total du jour suit donc « Énergie aujourd'hui » de l'accueil, sauf heure non notée après une coupure). Un compteur
  qui baisse, ou un écart impossible (`EnergyTotal` rétabli à la main), n'est pas compté : log `erreur`.
- **Prix** : Configuration > « Tarifs de l'électricité » (`/energie?f=tarifs`) : liste des tarifs et, en petit dessous,
  le tarif en vigueur. On saisit une date d'effet, en € TTC par kWh, et **Base** (un prix) ou **HC/HP** (deux prix et les
  plages d'heures creuses, par exemple `22-6` ou `2-7,14-17`). Plages en heures entières : le compteur est noté une fois
  par heure, une heure compte en entier au tarif de son début. Chaque consommation garde le coût du tarif en vigueur à sa
  date et à son heure : un nouveau tarif ne touche jamais le passé. Même date = tarif remplacé. `/energie` alerte si
  aucun prix n'est saisi ou s'il a plus de 6 mois.
- **Fichiers de la carte**, dans `/energie/` : `etat.json` (une écriture par heure), `mois-AAAA-MM.json` (mois clos, 24
  au plus ; les plus anciens sont effacés si le FS passe sous 16 Ko libres), `prix.json`, `courbe.bin` (copie horaire de
  la courbe : une coupure en perd au plus 1 h).
- **Calibrage** : `diverses.energie.calibrage` du persist. Une minute après le démarrage, si les trois valeurs lues sont
  les défauts de la BL0942 (596 / 15187 / 251213), celles du persist sont rejouées ; sinon rien, un recalibrage manuel est
  respecté. Le compteur `Total` n'est PAS rétabli seul : avant un flash, le relever, puis `EnergyTotal <Wh>`.
- **Disposition pilotée par une description** (2026-11-08, palier 4 de l'atelier) : si `/json/energie_page.json` existe, la page
  se dessine d'après elle (`data/sd/js/energie.js`, `Energie.valide` puis `Energie.trace`) ; la carte la relaie sans jamais la
  parser (`/energie?f=description`, 404 si absente). **Repli** : description absente, au-delà de 4 096 octets, tronquée ou
  refusée par `Energie.valide` = la page d'avant, plus une ligne « Description ignorée : <motif> ». Un élément mal formé est
  ignoré seul, avec sa ligne. Un graphique « jour » sur un mois fixe dont l'archive a été purgée reste vide (« archive
  effacée ») sans arrêter la page ; un champ absent du bloc ENERGY donne une tuile « -- ». Routes de lecture ajoutées :
  `f=description`, `f=mois&m=AAAA-MM` (JSON `{"d","de"}`, 404 si pas d'archive, 400 si mois illisible) et `f=direct` élargi
  (puissance, courant, facteur, fréquence et les autres champs ENERGY sous leur nom Tasmota). Comptage et stockage inchangés.
  La description s'écrit par l'atelier (voir « Atelier des graphiques > Destination Énergie »), pas à la main.
- **Code** : `data/fs/energieFonctions.be`, `data/fs/controleEnergie.be`, `data/sd/{html,css,js}/energie.*`, sur le seul
  différentiel (liste `page_energie` de `[berry_commun]`, exclue des autres envs). Bancs :
  `outils_docs/scripts_python/berry/banc_energie.py` (page d'avant), `banc_energie_routes.py` (routes de lecture),
  `banc_energie_description.py` (page pilotée par sa description, rendu Chrome) et
  `outils_pc/test_energie_rendu.mjs` (validation JS = Python). Conception :
  `docs/superpowers/specs/2026-10-31-page-energie-differentiel-design.md`.
- **Poser la page sur une autre carte** (au 2026-11-09 seul le différentiel s'en servait ; les projecteurs du jardin et du barbecue l'ont depuis, avec leur calibrage BL0942). Le module ne lit que le
  bloc `ENERGY` du JSON SENSOR : il vaut pour tout capteur d'énergie MONOPHASÉ, à une seule voie. Un compteur à plusieurs
  voies ou phases (`Total` en liste) n'est pas compté : la page s'affiche, avec un compteur illisible et rien d'écrit en
  flash (banc `banc_energie.be`, « plusieurs voies »). La protection du calibrage ne joue que pour une BL0942 ; avec une
  autre puce, ou sans `calibrage` au persist, elle ne fait rien. Pour une nouvelle carte, dans cet ordre :
  1. `platformio_tasmota_cenv.ini`, section de l'env : retirer `${berry_commun.page_energie}` de son `custom_files_exclude`
     (ou de celui de la base dont il hérite, en le redéfinissant) ; ajouter `data/fs/energieFonctions.be` et
     `data/fs/controleEnergie.be` à son `custom_berry_solidify`, comme l'env `tasmota32-bureau-interrupteur-energie`.
  2. `autoexec.be` de la carte : `demarrage.charge(["controleEnergie"], "diverses.energie")`, après `controleWeb`.
  3. `_persist.json` de la carte : `"energie": {"activation": "ON"}` sous `diverses` (plus `calibrage` pour une BL0942).
  4. `banc_demarrage.py` (instantané de la carte relu, seul écart attendu), puis compilation et envoi du firmware ET du
     FS par la page Build : le module est solidifié, un envoi du FS seul ne suffit pas.
  5. Sur la carte : bouton **Énergie** sur l'accueil, `/energie` affiche la puissance ; la première note horaire apparaît au
     changement d'heure suivant. Saisir un prix dans Configuration > « Tarifs de l'électricité ».
