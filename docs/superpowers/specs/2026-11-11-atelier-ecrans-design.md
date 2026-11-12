# Atelier des écrans (page 7960) : conception

Date : 2026-11-12 (nom de fichier fixé le 2026-11-11 par le plan). Plan : `tasks/plans/atelier-ecrans.md`, action A1.
Maquettes et décisions : `outils_docs/atelier_ecrans/` (`README.md`, `modele-retenu.png`, `modele-retenu-sombre.png`,
`maquettes_atelier_ecrans.html?m=R`). Premier cas réel : carte `tasmota32s3-bureau-ecran-debits-pac` (Waveshare
ESP32-S3-Touch-LCD-7B, 1024 × 600, GT911), dossier `data/bureau/tasmota32s3-ecran-debits-pac/`.

## 1. Intention

Aujourd'hui, changer quoi que ce soit sur l'écran tactile d'une carte veut dire éditer à la main un `pages.jsonl` de
89 lignes (coordonnées, polices, couleurs), puis, pour la variante LVGL pur, réécrire le même dessin en Berry. Personne
ne voit le résultat avant d'avoir compilé, envoyé et regardé la carte.

L'atelier est un outil PC (tuile de l'annuaire) qui montre l'écran de la carte à sa taille, permet d'y déplacer,
ajouter et régler des objets, d'y épingler des remarques que Claude traite, puis génère les deux interfaces (HASPmota et
LVGL pur) à partir d'UNE description neutre, et les écrit dans le dépôt pour l'envoi par la page Build.

## 2. Buts, non-buts, anti-buts

Buts :
- modifier la disposition d'un écran (objets, boutons, pages) sur le PC, avec un aperçu fidèle ;
- épingler des remarques (sur un objet, une zone, une page) et les faire traiter par Claude depuis la page ;
- une seule description par carte, deux interfaces générées (`pages.jsonl`, `ecranLvgl.be`), l'interface envoyée
  restant choisie par `custom_interface_ecran` du cenv ;
- choisir la carte et l'écran dans la page, et pouvoir changer l'écran déclaré par la carte.

Non-buts (premier palier) :
- objets autres que les sept de la palette (voir § 5.2) ;
- reprise automatique d'un `pages.jsonl` écrit à la main d'une autre carte (amélioration du plan) ;
- écrans des autres cartes (ILI9488 SPI, petits OLED) ajoutés au catalogue (amélioration du plan), sauf ce qu'exige le
  changement d'écran (§ 5.6) ;
- logique métier : l'atelier dessine et lie des objets aux valeurs d'un modèle d'écran existant, il n'écrit pas le
  module métier (`ecranDebitsFonctions.be`).

Anti-buts (échec même si « ça marche ») :
- une description qui produit un écran différent sur la carte de ce que montre l'atelier sans le signaler ;
- un fichier du dépôt écrit sans diff vu et confirmé, ou pendant un build ;
- une session Claude lancée par la page qui modifie autre chose que le fichier des remarques ;
- une police, un objet ou un attribut proposé par la page alors que le firmware ne l'a pas (police non compilée,
  attribut inconnu de HASPmota : erreur `HSP: unknown attribute` ou `Unsupported font` sur la carte) ;
- un fichier qui n'a rien à faire en flash envoyé sur le FS de la carte (leçon du 2026-10-12).

## 3. Contraintes

- Fichiers sous 500 lignes ; aucune nouvelle dépendance Python ni JS sans accord. Bancs `outils_pc/` avec
  `"$USERPROFILE/.platformio/penv/Scripts/python.exe"`, sur copies temporaires du dépôt.
- Modèle des autres outils PC : serveur Python, `acces_web.py` (sans jeton depuis ce PC, jeton depuis un autre
  appareil), fiche de présence, tuile de l'annuaire (groupe Maintenance, `annuaire_registre.py`, `_port("http", 7960)`,
  `lieu=True`), tâche VS Code « Outil : atelier des écrans », cible Custom détachée `build/cible_atelier_ecrans.py`
  (`NOM_CIBLE` ajouté à `CIBLES_OUTILS` de `garde_build.py`), comme `atelier_graphiques_*` et `tapp_*`.
- Liste des cartes par lieu : `outils_pc/lieux.py` (`remplitParLieu`), comme les pages 7700 à 7980.
- Écriture : diff puis écriture atomique (`fichiers_berry_sauvegarde.Transaction`), empreinte périmée refusée, refus
  pendant un build (`build_serie` / `garde_build`). Compilation et FS par la page Build seulement.
- `user_config_override.h`, `_persist.json`, `data/fs/*.be` : jamais écrits sans diff montré et confirmation explicite
  dans la page (règle du dépôt : accord de l'utilisateur).
- Ressources d'écran (images, fonds, polices ajoutées) sous `/sd`, choisies avec l'utilisateur (action A9 du plan).
- Logs Berry du code généré : charte du `CLAUDE.md` (`logFonctions.log`, constantes `LOG_LEVEL_*`).
- Avant commit : `relecteur-pages-web` (page) et `relecteur-berry` (Berry généré et modules touchés).

## 4. Décisions de l'utilisateur (2026-11-12)

1. Disposition retenue : modèle A (trois colonnes) avec le fil de remarques de C dans l'onglet « Remarques », le zoom
   à 100 % (B), la fenêtre basse de C (fichier généré en onglets avec ses différences) et le tableau de D en onglet
   « Tableau des objets » à côté de l'onglet « Écran ». Bascule Sombre / Clair dans l'en-tête.
2. Bouton « Traiter les remarques (Claude) » près du fil : la page lance une session Claude en arrière-plan
   (`claude -p`) qui écrit ses propositions dans le fichier des remarques ; la page les affiche avec Appliquer /
   Refuser / Répondre. Seul « Appliquer » modifie la description.
3. En-tête : la carte se choisit dans une liste déroulante (par lieu), on en change sur la page ; une seconde liste
   donne tous les écrans connus des envs personnels, présélectionnée sur celui de la carte. Choisir un autre écran
   permet aussi de CHANGER l'écran déclaré par la carte.
4. Quand l'écran change, la disposition existante est mise à l'échelle par PROPOSITION (positions et tailles au
   rapport des résolutions, police ramenée à la taille compilée la plus proche), objets trop petits pour le doigt
   et textes qui débordent signalés ; vue sur le canevas et dans le diff avant écriture.
5. Objets du premier palier : libellé (`label`), bouton (`btn`), barre (`bar`), cadre (`obj`), courbe (`chart`), arc
   (`arc`), curseur (`slider`).
6. Aperçu : dessiné par le navigateur avec les vraies polices, plus un bouton « Capture de la carte » qui affiche
   l'écran réel (`lv.screenshot()`).
7. L'interface LVGL pur de l'écran des débits ne s'écrit pas à la main : elle sera le premier produit du générateur
   (A5). En attendant, la carte reste en HASPmota.

## 5. Conception

### 5.1 Fichiers

| Fichier | Rôle | Où |
|---|---|---|
| `catalogue_ecran.json` | objets, attributs gérés, polices compilées et tailles, écrans connus | `outils_docs/schemas/` |
| `ecran.json` | description neutre de l'écran d'une carte | `outils_docs/atelier_ecrans/cartes/<env>/` |
| `remarques.json` | remarques de cet écran, leur état, les propositions de Claude | même dossier |
| `pages.jsonl` | interface HASPmota générée | dossier de la carte `data/<lieu>/<carte>/` (déjà là) |
| `ecranLvgl.be` | interface LVGL pur générée | dossier de la carte |

Décision de Claude : `ecran.json` et `remarques.json` vont HORS du dossier de la carte (le plan disait
`data/<lieu>/<carte>/ecran.json`) car ce dossier part en flash (leçon du 2026-10-12) ; seuls les fichiers générés y
vont. Les deux fichiers sont suivis par git.

### 5.2 Catalogue (`catalogue_ecran.json`)

Extrait des sources par un script (`outils_pc/atelier_ecrans_catalogue.py --generer`, `--verifier` = code 1 si le
fichier n'est plus à jour) :
- objets : pour chacun des sept du palier, les attributs que la page sait éditer (position, taille, texte, police,
  couleurs, rayon, bordure, `min`/`max`/`val`, `action`, etc.), lus dans les classes `lvh_*` de
  `lib/libesp32_lvgl/lv_haspmota/src/embedded/lv_haspmota.be` ; les autres classes y figurent, marquées « palier
  suivant » ;
- polices : polices embarquées du firmware (`robotocondensed`, `montserrat`, `seg7`… et leurs tailles compilées,
  selon les gardes de l'env) et polices `.ttf` de `/sd/polices/` d'une carte ;
- écrans : un par `display.ini` des envs personnels (`data/*/*/display.ini`, ligne `:H` : pilote, résolution, bus),
  avec le tactile et la carte qui le porte (écran intégré ou câblé). Au 2026-11-12 il y en a deux : le 7B (`ST7262`,
  1024 × 600, RGB) et l'ILI9488 (480 × 320, SPI) de `tasmota32s3-serveur-debits-pac`. La liste des écrans de la page
  est CELLE-LÀ (décision 3 : « écrans connus des envs personnels ») : un écran sans env n'est pas proposé, il entre
  au catalogue le jour où un env le déclare. Une carte sans `display.ini` affiche « aucun écran » ; lui choisir un
  écran suit le mode « changement d'écran » (§ 5.6).

La skill `lvgl-haspmota` renvoie au catalogue (source unique) et décrit l'atelier (action A2).

### 5.3 Description neutre (`ecran.json`)

Contenu : l'écran visé (clé du catalogue, résolution, orientation, tactile), les pages (0 = commun, puis 1..n avec
leur titre), les objets (identifiant, page, type, position, taille, style, police, texte), la liaison de chaque objet
à une valeur du modèle d'écran (clés de `ecranDebitsFonctions.modele`, documentées en tête du module), l'action au
toucher (page, commande Tasmota, appel d'une fonction du module métier).

Valeurs liables : la description porte une section `modele` (clé, type, exemple : `voies[i].debit` texte,
`voies[i].barre` 0-100, `total` texte…) recopiée de l'en-tête de `ecranDebitsFonctions.be`. Décision de Claude : pas
de lecture du commentaire Berry par le validateur (fragile) ; un banc compare cette section à la map réellement rendue
par `ecranDebitsFonctions.modele(now)` sous `berry.exe` (bouchons de `banc_ecran_debits.py`) : clé manquante ou en trop
= rouge.

Validateur Python (refus motivé) : objet hors écran, police ou attribut absent du catalogue, liaison vers une valeur
absente de la section `modele`, identifiant en double, objet hors palier. Banc à mutants.

Premier cas : la description de l'écran des débits, équivalente au `pages.jsonl` actuel (pages Commun, Débits,
Courbes, Réglages).

### 5.4 Générateurs

- HASPmota : description vers `pages.jsonl`. Banc : la description des débits redonne le `pages.jsonl` du dépôt
  (écart nul, ou listé et justifié) ; `banc_ecran_debits.py` vert sur le fichier généré. Décision de Claude :
  équivalence SÉMANTIQUE (mêmes lignes dans le même ordre, mêmes clés et valeurs, ordre des clés d'une ligne libre,
  lignes `comment` gardées). Le fichier actuel n'emploie que des objets et attributs du palier (`label` 59, `obj` 7,
  `btn` 9, `bar` 6, `chart` 1 ; attributs de position, texte, police, couleurs, rayon, bordure, `min`/`max`/`val`,
  `action`, `point_count`, `y_min`/`y_max`, lignes de division) : rien n'est perdu.
- LVGL pur : description vers `ecranLvgl.be`, qui respecte l'API d'interface en tête de `ecranDebitsFonctions.be`
  (`demarre()`, `affiche(modele)` avec cache par objet et attribut, aucune fonction anonyme). Compilé par
  `verifie_berry.py`, banc Berry à objets LVGL simulés, `banc_demarrage` de la variante `lvgl` vert.
- L'atelier génère toujours les deux ; l'écriture dans le dépôt porte les deux ; `build/interface_ecran.py` reste
  seul juge de ce qui part sur le FS. Vérifié : le cenv déclare déjà `custom_interface_ecran_lvgl` ;
  `interface_ecran.py::exclusions` ajoute les fichiers de l'autre interface à `custom_files_exclude` par nom de base,
  sans exiger qu'ils existent : écrire `ecranLvgl.be` alors que la carte reste en `haspmota` ne casse pas le build et
  ne l'envoie pas sur le FS (à confirmer par `build/test_interface_ecran.py` en A5).

### 5.5 Page (port 7960)

Disposition `modele-retenu.png` :
- en-tête : titre, liste des cartes par lieu, liste des écrans (celui de la carte présélectionné et marqué), état en
  ligne de la carte (IP du cenv ou par le maître, comme l'atelier des graphiques), interface envoyée, nombre de
  remarques ouvertes, bascule Sombre / Clair (mémorisée dans le navigateur, page lisible sans) ;
- colonne gauche : pages (ajout), objets de la page, palette des sept objets ;
- centre : onglets « Écran » (canevas, zoom − / + / 100 %, grille, aligner, outil Remarque, coordonnées) et « Tableau
  des objets » (une ligne par objet, cases modifiables) ; dessous, la fenêtre des fichiers générés en onglets
  (`pages.jsonl`, `ecranLvgl.be`, `ecran.json`) avec différences colorées, puis « Écrire dans le dépôt » et « Envoyer
  par la page Build ↗ » (`?env=` et fichiers choisis, comme l'atelier des graphiques) ;
- colonne droite : onglets « Propriétés », « Liaison », « Remarques ».

Canevas : glisser-déposer depuis la palette, déplacement, redimensionnement par poignées, annuler / rétablir, grille
aimantée. Seules les polices du catalogue sont proposées ; une taille absente est refusée avec les tailles possibles.
Aperçu : rendu navigateur (polices `.ttf` du dépôt chargées par `@font-face`) ; valeurs liées simulées, ou lues sur
la carte en ligne (`Status 10` / JSON SENSOR) au choix.

Capture de la carte : bouton qui lance `lv.screenshot()` sur la carte (fonction du firmware avec LVGL :
`tasmota/tasmota_xdrv_driver/xdrv_52_3_berry_lvgl.ino::lv0_screenshot`, déclarée dans
`lib/libesp32/berry_tasmota/src/be_lv_tasmota_lib.c` ; exemple d'usage `tasmota/berry/haspmota_src/pages_screenshot.be` ;
aucune modification du firmware) par la commande `Br`, par HTTP ou MQTT, récupère le
fichier, l'affiche à côté du canevas puis l'efface de la carte. Refusé si la carte est hors ligne. Mémoire à
vérifier sur la carte (1024 × 600 × 2 o, environ 1,2 Mo de PSRAM).

### 5.6 Changer d'écran

Choisir dans la liste un écran autre que celui de la carte ouvre un mode « changement d'écran » :
1. mise à l'échelle proposée de la description (décision 4), objets signalés (cible tactile sous 40 px environ, texte
   qui déborde, objet hors écran) ;
2. fichiers de la carte à modifier, montrés en diff : `display.ini` (repris de l'env qui porte déjà cet écran),
   et, si besoin, la base de l'env dans le cenv (LVGL, tactile) ; broches de l'écran confrontées à celles du persist,
   conflit = refus motivé ;
3. avertissement si l'écran est intégré à une autre carte (le 7B est une carte avec écran) ;
4. écriture confirmée, puis rappel : firmware à recompiler et téléverser par la page Build.

Sans écriture, le choix d'un autre écran reste un aperçu ; revenir à l'écran de la carte annule le mode.

### 5.7 Remarques

`remarques.json` : liste de remarques {identifiant, cible (objet `id` / zone `x,y,l,h` / page `n`), texte, date,
état `ouverte` | `proposée` | `appliquée` | `refusée`, proposition de Claude (texte + modifications de la description
sous forme d'opérations), réponses}. Épinglage depuis le canevas (objet, zone tracée) ou la page.

Bouton « Traiter les remarques (Claude) » :
- la page lance `claude -p` dans le dépôt, consigne : « traite les remarques ouvertes de `<chemin remarques.json>`
  pour l'écran de `<env>` avec la skill `lvgl-haspmota` ; rends tes propositions en JSON sur la sortie » ;
- décision de Claude (plus sûre que la limitation d'écriture à un fichier, décision 2 respectée) : la session est en
  LECTURE SEULE (outils de lecture seulement, mode de permission non interactif, jamais `bypassPermissions` ; options
  exactes de `claude` à vérifier au moment de construire). Elle rend ses propositions sur la sortie standard ; c'est
  la PAGE qui les valide (format, cibles existantes, opérations conformes au catalogue) puis les écrit dans
  `remarques.json`. Exigé dès A7 : si la lecture seule ne peut pas être imposée par les options, la fonction n'est pas
  livrée (repli : bouton qui copie la consigne pour une conversation) ;
- contrôle en plus, après la fin : aucun fichier du dépôt n'a changé (`git status` et empreintes avant / après) ;
  sinon le résultat est rejeté et signalé ;
- un seul traitement à la fois, état « en cours » et durée affichés, délai maximal (10 min), journal dans
  `%LOCALAPPDATA%\outils_tasmota\atelier_ecrans\` ;
- « Appliquer » rejoue les opérations de la proposition sur la description en mémoire (vue sur le canevas et dans le
  diff) ; l'écriture dans le dépôt reste celle du bouton « Écrire ».

### 5.8 Sécurité

Comme les autres pages : en-tête anti-CSRF et origine 127.0.0.1 depuis ce PC, jeton depuis un autre appareil ;
textes échappés à l'affichage (XSS : les remarques et les textes d'objets viennent de l'utilisateur et de Claude) ;
chemins validés (env de la liste du cenv, aucun chemin libre venu de la page) ; adresse de la carte prise au cenv ou
au persist, jamais dans la requête (SSRF) ; le lancement de `claude -p` n'est permis que depuis ce PC.

## 6. Découpage (actions du plan)

- A2 catalogue et son script, skill `lvgl-haspmota` mise à jour ;
- A3 format `ecran.json`, validateur, description des débits ;
- A4 générateur HASPmota ; A5 générateur LVGL pur (premier `ecranLvgl.be` des débits) ;
- A6 serveur et page (canevas, palette, propriétés, tableau, pages, zoom, thème, cartes et écrans, capture), tuile,
  tâche, cible ; sonde Chrome hermétique ;
- A7 remarques et traitement par Claude ; A8 écriture, changement d'écran, lien vers la page Build ;
- A9 ressources `/sd` et import de polices ; A10 documentation, relectures, essai réel (un bouton ajouté à l'écran des
  débits, généré dans les deux interfaces, envoyé, vu et touché sur la carte).

## 7. Laissé au constructeur

Noms des modules Python (préfixe `atelier_ecrans_`), découpage des fichiers sous 500 lignes, forme exacte des
opérations d'une proposition, algorithme d'aimantation et d'alignement, rendu de la courbe dans l'aperçu,
options exactes de `claude -p`, format de la capture (BMP lu tel quel ou converti côté PC).
