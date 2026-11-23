# Atelier des graphiques

Tiré de `outils_docs/README.md` le 2026-11-23 (plan `binomes-berry`, A20). Aiguillage : `outils_docs/INDEX.md`.

## Atelier des graphiques (page web)

Une page qui prépare des **pages de graphiques** pour une carte S3/P4 : on choisit la carte, ses séries (courbes de
l'historique, valeurs du JSON SENSOR, valeurs calculées), un style conseillé, et l'aperçu est tracé par **le vrai moteur
de la carte** avec les vraies valeurs. « Écrire dans le dépôt » pose ensuite la description et ce qu'il faut pour que la
page apparaisse sur la carte. C'est le palier 1 (page dédiée avec bouton d'accueil), complété le 2026-11-05 par la
destination « Graphiques » et le bouton « Téléverser » ; modèle B de
`outils_docs/atelier_graphiques/` (trois colonnes) avec la grille du modèle C.
Conception : [spec](../../docs/superpowers/specs/2026-11-03-atelier-graphiques-design.md) et
[spec destinations](../../docs/superpowers/specs/2026-11-04-atelier-destinations-televersement-design.md) ; plans :
`tasks/plans/atelier-graphiques.md`, `tasks/plans/atelier-destinations.md`.

La liste des cartes S3/P4 est groupée par lieu de la maison (`outils_pc/lieux.py`) ; la carte du différentiel y est
rangée en Bureau.

### Lancer la page

- **Tuile de l'annuaire** (http://127.0.0.1:7600), groupe « Ateliers » : « Atelier des graphiques ». Rien n'est écrit
  avant « Écrire dans le dépôt » : on peut l'arrêter à tout moment.
- **Tâche VS Code** : `Ctrl+Maj+P` > Run Task > « Outil : atelier des graphiques (http://127.0.0.1:7950) ».
- **Ligne de commande** : `python outils_docs/scripts_python/outils_pc/atelier_graphiques_web.py` (`--http 7950`,
  `--local`, `--sans-navigateur`).
- **Cible PlatformIO** « Atelier des graphiques (page web) » dans *Project Tasks > <env> > Custom* : démarre la page
  détachée puis rend la main. Comme toute cible, **jamais pendant un build**.

Port **7950**. Depuis un autre appareil : lien à jeton de la console, comme les autres outils (`acces_web.py`).
Le commutateur « Mode sombre » règle la page ; la case « thème sombre » de l'aperçu est indépendante (thème de la carte).

### Utilisation

1. **Carte** : liste des cartes S3/P4 du cenv. Séries et valeurs viennent de la carte **en ligne** ; muette ou hors
   ligne, la page se rabat sur le persist du dépôt et sur des **valeurs simulées**, et le dit.
2. **Séries** : par graphique, de 1 à 12, chacune une chaîne (chemin du SENSOR, ou `calc:<nom>` d'une valeur calculée) ou
   un objet `{chemin, libelle, unite, couleur}`. Un même chemin n'apparaît qu'une fois dans un graphique.
3. **Conseil** : l'intention (texte) croisée avec la nature des séries donne 3 à 5 styles classés avec leur raison.
   Styles : courbe, aire, escalier, barres, barres-empilees, barres-periode, deux-axes, lies, cadran, anneau, chaleur,
   nuage, radar, liquide, demi-cercle.
4. **Réglages** : titre, libellés, unités, couleurs, min / max, zones de couleur, période (direct, jour, mois), cadence (sans effet sous `/graphiques` : la cadence y est celle de la liste « Direct » de la page),
   largeur (demi ou pleine) et hauteur ; l'aperçu montre l'effet de chaque réglage. Jusqu'à 8 pages, 8 graphiques par
   page ; la description compacte tient en 8 Ko.
5. **Diff** de chaque fichier touché, puis **écriture** atomique (copie horodatée).

### Ce qui est écrit

- `data/<lieu>/<carte>/pages_graphiques.json` : la description (validée par `atelier_graphiques_description.py::valide`) ;
- l'`autoexec.be` de la carte : la ligne `demarrage.charge(["pagesGraphiques"])` ;
- le cenv : la liste `pages_graphiques` de `[berry_commun]` est exclue du FS de **tous** les envs sans page ; une carte
  qui reçoit sa première page la voit levée pour elle seule. La case « Solidifier » ajoute les 2 `.be` du moteur au
  `custom_berry_solidify` (firmware à recompiler).

Refusé pendant un build, et si l'empreinte a changé depuis « Voir le diff ». Retirer la dernière page remet le dépôt
dans son état exclu, octet pour octet. En ligne de commande : `atelier_graphiques_ecriture.py --exclusions [--ecrit]`.
Après écriture, lancer `berry/banc_demarrage.py` (jamais `--enregistre`).

### Côté carte

Le moteur est `data/fs/pagesGraphiques.be` (+ `pagesGraphiquesValidation.be`, même verdict que le validateur Python) ;
route `/pages?p=<id>` (page), `?f=valeurs&c=` (valeurs), `?f=sources`, `?f=liquidfill.js.gz`. Gabarits dans `data/sd`
(`html/pages_graphiques.html`, `css/pages_graphiques.css`, `js/pages_graphiques.js` et `pages_graphiques_formule.js`).
Au démarrage seul l'index des pages reste en RAM ; les graphiques ne sont relus qu'à l'ouverture d'une page.
`?f=valeurs` applique les mêmes filtres que le Direct de `/graphiques` (`historiqueFonctions.ajouteFiltre`) : une mesure en
erreur ou un esclave muet donne `null`, pas un faux 0.

### Le menu « Page » : où poser le graphique

Le menu **Page** de la colonne de réglages propose, dans cet ordre :

- les **pages dédiées** déjà décrites pour la carte (`/pages?p=<id>`) ;
- **« Graphiques (/graphiques) »**, la page composable existante de la carte, **seulement si l'historique de la carte
  est actif** (`diverses.historique.activation` = ON dans son persist du dépôt) : sans historique, `/graphiques`
  n'existe pas sur elle ;
- **« Autre… (nouvelle page) »**, qui remplace l'ancien bouton « + Page » : crée une page dédiée (champs « Adresse » et
  « Titre page », mêmes règles).

Avec la destination « Graphiques », les champs sans objet sont **masqués** : « Adresse », « Titre page », « Accès » et la
case « Solidifier » (ainsi que « Retirer la page »). Les autres réglages restent. Le graphique est écrit dans la clé
`graphiques` de `data/<lieu>/<carte>/graphiques.json` avec `"moteur": "pages"` : `/graphiques` le valide et le trace avec
le même moteur que les pages dédiées, donc **tous les styles de l'atelier** y sont disponibles, pas seulement ses
4 types d'origine. Les autres clés du fichier (`affichage`, `groupes`...) et les graphiques déjà là ne sont pas touchés ;
8 graphiques au plus, corps compact de 8 Ko au plus. Une **réécriture** du même graphique le **remplace** (la page retient
son rang et vérifie qu'il n'a pas changé entre-temps) : jamais de doublon.

**Tant que la composition ne contient que des graphiques de l'atelier, `/graphiques` garde ses graphiques automatiques**
(« Mesures » et un par groupe) et y ajoute ceux de l'atelier (décision du 2026-11-07). Une tuile de l'atelier ne retire pas
sa série de « Mesures ». « Enregistrer » depuis le mode édition rend tout explicite : la composition ne contient alors plus
seulement des graphiques de l'atelier, et ce qui a été retiré reste retiré. Retirer tous les graphiques automatiques demande
donc d'en garder au moins un qui ne vient pas de l'atelier.

**Composition de la carte comparée au dépôt.** La composition a pu être modifiée **sur la carte** (mode édition de
`/graphiques`) depuis le dernier envoi. Avant d'écrire, l'atelier relit `/json/graphiques.json` sur la carte en ligne
(lecture seule, `atelier_graphiques_graphiques.py::etat_carte`) et compare les deux JSON normalisés :

- **identique** : une mention discrète, rien à décider ;
- **différente** : bandeau, diff dépôt vers carte, et un choix obligatoire (rien n'est écrit et « Écrire » reste grisé
  tant qu'il n'est pas fait) :
  - **« Partir de la version de la carte »** : ses graphiques sont recopiés dans le dépôt avant d'y ajouter le
    nouveau. Ce que ce choix fait perdre : **les graphiques écrits dans le dépôt et pas encore téléversés**. Indisponible
    (avec le motif) si la composition de la carte n'est pas valide pour le validateur du dépôt ;
  - **« Garder celle du dépôt »** : ce que ce choix fait perdre : **les changements faits sur la carte**, écrasés à
    l'envoi ;
- **non vérifiée** (carte hors ligne, muette, ou fichier absent chez elle) : bandeau « Composition de la carte non
  vérifiée » avec son motif. L'écriture reste possible, mais sans garantie sur ce que la carte porte.

Une composition de la carte modifiée entre « Voir le diff » et l'écriture fait refuser l'écriture (empreinte périmée).

Deux limites propres à la destination « Graphiques » :

- le style **`liquide`** est **refusé** sur une carte dont le FS n'embarque pas `echarts-liquidfill.min.js.gz`
  (exclu de son env) ; la page le dit à l'écriture ;
- le réglage **`largeur: demi`** reste **sans effet** sur `/graphiques` (décision : c'est `/graphiques` qui fait la mise en
  page de ses tuiles). Sur la carte, en **mode édition**, un graphique de l'atelier se **déplace et se retire**, mais ses
  réglages (série, style, titre...) ne s'éditent **que dans l'atelier** ; la tuile le dit.

### Envoyer sur la carte : le bouton « Téléverser »

Après une **écriture réussie** dans le dépôt, le bouton **« Téléverser »** apparaît à côté de « Écrire dans le dépôt »
(il disparaît à la modification suivante, et se perd au rechargement de la page). Un clic ouvre la page Build dans un
nouvel onglet : `http://127.0.0.1:7700/?env=<env>&depuis=atelier&fichiers=<liste>&redemarrer=<0|1>`. La liste, calculée
par `atelier_graphiques_televerse.py::plan`, contient les chemins **tels qu'ils sont dans l'image du FS** :

- toujours le fichier de description écrit (`pages_graphiques.json` ou `graphiques.json`) ;
- `autoexec.be` s'il a été écrit ;
- les fichiers du **moteur** qui viennent d'entrer dans le FS de l'env (exclusion levée dans le cenv), et, si la carte
  est en ligne, ceux dont elle manque (`Br (def() import path return path.exists("/...") end)()`, par `/cm?cmnd=`, lecture seule ; la forme sans fonction rend `nil`). Destination « Graphiques » : sonde du firmware (`graphiquesFonctions.FICHIERS` doit contenir `pages_graphiques.js`) ; firmware d'avant, aucun bouton et le message « compilez et envoyez le firmware et le FS par la page Build » ; moteur absent de la carte, `graphiques.js` et `graphiques_edition.js` sont joints aussi. À l'envoi partiel, un `.json` de la racine de l'image (hors persist) est posé dans `json/`, comme le fait `gestionFileFolder.be` au démarrage. Sous « Graphiques », la page liste les graphiques de la composition : « Modifier » (remplace au même rang, avec témoin) et « Retirer » pour la forme atelier, lecture seule pour la forme actuelle. Carte hors
  ligne ou réponse illisible : seule la première règle s'applique, et la note le dit. Un fichier toujours exclu n'est
  jamais proposé ;
- `redemarrer=1` si `autoexec.be` change ou si l'index des pages dédiées change (id, titre, accès) ; `0` pour un simple
  réglage de graphique, et toujours `0` pour la destination « Graphiques ».

Rien n'est envoyé par l'atelier. Si la page Build ne tourne pas (sondée au clic par `GET /build_actif`), aucun onglet
ne s'ouvre : un message rouge propose de la lancer par l'annuaire. Pour l'arrivée côté Build, voir « Arrivée depuis
l'atelier des graphiques » dans la page Build.

### Destination « Énergie (/energie) » : la page du différentiel

Le menu **Page** propose « Énergie (/energie) » pour la carte `tasmota32-bureau-interrupteur-energie` (toute carte dont le FS
embarque `energie.js`). L'atelier reprend la disposition de la page `/energie` et la modifie sans toucher au comptage.

1. **Choisir** la carte différentiel. Si la description de la carte diffère de celle du dépôt, le choix « carte / dépôt » est
   exigé avant toute modification (jamais d'écrasement implicite).
2. **Éditer** la liste d'éléments : type (`valeur`, `cadran`, `demi-cercle`, `barres`, `courbe`, `aire`, `escalier`), source
   (champ « direct » de ENERGY, total jour/mois/an, ou historique flash minutes/heure/jour/mois/an en kWh ou euros), titre,
   unité, couleur, largeur (demi/pleine), hauteur, min/max des jauges ; ajout (16 au plus), retrait, place dans la liste (en tête, monter, descendre). Échelle de temps d'un graphique « jour » : mois
   relatif (décalage 0 à 23) ou **mois fixe** (`AAAA-MM`) ; si l'archive de ce mois a été purgée, l'atelier le signale avant
   l'écriture. L'aperçu est tracé par le vrai `energie.js`, avec les données de la carte en ligne, sinon des valeurs simulées.
3. **Écrire dans le dépôt** (diff puis écriture atomique, refusée pendant un build ou sur empreinte périmée) : seul
   `data/<lieu>/<carte>/energie_page.json` est écrit, en JSON compact ; la carte le déplace vers `/json/` au démarrage.
4. **Téléverser** : ouvre la page Build avec les 4 fichiers (`energie_page.json`, `energie.js`, `energie.html`,
   `energie.css`), `redemarrer=0`. Rien n'est envoyé par l'atelier.

**Firmware à recompiler une fois.** `energieFonctions.be` est solidifié : les routes `f=description` et `f=mois` n'existent
qu'après un firmware recompilé et envoyé **par la page Build**. Sur une carte à l'ancien firmware (`f=description` rend la page
HTML en 200), « Téléverser » est bloqué avec le message du firmware requis.

**Ne jamais envoyer ce firmware par le port série.** Le différentiel a `custom_files_upload` : un upload série réécrit TOUT
le FS, donc `/energie/etat.json`, `mois-*.json` et `courbe.bin` (jusqu'à 24 mois d'archives) seraient perdus. Procédure :
firmware par OTA (ligne OTA de la page Build ; l'OTA du firmware n'écrit que la partition applicative, `build_ota_firmware.py`,
le FS est une autre partition), puis les 4 fichiers par « Téléverser » ou par l'onglet Fichiers ; jamais d'upload série sauf
après sauvegarde de `/energie/`. Si la description a été écrite quand la carte avait l'ancien firmware, « Écrire » n'a plus
rien à écrire et le bouton « Téléverser » n'apparaît pas : envoyer les 4 fichiers (`energie_page.json`, `sd/js/energie.js`,
`sd/html/energie.html`, `sd/css/energie.css`) par l'onglet Fichiers de la page Build.

Limites (validées par `atelier_energie_description.py::valide` et `Energie.valide`, mêmes cas dans
`outils_pc/cas_energie.json`) : 16 éléments, 4 096 octets de description, titres de 40 caractères, couleur `#rrggbb`.
Conception : [spec](../../docs/superpowers/specs/2026-11-08-atelier-energie-differentiel-design.md) ; plan
`tasks/plans/energie-atelier.md`.

### Première page : la cuve

Env `tasmota32s3-garage-capteurs-cuve-modbus` : page `/pages?p=tableau`, bouton d'accueil « Tableau », courbe
« Hauteur d'eau » (cm, 24 h).

### Essayer sans sonde : `ReglageCuve simulation`

`ReglageCuve simulation <ON|OFF|minutes>` (`data/garage/tasmota32s3-capteurs-cuve-modbus/cuveFonctions.be::reglageCuve`, relevé fabriqué par
`::releveSimule` ; ce module est dans le dossier de la carte, pas dans `data/fs`) fait onduler la hauteur d'eau entre 20 et 90 % de la cuve, une ondulation par période
donnée en minutes. **RAM seulement** : un redémarrage l'arrête. La valeur est enregistrée dans l'historique et dans
Influx comme une vraie mesure. Fonctionne **sans ADS1115** sur le bus (le relevé suppose ±6,144 V et ajoute la lecture
de la minute).

### Bancs

Dans `outils_docs/scripts_python/outils_pc/` (Python de PlatformIO) : `test_atelier_graphiques_description.py`,
`_series.py`, `_conseil.py`, `_ecriture.py`, `_graphiques.py` (destination « Graphiques », composition de la carte),
`_televerse.py` (liste du bouton « Téléverser »), `_web.py`, puis la sonde Chrome `test_atelier_graphiques_page_chrome.py` ;
`build/test_cible_atelier_graphiques.py`. Destination Énergie : `test_atelier_energie_description.py`,
`test_atelier_graphiques_energie.py`, sonde Chrome `test_atelier_energie_page_chrome.py` (mutants `absent`, `archive`,
`mobile`, `vol`). Côté carte : `node outils_docs/scripts_python/outils_pc/test_pages_graphiques.mjs`,
`test_pages_graphiques_chrome.py` et `berry/banc_pages_graphiques.py` (cas partagés avec le validateur Python :
`berry/bouchons_berry/pages_graphiques/cas_description.json`). Commandes exactes : skill `bancs`.
