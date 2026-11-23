# Atelier des écrans

Tiré de `outils_docs/README.md` le 2026-11-23 (plan `binomes-berry`, A20). Aiguillage : `outils_docs/INDEX.md`.

## Atelier des écrans (page web)

Une page qui dessine l'écran tactile d'une carte (HASPmota ou LVGL pur) d'après **une description neutre** : on place
les objets sur un canevas à la taille de l'écran, et la page génère les deux interfaces, `pages.jsonl` (HASPmota) et
`ecranLvgl.be` (LVGL pur). La carte n'en charge qu'une, celle que choisit `custom_interface_ecran` dans son cenv.
Palier 1 : sept objets, libellé (`label`), bouton (`btn`), barre (`bar`), cadre (`obj`), courbe (`chart`), arc
(`arc`) et curseur (`slider`) ; le palier 2 y ajoute image, liste déroulante, roue, interrupteur et QR code (voir plus bas).
Les paliers 1 et 2 sont les 12 types que l'atelier sait poser ; les 18 types du palier 3 sont catalogués mais hors de l'atelier (le validateur les refuse, l'import les garde en lignes `brut`). Première carte : l'écran des débits (`tasmota32s3-bureau-ecran-debits-pac`, Waveshare
ESP32-S3-Touch-LCD-7B).
Conception : [spec](../../docs/superpowers/specs/2026-11-11-atelier-ecrans-design.md) ; plan `tasks/plans/atelier-ecrans.md` ;
maquettes `outils_docs/atelier_ecrans/` ; savoir-faire HASPmota / LVGL : skill `lvgl-haspmota`.

### Lancer la page

- **Tuile de l'annuaire** (http://127.0.0.1:7600), groupe « Ateliers » : « Atelier des écrans ». Rien n'est écrit
  avant « Écrire dans le dépôt », l'arrêt est libre.
- **Tâche VS Code** : `Ctrl+Maj+P` > Run Task > « Outil : atelier des écrans (http://127.0.0.1:7960) ».
- **Ligne de commande** : `python outils_docs/scripts_python/outils_pc/atelier_ecrans_web.py` (`--http 7960`, `--local`,
  `--sans-navigateur`).
- **Cible PlatformIO** « Atelier des écrans (page web) » dans *Project Tasks > <env> > Custom* : démarre la page détachée
  puis rend la main. Comme toute cible, **jamais pendant un build**.

Port **7960**. Depuis un autre appareil : lien à jeton de la console (`acces_web.py`). Bascule Sombre / Clair mémorisée
dans le navigateur.

### Utilisation

1. **Carte** : liste des cartes à écran, groupée par lieu. L'en-tête montre l'écran déclaré (présélectionné), l'état en
   ligne de la carte et l'interface envoyée.
2. **Canevas** : glisser un objet depuis la palette, le déplacer (grille aimantée à 8 px), le redimensionner ; zoom − / + /
   100 % ; annuler / rétablir (`Ctrl+Z`, `Ctrl+Y`). L'onglet « Tableau des objets » donne une ligne par objet, cases
   modifiables. Seules les polices du catalogue sont proposées ; une taille absente est refusée avec les tailles possibles.
3. **Aperçu** : dessiné par le navigateur avec les vraies polices `.ttf`, valeurs liées simulées ou lues sur la carte en
   ligne (`Status 10`). « Capture de la carte » affiche l'écran réel (`lv.screenshot()` par la commande `Br`) ; refusée si
   la carte est hors ligne. Pas encore essayée sur la carte.
4. **Fichiers générés** : onglets `pages.jsonl`, `ecranLvgl.be`, `ecran.json`, avec leurs différences au dépôt.
5. **Écrire dans le dépôt** : confirmation avec la liste des fichiers, écriture atomique (copie horodatée). Refusée pendant
   un build, et si un fichier a changé depuis le chargement ou le diff. Le message donne le lien « Envoyer par la page
   Build ↗ » (`?env=` et fichier de l'interface coché).

### Changer d'écran

Choisir dans la liste un écran autre que celui de la carte ouvre une **proposition** : la description est mise à
l'échelle (positions et tailles au rapport des résolutions, police ramenée à la taille compilée la plus proche), les
boutons trop petits pour le doigt et les textes qui débordent sont signalés. Le diff montre aussi le `display.ini` de la
carte, repris d'un env qui porte déjà cet écran ; broches de l'écran en conflit avec le persist = refus motivé. Revenir à
l'écran de la carte annule la proposition. Après écriture : firmware à recompiler et téléverser par la page Build.

La liste des écrans (écrans couleur seulement) a trois groupes, par ordre de priorité : **écrans des cartes** (le
`display.ini` d'un env, sauf s'il est exclu de son FS), **bibliothèque personnelle** (`outils_docs/atelier_ecrans/display/*.ini`)
et **fournis par Tasmota** (`tasmota/displaydesc/*.ini`, lus sans jamais être modifiés). Un même écran trouvé plus loin
prend la clé `<pilote>_<l>x<h>@<fichier>`. Un écran de la bibliothèque ou de Tasmota part sur la carte tel quel, avec un
avertissement : il n'a jamais tourné sur une carte du dépôt. Une carte sans écran peut aussi en recevoir un (description
vierge). Le catalogue se régénère par `python outils_docs/scripts_python/outils_pc/atelier_ecrans_catalogue.py --generer`.

### Remarques et Claude

L'outil « Remarque » épingle un texte sur un objet, une zone tracée ou une page (`remarques.json`). « Traiter les
remarques (Claude) » lance `claude -p` **en lecture seule** (outils de lecture seulement, hooks coupés, jamais
`bypassPermissions`), depuis ce PC seulement : Claude rend des propositions, la page les valide puis les range dans
`remarques.json`. Un fichier du dépôt changé pendant le traitement est signalé, sans rejet (d'autres conversations
travaillent en même temps). « Appliquer » rejoue une proposition sur la description en mémoire ; l'écriture reste celle
du bouton « Écrire dans le dépôt », et c'est elle qui fait passer la remarque à « appliquée » (annulée sur le canevas
avant l'écriture, elle reste « proposée »). Un traitement à la fois, 10 min au plus, journal dans
`%LOCALAPPDATA%\outils_tasmota\atelier_ecrans\`.

### Importer une police

Panneau « Importer une police (.ttf) » sous la palette, avec des liens vers Google Fonts et Font Squirrel. Le fichier
choisi est analysé : famille, licence lue dans la police (table `name`), caractères français manquants. Import refusé si
le Latin-1 est incomplet, tant que la case « J'ai vérifié la licence » n'est pas cochée, pendant un build, ou si une
police du même nom existe déjà dans le dépôt. L'import écrit la police dans le dossier de la carte choisie
(`data/<lieu>/<carte>/<nom>.ttf`, rangée au démarrage sous `/sd/polices/` par `ecranFonctions.rangePolices`), son texte de
licence dans `outils_docs/atelier_ecrans/polices/` (hors du dossier de la carte, qui part en flash) et régénère le
catalogue. Polices `.bin` de LVGL : pas encore importables.

### Images

Une image `.png`, `.jpg` ou `.bmp` posée à la racine du FS est rangée au démarrage dans un dossier par format :
`/sd/images/PNG/`, `/sd/images/JPG/`, `/sd/images/BMP/` (`gestionFileFolder.be::listeEtRepartitLesFichiers`, casse de
l'extension indifférente). Un écran la cite en `A:sd/images/PNG/<nom>`. Le firmware ne décode que le PNG (LodePNG) :
`.jpg` et `.bmp` sont rangés mais pas affichables par un écran. Le module est solidifié : la règle n'agit qu'après
recompilation du firmware de la carte.

### Objets du palier 2

La palette propose aussi **image** (un PNG du dossier de la carte, cité en `A:sd/images/PNG/<nom>`), **liste
déroulante** et **roue** (une option par ligne), **interrupteur** et **QR code** (toujours carré, sa taille est sa
largeur). L'aperçu dessine le PNG réel et le QR code du texte saisi. L'action d'une liste, d'une roue ou d'un
interrupteur part au changement de valeur et reçoit la valeur choisie : dernier argument d'une fonction Berry, `%val%`
dans une commande, 1 ou 0 pour un interrupteur. Ceci vaut pour l'interface LVGL pur : dans un `pages.jsonl`, une
fonction ou une commande n'a pas de clé `action`, c'est le Berry de la carte qui réagit à l'événement HASPmota.
Une roue ne prend pas de texte.

### Barre de navigation construite

Sur la page 0, le panneau « Barre de navigation construite » remplace les boutons de page posés à la main : position,
hauteur, écart, couleurs des boutons et de la page courante. Un bouton par page, dans l'ordre des pages, avec le titre
de la page ; sa largeur suit la longueur du titre. Une page sort de la barre par sa case « Dans la barre de navigation »
(page de confirmation). Les boutons sont générés dans les deux interfaces (ids 201 à 254, réservés : un objet de la
page 0 ne peut pas les prendre) ; ils sont dessinés en pointillés sur l'écran et ne se sélectionnent pas. Une barre plus
large ou plus haute que l'écran est refusée avec sa taille. Au changement d'écran, la barre est mise à l'échelle.

### Page « Système » construite

Une page de la description peut porter `"modele": "systeme"` (une seule, numéro 1 ou plus, aucun objet saisi à la main
dessus) : l'atelier la dessine lui-même d'après la table `CHAMPS` de `data/fs/ecranSysteme.be` (mémoire, flash, charge,
redémarrages, réseau, ModBus, écran, firmware, cinq dernières erreurs) et ajoute les boutons « Lancer le GC » et
« Redémarrer ». La mise en page occupe la zone libre entre l'en-tête de la page 0 et la barre de navigation, en colonnes
de groupes. Il suffit d'ajouter `{"n": 4, "titre": "Système", "modele": "systeme"}` aux pages de la description d'une
carte à écran, puis « Écrire » ; le module Berry ne pose que les valeurs sur les ids de la table. Un champ ajouté à
`CHAMPS` hors des groupes connus, un écran trop petit pour la page (changement d'écran refusé avec le motif) ou un objet
posé à la main sur la page sont refusés par le validateur. Aucune icône n'est encore émise sur cette page (ids 190 à 198 réservés aux icônes de groupe, `atelier_ecrans_systeme.py`) ; le panneau « Icônes » (A15) existe, mais il n'est pas branché sur elle.

### Page « QR code » d'une carte à écran

Même contenu que la page web `/qrcode` de la carte : le QR code du texte réglé par l'outil des étiquettes (« Page sur la
carte » activée, port 7970), l'IP réelle de la carte, l'IP inscrite sur l'étiquette, le nom d'hôte, et une pastille qui
dit si les deux IP concordent (verte si oui, orange si elles diffèrent, grise si l'une manque). Sur l'écran des débits
c'est la page 5 de `ecran.json` : un objet `qrcode` lié à `qr.texte` (attribut `qr_text`), quatre libellés liés à `qr.ip`,
`qr.ipInscrite`, `qr.hostname`, `qr.accord`, la pastille liée à `qr.etat`. Les valeurs viennent de
`ecranDebitsFonctions.qr` (module du dossier de la carte, `data/bureau/tasmota32s3-ecran-debits-pac/`, pas de `data/fs`), sous-table `qr` du modèle : `/json/qrcode.json` (8 Ko au plus) et `Status 5` sont relus au
plus une fois par 10 minutes, toutes les minutes tant que l'IP reste inconnue, jamais à chaque seconde. Sans réglage de
l'outil des étiquettes, la page affiche « Aucun réglage ». Un fichier trop gros ou illisible est journalisé en erreur
(cible `ecranDebits`). La barre de navigation gagne son sixième bouton toute seule (A17). La cave n'a pas encore sa page :
son `ecran.json` (`tasmota32s3-cave-ecran`) n'a que 5 pages, ni Système ni QR code. Pas essayée sur la carte (A20) ; le firmware est à recompiler par la page Build.

### Panneau « Icônes »

Onglet « Icônes » du panneau de droite : la grille des 120 glyphes Material Design embarqués dans le firmware, avec
recherche par nom. Un clic pose le glyphe en `montserrat-28` dans l'objet choisi (libellé ou bouton), sinon dans un
nouveau libellé. L'aperçu dessine ces glyphes par la police locale `materialdesignicons-webfont.ttf` (aucun CDN) ; les
symboles Font Awesome du firmware restent des carrés vides. Sous la grille : le parcours pour une icône absente du
firmware (PNG blanc sur fond transparent, couleur par `image_recolor`) et les sites de l'annuaire avec leur licence.
Sous la grille, « Importer un PNG » : on choisit un fichier .png (512 x 512 px et 300 Ko au plus, avertissement au-delà de
160 px ou sans transparence), la page affiche ses dimensions, on indique l'origine (site ou URL) et on confirme la
licence ; le PNG est écrit dans le dossier de la carte choisie (il part sur le FS, `gestionFileFolder.be` le range sous
`/sd/images/PNG/` au démarrage et l'objet `img` le propose) et la note de licence dans `outils_docs/atelier_ecrans/images/<env>/`.
Refusé pendant un build, sans origine, sans licence confirmée, ou si le nom existe déjà dans le dossier de la carte.
Le catalogue `outils_docs/schemas/icones_firmware.json` vient de `lib/libesp32_lvgl/LVGL_assets/gen.sh` : après une
synchro du fork, `python outils_docs/scripts_python/outils_pc/genere_icones_firmware.py --verifier` (Python système,
fontTools) dit s'il est à refaire, sans `--verifier` il le réécrit.
### Importer un pages.jsonl écrit à la main

Une carte dont le dossier a un `pages.jsonl` montre, sous « + page », le bouton **Importer le pages.jsonl de la carte**.
Le fichier est lu comme HASPmota le lit : une ligne sans clé `page` appartient à la page courante, les lignes vides sont
ignorées. Une ligne d'un objet du palier 1, avec `x`, `y`, `w`, `h` entiers, des attributs connus du catalogue et une
`action` `p<n>` vers une page du fichier devient un objet **éditable**. Le premier commentaire d'une page devient son
titre, son `{"id":0,...}` placé avant tout objet devient ses réglages. Tout le reste reste **brut** : classe hors
catalogue, attribut inconnu, `val_rule`, `text_rule`, `berry_run`, `parentid`, autre `action`, objet hors de l'écran,
ligne non JSON (signalée). Une ligne brute est réécrite à l'identique dans le `pages.jsonl`, hachurée sur l'écran si elle
porte une position, grisée dans la liste ; elle n'est ni éditable ni présente dans `ecranLvgl.be` (signalée en tête de
ce fichier). Aucune liaison n'est importée : un écran écrit à la main est rempli par son Berry.

L'import remplace la description de la page (« Annuler » la rend) et n'écrit rien : « Écrire dans le dépôt » montre ensuite
le diff de `ecran.json`, `pages.jsonl` et `ecranLvgl.be`. Garantie vérifiée par `test_atelier_ecrans_import.py` sur les
six `pages.jsonl` du dépôt : le `pages.jsonl` régénéré porte les mêmes objets que la source, dans le même ordre.

### Onglet « display.ini »

Bascule « Interface | display.ini » en haut de la page. À gauche, les `display.ini` en trois groupes : **cartes**
(lecture seule), **ma bibliothèque** (`outils_docs/atelier_ecrans/display/<nom>.ini`, suivie par git, hors flash) et
**Tasmota** (`tasmota/displaydesc/`, lecture seule : la synchro du fork les remplace). Au centre, le texte du fichier et
son analyse ligne par ligne, lue comme le pilote la lit (`uDisplay.cpp::uDisplay::uDisplay`) : section, arguments nommés
(explication, valeurs, défaut au survol), erreurs et avertissements. L'analyse suit la frappe. À droite, le panneau
**Paramètres** liste les lignes `:X` valables pour le bus de `:H`, avec leurs arguments et leurs pièges ; « Ajouter »
insère la ligne à sa place (ordre de lecture du pilote) avec ses valeurs par défaut, à régler ensuite.

Contrôles (référence `outils_docs/schemas/display_ini_parametres.json`) : `:H` en première ligne, bus connu, nombre de
broches par bus, espace dans une ligne de valeurs (le pilote coupe la ligne à chaque espace), ligne de 256 caractères ou
plus, `#` final, `:F` avant `:A`, `:I` avant `:f` avant `:p`, `:B` sans drapeaux (255 : tous les bits), base
hexadécimale ou décimale, `*` dans une broche RGB, QSPI ou DSI, mot `I2C`/`SPI`/`PAR` dans un commentaire. Les
tolérances du pilote ne sont que des avertissements (commentaire en fin de ligne, `0;`, fréquence RGB absente). Le banc
`test_atelier_ecrans_display.py` vérifie que la référence couvre toutes les sections lues par le code : après une synchro
du fork qui ajoute un paramètre, il devient rouge.

« Enregistrer dans ma bibliothèque » montre le diff puis écrit (refus pendant un build, ou si le fichier a changé depuis
le diff). Pour partir d'un fichier Tasmota ou d'une carte : l'ouvrir, choisir un nom, enregistrer. Un fichier de la
bibliothèque a ses **notes de terrain** (`<nom>.notes.md`) : observations datées, avec la carte choisie en haut.
« Appliquer à la carte » passe par le changement d'écran (diff, broches du persist, lien vers la page Build).

### Ce qui est écrit

| Fichier | Où |
|---|---|
| `ecran.json` (description), `remarques.json` | `outils_docs/atelier_ecrans/cartes/<env>/` (hors flash) |
| `<nom>.ini`, `<nom>.notes.md` | `outils_docs/atelier_ecrans/display/` (onglet « display.ini ») |
| `pages.jsonl`, `ecranLvgl.be` | dossier de la carte `data/<lieu>/<carte>/` |
| `display.ini` | dossier de la carte, au changement d'écran seulement |
| police `.ttf` + licence + `outils_docs/schemas/catalogue_ecran.json` | à l'import d'une police |

Les fichiers de l'interface non choisie sont exclus du FS par `build/interface_ecran.py::applique`.

### Bancs

`outils_pc/test_atelier_ecrans_catalogue.py`, `_description.py`, `_haspmota.py`, `_lvgl.py`, `_ecriture.py`, `_ecran.py`,
`_remarques.py`, `_polices.py`, `_import.py`, `_display.py`, `_display_fichiers.py`, `_web.py`, puis la sonde Chrome `test_atelier_ecrans_page_chrome.py` (copie du dépôt,
carte et `claude` simulés) ; `build/test_cible_atelier_ecrans.py` ; rangement des images : `berry/banc_repartition_fichiers.py`.
Commandes exactes : skill `bancs`.
