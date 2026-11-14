---
chantier: atelier-visuels
titre: Atelier des visuels d'accueil (page 7990) : photo ou dessin dérivé, points chauds, page d'accueil des cartes
objectif: Depuis une photo réelle, produire par carte un fond (photo allégée ou dessin vectorisé) et des points chauds reliés aux relais, mesures et liaisons, et les faire vivre sur la page d'accueil du module
statut: actif
cree: 2026-11-13
maj: 2026-11-14
---
# Atelier des visuels d'accueil

## Contexte
Demande de l'utilisateur du 2026-11-13. **Spec validée le même jour :
`docs/superpowers/specs/2026-11-13-atelier-visuels-accueil-design.md`** (à lire avant toute action ; décisions au § 6,
paliers au § 7, choix laissés au constructeur au § 8). En bref : page de l'annuaire, port 7990 ; une photo déposée,
recadrée, puis un fond au choix, *photo* (WebP réduit) ou *dessin* (SVG vectorisé dans le navigateur) ; des points chauds
(*voyant*, *valeur*, *liaison*) posés à la souris et reliés aux états de la carte ; description `visuel.json` + fond
dans `data/<lieu>/<carte>/` ; module Berry commun `visuelFonctions.be` + `controleVisuel.be` et moteur `visuel.js`
qui dessinent les calques sur l'accueil, injectés une fois par `web_add_main_button` comme la façade des volets ;
route `/visuel?f=fond|etat` ; écriture au dépôt en deux temps et lien vers la page Build.

Architecture reprise : squelette `tapp_web.py` (serveur, `acces_web`), écriture `etiquettes_qr_ecriture.py`
(`prevoit`/`ecrit`, Transaction, liste de `[berry_commun]`), injection `vrPages.be::vrPages_accueil`, envoi binaire
`graphiquesFonctions.be::envoieFichier`, module de page `qrcodePage.be` (driver posé seulement si le fichier existe),
glisser du canevas `atelier_ecrans_page_canevas.py`.

Ouverts au démarrage : la **photo** de l'essai A0 (à fournir par l'utilisateur) ; l'**accord** pour la règle de
rangement `.svg`/`.webp` de `gestionFileFolder.be` (A8, repli : fond lu à la racine).

### Contraintes globales (spec § 4, § 6)
- Fichiers sous 500 lignes ; modules Python préfixés `atelier_visuels_` dans `outils_docs/scripts_python/outils_pc/`.
- Aucune dépendance Python nouvelle (pas de Pillow). Une seule bibliothèque JS nouvelle, la vectorisation, copiée dans
  `outils_docs/visuels_accueil/lib/` avec sa licence et son empreinte, servie par l'outil, jamais envoyée sur la carte.
- Python des bancs : `"$USERPROFILE/.platformio/penv/Scripts/python.exe"` ; bancs sur copies temporaires du dépôt ;
  bancs Berry par `berry.exe` ; tests JS par `node`.
- Compilation et FS par la page Build (:7700) seulement ; toute écriture au dépôt refusée pendant un build.
- Seuls `data/fs/visuelFonctions.be` et `data/fs/controleVisuel.be` sont créés dans `data/fs` ; `gestionFileFolder.be`
  n'est touché qu'en A8, avec l'accord de l'utilisateur. Jamais de `_persist.json` ni de `user_config_override.h`.
- Liste `visuel_accueil` de `[berry_commun]` (`visuelFonctions.be`, `controleVisuel.be`, `visuel.js`) exclue de tous les
  envs tant qu'aucune carte n'a de visuel ; `banc_demarrage.py` après chaque modification du cenv.
- Script injecté : une IIFE, sans `</` ni `<!` ; JSON inséré avec `<` échappé. Routes de la carte derrière
  `check_privileged_access`. Charte des logs Berry (cible `visuel`, préfixe `VISUEL:`, `debug`/`detail` dans `f=etat`).
- Secrets : filtre `assistant_persist_modele.SECRET` sur les clés du persist lues pour les listes de sources ; aucun
  secret dans une réponse HTTP ni un fichier écrit. La photo d'origine ne quitte jamais le navigateur.
- Poids du fond : avertissement à 40 Ko ; refus à 60 Ko sur ESP32 classique (`lieux.puce()`), 200 Ko ailleurs.
- Commits en français, sans accents, sans trailer ; `git commit -- <chemins>` puis `git show --stat HEAD`. Avant commit :
  `relecteur-berry` (A3, A4), `relecteur-pages-web` (A4 à A7).

### Points de vigilance (hors spec, un test chacun dans l'action indiquée)
1. SVG déposé qui porte `<script>`, `<a href>`, `<image>`, une entité XML ou un `DOCTYPE` : rejeté ou vidé par le
   nettoyage, jamais écrit tel quel (A5).
2. Description qui cite un relais ou un esclave absent du persist, ou un chemin SENSOR vide : refusée par le validateur
   Python ET ignorée sans exception par le lecteur Berry, le reste du visuel s'affiche (A2, A3).
3. Carte sans module ModBus ni UDP chargé : `f=etat` rend des blocs vides, pas d'exception (A3).
4. Fond absent du FS (`visuel.json` présent, `visuel.svg` manquant) : la page d'accueil se charge, un `erreur` dans le
   journal, l'image reste vide (A3).
5. Carte injoignable pendant l'aperçu : état « inconnu » rendu en moins de 3 s, la page de l'outil reste utilisable (A6).

## A0 — Essai jetable de vectorisation (attend la photo de l'utilisateur)
Fichiers : `outils_docs/visuels_accueil/lib/<bibliotheque>.js` + `LISEZMOI.md` (version, licence, empreinte SHA-256) ;
page d'essai et rendus PNG dans le scratchpad de la session (hors dépôt : ce sont des photos du domicile) ;
`outils_docs/visuels_accueil/README.md` (décision).
- [x] Bibliothèque choisie et copiée : ImageTracer.js (jankovicsandras, version épinglée), ou équivalent libre si elle ne
  convient pas ; `LISEZMOI.md` avec licence et empreinte ; entrée dans `outils_docs/ICONES_IMAGES_SOURCES.md` — preuve : outils_docs/visuels_accueil/lib/ (imagetracer_v1.2.6.js, LICENSE Unlicense, LISEZMOI.md, SHA-256 7d777599…), ligne ajoutée au tableau des formats de ICONES_IMAGES_SOURCES.md
- [x] Page d'essai dans le scratchpad : charge la photo fournie, la réduit à 480 px, produit trois rendus (aplats
  8 couleurs, aplats 16 couleurs, trait par filtre de Sobel puis vectorisation en 2 couleurs) et affiche le poids de
  chaque SVG (brut et gzip) — preuve : scratchpad/essai_a0/essai.html, 7 rendus mesurés, tableau dans outils_docs/visuels_accueil/README.md
- [x] Trois PNG livrés avec liens cliquables dans le message, poids des SVG en tableau ; temps de calcul noté — preuve : rendu_A, rendu_B, rendu_C, rendu_D (.png) du scratchpad, 0,9 à 1,1 s par rendu
- [x] Décision de l'utilisateur notée dans `README.md` et dans la spec § 5 : voie 1 confirmée, ou vtracer pour l'A5 — preuve : outils_docs/visuels_accueil/README.md (dernier paragraphe) et spec § 5 ; voie 1 choisie avant l'essai, non remise en cause après, rendu à plat demandé ensuite

## A1 — Maquettes de la page et des calques (choix de l'utilisateur)
A3 attend la fin du build en cours de l'utilisateur (règle : aucune édition de data/ ni du cenv pendant un pio run).
Fichiers : `outils_docs/visuels_accueil/maquettes_visuels.html` (`?m=A|B`), `modele-A.png`, `modele-B.png`,
`calques.png`, `README.md`, sur le modèle de `outils_docs/etiquettes_qr/`.
- [x] Deux dispositions de la page 7990 (A : canevas à gauche, panneaux import/fond/élément à droite ; B : canevas
  pleine largeur, panneaux en bandeau repliable), clair et sombre, captures relues — preuve : outils_docs/visuels_accueil/maquettes_visuels.html (?m=A|B), modele-A.png et modele-B.png relus (la planche `calques.png` reste à faire)
- [x] Une planche `calques.png` : voyant (rond, carré, icône MDI), valeur (texte sur cartouche), liaison active et muette — preuve : outils_docs/visuels_accueil/calques.png relue (voyant rond, carré, icône MDI, clignotant ; valeur en cartouche, contour, inconnue ; liaison active, alerte, muette, coupée ; puis le tout posé sur le dessin de la maison), source planche_calques.html
  (trait pointillé animé, trait gris) sur un fond d'exemple dessiné
- [x] Choix de l'utilisateur noté dans `README.md` et ici (liens cliquables donnés avant la question) — preuve : disposition A choisie par l'utilisateur le 2026-11-13 (trois colonnes), modele-A.png ; le SVG d'exemple de la maquette n'est pas le bon rendu (voir spec § 2.3, rendu-cible-page-reelle.png)

## A2 — Description `visuel.json` : validateur et sources
Fichiers : créer `outils_pc/atelier_visuels_description.py`, `outils_pc/test_atelier_visuels_description.py`,
`outils_docs/schemas/cas_visuel.json` (cas valides et invalides, partagés avec le banc Berry de l'A3), exemple
`outils_docs/schemas/exemple_visuel.json`.
Interfaces produites : `valide(desc: dict, octets_fond: int | None, puce: str) -> list[str]` (liste vide = valide ;
messages en français) ; `SEUIL_AVERT = 40 * 1024`, `SEUILS_REFUS = {"esp32": 60 * 1024, "autre": 200 * 1024}` ;
`sources(racine: Path, env: str) -> dict` avec les clés `relais` (`[{"n", "nom"}]`), `mesures` (chemins trouvés dans
le persist : blocs métier et `configGlobal`), `esclaves` (`[{"id", "nom"}]` de `drivers.ModBus`), `udp` et `rgx`
(`[{"mac", "nom"}]` de `discovery.json` du dossier de la carte), `periodeReleve`, `telePeriod` ;
`defauts_seuils(sources) -> dict` (spec § 6.2 : ModBus 3 × periodeReleve ou 30, udp 2 × telePeriod).
- [x] Test écrit : chaque cas — preuve : test_atelier_visuels_description.py + schemas/cas_visuel.json (17 cas, exemple_visuel.json) de `cas_visuel.json` rend les erreurs attendues (`version` autre que 1, type inconnu,
  coordonnées hors du fond, `source.n` absent, `chemin` vide, liaison sans `x2`, `seuil_s` négatif sur une liaison ModBus, poids au-dessus du
  seuil selon la puce) ; `sources()` sur la copie du persist de la cuve rend ses relais nommés et ses esclaves
- [x] Test lancé : rouge (module absent) — preuve : 1er lancement rouge (FileNotFoundError cas_visuel.json), puis cas générés
- [x] `atelier_visuels_description.py` écrit ; test vert — preuve : sortie du banc : VERT, code 0
- [x] Commit `feat(atelier-visuels): validateur de visuel.json et sources du persist (A2)` — preuve : abee06fb8

## A3 — Côté carte : `visuelFonctions.be`, `controleVisuel.be`, cenv
Fichiers : créer `data/fs/visuelFonctions.be`, `data/fs/controleVisuel.be`, `berry/banc_visuel.py`, `berry/banc_visuel.be`,
`berry/bouchons_berry/visuel/` (faux `tasmota`, `webserver`, `modbusFonctions`, `udpFonctions`, `discoveryFonctions`,
`persist`) ; modifier `platformio_tasmota_cenv.ini` (liste `visuel_accueil`, exclue de tous les envs, et
`custom_berry_solidify` : NON, tant qu'aucun env ne la lève).
Interfaces produites (module solidifié, appels par `visuelFonctions.nom`) : `visuelFonctions.FICHIER = "/json/visuel.json"` ;
`charge() -> map | nil` (lit et valide la description une fois, garde la liste des types de sources présents) ;
`html() -> string` (`<div id='vz'></div><script>window.VISUEL=…</script><script>…visuel.js…</script>`, `<` échappé) ;
`etat() -> map` (`t`, `power`, `sensor` réduit aux chemins demandés, `modbus{serie_ms, esclaves}`, `udp`, `reseau` ;
chaque bloc seulement si une source de ce type existe ; module absent = bloc vide) ; `cheminFond() -> string | nil`
(`/sd/images/SVG/visuel.svg`, `/sd/images/WEBP/visuel.webp`, `/sd/images/JPG/visuel.jpg`, puis la racine) ;
`route()` (`f=fond` : SVG par `readFileByLineAndContentSend`, binaire par morceaux de 2048 o comme
`graphiquesFonctions.envoieFichier`, `Cache-Control: max-age=86400` ; `f=etat` : JSON ; autre `f` : 404) ;
`controleVisuel.be` : classe `CONTROLE_VISUEL : Driver`, `web_add_main_button()` et `web_add_handler()` posés
SEULEMENT si `charge()` a rendu une map (modèle `qrcodePage_init`).
- [x] `banc_visuel.be` écrit (lancé par `banc_visuel.py`, code de sortie 0/1) : sans `/json/visuel.json` aucun driver ;
  description valide : `html()` sans `</` dans le JSON, `etat()` avec les seuls blocs demandés ; description qui cite un
  relais absent : élément ignoré, pas d'exception (vigilance 2) ; modules ModBus/UDP absents : blocs vides (3) ; fond
  manquant : `f=fond` 404 et un `erreur` dans le journal (4) ; `f=etat` sans `info` ; accès non privilégié refusé — preuve : banc_visuel.{be,py} : BANC_VISUEL: OK, 14 mutants rouges, 21 cas partages avec cas_visuel.json
- [x] Banc lancé : rouge (modules absents) — preuve : banc_visuel.lance() sur un dossier sans visuelFonctions.be ni controleVisuel.be (2026-11-14) : « BANC_VISUEL: OK » absent, io_error « cannot open file …/fs/visuelFonctions.be » ; banc vert sur data/ (VERT)
- [x] `visuelFonctions.be` et `controleVisuel.be` écrits (charte des logs ; aucun nom de builtin Berry en variable) ;
  hook `verifie_berry_edition` vert ; banc vert — preuve : verifie_berry 0 erreur 0 avertissement, banc_visuel VERT
- [x] Cenv : liste `visuel_accueil` ajoutée à `[berry_commun]`, `${berry_commun.visuel_accueil}` dans le
  `custom_files_exclude` de chaque env ; `banc_demarrage.py` vert (instantanés inchangés) — preuve : 19 lignes ${berry_commun.visuel_accueil} (17 envs + 2 envs qui levent etiquette_qr) ; banc_demarrage.py VERT sans --enregistre
- [x] `relecteur-berry` lancé, remarques traitées — preuve : relecteur-berry : aucun bloquant ; RAM de html() et cache du fond notes
- [ ] Commit `feat(visuel): module Berry du visuel d'accueil, route /visuel, liste visuel_accueil exclue partout (A3)`

## A4 — Moteur `visuel.js` et premier essai sur carte à la main
Fichiers : créer `data/sd/js/visuel.js`, `outils_pc/test_visuel_js.mjs` ; fichiers d'essai écrits à la main dans le
dossier de la cuve (`visuel.json`, `visuel.svg` tiré de l'A0 ou dessiné), retirés avant le commit.
Interfaces produites : IIFE qui pose `window.VisuelAccueil = {monte(conteneur, desc, urlFond) -> svg, applique(etat, t)}`
et, si `window.VISUEL` existe, monte dans `#vz`, lit `/visuel?f=fond&v=<empreinte>` par `<image href>`, puis
`fetch('/visuel?f=etat')` toutes les `desc.rafraichissement` ms (défaut 2345, minimum 1000 ; requête suivante après la réponse, coupée à 4 s : état « inconnu », dessin grisé). Un `voyant` passe en classe `on` si
`power[n-1]` vrai, ou si la mesure vérifie `on` / `on_min` ; une `valeur` affiche `texte_avant + mesure.toFixed(decimales) + unite` ;
une `liaison` est active si `t - horodatage < seuil_s * 1000` (ModBus, UDP), si `etat == "ok"` (rgx), si `up` (wifi) ;
`stroke-dashoffset` animé par CSS inliné dans le SVG. Icônes : une dizaine de chemins MDI dans une table du fichier
(choisis dans `ICONES_IMAGES_SOURCES.md`, licence notée en tête).
- [x] `test_visuel_js.mjs` écrit (`node`, faux `document` minimal ou `jsdom` absent : le test construit le SVG par
  `monte` sur un faux DOM maison et lit les attributs) : voyant ON/OFF par relais et par mesure, valeur formatée,
  liaison active puis muette au passage du seuil, rgx `ok`/`muet`, wifi `up`, élément de type inconnu ignoré, aucun
  `</` dans le texte du fichier — preuve : test_visuel_js.mjs : 26 controles, 12 mutants rouges (VERT, rc 0) ; DOM minimal maison
- [ ] Test lancé : rouge
- [x] `visuel.js` écrit ; test vert ; `node --check` vert — preuve : node test_visuel_js.mjs VERT ; node --check data/sd/js/visuel.js ok ; 9472 octets, aucune balise fermante
- [ ] Essai sur la cuve : `visuel.json` + `visuel.svg` d'essai dans son dossier, liste `visuel_accueil` levée pour la
  cuve et `visuelFonctions.be`/`controleVisuel.be` dans son `custom_berry_solidify`, compilation et envoi par la page
  Build, accueil chargé, capture Chrome de la vraie page avec largeur mesurée avant et après (leçon du 2026-10-31),
  tas lu avant et après (`Status 0` ou journal `BRY: GC`) ; résultats notés ici
- [ ] Fichiers d'essai retirés du dossier de la cuve (ou gardés si l'utilisateur le demande), cenv remis à l'état exclu
  partout, `banc_demarrage.py` vert
- [ ] Commit `feat(visuel): moteur visuel.js des calques de l'accueil (A4)`

## A5 — Outil 7990 : squelette, import de la photo, deux modes de fond, poids
Fichiers : créer `outils_pc/atelier_visuels_web.py`, `atelier_visuels_page.py`, `atelier_visuels_page_js.py`,
`atelier_visuels_fond.py`, `test_atelier_visuels_web.py`, `test_atelier_visuels_fond.py`,
`test_atelier_visuels_page_chrome.py`, `build/cible_atelier_visuels.py`, `build/test_cible_atelier_visuels.py` ;
modifier `build/pre_utilitaires_platformio.py` (enregistrement de la cible), `annuaire_registre.py` (tuile, port
7990, groupe Maintenance, `_o.lieu`), `.vscode/tasks.json` (« Outil : atelier des visuels (http://127.0.0.1:7990) »),
`.claude/hooks/garde_build.py::CIBLES_OUTILS` (+ `atelier_visuels`) et `build/test_garde_build.py`.
Interfaces produites : routes `GET /` (page), `GET /envs` (`lieux.pour_page`), `GET /visuel.js` (le fichier de
`data/sd/js`), `GET /lib.js` (la bibliothèque de l'A0), `POST /fond?env=&type=svg|webp|jpg` (corps binaire brut, 1 Mo
au plus, `Content-Type` de l'image ; rend `{"empreinte", "octets", "avertissement"}` ; le fond est gardé en mémoire du
serveur sous son empreinte SHA-256, 20 fonds au plus), `GET /fond?env=&empreinte=` (le fond gardé, pour l'aperçu) ;
`atelier_visuels_fond.py::nettoie_svg(texte: str) -> str` (`xml.etree`, refus de tout `DOCTYPE` ou entité ; garde
`svg`, `g`, `path` et les attributs `d`, `fill`, `stroke`, `stroke-width`, `opacity`, `transform`, `viewBox`, `width`,
`height`, `xmlns` ; lève `ValueError` sur un texte qui n'est pas du SVG) ; `controle_fond(type, octets, puce) -> str | None`
(message de refus selon les seuils de l'A2).
Page (JS) : dépôt d'une photo (`<input type=file>`, `FileReader`), canvas, recadrage par rectangle à poignées, rotation
par quarts de tour, largeur cible (320 à 800, défaut 480) ; mode *photo* : `canvas.toBlob('image/webp', q)` avec repli
`image/jpeg` si le blob rendu n'est pas WebP ; mode *dessin* (changement du 2026-11-13, spec § 2.3) : **formes à plat** posées sur la photo transparente
(`rect`, `polygon`, couleur médiane de la zone recouverte ou motif briques/tuiles/lames repris de `volets.js`, contour facultatif, ordre réglable ; rendu cible : `maquette_rdc_porte_cuisine.html`), exportées en SVG propre ;
palette de gabarits posés puis ajustés (mur, toit monopente à pente réglable ou à deux pans, fenêtre, porte, porte de garage, volet, cheminée, boîte aux lettres, numéro ; spec § 2.3) ;
« pré-remplir » (ImageTracer, 6 couleurs, lissage 96 px) en aide facultative ; poids affiché, avertissement orange, refus rouge ; `POST /fond` au clic « Garder ce fond ».
**Zones de décor** (demande du 2026-11-13, spec § 2.3) : rectangles ou polygones tracés sur la photo recadrée, chacun
*effacer* (aplat de la couleur moyenne du bord, avant la génération, dans les deux modes) ou *garder en photo* (mode
dessin : le morceau de photo est posé par-dessus le tracé, dans le même SVG, en `<image>` encodée dans le fichier) ;
les zones vivent dans le réglage de l'outil, pas sur la carte.
- [x] `test_atelier_visuels_fond.py` écrit : `nettoie_svg` retire `<script>`, `<a>`, `<image>`, `onload=`, `style`
  avec `url(`, refuse `DOCTYPE` et entités (vigilance 1), garde un SVG de chemins intact octet pour octet ;
  `controle_fond` : 50 Ko sur ESP32 = avertissement, 70 Ko sur ESP32 = refus, 150 Ko sur S3 = rien — preuve : test_atelier_visuels_fond.py VERT code 0 ; temoin : nettoyage neutralise = 6 KO ; ecrit apres les modules (rouge prouve par mutant, pas par module absent)
- [x] `test_atelier_visuels_web.py` écrit : `GET /envs` liste les envs par lieu ; `POST /fond` sans en-tête `X-…` = 403 ;
  corps de 1 Mo + 1 = 413 ; type inconnu = 400 ; SVG malveillant = 400 avec le message ; fond gardé relu par
  `GET /fond` octet pour octet ; 21e fond = le plus ancien évincé — preuve : test_atelier_visuels_web.py VERT code 0, serveur arrete en fin de banc
- [ ] Tests lancés : rouges
- [x] `atelier_visuels_fond.py`, `atelier_visuels_web.py` (squelette de `tapp_web.py`), page et JS écrits selon la
  maquette choisie en A1 ; tests verts — preuve : atelier_visuels_page.py + _page_js.py (disposition A, 3 colonnes, theme sombre/clair), test_atelier_visuels_web.py VERT, test_atelier_visuels_page_chrome.py VERT
- [x] Editeur de formes (module `atelier_visuels_page_formes*.py`) : rectangle, polygone, 10 gabarits, motifs briques/tuiles/lames, couleur mediane, aimantation 8 px, annuler/retablir 100 pas, zones effacer/garder, `AV.svg()` propre — preuve : test_atelier_visuels_page_formes.py VERT (31 verifications node, SVG sans perte par nettoie_svg) ; liaison DOM non essayee (sonde Chrome a faire)
- [ ] Cible `build/cible_atelier_visuels.py` (`NOM_CIBLE = "atelier_visuels"`, page détachée, modèle `cible_tapp.py`),
  enregistrée dans le pré-script ; `test_cible_atelier_visuels.py` vert ; `garde_build.py` et son banc verts ;
  tuile de l'annuaire et tâche VS Code ajoutées, annuaire relancé, tuile vue
- [x] Sonde `test_atelier_visuels_page_chrome.py` : fabrique une image de test dans le navigateur (formes colorées sur
  un canvas, aucune photo réelle), la dépose, recadre, produit les deux modes, lit le poids affiché, garde le fond,
  compare `GET /fond` au blob ; attend des conditions, jamais une durée ; arrête ses Chrome (mémoire du 2026-11-13) — preuve : test_atelier_visuels_page_chrome.py VERT (image fabriquee, recadrage, rotation, 2 modes, poids, GET /fond == blob, theme, editeur de formes, aucun Chrome sonde_atelier_visuels_page_* vivant)
- [ ] `relecteur-pages-web` lancé, remarques traitées
- [ ] Commit `feat(atelier-visuels): page 7990, import de la photo, fond photo ou dessin, poids (A5)`

## A6 — Points chauds, sources et aperçu par le vrai moteur
Fichiers : créer `outils_pc/atelier_visuels_page_canevas.py` (glisser copié et allégé de
`atelier_ecrans_page_canevas.py`), `atelier_visuels_page_elements.py` (panneau de l'élément sélectionné),
`atelier_visuels_carte.py` ; modifier `atelier_visuels_web.py`, `test_atelier_visuels_web.py`, la sonde Chrome.
Interfaces produites : `GET /sources?env=` (`description.sources` + `defauts_seuils`, secrets filtrés) ;
`GET /etat?env=` (`atelier_visuels_carte.py::etat(racine, env, delai=3.0) -> dict` : `GET http://<ip>/visuel?f=etat`
sur la carte, IP du persist du dépôt ou `adresse_par_maitre` pour un esclave ; `{"etat": "inconnu"}` après 3 s ou
erreur, vigilance 5) ; `POST /valide` (corps : description ; rend `description.valide`).
Page : palette voyant / valeur / liaison, pose au clic, glisser, poignées pour `x2,y2`, aimantation, annuler/rétablir ;
panneau de l'élément : source choisie dans les listes de `/sources`, style, seuil ; aperçu = `visuel.js` monté sur le
fond gardé avec un état **simulé** (interrupteurs ON/OFF, actif/muet par source) ou **réel** (`/etat` toutes les
`rafraichissement` s, bouton « Carte en ligne »).
- [ ] Tests ajoutés à `test_atelier_visuels_web.py` : `/sources` de la cuve (copie) sans aucune clé secrète même si le
  persist en contient une ; `/etat` sur une IP qui ne répond pas rend `inconnu` en moins de 3,5 s ; `/valide` rend les
  erreurs du validateur
  - [ ] Routes `GET /sources`, `GET /etat`, `POST /valide` : absentes du serveur ; la page essaie `/sources` et retombe sur la saisie à la main (champs identiques) — à brancher côté serveur
- [ ] Tests lancés : rouges ; modules écrits ; tests verts
- [ ] Recherche d'icônes en ligne (spec § 2.4, `atelier_visuels_icones_web.py`) : lire d'abord la documentation de l'API
  Iconify et noter ses limites ; routes `GET /icones/recherche?q=` et `GET /icones/svg?jeu=&nom=` (hôte fixe, jeu et nom
  validés par expression régulière, délai court, hors ligne = message clair) ; licence de la collection lue et affichée,
  permissives d'office, CC BY avec confirmation, autres masquées ; SVG nettoyé par `nettoie_svg` ; cache hors dépôt ; ligne
  ajoutée à `LICENCES.md` à la conservation ; test avec un faux serveur (SVG hostile nettoyé, jeu inconnu refusé, hôte
  non permis refusé, licence non permissive masquée, hors ligne) ; essai réel d'une recherche « camera »
  - [x] Routes `GET /icones/recherche`, `GET /icones/svg`, `POST /icones/garde` branchées dans `atelier_visuels_web.py` (via `atelier_visuels_web_routes.py`) — preuve : `test_atelier_visuels_web.py` VERT (hôte Iconify fixe par faux `ouvre`, nom `../` 400, licence NC masquée, garde 403 sans en-tête, 409 si déjà gardée)
  - [x] Module autonome `atelier_visuels_icones_web.py` + banc `test_atelier_visuels_icones_web.py`, essai réel « camera » (routes HTTP restent à brancher) — preuve : banc VERT 42 contrôles ; essai réel 47 icônes, svg mdi:camera 325 o ; README § « Recherche d'icônes en ligne »
- [ ] Icônes (spec § 2.4) : sélecteur d'icône avec recherche, alimenté par `icones_firmware.json` (`atelier_ecrans_icones.charge`)
  puis les collections de `ICONES_IMAGES_SOURCES.md` ; conversion en tracé `path` (jeu des tracés MDI rangé dans
  `outils_docs/visuels_accueil/icones/` avec sa licence) ; taille réglable ; `icone_on` / `icone_off` / `icone_inconnu` et
  couleur par état ; import d'un `.svg` nettoyé ; test : l'icône change avec l'état simulé (caméra ON/OFF) dans l'aperçu
  - [x] Recherche en ligne dans la page (licence sur chaque résultat, NC masquée, hors ligne = message, attribution confirmée avant conservation), icône posée comme voyant, `icone_on` / `icone_off` / `icone_inconnu`, taille réglable, import d'un `.svg` du PC nettoyé par le serveur — preuve : sonde_icones VERT (faux Iconify, dépôt copié), commit 52a4d672e
  - [ ] Banque locale du firmware (`icones_firmware.json`) dans le sélecteur : aucune route ne la sert (police de glyphes, pas de tracé) ; à décider avec l'utilisateur
- [x] Sonde Chrome étendue : un élément de chaque type posé et déplacé, source choisie, aperçu simulé bascule ON/OFF
  (classe `on` lue dans le SVG), liaison active puis muette — preuve : test_atelier_visuels_page_chrome_faux.py::sonde_points VERT (voyant, valeur, liaison posés, source, déplacés, aperçu ON/OFF lu dans la classe du SVG, liaison active/muette), commit 2e1c0e438
- [ ] `relecteur-pages-web` lancé, remarques traitées
- [ ] Commit `feat(atelier-visuels): points chauds, sources du persist, apercu simule ou reel (A6)`

## A7 — Écriture dans le dépôt, lien vers Build, suivi, documentation
Fichiers : créer `outils_pc/atelier_visuels_ecriture.py`, `atelier_visuels_suivi.py`,
`test_atelier_visuels_ecriture.py`, `test_atelier_visuels_suivi.py` ; modifier `atelier_visuels_web.py`,
`build_page_atelier.py::AT_ORIGINES` (+ `visuel`), `test_build_page_fichiers_chrome.py::sonde_atelier` (arrivée
`depuis=visuel`), `outils_docs/README.md` (§ « Atelier des visuels (page web) »), `CLAUDE.md` (carte des documents),
`tasks/README.md` (régénéré par le hook).
Interfaces produites : `LIGNE_AUTOEXEC` (ligne `demarrage.charge([...])` ou l'équivalent du dépôt, écrite EN DERNIER
dans l'autoexec : le visuel vient sous la façade), `FICHIERS_PAGE` (les trois fichiers de la liste `visuel_accueil`) ;
`prevoit(racine, env, description, fond: bytes | None, type_fond) -> {"diff", "empreinte", "avertissements"}` ;
`ecrit(racine, env, description, fond, type_fond, empreinte_lue, builds_en_cours)` : `data/<lieu>/<carte>/visuel.json`,
`visuel.<svg|webp|jpg>` (l'autre type retiré), ligne d'autoexec, liste `visuel_accueil` levée pour l'env et exclue des
autres, `custom_berry_solidify` tenu comme dans `etiquettes_qr_ecriture`, en une Transaction ; `retire(...)` (visuel
décoché : fichiers, ligne et cenv retirés) ; `atelier_visuels_suivi.py::etat(racine, env, lecteur) -> {"carte":
"identique" | "differente" | "absente" | "inconnue"}` (compare `visuel.json` du dépôt au fichier lu sur la carte par
`/ufsd?download=/json/visuel.json`, comme le suivi des étiquettes QR ; `lecteur` injectable pour le test).
Page : bouton « Écrire dans le dépôt » (diff montré, confirmation), puis lien « Téléverser »
`http://<hôte>:7700/?env=&depuis=visuel&fichiers=visuel.json,visuel.svg&redemarrer=1` ; badge de suivi par carte.
- [x] `test_atelier_visuels_ecriture.py` écrit (copie temporaire du dépôt, relue par `ProjectConfig`) : écriture crée
  les fichiers, la ligne d'autoexec en dernière position, lève la liste pour l'env et l'exclut ailleurs ; empreinte
  périmée = refus, rien écrit ; build en cours = refus ; `retire` rend le dépôt à l'identique ; fond `webp` remplace
  un `svg` existant — preuve : `test_atelier_visuels_ecriture.py` BANC_VISUELS_ECRITURE: OK (cenv sans puis avec la liste `visuel_accueil`, rouge ModuleNotFoundError avant les modules)
- [x] `test_atelier_visuels_suivi.py` écrit : les quatre états, lecteur qui lève = `inconnue` — preuve : `test_atelier_visuels_suivi.py` BANC_VISUELS_SUIVI: OK (rouge avant le module)
  - [x] Routes `POST /ecriture/prevoit`, `POST /ecriture/ecrit` (409 si build en cours) et `GET /suivi?env=` (lecteur HTTP 3 s) branchées — preuve : `test_atelier_visuels_web.py` VERT (écriture pendant un build = 409 sans trace Python, lecteur sur carte muette en échec < 3,5 s) ; `prevoit` sur le vrai dépôt = 400 motivé tant que les fichiers de la page (A3/A4) manquent
- [ ] Tests lancés : rouges ; modules écrits ; tests verts ; `banc_demarrage.py` vert sur la copie après écriture
  (reste : `banc_demarrage.py` sur la copie après écriture, à lancer APRÈS le build en cours ; écriture et suivi : rouges puis verts le 2026-11-13)
- [ ] `AT_ORIGINES` : entrée `visuel` ; `sonde_atelier` étendue ; sonde Chrome de l'outil : « Écrire » puis lien Build
  présent avec les bons fichiers
  - [x] Page : « Écrire dans le dépôt » (diff, confirmation, refus pendant un build, motif de validation affiché), badge de suivi, lien « Téléverser » vers la page Build (`?env=&depuis=visuel&fichiers=visuel.json,visuel.<type>&redemarrer=1`) — preuve : sonde_ecriture VERT sur dépôt copié, commit 3f37b3948 (reste : `AT_ORIGINES` et `sonde_atelier` côté page Build)
- [ ] `outils_docs/README.md`, `CLAUDE.md` (carte des documents, une entrée) ; `verifie_references_docs.py` vert
- [ ] `relecteur-pages-web` lancé, remarques traitées
- [x] Export (spec § 2.5) : boutons « Télécharger le SVG », « Copier le code SVG », « Copier le code HTML »
  (fragment autonome : SVG + calques + script d'animation de `visuel.js` en ligne, aucune requête), « Télécharger le
  PNG » (canvas) ; test : le fragment HTML s'affiche seul dans la sonde Chrome et son voyant change d'état sans la
  carte ; aucun envoi au serveur ni écriture au dépôt — preuve : sonde_export VERT : SVG, code SVG, code HTML copiés (crochets AV.presse / AV.telecharge), PNG signature 137 80 78 71, fragment HTML ouvert seul dans une iframe srcdoc : voyant ON -> OFF et liaison muette -> active au clic sans requête, commit eed444696
- [ ] Commit `feat(atelier-visuels): ecriture au depot, lien Build, suivi depot/carte, mode d'emploi (A7)`

## A8 — Première carte réelle, cohabitation, mesures, rangement
- [ ] Accord de l'utilisateur demandé pour la règle `.svg`/`.webp` de `gestionFileFolder.be::listeEtRepartitLesFichiers`
  (spec § 6.4) ; si oui : règle ajoutée, `banc_repartition_fichiers` étendu et vert ; si non : repli racine noté dans
  la spec et le README
- [ ] Cuve : photo réelle, fond et points chauds (niveau, relais, liaison ModBus série, liaison UDP vers le P4) écrits par
  l'outil, envoyés par la page Build, accueil vu, capture Chrome, largeur de page mesurée, tas avant/après noté ici
- [ ] P4 du garage : visuel sous la façade des volets, les deux vivants, ordre vérifié, capture
- [ ] Un ESP32 classique (proposition : le différentiel) : fond dessin, `UfsFree` et tas avant/après notés ; seuils
  ajustés si besoin dans `atelier_visuels_description.py`
- [ ] `tasks/lessons.md` complété si une leçon est apparue ; plan `statut: clos` si tout est coché
- [ ] Commit `feat(atelier-visuels): premieres cartes (cuve, P4, ESP32) et rangement des images (A8)`

## A9 — Assistant IA facultatif (spec § 2.10)
Fichiers : créer `outils_pc/atelier_visuels_ia.py` (fournisseurs, quota), `atelier_visuels_ia_config.py` (clés hors dépôt),
`atelier_visuels_page_ia.py` (panneau), `test_atelier_visuels_ia.py` ; modifier `atelier_visuels_web.py`.
Interfaces produites : `fournisseurs() -> list[{"id","nom","externe": bool,"gratuit": str,"cle_requise": bool}]` ;
`demande(env, fournisseur, consigne, empreinte_photo, confirme: bool) -> {"svg"|"erreur", "quota"}` (refuse si `confirme`
est faux pour un fournisseur externe ; le SVG rendu passe par `atelier_visuels_fond.nettoie_svg`) ; `quota(fournisseur) ->
{"envois_jour", "plafond", "etat": "ok"|"orange"|"rouge", "reprise": str | None}` ; routes `GET /ia/fournisseurs`,
`POST /ia/demande`, `POST /ia/cle` (la clé n'est jamais renvoyée).
- [ ] Lire la documentation de chaque offre gratuite visée (limites, données utilisées pour l'entraînement) et noter le
  résultat dans le README ; choisir avec l'utilisateur les fournisseurs retenus
- [x] Test écrit : `demande` refuse sans confirmation pour un fournisseur externe ; clé jamais présente dans une réponse HTTP,
  un journal ni le dépôt ; réponse 429 simulée = quota « rouge » et aucun réessai ; SVG hostile rendu par un faux
  fournisseur = nettoyé ; plafond saisi à 80 % = « orange » — preuve : `test_atelier_visuels_ia.py` VERT (modules `atelier_visuels_ia.py`, `atelier_visuels_ia_config.py`, 2026-11-13)
  - [x] Routes `GET /ia/fournisseurs`, `POST /ia/demande` (corps jusqu'à 10 Mo pour cette route seule), `POST /ia/cle`, `GET /ia/quota` branchées — preuve : `test_atelier_visuels_web.py` VERT (externe sans confirmation = refus sans appel, clé absente de toutes les réponses, 413 à 10 Mo, 403 sans en-tête)
- [ ] Relire `atelier_ecrans_remarques.py` (options `OPTIONS`, `reglages_sans_hooks`, délai, arrêt de l'arbre, journal,
  contrôle des fichiers changés) et en importer les fonctions communes au lieu de les recopier ; remarques épinglées sur une
  zone de la photo (états ouverte, proposée, appliquée, refusée) dans `outils_docs/visuels_accueil/cartes/<env>/remarques.json`
- [x] Fournisseur *Claude Code local* (`claude -p`, lecture seule, jamais bypassPermissions, hooks coupés) puis Ollama,
  puis une API externe au choix de l'utilisateur ; chacun avec un faux fournisseur dans le banc — preuve : `atelier_visuels_ia.py` (ClaudeLocal, Ollama, ApiExterne) et `test_atelier_visuels_ia.py` VERT (faux claude, faux serveurs locaux, faux fournisseurs ; aucun essai réel)
- [x] Panneau de la page : consigne, choix du procédé, avertissement avant envoi, compteur de quota, résultat ouvert dans
  l'éditeur ; sonde Chrome avec faux fournisseur — preuve : sonde_ia VERT (faux fournisseur) : avertissement nommant le service, confirmation à refaire à chaque envoi, quota, clé jamais relue (ni DOM ni stockage), SVG nettoyé ouvert dans l'éditeur en une étape annulable, commit feb1af500
- [ ] Essai réel avec la photo de l'utilisateur, un fournisseur à la fois et son accord, rendu comparé à la référence
  (`rendu-cible-page-reelle.png`) ; `relecteur-pages-web`
- [ ] Commit `feat(atelier-visuels): assistant IA facultatif, quota et avertissements (A9)`

## Améliorations restantes
- [ ] [projet] Commander un relais en cliquant son voyant (spec § 3, non-objectif)
- [ ] [projet] vtracer côté PC si l'A0 juge le tracé du navigateur insuffisant (spec § 5, voie 2)
- [ ] [projet] Plusieurs visuels par carte, visuel sur les écrans HASPmota/LVGL

## Vérification
Bancs : `test_atelier_visuels_*.py`, `test_visuel_js.mjs`, sonde `test_atelier_visuels_page_chrome.py`,
`berry/banc_visuel.py`, `banc_demarrage.py`, `banc_repartition_fichiers`, `build/test_cible_atelier_visuels.py`,
`build/test_garde_build.py`, `verifie_references_docs.py`. Sur carte : compilation par la page Build, capture Chrome
de la vraie page avec largeur mesurée, tas et `UfsFree` lus. Un banc PC ne prouve ni la RAM, ni le rendu, ni le canal.
