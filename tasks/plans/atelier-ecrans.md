---
chantier: atelier-ecrans
titre: Atelier des écrans (page 7960) : une description d'écran, deux interfaces générées
objectif: Modifier sur le PC la disposition d'un écran tactile de carte (objets, boutons, pages) et y épingler des remarques, puis générer de la même description le pages.jsonl de HASPmota et le code LVGL pur en Berry
statut: actif
cree: 2026-11-11
maj: 2026-11-13 (A19 : page Système construite par l'atelier, faite pour l'écran des débits ; actions renumérotées dans l'ordre du plan, livraison sur la carte en dernier : A20 ; A18 catalogue d'icônes et A19 page Système ajoutées ; A17 : bancs, description, page faits)
---
# Atelier des écrans

## Contexte
Demande de l'utilisateur du 2026-11-11, version **C** retenue parmi trois (A : remarques seules ; B : éditeur HASPmota ;
C : description neutre dont on génère les deux interfaces). Ce plan est l'action A9 du plan
`tasks/plans/debits-deux-cartes.md` ; l'écran des débits (Waveshare 7B, 1024 × 600, pages A « Débits », D « Courbes »
et « Réglages ») est son premier cas réel.

**Spec validée le 2026-11-12 : `docs/superpowers/specs/2026-11-11-atelier-ecrans-design.md`** (à lire avant toute
action : décisions 1 à 7 de son § 4, conception au § 5). Maquette retenue : `outils_docs/atelier_ecrans/modele-retenu.png`
(`maquettes_atelier_ecrans.html?m=R`), décisions détaillées dans `outils_docs/atelier_ecrans/README.md`.

En bref : une description neutre `outils_docs/atelier_ecrans/cartes/<env>/ecran.json` (HORS du dossier de la carte, qui
part en flash) et ses remarques `remarques.json` à côté ; un catalogue `outils_docs/schemas/catalogue_ecran.json` ;
deux générateurs (`pages.jsonl`, `ecranLvgl.be`, écrits dans `data/<lieu>/<carte>/`) ; la page 7960 (modèle A, remarques
de C avec bouton « Traiter les remarques (Claude) » en session `claude -p` LECTURE SEULE, fenêtre basse des fichiers
générés, tableau des objets en onglet, zoom 100 %, bascule Sombre / Clair, listes carte et écran, changement d'écran
par mise à l'échelle proposée, capture de la carte par `lv.screenshot()`). L'interface LVGL pur des débits ne s'écrit
pas à la main : premier produit du générateur (A5).

**Lien avec la skill globale `lvgl-haspmota`** : le catalogue du dépôt est la source unique des objets, attributs et
polices ; la skill y renvoie et décrit l'atelier ; les remarques sont traitées par Claude avec cette skill.

**Sources : ouvertes seulement.** LVGL (MIT), Tasmota, HASPmota et la liaison Berry (GPL) : attributs et rendu lus dans
`lib/libesp32_lvgl/`. Pas de rétro-ingénierie d'éditeurs propriétaires (SquareLine Studio, LVGL Pro).

### Contraintes globales
- Fichiers sous 500 lignes ; aucune nouvelle dépendance Python ni JS sans accord.
- Python des bancs `outils_pc/` : `"$USERPROFILE/.platformio/penv/Scripts/python.exe"` ; bancs sur copies temporaires.
- Compilation et FS par la page Build (:7700) seulement ; écriture refusée pendant un build.
- `data/fs/*.be`, `_persist.json`, `user_config_override.h` : accord de l'utilisateur avant modification (dans la page :
  diff montré puis confirmation explicite).
- Ressources d'écran (images, fonds, polices ajoutées) sous `/sd`, choisies AVEC l'utilisateur.
- Logs Berry : charte du `CLAUDE.md` ; avant commit : `relecteur-berry` (Berry) et `relecteur-pages-web` (page).
- Modules Python préfixés `atelier_ecrans_` dans `outils_docs/scripts_python/outils_pc/`, sur le modèle de
  `atelier_graphiques_*` (serveur `fabrique_gestionnaire`, `acces_web.Acces`, `fichiers_berry_sauvegarde.Transaction`,
  `lieux.pour_page`). Env du premier cas : `tasmota32s3-bureau-ecran-debits-pac` (dossier
  `data/bureau/tasmota32s3-ecran-debits-pac/`).
- Messages de commit en français, sans accents, sans trailer ; `git commit -- <chemins>` puis `git show --stat HEAD`.

### Points de vigilance (non couverts par la spec, un test chacun dans l'action indiquée)
1. Description modifiée dans le dépôt pendant que la page est ouverte : écriture refusée (empreinte périmée), rien
   écrasé (A8).
2. Carte hors ligne : aperçu en valeurs simulées signalé, capture refusée avec un message, page utilisable (A6).
3. `claude` absent, limite d'utilisation atteinte ou délai dépassé : état « échec » lisible, `remarques.json` intact,
   bouton de nouveau disponible (A7).
4. Texte d'objet avec accents, guillemets, barre oblique inverse, `%` : `pages.jsonl` valide en UTF-8 et `ecranLvgl.be`
   qui compile (A4, A5).
5. Env sans `display.ini`, ou `display.ini` sans ligne `:H` lisible : « aucun écran » dans la liste, pas d'erreur 500 (A2).

## A1 — Conception avec l'utilisateur
- [x] Maquettes de la page, choix de l'utilisateur — preuve : `outils_docs/atelier_ecrans/modele-A.png` à `modele-D.png`
  et `README.md` (choix du 2026-11-12 : A + remarques de C avec bouton « Traiter les remarques (Claude) » + zoom 100 % +
  fenêtre basse de C + tableau de D en onglet, bascule sombre/clair ; `modele-retenu.png`, `modele-retenu-sombre.png`)
- [x] Questions tranchées (objets du palier, remarques, aperçu, LVGL des débits) — preuve : décisions 1 à 7 du § 4 de
  la spec ; capture par `xdrv_52_3_berry_lvgl.ino::lv0_screenshot` ; LVGL des débits produit par A5
- [x] Spec validée, actions A2 à A10 détaillées — preuve : « ok » de l'utilisateur du 2026-11-12 sur
  `docs/superpowers/specs/2026-11-11-atelier-ecrans-design.md` (relue par un sous-agent constructeur) ; actions ci-dessous

## A2 — Catalogue commun (objets, attributs, polices, écrans)
Fichiers : créer `outils_pc/atelier_ecrans_catalogue.py`, `outils_pc/test_atelier_ecrans_catalogue.py`,
`outils_docs/schemas/catalogue_ecran.json` ; modifier la skill `~/.claude/skills/lvgl-haspmota/` (références).
Produit : `genere(racine) -> dict` (clés `objets`, `polices`, `ecrans`), `charge(racine) -> dict` (lit le JSON),
`verifie(racine) -> list[str]` (écarts entre le fichier et les sources, vide = à jour), `ecrans_des_envs(racine) ->
dict[env, cle_ecran | None]` ; ligne de commande `--generer` / `--verifier` (code 1 si écart).
Forme : `objets[<type>] = {"palier": 1|2, "attributs": {<nom>: {"type": "entier"|"texte"|"couleur"|"police"|"action"|
"booleen", "min"?, "max"?}}}` ; `polices = [{"nom", "tailles": [..], "source": "firmware"|"sd", "fichier"?}]` ;
`ecrans[<cle>] = {"pilote", "largeur", "hauteur", "bus", "tactile", "integre_a"?, "display_ini": <chemin source>,
"envs": [..]}` (clé = `<pilote>_<largeur>x<hauteur>`).
- [x] Banc d'abord (rouge) : `test_objets_palier` (les 7 types `label btn bar obj chart arc slider` en palier 1, les — preuve : rouge partiel lu (catalogue absent -> FileNotFoundError ; tactile ILI9488 corrige dans le banc), puis `test_atelier_ecrans_catalogue.py` VERT, commit 58b61ebb1
  autres classes `lvh_*` en palier 2), `test_attributs_pages_debits` (toute clé du `pages.jsonl` des débits sauf `page`,
  `id`, `obj`, `comment` est un attribut connu de son type), `test_polices` (RobotoCondensed `.ttf` de la carte et ses
  tailles 20, 24, 32, 36 présentes), `test_ecrans` (deux écrans : `ST7262_1024x600` RGB tactile, `ILI9488_480x320` SPI),
  `test_env_sans_ecran` (env sans `display.ini` -> `None` ; `display.ini` sans `:H` -> `None`, pas d'exception),
  `test_temoin_police_retiree` (copie temporaire des sources sans une police -> `verifie` non vide)
- [x] `genere` : classes et attributs lus dans `lib/libesp32_lvgl/lv_haspmota/src/embedded/lv_haspmota.be` (setters et — preuve : `atelier_ecrans_catalogue.py::genere`, banc VERT dont `test_temoin_police_retiree` (ttf retire et robotocondensed 24 desactivee -> ecart `polices`), 58b61ebb1
  tables de correspondance de `lvh_obj` et de chaque classe, à identifier en lisant le fichier) ; polices compilées lues
  dans les sources du firmware (gardes de l'env de la carte) et `.ttf` des dossiers de cartes ; écrans d'après
  `data/*/*/display.ini` (ligne `:H`) ; banc VERT, témoin rouge lu
- [x] `catalogue_ecran.json` généré et commité ; `--verifier` code 0 — preuve : `--verifier` -> « catalogue a jour », code 0 ; 58b61ebb1
- [x] Skill `lvgl-haspmota` : ses références renvoient au catalogue (source unique) et décrivent l'atelier (page 7960, — preuve : SKILL.md (section « Atelier des écrans et catalogue »), references/haspmota.md et polices.md renvoient au catalogue ; skill hors depot git (~/.claude), pas de commit
  description, remarques) ; commit

## A3 — Description neutre de l'écran
Fichiers : créer `outils_pc/atelier_ecrans_description.py`, `outils_pc/test_atelier_ecrans_description.py`,
`outils_docs/atelier_ecrans/cartes/tasmota32s3-bureau-ecran-debits-pac/ecran.json` ; modifier
`berry/banc_ecran_debits.py` (+ `.be`) pour le contrôle de la section `modele`.
Consomme : `atelier_ecrans_catalogue.charge`. Produit : `chemin(racine, env) -> Path`, `charge(racine, env) -> dict |
None`, `valide(desc, catalogue) -> list[str]` (messages en français, vide = valide), `empreinte(octets) -> str`.
Forme de `ecran.json` : `{"version": 1, "ecran": <clé du catalogue>, "orientation": 0, "modele": [{"cle":
"voies[].debit", "type": "texte", "exemple": "4,20"}, ..], "pages": [{"n": 0, "titre": "Commun"}, ..], "objets": [{"id",
"page", "type", "x", "y", "l", "h", "attributs": {..}, "liaison"?: {"cle", "attribut"}, "toucher"?: {"page"|"commande"|
"fonction"}, "commentaire"?}]}`.
- [x] Banc à mutants d'abord (rouge) — preuve : test_atelier_ecrans_description.py lancé sans module = ModuleNotFoundError (rouge), puis 25 mutants refusés chacun avec son message (vert) ; description de référence valide ; mutants refusés chacun avec son message :
  objet hors écran (x + l > largeur), police absente, taille absente, attribut inconnu du type, type de palier 2,
  liaison vers une clé absente de `modele`, `id` en double sur une même page, page inconnue
- [x] `valide` et `charge` ; banc VERT, chaque mutant rouge lu — preuve : atelier_ecrans_description.py, `BANC_ATELIER_ECRANS_DESCRIPTION: OK (25 mutants)`, message attendu vérifié par mutant
- [x] `ecran.json` des débits écrit — preuve : 82 objets, mêmes ids et coordonnées que pages.jsonl (vérifié par le banc), valide() vide ; écrit à partir du `pages.jsonl` actuel (pages Commun, Débits, Courbes, Réglages ; lignes
  `comment` gardées en `commentaire`) ; `valide` vide
- [x] Section `modele` contrôlée — preuve : banc_ecran_debits.py, 16 clés rendues = 16 décrites, 3 témoins rouges, banc entier VERT ; cas : cas ajouté à `berry/banc_ecran_debits.py` qui fait rendre `ecranDebitsFonctions.modele(now)`
  sous `berry.exe` (bouchons existants) et compare ses clés à la section ; témoin : une clé retirée de la section -> rouge
- [x] Commit — preuve : voir git log (commit A3)

## A4 — Générateur HASPmota
Fichiers : créer `outils_pc/atelier_ecrans_haspmota.py`, `outils_pc/test_atelier_ecrans_haspmota.py`.
Consomme : `atelier_ecrans_description.charge`. Produit : `genere(desc) -> str` (texte du `pages.jsonl`, une ligne JSON
par page et par objet, UTF-8, `ensure_ascii=False`), `ecarts(attendu: str, obtenu: str) -> list[str]` (équivalence
SÉMANTIQUE : mêmes lignes dans le même ordre, mêmes clés et valeurs, ordre des clés libre).
- [x] Banc d'abord (rouge) — preuve : ModuleNotFoundError puis 3294ce647, test_atelier_ecrans_haspmota OK : `test_debits_identique` (`ecarts(pages.jsonl du dépôt, genere(ecran.json des débits)) ==
  []`), `test_texte_special` (texte `Débit "5" \ 100 %` -> ligne qui se relit par `json.loads` à l'identique),
  `test_ecart_detecte` (une valeur changée -> un écart nommant la ligne et la clé)
- [x] `genere` ; banc VERT — preuve : 3294ce647, BANC_ECRANS_HASPMOTA: OK
- [x] `berry/banc_ecran_debits.py` VERT sur le `pages.jsonl` généré (copie temporaire) — preuve : banc_ecran_debits VERT sur copie, pages.jsonl genere identique a l'octet, 3294ce647 ; commit

## A5 — Générateur LVGL pur
Fichiers : créer `outils_pc/atelier_ecrans_lvgl.py`, `outils_pc/test_atelier_ecrans_lvgl.py`,
`berry/banc_ecran_lvgl.py` + `.be` (+ bouchons `berry/bouchons_berry/ecran_lvgl/` : objets `lv.*` simulés qui
enregistrent les appels) ; écrire `data/bureau/tasmota32s3-ecran-debits-pac/ecranLvgl.be` (généré).
Consomme : `atelier_ecrans_description.charge`. Produit : `genere(desc) -> str` (module Berry `ecranLvgl` :
`demarre()` et `affiche(modele)` de l'API en tête de `ecranDebitsFonctions.be`, cache par objet et attribut, fonctions
nommées, logs par `logFonctions.log` et constantes `LOG_LEVEL_*`).
- [x] Banc d'abord (rouge) : `test_compile` (le texte généré passe `berry/verifie_berry.py`, charte des logs sans — preuve : `test_atelier_ecrans_lvgl.py` ROUGE `ModuleNotFoundError: atelier_ecrans_lvgl`, `banc_ecran_lvgl.py` ROUGE `FileNotFoundError ecranLvgl.be` (avant le générateur) ; en cours d'écriture ROUGE encore sur 82 objets/liaisons absentes et 530 lignes
  avertissement), `test_texte_special` (même texte qu'en A4 -> compile, chaîne restituée à l'identique) ; banc Berry :
  `demarre()` crée les objets des 4 pages aux positions de la description, deux `affiche(modele)` identiques -> aucun
  appel au second, une valeur changée -> un seul appel
- [x] `genere` ; bancs VERT — preuve : `BANC_ECRANS_LVGL: OK` (compile sans avertissement, témoins module cassé et préfixe hors charte, texte spécial restitué, commande et args restitués, refus) ; `banc_ecran_lvgl.py` VERT (82 objets = ecran.json, 4 pages, polices chargées une fois, couleurs selon l'état, courbe, cache : 0 appel au 2e affiche, 1 au changement) et 13 mutants rouges
- [x] `ecranLvgl.be` des débits généré et écrit ; `build/test_interface_ecran.py` VERT (le fichier présent, interface — preuve : fichier de 484 lignes, `verifie_berry` 0 erreur 0 avertissement ; `BANC_INTERFACE_ECRAN : VERT` ; `banc_demarrage.py` VERT (10 cartes, référence de l'affichage inchangée grâce à `preparation_boot.be::autresInterfaces`) ; variante lvgl `--dossier ... --cenv <copie custom_interface_ecran = lvgl>` VERT (`/ecranLvgl.bec` seul, 0 erreur) ; témoin sans l'option : les deux interfaces compilées
  `haspmota` : exclu du FS) ; `banc_demarrage.py` de la variante `lvgl` VERT
- [x] Commit (le fichier généré compris) ; noter dans `debits-deux-cartes` A8 que l'interface LVGL vient du générateur — preuve : d3973eaa0 (12 fichiers, `ecranLvgl.be` compris), note sous l'étape « Interface LVGL pur » de `debits-deux-cartes.md` A8

## A6 — Page web de l'atelier (port 7960)
Fichiers : créer `outils_pc/atelier_ecrans_web.py` (serveur, routes), `atelier_ecrans_page.py` (HTML, CSS, thème),
`atelier_ecrans_page_js.py` (canevas, palette, propriétés, tableau, pages, zoom), `atelier_ecrans_capture.py`,
`test_atelier_ecrans_web.py`, `test_atelier_ecrans_page_chrome.py` ; `build/cible_atelier_ecrans.py` +
`build/test_cible_atelier_ecrans.py` ; modifier `annuaire_registre.py` (outil `atelier_ecrans`, groupe Maintenance,
`_port("http", 7960)`, `lieu=True`), `.claude/hooks/garde_build.py` (`CIBLES_OUTILS`), `.vscode/tasks.json` (tâche
« Outil : atelier des écrans »), cible déclarée dans le pre-script comme les autres `cible_*.py`.
Consomme : A2 à A5. Produit, routes (JSON) : `GET /cartes` (envs par lieu, écran de chaque env, IP), `GET /catalogue`,
`GET /description?env=` (description + empreinte), `POST /apercu` {env, description} -> fichiers générés et leurs diffs,
`GET /valeurs?env=` (JSON SENSOR de la carte ou valeurs simulées + drapeau `simule`), `POST /capture` {env} -> image ou
refus, `GET /police?nom=` (`.ttf` du catalogue, chemin jamais pris dans la requête).
- [x] Banc serveur d'abord (rouge), sur copie temporaire — preuve : 8e5664d02, test_atelier_ecrans_web.py rouge puis VERT ; routes ci-dessus ; env inconnu -> 400 ; requête sans en-tête
  anti-CSRF -> 403 ; carte injoignable -> `/valeurs` simulé avec `simule: true` et `/capture` refusé avec message ;
  `nom` de police hors catalogue -> 404 ; adresse de la carte prise au cenv, jamais à la requête
- [x] Serveur et routes ; banc VERT — preuve : 8e5664d02 + ed4b3f387 (cible, tuile, tâche), test_atelier_ecrans_web.py VERT le 2026-11-12
- [x] Page (maquette `modele-retenu.png`) — preuve : commit A6b, sonde test_atelier_ecrans_page_chrome.py VERTE (28 vérifications, 2 passes) ; en-tête (liste des cartes par `lieux.pour_page`, liste des écrans
  présélectionnée et marquée « celui de l'env », état en ligne, bascule Sombre / Clair mémorisée par `localStorage`
  sous try/catch), colonne gauche, onglets « Écran » / « Tableau des objets », zoom − / + / 100 %, grille aimantée,
  glisser-déposer, poignées, annuler / rétablir, propriétés limitées au catalogue (taille de police absente refusée avec
  les tailles possibles), fenêtre basse des fichiers générés avec différences colorées
- [x] Capture : `atelier_ecrans_capture.capture(ip, get) -> bytes` (`Br lv.screenshot()`, téléchargement, effacement du
  fichier sur la carte) ; banc avec carte simulée — preuve : `atelier_ecrans_capture.py`, route POST /capture ; sonde Chrome
  « capture affichée » (vrai BMP 4 x 2 rendu par un faux `get`) VERT. L'essai réel sur le 7B est passé dans A20
- [x] Sonde Chrome hermétique — preuve : test_atelier_ecrans_page_chrome.py VERT, test_cible_atelier_ecrans.py et test_atelier_ecrans_web.py VERTS le 2026-11-12, Chrome arrêté (0 sonde_*) ; (thème clair et sombre, glisser un bouton, zoom 100 %, aucune erreur console, Chrome
  arrêté à la fin) VERT ; tuile de l'annuaire, tâche VS Code, cible détachée (`test_cible_atelier_ecrans.py` VERT,
  `test_garde_build.py` VERT)
- [x] Commit — preuve : ed4b3f387 (serveur et routes), dba364cb0 (page et sonde)

## A7 — Remarques épinglées et traitement par Claude
Fichiers : créer `outils_pc/atelier_ecrans_remarques.py`, `atelier_ecrans_page_remarques.py` (JS de l'onglet),
`test_atelier_ecrans_remarques.py`.
Consomme : A3, A6. Produit : `charge(racine, env) -> list`, `valide_propositions(sortie: str, desc, catalogue) ->
(list, list[str])`, `applique(desc, proposition) -> dict` (nouvelle description, sans écrire), `Traitement` (un seul
à la fois : `lance(racine, env)`, `etat() -> {"etat": "libre"|"en_cours"|"fini"|"echec", "debut", "message"}`) ;
routes `GET /remarques?env=`, `POST /remarques` (épingler, répondre, refuser), `POST /remarques/traiter`,
`GET /remarques/etat`, `POST /remarques/appliquer` (rend la description modifiée, n'écrit rien).
Forme d'une remarque : `{"id", "cible": {"objet": id} | {"zone": [x, y, l, h]} | {"page": n}, "texte", "date", "etat":
"ouverte"|"proposee"|"appliquee"|"refusee", "proposition"?: {"texte", "operations": [{"op": "modifie"|"ajoute"|"retire",
"id", "attributs"?}]}, "reponses": [..]}`.
- [x] Vérifier les options de `claude -p` qui imposent la LECTURE SEULE — preuve : claude 2.1.319, --tools Read,Grep,Glob --permission-mode dontAsk --strict-mcp-config ; demande d'écrire un témoin : non écrit, outils vus Read/Grep/Glob seulement (2026-11-12) ; consigne par l'entrée standard (claude.CMD) (liste d'outils permis, mode de permission non
  interactif, jamais `bypassPermissions`) et la sortie JSON ; si impossible, livrer le repli (bouton qui copie la
  consigne) et le noter ici
- [x] Banc d'abord (rouge), `claude` remplacé par un faux exécutable — preuve : test_atelier_ecrans_remarques.py 3 KO puis VERT (50), 3 mutants lus rouges (contrôle du dépôt, remarque ouverte, depuis ce PC) : propositions valides écrites par la PAGE dans
  `remarques.json` ; opération vers un `id` inconnu ou un attribut hors catalogue rejetée ; faux `claude` qui modifie un
  fichier du dépôt -> résultat rejeté (contrôle `git status` et empreintes) ; `claude` absent, code d'erreur, délai de
  10 min dépassé -> état `echec` avec message, `remarques.json` intact ; second lancement pendant `en_cours` -> refus
- [x] Module, routes et onglet « Remarques » — preuve : commit A7, test_atelier_ecrans_remarques.py VERT, sonde Chrome VERTE (38, 2 passes), relecture dédiée traitée (hooks coupés par --settings disableAllHooks, prouvé par un hook témoin) (épingler sur un objet, une zone tracée, la page ; Appliquer / Refuser /
  Répondre ; journal dans `%LOCALAPPDATA%\outils_tasmota\atelier_ecrans\`) ; bancs VERT, sonde Chrome étendue VERT
- [x] Essai réel : une remarque traitée par le vrai `claude -p`, proposition appliquée sur le canevas ; commit — preuve : remarque 1 (noms des voies trop petits) proposée par le vrai `claude -p`, appliquée puis écrite par l'utilisateur dans la page le 2026-11-12 (« ça fonctionne ») : six `text_font` passés à `RobotoCondensed-Regular.ttf-28` dans `ecran.json`, `pages.jsonl` et `ecranLvgl.be` régénérés, `remarques.json` état `appliquee` ; bancs de description, HASPmota, LVGL, `banc_ecran_debits`, `banc_demarrage` VERT

## A8 — Écriture dans le dépôt, changement d'écran, envoi
Fichiers : créer `outils_pc/atelier_ecrans_ecriture.py`, `atelier_ecrans_ecran.py`, `test_atelier_ecrans_ecriture.py`,
`test_atelier_ecrans_ecran.py`.
Consomme : A2 à A7, `fichiers_berry_sauvegarde.Transaction`, `atelier_graphiques_televerse.url`. Produit :
`prevu(racine, env, desc) -> list[{"rel", "avant", "apres"}]`, `ecrit(racine, env, desc, empreinte) -> list[str]`
(refus si empreinte périmée ou build en cours) ; `met_a_echelle(desc, ecran_cible, catalogue) -> (dict, list[str])`
(avertissements : cible tactile sous 40 px, texte qui déborde, objet hors écran) ; `changement(racine, env, ecran_cible)
-> list[{"rel", "avant", "apres"}]` (`display.ini` repris de l'env qui porte l'écran, base de l'env si besoin, conflit
de broches avec le persist -> refus motivé, avertissement si écran intégré à une autre carte) ; routes `POST /diff`,
`POST /ecrire`, `POST /ecran/diff`, `POST /ecran/changer`.
- [x] Banc d'abord (rouge), copie temporaire — preuve : test_atelier_ecrans_ecriture.py et test_atelier_ecrans_ecran.py rouges puis VERTS (2026-11-12) ; écriture de `ecran.json`, `pages.jsonl`, `ecranLvgl.be` en une
  transaction ; description modifiée sur le disque après lecture -> refus, rien écrit ; build en cours -> refus ;
  mise à l'échelle 1024 × 600 -> 480 × 320 (positions et tailles au rapport, police ramenée à la taille la plus proche,
  bouton de 46 px -> 25 px signalé) ; changement d'écran : diff du `display.ini`, conflit de broches refusé
- [x] Modules et routes ; bancs VERT — preuve : commit A8, sonde Chrome VERTE (52, 2 passes), test_atelier_ecrans_web.py VERT (routes, 403, 400, 409), relecture traitée (broches :H RGB sans la fréquence) ; dans la page, « Écrire dans le dépôt » (diff puis confirmation), mode
  « changement d'écran » (diff, confirmation, rappel de recompiler par la page Build), lien « Envoyer par la page
  Build ↗ » (`?env=` et fichiers) ; sonde Chrome VERT
- [x] Commit — preuve : commit A8 (feat(atelier-ecrans): A8)

## A9 — Ressources sous `/sd`
- [x] Liste des ressources utiles (fonds, icônes, polices ajoutées) proposée à l'utilisateur, choix fait ; règle de — preuve : choix « Règle + import de polices » du 2026-11-12 ; branche images de `gestionFileFolder.be::listeEtRepartitLesFichiers` (.png/.jpg/.bmp -> /sd/images), `berry/banc_repartition_fichiers.py` VERT, 9 mutants rouges, relecteur-berry « prêt » ; aucune image déposée avant le palier 2
  rangement des images dans `data/fs/gestionFileFolder.be::listeEtRepartitLesFichiers` (accord pour `data/fs`)
- [x] Import d'une police nouvelle depuis la page (demande du 2026-11-11) : liens vers les sites de polices et de — preuve : `atelier_ecrans_polices.py` + panneau `atelier_ecrans_page_polices.py`, routes /polices/analyse et /polices/importer ; `test_atelier_ecrans_polices.py` VERT (mutants licence, Latin-1, borne cmap 51 s, struct.error rouges) ; sonde Chrome 55 OK dont l'import par un vrai fichier ; relecteur-pages-web : B1, C1, C2, M1 à M3 corrigés. shortcut : .ttf seulement, pas de .bin LVGL (catalogue et générateurs ne les connaissent pas)
  conversion de la skill `lvgl-haspmota` (`references/polices.md`, « Trouver et importer une police nouvelle ») ; fichier
  `.ttf` ou `.bin` déposé par l'utilisateur, licence et couverture Latin-1 contrôlées, tailles proposées, rangé sous
  `/sd/polices/` et ajouté au catalogue (`atelier_ecrans_catalogue.genere` relancé) ; banc

## A10 — Documentation, relecture, essai réel
- [x] `outils_docs/README.md` (mode d'emploi), carte des documents du `CLAUDE.md`, `verifie_references_docs.py` 0 défaut — preuve : section « Atelier des écrans (page web) » du README, entrée `atelier_ecrans_web.py` de CLAUDE.md, « 20 document(s), 0 defaut(s) »
- [x] `relecteur-pages-web` et `relecteur-berry` sur le chantier ; corrections confirmées faites — preuve : pages web relues à chaque action (A6b, A7, A8, A9, défauts corrigés) ; relecteur-berry sur `ecranLvgl.be` : toucher mort écarté (`lvgl_glob.be::lvgl_event_dispatch` rappelle l'instance enregistrée), police nil journalisée, courbe qui repart, cache par objet corrigés dans `atelier_ecrans_lvgl_moteur.py` ; `banc_ecran_lvgl.py` VERT avec 2 mutants de plus, `test_atelier_ecrans_lvgl.py` OK, `banc_demarrage.py` VERT. Laissés : `demarre()` rappelé (latent, un seul appel), cache des attributs statiques, un seul toucher en attente

## A11 — Écrans des autres cartes au catalogue
Conception : `docs/superpowers/specs/2026-11-12-atelier-ecrans-ameliorations-design.md` § 4. Ordre de réalisation :
A11, A12, A13, A14 (§ 8).
- [x] Banc d'abord (rouge) : trois sources (cartes, `outils_docs/atelier_ecrans/display/`, `tasmota/displaydesc/`) ;
  clés existantes inchangées (`ST7262_1024x600`) ; collision -> `<pilote>_<l>x<h>@<fichier>` ; tactile par `:UTI`, `:TI`,
  `:TS`, `:TR` ; `display.ini` exclu du FS ou env sans LVGL -> écran non rattaché ; bpp 1 -> `couleur: false`
  — preuve : `test_atelier_ecrans_catalogue.py::test_ecrans`, `::test_bibliotheque_perso`, `::test_env_sans_ecran` ; 3 mutants
  (exclusion, tactile, cartes) lus rouges. Env sans LVGL : non traité (`shortcut:` dans `_fichiers`, aucun cas au dépôt)
- [x] `atelier_ecrans_catalogue.py` (sources, clés, champs `source`, `fichier`, `bus`, `bpp`, `couleur`) ; catalogue
  régénéré ; banc VERT avec mutants ; liste des écrans de la page limitée aux écrans couleur
  — preuve : 61 écrans (60 amont, 1 carte, 47 couleur), le fichier garde son nom dans `display_ini` ; liste de la page en
  trois `optgroup` (cartes, bibliothèque, Tasmota), monochromes masqués (sonde : groupe Tasmota, SSD1306 absent)
- [x] Changement d'écran (A8) : `display.ini` repris de la source de l'écran (carte, bibliothèque ou amont) ; bancs
  `test_atelier_ecrans_ecran.py` et sonde Chrome VERT
  — preuve : `atelier_ecrans_ecran.py::changement` (amont/bibliothèque signalés, carte sans écran = description vierge,
  bouton « Proposer » ouvert à une carte sans écran) ; les 10 bancs de l'atelier, la sonde et `test_cible_atelier_ecrans.py`
  VERT le 2026-11-13
- [x] Commit — preuve : `413e30a6d`

## A12 — Onglet « display.ini » : lire, expliquer, valider, créer
Conception : § 6 de la même spec. Bibliothèque personnelle `outils_docs/atelier_ecrans/display/` (+ `<nom>.notes.md`).
- [x] Référence `outils_docs/schemas/display_ini_parametres.json` (sections, arguments, bases, ordre, pièges, sources) ;
  banc de concordance avec `uDisplay.cpp::uDisplay::uDisplay` (section absente de la référence ou référence sans lecture
  dans le code -> rouge), mutants — preuve : `test_atelier_ecrans_display.py::test_concordance` VERT ; mutants
  référence sans `:TR` et avec `:Z` inventée lus rouges (2026-11-13)
- [x] Analyseur et contrôles du § 6.4 (`atelier_ecrans_display.py`) : banc d'abord (rouge) sur les trois `display.ini` du
  dépôt et les 60 amont (aucune erreur fausse sur un fichier amont), pièges fabriqués un par un ; puis VERT — preuve :
  `test_atelier_ecrans_display.py` VERT (63 fichiers, 14 pièges, tolérances lues dans `uDisplay_utils.cpp::strlen_ln`
  et `::next_val`, insertion par rang) ; six mutants de `atelier_ecrans_display.py` lus rouges (2026-11-13)
- [x] Routes (liste, lecture expliquée, diff, enregistrement dans la bibliothèque, copie depuis l'amont, notes) ; refus
  pendant un build, empreinte périmée, nom de fichier hors bibliothèque ; banc VERT — preuve : `test_atelier_ecrans_display_fichiers.py`
  VERT (21 contrôles ; copie amont = enregistrer son texte sous un nom de la bibliothèque) ; mutants build, empreinte, nom,
  catalogue lus rouges ; `test_atelier_ecrans_web.py` VERT (2026-11-13)
- [x] Onglet de la page : liste des fichiers, éditeur ligne par ligne expliqué, panneau « Paramètres » avec « Ajouter » à la
  bonne place, notes de terrain ; sonde Chrome VERT ; relecture `relecteur-pages-web` — preuve : `atelier_ecrans_page_display.py` ;
  `test_atelier_ecrans_page_chrome.py::sonde_display` VERT ; relecture : sécurité conforme, 4 défauts d'état corrigés
  (confirmation périmée, message effacé, réponses tardives, catalogue annoncé) et contrôlés par la sonde (2026-11-13)
- [x] « Appliquer à la carte » par le chemin du changement d'écran (diff, broches du persist, lien page Build) — preuve :
  `atelier_ecrans_page_display.py::appliqueACarte` ; sonde : proposition puis display.ini de la carte = fichier de la
  bibliothèque (2026-11-13)
- Essai sur la carte : déplacé dans A20 (demande du 2026-11-13)
- [x] Mode d'emploi (`outils_docs/README.md`), carte des documents du `CLAUDE.md` ; commit — preuve : commit 81450c2d9
  (2026-11-13)

## A13 — Import d'un `pages.jsonl` écrit à la main
Conception : § 5 de la même spec.
- [x] Banc d'abord (rouge) : import puis génération HASPmota = mêmes objets JSON que la source, sur les six `pages.jsonl`
  du dépôt ; objets hors catalogue gardés en `brut` ; ligne non JSON gardée en commentaire et signalée — preuve :
  `test_atelier_ecrans_import.py` rouge (module absent) puis VERT ; lecture comme HASPmota (page courante héritée, lignes
  vides ignorées) ; débits 82 objets éditables / 0 brut, démo HASPmota 20 / 161 (2026-11-13)
- [x] Description : objet `brut` accepté par le validateur, réécrit tel quel par le générateur HASPmota, signalé absent de
  `ecranLvgl.be` ; import (`atelier_ecrans_import.py`) ; bancs VERT avec mutants — preuve : 12 mutants (import, générateurs,
  validateur) lus rouges ; bancs description, haspmota, lvgl, ecran, ecriture, remarques VERT (2026-11-13)
- [x] Page : bouton « Importer le pages.jsonl de la carte », diff avant écriture, objets `brut` hachurés et non éditables
  sur le canevas ; sonde Chrome VERT ; relecture — preuve : `atelier_ecrans_page_import.py`, route `POST /importer` ;
  `test_atelier_ecrans_page_chrome.py::sonde_import` VERT (confirmation sur carte décrite, diff d'écriture fermé, brut
  hachuré, aperçu = source, Annuler, rien d'écrit) ; relecture : 1 défaut et 3 suggestions corrigés (remarque sur un brut
  refusée, texte brut d'une ligne) (2026-11-13)
- [x] Commit — preuve : commit b4d2757ac (2026-11-13)

## A14 — Objets du palier 2 : image, liste déroulante, interrupteur, roue, QR code
Conception : § 7 de la même spec.
- [x] Bancs d'abord (rouge), validateur et deux générateurs — preuve : commit 2590f4fe5, bancs lus ROUGES avant le code
  Détail : `img` (PNG seul), `dropdown`, `switch`, `roller`, `qrcode` dans le validateur et les deux générateurs ; type
  « liste » pour `options` et `points` ; `textarea` absent du catalogue ; bancs `_catalogue`,
  `_description` (mutants palier 3, image hors `PNG/`, interrupteur à `val` entier, QR code non carré, `qr_size` saisi),
  `_haspmota::test_palier2`, `_lvgl::test_palier2`, `_import::test_palier2` lus ROUGES avant le code (2026-11-13)
- [x] Catalogue, validateur, générateur HASPmota, moteur LVGL pur — preuve : commit 2590f4fe5, 13 bancs VERT
  Détail : `lv.image`, `lv.dropdown`, `lv.switch`, `lv.roller`, `lv.qrcode` ; `add_state`, `set_options`, `update` ;
  `banc_ecran_lvgl.py` VERT avec mutants ; 13 bancs
  `test_atelier_ecrans_*` VERT, `banc_ecran_lvgl.py` VERT (16 témoins rouges), `banc_demarrage.py` VERT (2026-11-13) ;
  paliers 1, 2, 3 (`atelier_ecrans_catalogue.py::dans_atelier`), types `liste`, `lignes`, `booleen` ; QR code carré,
  `qr_size` = l posé par les générateurs ; action d'un interrupteur, d'une liste ou d'une roue au changement de valeur,
  valeur choisie passée à l'action (dernier argument d'une fonction, `%val%` d'une commande, interrupteur en 1 / 0) ;
  police `.ttf` présente sur deux cartes : une seule entrée ; `ecranLvgl.be` des débits régénéré (interface `haspmota`
  de la carte : fichier hors de son FS)
- [x] Page : palette, propriétés, dessin approché, QR code — preuve : sonde_palier2 VERT, relecteur-pages-web prête
  Détail : éditeur de liste d'options, choix d'un PNG du dossier de la carte, QR code par la bibliothèque de la page des
  étiquettes ; module
  `atelier_ecrans_page_palier2.py`, routes `GET /images`, `/image`, `/lib/qr.js` (`test_atelier_ecrans_web.py::test_images`
  VERT), `test_atelier_ecrans_page_chrome.py::sonde_palier2` VERT (12 types en palette, QR code dessiné, PNG affiché,
  options nettoyées, QR code carré, qr_size dans le pages.jsonl généré, rien d'écrit), relecture `relecteur-pages-web` :
  prête, sa suggestion « liste des images indisponible » appliquée ; texte refusé sur une roue (`lvh_roller::set_text`
  lève) (2026-11-13)
- [x] Rangement des images par format — preuve : banc_repartition_fichiers.py VERT (4 mutants images rouges), relecteur-berry prêt
  Détail : décision de l'utilisateur du 2026-11-13, au lieu du `.png` seul : `.png`, `.jpg`,
  `.bmp` vers `/sd/images/PNG|JPG|BMP/` (`gestionFileFolder.be`, accord donné) ; scripts Berry, pages.jsonl et pages
  web des cartes (`data/sd/html|css|js`, routes Berry qui servent des fichiers : `qrcodePage`, `pagesGraphiques`,
  `cuvePageFonctions`, `equilibragePage`) recherchés le 2026-11-13 : aucun ne charge d'image du FS, aucune image dans `data/` ; `banc_repartition_fichiers.py` VERT avec mutants ; README, `CLAUDE.md`,
  `ICONES_IMAGES_SOURCES.md` à jour ; l'objet `img` de l'atelier ne propose que `PNG/`

## A15 — Icônes et images depuis la page (demande du 2026-11-13, transmise par la session « Modules ESP32-S3 avec ecran »)
Sources : `outils_docs/ICONES_IMAGES_SOURCES.md` (commit 495e0776f : ordre de recherche, licences, formats selon la cible).
Après A14 (l'import d'un PNG aboutit dans l'objet `img`). Si A18 est faite avant : la grille lit son catalogue
`outils_docs/schemas/icones.json` au lieu de relire `gen.sh`.
- [x] Panneau « Icônes » : grille des glyphes Material Design embarqués dans le firmware (codes lus dans
  `lib/libesp32_lvgl/LVGL_assets/gen.sh`, `0xf0335=>0xE335` = icône MDI F0335 servie en U+E335 dans montserrat-10/14/20/28
  et icons-xx), recherche par nom ; clic -> label avec le glyphe en montserrat-28 (ou texte de l'objet choisi) — preuve : onglet « Icônes », `atelier_ecrans_page_icones.py` ; `outils_pc/test_atelier_ecrans_page_chrome_icones.py` : 120 cases = catalogue, recherche, clic -> libellé montserrat-28 ; `test_atelier_ecrans_web.py::test_icones` : catalogue = codes de gen.sh, noms de la police
- [x] Aperçu : glyphes dessinés par la police locale `lib/libesp32_lvgl/LVGL_assets/fonts/Symbols/materialdesignicons-webfont.ttf`
  (codes E0xxx -> F0xxx), sans CDN ; aujourd'hui des carrés vides (cas de l'écran de la cave : E335, E6E8, E72A, E58F) — preuve : `GET /lib/mdi.ttf` (octets du dépôt) ; sonde : `document.fonts.check` vrai, U+E335 dessiné en MDI F0335 dans l'écran
- [x] Liens vers les sites de l'annuaire (Pictogrammers MDI, Material Symbols, Tabler, Lucide, Phosphor, Simple Icons ;
  Iconify pour chercher), licence de chacun, explications dans la page : glyphe du firmware d'abord ; sinon PNG à la taille
  d'affichage, blanc sur fond transparent, coloré par `image_recolor` + `image_recolor_opa` ; conversion SVG -> PNG — preuve : 7 liens `rel=noopener noreferrer` et licences dans le panneau (sonde), parcours PNG expliqué ; les glyphes Font Awesome restent non dessinés
- [x] Import d'un PNG déposé par l'utilisateur (parcours de l'import de polices A9 : licence confirmée, taille contrôlée),
  rangé sous `/sd/images`, choisi dans l'objet `img` (A14) — preuve : `atelier_ecrans_images.py`, `test_atelier_ecrans_images.py` VERT (refus, écritures exactes), `test_atelier_ecrans_web.py::test_images_import` VERT (400, 403, 409, liste `GET /images`), sonde Chrome `sonde_import_png` VERTE (fichier refusé, import dans la copie du dépôt)
- [x] Banc, sonde Chrome — preuve : `test_atelier_ecrans_images.py`, `test_atelier_ecrans_web.py`, sonde Chrome VERTS
- [ ] Relecture `relecteur-pages-web` de l'import PNG : coupée par la limite d'usage ; faite à la main sur les noms réservés Windows et l'origine multiligne, reste l'échappement côté page, la course entre deux analyses et la borne de taille (à relancer après le 15 novembre). Relecture du panneau Icônes : faite, aucun bloquant
- [x] Commit — preuve : `bfc7fd7b2` (panneau Icônes), `7ea9cd7dd` (import PNG)

## A16 — Page « QR code » sur chaque carte à écran (demande de l'utilisateur du 2026-11-13)
Les mêmes informations que la page web `/qrcode` (`data/fs/qrcodePage.be`) : le QR code du texte réglé dans
`/json/qrcode.json` par l'outil des étiquettes (7970), l'IP réelle de la carte comparée à l'IP inscrite, le nom d'hôte.
Cartes visées : toutes celles qui ont un écran (aujourd'hui `tasmota32s3-bureau-ecran-debits-pac`, `tasmota32s3-cave-ecran`).
Après A14 (objet `qrcode`). Limites connues : QR code LVGL à deux couleurs (ni modules arrondis ni dégradé) ; logo central
seulement par un PNG sous `/sd/images/PNG/` posé en `img` (le data URI de `qrcode.json` n'est pas lisible par LVGL).
- [ ] `qrcode.json` de chaque carte à écran écrit par l'outil des étiquettes (aujourd'hui seul le P4 du garage en a un)
- [ ] Valeurs du modèle de chaque module métier d'écran : texte du QR code, IP réelle (`diversFonctions.ipLAN`), IP
  inscrite, nom d'hôte, accord des deux IP ; lues au démarrage, pas à chaque seconde
- [ ] Page ajoutée à chaque `ecran.json` (QR code lié au texte, labels liés), bouton de navigation ; écran de la cave :
  accord de la session qui tient `tasks/plans/ecran-cave-vues-commandes.md` avant d'écrire son `pages.jsonl`
- [ ] Bancs (modèle, description valide, deux générateurs), sonde Chrome de l'aperçu ; essai sur chaque carte (avec A20)

## A17 — Barre de navigation construite d'après les pages (demande du 2026-11-13, planification laissée à Claude)
Choix de Claude : construite à la GÉNÉRATION (pas sur la carte : HASPmota n'expose pas les titres des pages, et les pages
ne changent qu'à la génération). Une clé `navigation` à la racine de la description : `{"x", "y", "h", "ecart",
"attributs": {style des boutons}, "actif": {couleurs de la page courante}}` ; une page porte `"menu": false` pour en sortir
(page de confirmation). Les deux générateurs déroulent un bouton par page n >= 1 du menu, sur la page 0, ids réservés
(201 à 254, refus d'un objet de l'utilisateur sur ces ids), texte = titre de la page, toucher `{"page": n}`, couleurs `actif`
(mécanisme existant). Largeur des boutons d'après la longueur du titre et la taille de police ; refus avec message si la
barre dépasse l'écran. Hors champ : la fenêtre « Menu » de la cave (actions non déductibles des pages) ; un `pages.jsonl`
importé garde ses boutons tels quels.
- [x] Bancs d'abord (rouge) — preuve : `test_atelier_ecrans_navigation.py` rouge (module absent) puis VERT, 10 mutants du validateur refusés
  Détail : validateur (forme de `navigation`, ids réservés, débordement, `menu` booléen), deux générateurs (un bouton par
  page du menu, ordre des pages, `actif`) ; touchers et ACTIFS de la barre contrôlés dans le texte de `ecranLvgl.be`
  généré (`::test_generateurs`), `banc_ecran_lvgl` non étendu : les boutons déroulés sont des `btn` ordinaires, déjà
  couverts ; changement d'écran : barre mise à l'échelle, QR code resté carré (`::test_echelle`) (2026-11-13)
- [x] Description, validateur, déroulement commun — preuve : `atelier_ecrans_navigation.py::deroule`, 15 bancs de l'atelier VERT
  Détail : appelé par `atelier_ecrans_description.py::valide` (`::_navigation`), `atelier_ecrans_haspmota.py::genere`,
  `atelier_ecrans_lvgl.py::genere` ; `atelier_ecrans_ecran.py::met_a_echelle` met la barre à l'échelle ; les 14
  `test_atelier_ecrans_*.py` et `banc_ecran_lvgl.py` VERT le 2026-11-13
- [x] Page : panneau de la barre, case par page — preuve : `test_atelier_ecrans_page_chrome_palier2.py::sonde_navigation` VERT, 2 témoins rouges, relecteur-pages-web prêt
  Détail : panneau « Barre de navigation » (activer, position, hauteur, écart, couleurs) de la page 0, case « Dans la barre
  de navigation » des autres pages, boutons en pointillés non sélectionnables (`atelier_ecrans_page_navigation.py`) ;
  positions du DOM = `atelier_ecrans_navigation.boutons`, titre avec emoji compris (`Array.from` : points de code comme
  Python) ; `nouvelId` borné à 200 avec la barre. Relecture : 2 défauts mineurs corrigés (témoin de la borne, largeur
  d'un titre hors plan de base), témoins lus rouges ; sondes palier 2 et barre sorties dans un module voisin (sonde
  principale sous 500 lignes) ; aucun Chrome de sonde restant (2026-11-13)
- [x] Écran des débits passé à la barre construite — preuve : banc_ecran_debits, banc_ecran_lvgl (82 objets, 0 écart), banc_demarrage et 15 bancs de l'atelier VERT
  Détail : boutons p0b91-93 remplacés par la clé `navigation` (mêmes style, hauteur et position ; largeurs 112, 123, 134
  au lieu de 110, 124, 130), `pages.jsonl` et `ecranLvgl.be` (496 lignes) régénérés par `atelier_ecrans_ecriture.ecrit` ;
  `ecranHaspmota.be` colore `"p0b" + str(200 + n)` (accord de la session « Modules ESP32-S3 avec ecran ») ; bancs
  qui citaient 91-93 mis à jour (`banc_ecran_debits.be`, `banc_ecran_lvgl.be/.py`, `test_atelier_ecrans_description.py`,
  `test_atelier_ecrans_ecran.py`) ; changement d'écran : barre sous 40 px signalée (`atelier_ecrans_ecran.py::met_a_echelle`).
  Écran de la cave : proposé le 2026-11-13 à la session qui le tient, rien écrit (2026-11-13)
- [ ] Essai sur la carte (avec A20) ; commit

## A18 — Catalogue des icônes et logos : page de l'annuaire (demande de l'utilisateur du 2026-11-13)
Une page qui liste et présente toutes les icônes, logos et images retenus par les recherches du plan (annuaire
`outils_docs/ICONES_IMAGES_SOURCES.md`, glyphes du firmware, PNG du dépôt). Choix de Claude, à confirmer : outil à part
« Catalogue d'icônes » (port 7990, tuile de l'annuaire, groupe Maintenance, lecture seule), comme les autres pages
d'outils ; la police MDI du dépôt (`lib/libesp32_lvgl/LVGL_assets/fonts/Symbols/materialdesignicons-webfont.ttf`) dessine
les glyphes, sans CDN. A15 (panneau « Icônes » de l'atelier) reprend son catalogue au lieu d'en refaire un.
fontTools (noms des glyphes) n'est PAS dans le Python de PlatformIO (vérifié le 2026-11-13, présent dans le Python
du système, 4.63.0) : seule la génération du catalogue s'en sert, lancée par le Python du système comme
`genere_brochage_excel.py` ; la page, `--verifier` (codes de `gen.sh` seuls) et le banc lisent le JSON, sans fontTools.
- [ ] Catalogue généré `outils_docs/schemas/icones.json` : glyphes MDI de `gen.sh` (code `\uE…`, nom lu dans la police
  MDI, polices et tailles qui le portent), symboles LVGL des polices Montserrat, PNG du dépôt et de `/sd/images` (taille,
  licence), sources de l'annuaire (site, licence, usage) ; `--verifier` rouge si `gen.sh` change ; banc avec mutants
- [ ] Usages : où chaque icône sert dans le parc (`ecran.json`, `pages.jsonl`, `.be` des cartes), icônes absentes du
  firmware repérées dans les écrans (carrés vides)
- [ ] Page : grille avec recherche par nom, filtre par source (firmware, LVGL, PNG, sites), fiche d'une icône (code à
  copier pour `text`, taille, licence, usages, lien vers le site) ; mode sombre ; sonde Chrome ; relecture
  `relecteur-pages-web`
- [ ] Tuile de l'annuaire, tâche VS Code, cible Custom détachée ; mode d'emploi (`outils_docs/README.md`), carte des
  documents du `CLAUDE.md`, renvoi dans `ICONES_IMAGES_SOURCES.md` ; commit

## A19 — Page « Système » sur chaque carte à écran (décision de l'utilisateur du 2026-11-13)
Les niveaux de mémoire, de RAM et d'occupation, sur toutes les cartes à écran (aujourd'hui
`tasmota32s3-bureau-ecran-debits-pac`, `tasmota32s3-cave-ecran`), dans le menu par la barre construite (A17).
Données lues dans le firmware sans le modifier : `tasmota.memory()` (`xdrv_52_3_berry_tasmota.ino` : `heap_free`, `frag`,
`psram`, `psram_free`, `gc_heap`, `gc_time`, `stack_low`, `iram_free`, `program`, `program_free`, `flash`), système de
fichiers par la commande `Ufs` (`xdrv_50_filesystem.ino::UfsInfo`, sortie à lire sur une carte). Choix de Claude :
un module Berry commun aux cartes à écran, pas un ajout dans chaque module métier ; lecture toutes les 5 s, seulement
quand la page est affichée.
- [x] [utilisateur] Données en plus de la mémoire — preuve : « Je garde tout », réponse de l'utilisateur du 2026-11-13
  Détail : proposées le 2026-11-13, toutes retenues (champs de `Status` à lire
  sur une carte avant de s'y fier). Santé : RAM libre minimale depuis le démarrage et courbe sur 1 h, verdict « mise à
  jour OTA possible » (`program_free` >= `program`), charge (`LoadAvg`, `Sleep`), seuils vert / orange / rouge.
  Redémarrages : uptime, cause, nombre de démarrages. Réseau : RSSI, point d'accès (BSSID), IP, nombre de pertes du
  Wi-Fi et durée hors ligne, reconnexions MQTT, heure synchronisée ou non. Métier : ModBus (esclaves joignables,
  délais dépassés, âge du dernier push), clients du range extender. Écran : luminosité, délai de veille. Journal : les
  dernières erreurs Berry. Version et date du firmware, température de la puce. Boutons : redémarrer, GC
- [x] Module commun — preuve : banc_ecran_systeme.py VERT (41 témoins rouges), banc_demarrage, banc_test_modbus, banc_ecran_debits, banc_ecran_lvgl VERT, relecteur-berry prêt
  Résultat : `data/fs/ecranSysteme.be` (499 lignes), `controleEcranSysteme.be`, `logFonctions.be` (cible `ecranSysteme`,
  5 dernières erreurs) ; liste `berry_commun.ecran_systeme` du cenv exclue de TOUS les envs tant qu'aucun autoexec ne la
  charge ; relecture : persist absent gardé et message coupé hors d'un accent (2 témoins de plus). Délais ModBus dépassés :
  aucun compteur exposé, « -- ». Reste avant activation : bloc `modules.ecranSysteme` des persist (accord), autoexec,
  schéma du persist et README (2026-11-13). Énoncé d'origine : (`data/fs`, accord de l'utilisateur du 2026-11-13 ; chargé depuis le FS, non solidifié : avis de
  Claude retenu, ajouté à `custom_files_upload` des envs à écran et exclu des autres) ; dernières erreurs Berry gardées
  en mémoire par `data/fs/logFonctions.be` (accord du 2026-11-13, après le commit de la session « Modules ESP32-S3 avec
  ecran » qui y ajoute les cibles `ecranCave` et `ecranDebits`) ; banc Berry sur bouchons (`tasmota.memory`, `Ufs`),
  avec mutants ; `banc_demarrage.py`
  Conception (choix de Claude, 2026-11-13) : `data/fs/ecranSysteme.be` (module) + `data/fs/controleEcranSysteme.be`
  (driver, garde `modules.ecranSysteme.activation`, cible de log `ecranSysteme`). Table `ecranSysteme.CHAMPS` = SEULE
  référence des données (clé, libellé, unité, id du texte, id de la barre ou nil) : la page de l'atelier (étape suivante)
  la relit dans le `.be`. Écriture par `ecranFonctions.interface.ecris("p<page>b<id>", attribut, valeur)`, commune à
  HASPmota et au LVGL généré ; page = `modules.ecranSysteme.page` du persist. Mesures toutes les 5 s seulement si la page
  est affichée ; RAM libre minimale et courbe 1 h (120 points à 30 s) suivies en continu, par `tasmota.memory("heap_free")`
  (sans map). Boutons : « Lancer le GC », « Redémarrer » (confirmation par second appui dans les 5 s).
- [x] Page « Système » construite par l'atelier et ajoutée à l'écran des débits (page 4, sans icônes). Conception (choix de
  Claude, 2026-11-13) : une page de la description porte `"modele": "systeme"` ; `atelier_ecrans_systeme.py` relit
  `ecranSysteme.CHAMPS` dans le `.be` et déroule les objets (valeurs aux ids de la table, libellés 130+, titres de groupe
  180+, boutons 120 et 121) pour le validateur, les deux générateurs et l'aperçu, par le point d'entrée unique
  `atelier_ecrans_navigation.deroule` ; un écran trop petit est refusé au changement d'écran (`atelier_ecrans_ecran.py::changement`)
  — preuve : `data/bureau/tasmota32s3-ecran-debits-pac/{ecran.json,pages.jsonl,ecranLvgl.be}` régénérés par l'atelier ;
  `outils_pc/test_atelier_ecrans_systeme.py` VERT ; `berry/banc_page_systeme.py` VERT (vrai `ecranLvgl.be` : chaque écriture de
  `ecranSysteme` trouve son objet du bon type ; un clic sur 120 = un GC, sur 121 = pas de redémarrage, second clic = `Restart 1`
  une seule fois) ; `verifie_berry.py` strict : 0 erreur ; `ecranLvgl.be` = 600 lignes (exception actée dans CLAUDE.md)
- [ ] Icônes de la page Système : glyphes du firmware (`clock-outline`, `wifi`, `thermometer`…) et PNG pour celles qui manquent
  (`memory`, `chip`, `harddisk`, `micro-sd` : catalogue A18, import A15) ; ids 190 à 198 réservés, rien d'émis avant A15
- [ ] Écran de la cave : accord de la session qui tient `tasks/plans/ecran-cave-vues-commandes.md` avant d'écrire (page à ajouter
  à son `ecran.json`, `ecranSysteme` à charger par son autoexec, retirer `ecran_systeme` de ses exclusions du cenv)
- [x] Bancs (description valide, deux générateurs), sonde Chrome de l'aperçu — preuve : `test_atelier_ecrans_*.py` (description,
  navigation, lvgl, haspmota, ecran, ecriture, web, import, catalogue, systeme) VERTS ; `banc_ecran_lvgl.py`, `banc_ecran_debits.py`,
  `banc_ecran_systeme.py`, `banc_demarrage.py` VERTS ; sonde `test_atelier_ecrans_page_chrome.py` VERTE (refus de la page sur 480 x 320 contrôlé)
- [ ] Compilation par la page Build ; essai sur chaque carte (avec A20)

## A20 — Livraison de l'écran des débits (sur la carte, avec l'utilisateur)
Regroupe ce qui reste à faire sur la carte d'affichage `tasmota32s3-bureau-ecran-debits-pac` (192.168.0.51) ou par
l'utilisateur (demande du 2026-11-12). Interface de la carte : HASPmota (`custom_interface_ecran` du cenv), donc
`pages.jsonl`. Plan d'origine : [tasks/plans/debits-deux-cartes.md](debits-deux-cartes.md), action A9.
- [ ] [utilisateur] Carte d'affichage joignable : 192.168.0.51 muette depuis le 2026-11-12 (alimentation, Wi-Fi ; avec
  trois points d'accès, comparer les BSSID et redémarrer celui qui bloque)
- [ ] Firmware de la carte postérieur à 5c3291884 (`ecranFonctions.be` déplacé dans `data/fs`) : `Status 2` comparé à la
  date du commit ; sinon compilation et envoi par la page Build
- [ ] [utilisateur] Essai : un bouton ajouté à l'écran des débits dans l'atelier, généré dans les deux interfaces, écrit
  dans le dépôt, `pages.jsonl` envoyé par la page Build (onglet « Fichiers »), vu et touché sur la carte ; noms des voies
  en police 28 (remarque 1) vus au passage
- [ ] Capture réelle depuis l'atelier (« Capture de la carte ») : image identique à l'écran, mémoire PSRAM prise par
  `lv.screenshot()` notée (environ 1,2 Mo attendu pour 1024 x 600)
- [ ] Essai du `display.ini` (A12, déplacé ici le 2026-11-13) : envoi du `display.ini`, `DisplayReinit` ou `Restart 1`,
  « Garder » / « Revenir » ; comportement de `DisplayReinit` avec LVGL noté ; commandes à chaud `DisplayDimmer`,
  `DisplayRotate`
- [ ] Ligne non JSON d'un `pages.jsonl` importé (A13, demande du 2026-11-13) : lu dans `lv_haspmota.be::HASPmota._load`,
  une ligne commençant par `#` est sautée sans message, toute autre ligne non JSON est sautée avec le log niveau 2
  « HSP: invalid JSON line », le chargement continue. À voir sur la carte : ajouter `# essai` et `essai` au `pages.jsonl`,
  l'envoyer, relire les logs (niveau 2) et l'écran
- [ ] Essai des objets du palier 2 (venu d'A14, demande du 2026-11-13) : un objet de chaque type sur l'écran des débits
  (image PNG sous `/sd/images/PNG/`, liste déroulante, interrupteur, roue, QR code), vu et touché ; action au changement
  de valeur reçue avec la valeur choisie (LVGL pur) ; QR code lisible par un téléphone
- [ ] Commit des fichiers de l'essai (description, interfaces générées, remarques éventuelles)
- [ ] [utilisateur] Vue de droite : taper `/suivi suivre debits-deux-cartes` puis `/suivi suivre atelier-ecrans` ; à cocher
  quand la vue a basculé dans les deux sens
- [ ] Retour au plan `debits-deux-cartes` : cocher son action A9 avec la preuve de l'essai, passer ce plan en `statut: clos`

## Améliorations restantes
- [ ] [projet] Propositions de réglages des `display.ini` par Claude d'après les notes de terrain (`<nom>.notes.md`)

## Vérification
Bancs du catalogue, de la description et des deux générateurs VERT avec témoins rouges lus ; sonde Chrome de la page ;
essai réel de A10 sur la carte d'affichage des débits. Un banc PC ne prouve pas le rendu : seul l'écran fait foi.
