---
chantier: build-fin-partitions
titre: Pastille d'occupation des partitions à la fin d'une compilation (page Build)
statut: clos
cree: 2026-11-15
maj: 2026-11-15
objectif: Montrer dans la ligne de chaque env compilé « Flash 87 % · RAM 32 % » (orange dès 90 %, rouge dès 95 %), avec un détail complet des partitions au clic
famille: build
spec: aucune
liens: temps-compilation
---
# Pastille d'occupation en fin de compilation

## Contexte
Variante D choisie par l'utilisateur (maquettes `outils_docs/build_fin_partitions/`). Aucun changement serveur : la série
enregistre déjà l'analyse mémoire à la fin d'une compilation réussie (`build_serie.py`, appel de `build_memoire.enregistre`),
la page lit `GET /memoire?env=`. Code dans `outils_pc/build_page_fin_memoire.py`, 6 lignes ajoutées à `build_page.py`.

## A1 — Pastille et fenêtre de détail
- [x] Sonde Chrome écrite d'abord, rouge avant le code — preuve : test_build_page_fin_memoire_chrome.py, « sonde : deroulement » KO avant branchement
- [x] Module `build_page_fin_memoire.py` + branchement dans `build_page.py` — preuve : sonde VERT (13 contrôles)
- [x] Seuils, XSS, Échap, clic dehors, thèmes clair et sombre, env sans relevé — preuve : contrôles de la sonde, mutants rouges (seuil, innerHTML)
- [x] Essai réel après une vraie compilation depuis la page :7700 (l'utilisateur, aucun build lancé ici) — preuve : 2026-11-15, pastille affichée après la compilation de `tasmota-cave-lumiere-porte` (ESP8266) et, plus tôt, de `tasmota32s3-cave-serveur-rly` (capture : fenêtre de détail, IRAM du S3 puis corrigée) ; la pastille S3 après correctif (orange, Flash = app0) reste à revoir

## A3 — Envs ESP8266 : pastille d'après le bilan de pio
- [x] Relevé sans table de partitions : `build_memoire.py::analyse` lit « Flash: » et « RAM: » du journal et pose `bilan_flash` {utilise, taille} + zone « RAM », `partitions` reste vide (l'onglet Mémoire n'y voit pas de faux firmware éditable) — preuve : test_build_memoire.py VERT (cas esp8266-essai / esp8266-ansi / sans les deux lignes), mutant « ESP8266 : ligne Flash non lue » tué
- [x] Pastille et détail : `build_page_fin_memoire.py::fmParts` (repli sur `bilan_flash`) — preuve : test_build_page_fin_memoire_chrome.py VERT (pastille 70 %/94 %/95 %, relevé vide sans pastille, fenêtre « firmware » + RAM), mutant JS rouge
- [x] Essai réel : le relevé de `tasmota-cave-lumiere-porte` n'est régénéré qu'à la prochaine compilation depuis la page :7700 — preuve : 2026-11-15, compilation du journal 20261115-121727 (SUCCESS, 14 min) : relevé `bilan_flash` 721795 / 1023984 (70,5 %), RAM 43860 / 81920 (53,5 %), note « pas de table de partitions (ESP8266) » ; l'utilisateur confirme avoir vu la pastille « Flash … · RAM … » sur la ligne de l'env

## A4 — Pastille : IRAM du S3 et Flash = app0
- [x] IRAM de 16384 o d'un ESP32-S3 (cache d'instructions, toujours pleine) : ni rouge ni alerte, ligne gardée avec la mention « cache d'instructions, toujours plein » ; ESP32 classique à IRAM pleine : rouge — preuve : `build_page_fin_memoire.py::fmCache`, sonde `test_build_page_fin_memoire_chrome.py` VERT (cas s3-iram orange, classique-iram rouge), mutant « fmCache renvoie false » rouge
- [x] « Flash » = occupation d'app0 (sinon `bilan_flash` de pio, sinon somme) ; niveau = partition la plus pleine hors FS (spiffs, littlefs, ffat) et zone de RAM la plus pleine hors cache S3 — preuve : `fmResume`, sonde VERT (S3 app0 87 %, safeboot 93,4 % : « Flash 87 % · RAM 40 % ⚠ » orange ; ESP8266 inchangé)
- [x] Essai réel après redémarrage de la page :7700 et une compilation de `tasmota32s3-cave-serveur-rly` (l'utilisateur) — preuve : 2026-11-15, journal 20261115-124148 (SUCCESS, 9 min) ; relevé app0 87,0 %, safeboot 93,4 %, IRAM 100 % (cache du S3), DIRAM 39,8 % ; l'utilisateur confirme avoir vu la pastille (la couleur affichée n'a pas été relevée ici)

## A2 — Retour au plan en cours avant ce chantier
- [x] Reprendre le plan `build-reparations` : essai réel du diagnostic IA sur le journal `20261115-043620-tasmota-cave-lumiere-porte-compiler.log` (A6, dernière case), case « Relancer après réparation », puis A7 (documentation, relecteurs, essai hors série, commit) : `/suivi suivre build-reparations` — preuve : plan `build-reparations` repris le 2026-11-15 : essai réel du diagnostic IA fait (23 s, règle `attendre 20 s`), case de l'IA livrée (commits d5ddf60bc, c083c7494), A7 cochée (essai hors série 53/53, commit 608c8268c) ; reste dans ce plan un seul essai réel (relance IA réussie sur une vraie panne)

## Améliorations restantes
- [ ] [projet] Écart avec le build précédent (variante C : champ `avant` à enregistrer par `build_memoire.enregistre`)
- [ ] [projet] Accessibilité de la fenêtre : focus à l'ouverture, retour à la pastille, piège de Tab (relecteur-pages-web, 2026-11-15)
- [ ] [projet] Garder le relevé : ignorer un `date_build` antérieur au début de l'env, vérifier le bloc après l'`await`, rafale au rejeu
- [ ] [projet] Couleurs de `FM_COUL` et du voile : variables CSS du thème au lieu de valeurs en dur
- [ ] [projet] Sonde : filtre `ERR_CONNECTION_REFUSED` trop large, test de classe `fm-alerte` laxiste
