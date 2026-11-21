---
chantier: navigateur-ftp-cartes-a5-reprise
titre: Reprise d'A5 du navigateur FTP des cartes (page et sonde Chrome)
statut: actif
objectif: Vérifier, relire et commiter la page du navigateur FTP (A5), puis revenir au plan navigateur-ftp-cartes
famille: methode
parent: navigateur-ftp-cartes
cree: 2026-11-21
maj: 2026-11-21 (relectures faites, commit à venir)
source: imperative-meandering-journal.md
---
## Contexte

A5 (page de l'interface A et sa sonde Chrome) a été écrite par un sous-agent, puis arrêtée par le passage en mode plan avant
toute vérification. Rien n'est commité, rien n'est prouvé. Fichiers présents dans `outils_docs/scripts_python/outils_pc/` :
`ftp_cartes_page.py` (364 lignes, neuf), `test_ftp_cartes_page_chrome.py` (207 lignes, neuf), `ftp_cartes_web.py` (283 lignes,
la constante `PAGE` provisoire remplacée par `from ftp_cartes_page import PAGE`). Le rapport `task-5-report.md` n'existe pas.
Un `pio run ... -t upload` du P4 (COM4) tournait au moment du blocage : la sonde ne se lance pas pendant un build.
Décisions déjà prises (journal `.superpowers/sdd/navigateur-ftp-cartes/progress.md`) : `pagehide` de tout onglet envoie
`/ferme`, déplacement d'un fichier protégé à une seule confirmation, suppression à deux.

## A1 — Vérifier la page et la sonde
- [x] Sortie du mode plan ; contrôle en lecture qu'aucun `pio run` ni `scons` ne tourne ; s'il y en a un, attendre le feu vert de l'utilisateur (règle du dépôt, ne pas relancer sur la seule fin d'un scons) — preuve : aucun pio ni scons vu pendant 90 s après la fin du build du P4 (veille en arrière-plan), puis reprise du sous-agent
- [x] Reprendre le sous-agent d'A5 (SendMessage à `ad82baf0bb41e7fc8`) : sonde lancée ROUGE avec la page minimale (`%TEMP%\rouge_ftp.py`), sortie collée au rapport — preuve : sonde rouge avec la page minimale : 22 échecs (`.superpowers/sdd/navigateur-ftp-cartes/task-5-report.md`)
- [x] Sonde VERTE avec la vraie page (Python de PlatformIO, `PYTHONIOENCODING=utf-8`), sortie collée au rapport — preuve : 6 passages de suite verts, 77 OK chacun, relancée verte par chaque relecteur
- [x] `test_ftp_cartes_web.py` relancé, toujours vert (la page est importée par le serveur) — preuve : VERT, 92 OK (relecteur, après le tour 2)
- [x] Chrome `sonde_ftp_cartes*` arrêtés, vérifiés 15 s après — preuve : 0 Chrome `sonde_` vivant 15 s après chaque lot (implémenteur et trois relecteurs)
- [x] Trois doutes du sous-agent traités : `Banc.__exit__()` sans arguments dans `Montage.ferme`, téléchargement d'un seul fichier par lien `/telecharge` non couvert par la sonde (ajouter le cas), nom hostile simulé par `noms_pieges` du faux serveur — preuve : `Banc.__exit__()` sans argument fonctionne ; cas du lien `/telecharge` ajouté à la sonde ; `noms_pieges` justifié (`<` interdit dans un nom Windows)
- [x] Rapport `task-5-report.md` écrit — preuve : fichier écrit, sections « Tour de corrections 1 » et « 2 »

## A2 — Relecture et corrections
- [x] `relecteur-pages-web` (Opus) sur `ftp_cartes_page.py` et la sonde : XSS (noms de la carte), anti-CSRF, `sendBeacon`, état de la page, mode sombre, 375 px — preuve : relecture Opus : 0 critique, 8 importants ; mutants a à d rouges
- [x] Constats Critique et Important corrigés par le même sous-agent, puis re-relecture ciblée — preuve : tour 1 : 6/6 puis tour 2 : boîte périmée, contrôle sous verrou, B13 ; re-relecture : 3/3 ADDRESSED
- [x] Point à confirmer à la relecture : le sondage de `/etat` toutes les 5 s ne maintient pas la session en vie et ne la rouvre jamais seul — preuve : le sondage de `/etat` ne rouvre jamais la session seul (`sonde()` ne fait que lire) ; vérifié par les relecteurs

## A3 — Contrôle de secrets et commit
- [x] `controleur-secrets` lancé et lu, sur la page, la sonde et le plan — preuve : contrôle de secrets OK : 978 lignes examinées, 0 alerte
- [ ] Commit par chemins `feat(ftp): page du navigateur FTP` (français, sans accents, sans Co-Authored-By) ; `tasks/README.md` non commité
- [ ] Case d'A5 cochée dans `tasks/plans/navigateur-ftp-cartes.md` avec le numéro du commit, puis prévenir l'utilisateur

## A4 — Retour au plan d'avant
Ce plan n'est qu'une reprise de l'action A5 du plan `tasks/plans/navigateur-ftp-cartes.md` (le plan d'avant, qui reste le plan
de référence : spec, contraintes globales, A6 et A7). Il se referme quand A5 y est cochée.
- [ ] A5 cochée dans `tasks/plans/navigateur-ftp-cartes.md` avec les preuves de ce plan (sonde verte, relecture, commit)
- [ ] Ce plan passé à `statut: clos`, le journal `.superpowers/sdd/navigateur-ftp-cartes/progress.md` complété (« Task 5 (A5): complete »)
- [ ] Retour au plan d'avant : l'utilisateur prévenu que A5 est finie, puis feu vert demandé pour A6 (annuaire, tâche VS Code avec accord requis, cible Custom, documentation)

## Améliorations restantes
- [ ] [projet] Fermeture d'un onglet : décider si le FTP doit survivre tant qu'un autre onglet est ouvert (identifiant d'onglet) ; la règle actuelle suit la spec §7
- [ ] [projet] Déplacement d'un fichier protégé : seconde confirmation à décider avec l'utilisateur

## Vérification
Sonde Chrome verte (pastille « actif », liste de `/histo`, noms spéciaux, suppression de `autoexec.be` : 1 confirmation = toujours
présent, 2 = supprimé, fermeture d'onglet = `UfsFTP 0` reçu par le faux serveur, console sans erreur), banc du serveur web vert,
aucun Chrome `sonde_` orphelin.
