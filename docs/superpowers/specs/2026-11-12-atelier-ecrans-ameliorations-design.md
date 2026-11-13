# Atelier des écrans : quatre améliorations (conception)

Date : 2026-11-12. Demande de l'utilisateur du même jour : « 1. écrans des autres cartes ajoutés au catalogue, 2. reprise
d'un pages.jsonl écrit à la main, 3. objets du palier 2 : OK on fait ; 4. sur la même interface, paramétrer de nouveaux
display.ini ». L'utilisateur a laissé à Claude les choix de conception (« allons y ») ; ceux-ci sont marqués « choix de
Claude ». Plan : `tasks/plans/atelier-ecrans.md`, actions A11 à A14 (renumérotées le 2026-11-13). Conception d'origine :
`docs/superpowers/specs/2026-11-11-atelier-ecrans-design.md`.

Sources de l'état des lieux (lues dans le code le 2026-11-12) : pilote uDisplay
(`lib/lib_display/UDisplay/src/uDisplay.cpp::uDisplay::uDisplay` et fichiers voisins), chargement
`tasmota/tasmota_xdsp_display/xdsp_17_universal.ino::Init_uDisplay`, guide existant `.doc_for_ai/UDISPLAY_UTOUCH_GUIDE.md`,
`lib/libesp32_lvgl/lv_haspmota/src/embedded/lv_haspmota.be`, `tasmota/lvgl_berry/tasmota_lv_conf.h`.

## 1. Intention

L'atelier ne sait dessiner que pour l'écran 7B (ST7262 1024 x 600) et avec sept objets. L'utilisateur veut pouvoir :
préparer l'écran d'une carte qui porte un autre afficheur, faire entrer dans l'atelier un écran écrit à la main, utiliser
les objets courants qui manquent, et régler lui-même le `display.ini` d'un afficheur (nouveau ou existant) en sachant ce
que chaque ligne veut dire. À terme, Claude propose des ajustements (luminosité, rafraîchissement, adaptation matérielle)
d'après les observations notées sur le terrain.

## 2. Buts, non-buts, anti-buts

Buts :
- catalogue des écrans : cartes du dépôt, bibliothèque personnelle, descriptions amont `tasmota/displaydesc/` ;
- import d'un `pages.jsonl` existant SANS PERTE : ce que l'atelier ne sait pas éditer est gardé et réécrit à l'identique ;
- palier 2 : image (PNG), liste déroulante, interrupteur, roue (roller), QR code ;
- onglet « display.ini » : lire, expliquer, valider, modifier, créer un descripteur ; ranger les descripteurs
  personnels ; noter les observations de terrain.

Non-buts (cette fois) :
- écrans monochromes (bpp 1 : SSD1306, SH110x, ePaper…) dans le canevas : listés dans l'onglet « display.ini », pas
  proposés au dessin (HASPmota et l'atelier travaillent en couleur) ;
- propositions automatiques de réglages par Claude : seulement le journal d'observations qui les rendra possibles ;
- édition des objets importés hors catalogue (règles `val_rule`, classes `lv_*`, `stripes`…) : gardés, pas édités ;
- JPG, BMP, GIF : non compilés dans le firmware (`LV_USE_TJPGD`, `LV_USE_BMP`, `LV_USE_GIF` à 0).

Anti-buts (échec même si « ça marche ») :
- un import puis une génération qui perdent ou changent une ligne que l'atelier ne comprend pas ;
- un `display.ini` écrit avec une erreur que l'onglet savait détecter (pièges du § 6.4) ;
- un descripteur amont `tasmota/displaydesc/*.ini` modifié (conflit à chaque synchro du fork) ;
- un fichier hors firmware posé dans `data/<lieu>/<carte>/` (part en flash).

## 3. Contraintes

- Fichiers et règles du dépôt : écriture atomique (`fichiers_berry_sauvegarde.Transaction`), refus pendant un build,
  diff avant écriture, empreinte périmée = refus ; sécurité de la page comme l'existant (`acces_web`, en-tête anti-CSRF,
  env = carte du cenv, jamais un chemin).
- `display.ini` : lu sur le FS flash (`/display.ini`, pas la carte SD) ; une espace coupe une ligne ; `#` termine
  l'analyse ; ligne de 256 caractères ou plus ignorée sans message.
- Images : seul le PNG (LodePNG) est lu ; `src` = `A:sd/images/<nom>.png` (rangement de
  `gestionFileFolder.be::listeEtRepartitLesFichiers`, firmware à recompiler une fois).
- `lv.textarea` n'existe pas dans le firmware (`BE_LV_WIDGET_TEXTAREA` commenté) : à retirer du catalogue.

## 4. A11 — Écrans des autres cartes au catalogue

Sources, par priorité (choix de Claude) : 1) cartes du dépôt (`data/<lieu>/<carte>/display.ini`), 2) bibliothèque
personnelle `outils_docs/atelier_ecrans/display/*.ini` (§ 6.1), 3) amont `tasmota/displaydesc/*.ini` (lecture seule).

- Clé d'un écran : `<pilote>_<l>x<h>` pour le premier trouvé dans l'ordre des sources (les clés existantes, dont
  `ST7262_1024x600` des débits, ne changent pas) ; une collision ajoute le nom du fichier : `<pilote>_<l>x<h>@<fichier>`.
  Chaque écran porte `source` (carte, perso, amont), `fichier`, `bus`, `bpp`, `tactile`, `envs`.
- Tactile reconnu par `:UTI`, `:TI`, `:TS` ou `:TR` (aujourd'hui `:UT` seulement).
- Carte dont le `display.ini` est exclu du FS (`custom_files_exclude`) ou dont l'env n'a pas LVGL : écran non rattaché à
  cette carte (cas de l'ILI9488 du serveur des débits, périmé).
- bpp 1 : présent au catalogue avec `couleur: false`, absent de la liste des écrans du canevas.
- Changement d'écran (A8) : le `display.ini` proposé vient de la source de l'écran (carte, perso ou amont), toujours
  confronté aux broches du persist.

## 5. A13 — Import d'un `pages.jsonl` écrit à la main

- Bouton « Importer le pages.jsonl de la carte » quand la carte a un `pages.jsonl` sans `ecran.json` ; pour une carte
  qui a déjà les deux, l'import écrase la description après confirmation (diff montré).
- Conversion ligne par ligne : `{"page":n,"id":0,…}` -> attributs de la page ; `{"page":n}` -> page ; `comment` -> gardé
  à sa place ; objet du catalogue avec attributs connus -> objet éditable ; tout le reste (classe inconnue, attribut hors
  catalogue, `val_rule`, `text_rule`, `berry_run`, `parentid` vers un objet non repris…) -> objet `brut` (choix de
  Claude) : la ligne JSON d'origine gardée telle quelle, réécrite à l'identique par le générateur HASPmota, dessinée sur
  le canevas comme un cadre hachuré « non éditable », signalée absente de `ecranLvgl.be`. Ligne non JSON (ex. `# {…}`)
  -> gardée comme commentaire et signalée.
- Liaisons : aucune à l'import (un écran écrit à la main est rempli par son Berry) ; à poser ensuite dans l'atelier.
- Garantie vérifiée par banc : import puis génération HASPmota = mêmes objets JSON que la source (même ordre, mêmes
  clés et valeurs), sur les six `pages.jsonl` du dépôt (débits, ancien ILI9488, trois démos HASPmota amont, démo pixel).

## 6. A12 — Onglet « display.ini »

### 6.1 Où vivent les fichiers (choix de Claude)
- Bibliothèque personnelle : `outils_docs/atelier_ecrans/display/<nom>.ini` (suivi par git, hors flash), un fichier
  par afficheur réglé ; à côté, `<nom>.notes.md` : journal des observations de terrain (date, carte, réglage essayé,
  effet constaté), écrit depuis l'onglet.
- Le `display.ini` d'une carte reste `data/<lieu>/<carte>/display.ini` (c'est lui qui part sur le FS) ; « Appliquer à la
  carte » le copie depuis la bibliothèque, par le chemin du changement d'écran (diff, broches, Build).
- Amont `tasmota/displaydesc/` : lecture seule ; « Copier dans ma bibliothèque » pour partir d'un modèle.

### 6.2 Référence des paramètres
`outils_docs/schemas/display_ini_parametres.json` : une entrée par ligne `:X` (35 environ) avec bus concernés, arguments
ordonnés (nom, base décimale ou hexadécimale, unité, valeurs, défaut), rôle, obligatoire ou non, ordre dans le fichier,
source `fichier::fonction`, pièges. Écrite à partir de l'inventaire du 2026-11-12 et du guide
`.doc_for_ai/UDISPLAY_UTOUCH_GUIDE.md`. Un banc vérifie que chaque section citée est bien lue par
`uDisplay.cpp::uDisplay::uDisplay` et que toute section lue par le code est dans la référence : après une synchro du
fork qui ajoute un paramètre, le banc devient rouge.

### 6.3 L'onglet
- Liste des fichiers : cartes, bibliothèque, amont (avec bus, résolution, tactile).
- Éditeur ligne par ligne : chaque ligne lue comme le firmware la lit (section, arguments) et expliquée à côté
  (argument par argument, valeur traduite : broche, fréquence, couleur, drapeaux décomposés) ; erreurs et avertissements
  en marge.
- Panneau « Paramètres » : tous les paramètres valables pour le bus de `:H`, avec leurs arguments expliqués ; « Ajouter »
  insère la ligne à la bonne place (règles d'ordre) avec ses valeurs par défaut.
- Enregistrer dans la bibliothèque : diff, écriture atomique ; « Appliquer à la carte » : § 6.1.
- Notes de terrain : ajout d'une observation datée au `.notes.md`.
- Essai sur la carte (choix de Claude, à confirmer sur la carte, plan A20) : lire le `/display.ini` de la carte, envoyer
  le nouveau (`/ufsu`), `DisplayReinit` (ou `Restart 1` si LVGL ne le supporte pas), puis « Garder » (écrit dans le dépôt)
  ou « Revenir » (renvoie l'ancien). Commandes à chaud aussi proposées : `DisplayDimmer`, `DisplayRotate`, `DisplayInvert`.

### 6.4 Contrôles (d'après le code du pilote)
`:H` en première ligne ; bus connu ; nombre d'arguments par bus (RGB : 5 broches + 16 données + fréquence) ; espace
dans une ligne ou un commentaire (coupe la ligne) ; ligne de 256 caractères ou plus ; `#` final ; `:F` avant `:A` ;
`:I` avant `:f` avant `:p` ; `:B` sans drapeaux (vaut 255 : tous les bits) ; base attendue (hex pour `:0`..`:3`, `:I`,
`:A`, `:R` ; décimal pour `:B`, `:S`, `:M`, `:T`, `:V`) ; ordre des données RGB selon le bit 02 de `:B` ; mot `I2C`,
`SPI`, `PAR` dans un commentaire (déclenche une analyse à tort) ; `*` dans une broche RGB, QSPI ou DSI (non remplacé) ;
broches en conflit avec le persist de la carte.

## 7. A14 — Objets du palier 2

Objets ajoutés au palier 1 de l'atelier : `img`, `dropdown`, `switch`, `roller`, `qrcode`.
- `img` : `src` choisi parmi les PNG du dossier de la carte (rangés en `A:sd/images/` au démarrage) ; refus d'un autre
  format ; aperçu par le PNG lui-même.
- `dropdown`, `roller` : `options` éditées comme une liste (une option par ligne, envoyées jointes par `\n`) ; `val` =
  index ; événement `changed` -> `val`, `text`.
- `switch` : `val` booléen ; événement `changed`.
- `qrcode` : `qr_text`, `qr_size`, couleurs ; aperçu par la bibliothèque QR déjà utilisée par la page des étiquettes.
- Liaisons et actions sur `changed` comme pour les objets existants.
- Générateur LVGL pur : classes `lv.image`, `lv.dropdown`, `lv.switch`, `lv.roller`, `lv.qrcode` ; `switch.val` ->
  `add_state(CHECKED)` / `remove_state` ; `roller` -> `set_options(t, lv.ROLLER_MODE_NORMAL)` ; `qrcode` -> `update(texte)`.
- Catalogue : type « liste » pour les attributs qui en sont (`options` de msgbox et btnmatrix, `points` de line) ;
  `textarea` retiré.
- Règle de rangement des images : ramenée au `.png` seul (le firmware ne lit ni JPG ni BMP).

## 8. Ordre de réalisation (choix de Claude)

A11 (catalogue, prépare la bibliothèque) -> A12 (onglet display.ini, s'appuie sur A11) -> A13 (import) -> A14 (palier 2).
Chaque action : banc rouge d'abord, code, banc vert avec mutants, sonde Chrome si la page change, relecture
`relecteur-pages-web` (et `relecteur-berry` pour le Berry généré), commit.

## 9. Laissé au constructeur

Disposition fine de l'onglet « display.ini » (suivre le style de la page) ; dessin approché des objets du palier 2 sur
le canevas ; texte exact des explications de la référence ; seuil de taille au-delà duquel une liste d'options devient
trop longue pour un roller.
