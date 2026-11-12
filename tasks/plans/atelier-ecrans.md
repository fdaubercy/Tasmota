---
chantier: atelier-ecrans
titre: Atelier des écrans (page 7960) : une description d'écran, deux interfaces générées
objectif: Modifier sur le PC la disposition d'un écran tactile de carte (objets, boutons, pages) et y épingler des remarques, puis générer de la même description le pages.jsonl de HASPmota et le code LVGL pur en Berry
statut: actif
cree: 2026-11-11
maj: 2026-11-12
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

## A0 — Plan précédent : débits sur deux cartes
Plan d'origine de ce chantier : [tasks/plans/debits-deux-cartes.md](debits-deux-cartes.md), action A9.
- [ ] Rouvrir le plan précédent dans la vue de droite : taper `/suivi suivre debits-deux-cartes` (la conversation suit
  alors ce plan) ; revenir à celui-ci : `/suivi suivre atelier-ecrans`. À cocher quand l'aller-retour a été fait une
  fois et que la vue a basculé dans les deux sens.

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
- [ ] Banc d'abord (rouge) : `test_debits_identique` (`ecarts(pages.jsonl du dépôt, genere(ecran.json des débits)) ==
  []`), `test_texte_special` (texte `Débit "5" \ 100 %` -> ligne qui se relit par `json.loads` à l'identique),
  `test_ecart_detecte` (une valeur changée -> un écart nommant la ligne et la clé)
- [ ] `genere` ; banc VERT
- [ ] `berry/banc_ecran_debits.py` VERT sur le `pages.jsonl` généré (copie temporaire) ; commit

## A5 — Générateur LVGL pur
Fichiers : créer `outils_pc/atelier_ecrans_lvgl.py`, `outils_pc/test_atelier_ecrans_lvgl.py`,
`berry/banc_ecran_lvgl.py` + `.be` (+ bouchons `berry/bouchons_berry/ecran_lvgl/` : objets `lv.*` simulés qui
enregistrent les appels) ; écrire `data/bureau/tasmota32s3-ecran-debits-pac/ecranLvgl.be` (généré).
Consomme : `atelier_ecrans_description.charge`. Produit : `genere(desc) -> str` (module Berry `ecranLvgl` :
`demarre()` et `affiche(modele)` de l'API en tête de `ecranDebitsFonctions.be`, cache par objet et attribut, fonctions
nommées, logs par `logFonctions.log` et constantes `LOG_LEVEL_*`).
- [ ] Banc d'abord (rouge) : `test_compile` (le texte généré passe `berry/verifie_berry.py`, charte des logs sans
  avertissement), `test_texte_special` (même texte qu'en A4 -> compile, chaîne restituée à l'identique) ; banc Berry :
  `demarre()` crée les objets des 4 pages aux positions de la description, deux `affiche(modele)` identiques -> aucun
  appel au second, une valeur changée -> un seul appel
- [ ] `genere` ; bancs VERT
- [ ] `ecranLvgl.be` des débits généré et écrit ; `build/test_interface_ecran.py` VERT (le fichier présent, interface
  `haspmota` : exclu du FS) ; `banc_demarrage.py` de la variante `lvgl` VERT
- [ ] Commit (le fichier généré compris) ; noter dans `debits-deux-cartes` A8 que l'interface LVGL vient du générateur

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
- [ ] Banc serveur d'abord (rouge), sur copie temporaire : routes ci-dessus ; env inconnu -> 400 ; requête sans en-tête
  anti-CSRF -> 403 ; carte injoignable -> `/valeurs` simulé avec `simule: true` et `/capture` refusé avec message ;
  `nom` de police hors catalogue -> 404 ; adresse de la carte prise au cenv, jamais à la requête
- [ ] Serveur et routes ; banc VERT
- [ ] Page (maquette `modele-retenu.png`) : en-tête (liste des cartes par `lieux.pour_page`, liste des écrans
  présélectionnée et marquée « celui de l'env », état en ligne, bascule Sombre / Clair mémorisée par `localStorage`
  sous try/catch), colonne gauche, onglets « Écran » / « Tableau des objets », zoom − / + / 100 %, grille aimantée,
  glisser-déposer, poignées, annuler / rétablir, propriétés limitées au catalogue (taille de police absente refusée avec
  les tailles possibles), fenêtre basse des fichiers générés avec différences colorées
- [ ] Capture : `atelier_ecrans_capture.capture(ip, get) -> bytes` (`Br lv.screenshot()`, téléchargement, effacement du
  fichier sur la carte) ; banc avec carte simulée ; essai réel sur le 7B (mémoire PSRAM notée)
- [ ] Sonde Chrome hermétique (thème clair et sombre, glisser un bouton, zoom 100 %, aucune erreur console, Chrome
  arrêté à la fin) VERT ; tuile de l'annuaire, tâche VS Code, cible détachée (`test_cible_atelier_ecrans.py` VERT,
  `test_garde_build.py` VERT)
- [ ] Commit

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
- [ ] Vérifier les options de `claude -p` qui imposent la LECTURE SEULE (liste d'outils permis, mode de permission non
  interactif, jamais `bypassPermissions`) et la sortie JSON ; si impossible, livrer le repli (bouton qui copie la
  consigne) et le noter ici
- [ ] Banc d'abord (rouge), `claude` remplacé par un faux exécutable : propositions valides écrites par la PAGE dans
  `remarques.json` ; opération vers un `id` inconnu ou un attribut hors catalogue rejetée ; faux `claude` qui modifie un
  fichier du dépôt -> résultat rejeté (contrôle `git status` et empreintes) ; `claude` absent, code d'erreur, délai de
  10 min dépassé -> état `echec` avec message, `remarques.json` intact ; second lancement pendant `en_cours` -> refus
- [ ] Module, routes et onglet « Remarques » (épingler sur un objet, une zone tracée, la page ; Appliquer / Refuser /
  Répondre ; journal dans `%LOCALAPPDATA%\outils_tasmota\atelier_ecrans\`) ; bancs VERT, sonde Chrome étendue VERT
- [ ] Essai réel : une remarque traitée par le vrai `claude -p`, proposition appliquée sur le canevas ; commit

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
- [ ] Banc d'abord (rouge), copie temporaire : écriture de `ecran.json`, `pages.jsonl`, `ecranLvgl.be` en une
  transaction ; description modifiée sur le disque après lecture -> refus, rien écrit ; build en cours -> refus ;
  mise à l'échelle 1024 × 600 -> 480 × 320 (positions et tailles au rapport, police ramenée à la taille la plus proche,
  bouton de 46 px -> 25 px signalé) ; changement d'écran : diff du `display.ini`, conflit de broches refusé
- [ ] Modules et routes ; bancs VERT ; dans la page, « Écrire dans le dépôt » (diff puis confirmation), mode
  « changement d'écran » (diff, confirmation, rappel de recompiler par la page Build), lien « Envoyer par la page
  Build ↗ » (`?env=` et fichiers) ; sonde Chrome VERT
- [ ] Commit

## A9 — Ressources sous `/sd`
- [ ] Liste des ressources utiles (fonds, icônes, polices ajoutées) proposée à l'utilisateur, choix fait ; règle de
  rangement des images dans `data/fs/gestionFileFolder.be::listeEtRepartitLesFichiers` (accord pour `data/fs`)
- [ ] Import d'une police nouvelle depuis la page (demande du 2026-11-11) : liens vers les sites de polices et de
  conversion de la skill `lvgl-haspmota` (`references/polices.md`, « Trouver et importer une police nouvelle ») ; fichier
  `.ttf` ou `.bin` déposé par l'utilisateur, licence et couverture Latin-1 contrôlées, tailles proposées, rangé sous
  `/sd/polices/` et ajouté au catalogue (`atelier_ecrans_catalogue.genere` relancé) ; banc

## A10 — Documentation, relecture, essai réel
- [ ] `outils_docs/README.md` (mode d'emploi), carte des documents du `CLAUDE.md`, `verifie_references_docs.py` 0 défaut
- [ ] `relecteur-pages-web` et `relecteur-berry` sur le chantier ; corrections confirmées faites
- [ ] Essai avec l'utilisateur : un bouton ajouté à l'écran des débits par l'atelier, généré dans les deux interfaces,
  envoyé par la page Build, vu et touché sur la carte
- [ ] Retour au plan `debits-deux-cartes` : cocher son action A9 avec la preuve, passer ce plan en `statut: clos`

## Améliorations restantes
- [ ] [projet] Écrans des autres cartes (ILI9488 SPI, petits OLED) ajoutés au catalogue
- [ ] [projet] Reprise d'un `pages.jsonl` existant écrit à la main (import vers la description)
- [ ] [projet] Objets du palier 2 (image, liste déroulante, interrupteur, roue, QR code…)

## Vérification
Bancs du catalogue, de la description et des deux générateurs VERT avec témoins rouges lus ; sonde Chrome de la page ;
essai réel de A10 sur la carte d'affichage des débits. Un banc PC ne prouve pas le rendu : seul l'écran fait foi.
