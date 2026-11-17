---
chantier: menage-appliquer
titre: Ménage du dépôt, version 2 : appliquer un lot de propositions sans impact depuis la page
objectif: Depuis la page Ménage, appliquer par git mv et git rm les seules propositions dont git confirme qu'aucun fichier ne les cite, après un diff, avec refus pendant un build, sur fichier modifié ou destination prise, puis contrôle des renvois des documents.
statut: clos
cree: 2026-11-15
maj: 2026-11-17
famille: methode
parent: menage-page
liens: menage-page
---
# Ménage du dépôt, version 2 : appliquer un lot

> Pour l'exécutant : skill `superpowers:test-driven-development`. Les étapes se cochent avec `— preuve : …` (voir `_FORMAT.md`).
> Python de PlatformIO (`~/.platformio/penv/Scripts/python.exe`). Aucun `pio run` pendant ce chantier. Sensibilité critique
> (suppression de fichiers) : chaque résultat est relu dans le fil principal avant d'être appliqué.

## Décisions de conception (validées par l'utilisateur le 2026-11-15 : étape 1 seulement, déplacements seulement en version 1, essai réel proposé par Claude)
- **Périmètre minimal** : seule l'étape 1 du plan d'action de la page est applicable (aucun renvoi dans les documents, le code ou
  la configuration, vérifié par git, vérification disponible, chemin existant, destination libre, fichier suivi et propre).
  Les étapes 2 à 4 restent manuelles.
- **Actions** (révisé le 2026-11-15 après l'audit refait : l'étape 1 ne contient que des suppressions) : `deplacer` (git mv) et `supprimer` (git rm SANS -f ni -r), toujours limitées à l'étape 1. Jamais `archiver`, jamais un dossier d'un coup, jamais un chemin hors de la liste cochée, jamais le dossier `modbus poll` (code d'enregistrement d'un logiciel tiers : historique git, passe par `controleur-secrets`).
- **Dry-run d'abord** : l'aperçu lance `git rm -n` / `git mv -n` (sortie réelle de git affichée). « Appliquer » reste grisé tant que le dry-run du MÊME lot (empreinte, HEAD) n'est pas passé sans erreur ; il est relancé juste avant l'exécution réelle sans `-n`.
- **Réversibilité** : tout passe par git, rien n'est commité par la page. L'utilisateur relit `git status` et commite lui-même ; `git restore --staged --worktree` annule.
- **Garde-fous** : refus pendant un build ; refus si le fichier est modifié ou non suivi ; refus si la destination existe ; contre-vérification refaite
  juste avant l'application (l'état a pu changer depuis l'audit) ; en-tête anti-CSRF et nom d'hôte comme les autres routes ; une seule application à la fois.
- **Fin de chantier** : revenir au plan `menage-page` (A5 ci-dessous), demande de l'utilisateur du 2026-11-15.
- **Après** : `verifie_references_docs.py` est lancé et sa sortie affichée ; les renvois cassés sont listés, jamais corrigés seuls.

## A1 — Aperçu d'un lot (lecture seule)
- [x] `menage_application.py::previsualise(ids, rapport, racine)` : pour chaque proposition cochée, vérifie l'éligibilité (règles ci-dessus), rend les commandes git exactes et le motif de chaque refus ; aucun effet — banc avec faux dépôt, cas hostiles et mutants — preuve : test_menage_application.py VERT (cas hostiles, aperçu sans effet sur l'arbre et l'index, 3 mutants vus par le banc ; un trou réel trouvé et corrigé : destination hors dépôt ; révisé le 2026-11-15 : `supprimer` (git rm) accepté à l'étape 1, simulation par `git rm -n` / `git mv -n`, empreinte liée au HEAD, mutants dry-run)
- [x] Route `POST /appliquer/apercu` : refuse hors rapport en cours, ids inconnus, build en cours ; rend le diff (commandes + fichiers touchés) — preuve : test_menage_web.py VERT (404 sans rapport, 409 pendant un build, 400 lot vide, refus archiver et supprimer)

## A2 — Application
- [x] Garde-fous d'exécution relevés par la relecture de A1 : argv construit `["git","mv","--",chemin,vers]` (jamais en découpant la chaîne `commande`), `GIT_LITERAL_PATHSPECS=1`, `previsualise` REFAIT à l'application avec empreinte et HEAD identiques à l'aperçu, refus d'un build à CE moment-là — preuve : § 8 : aperçu refait, HEAD ou fichier changé = refus, empreinte/head vides ou inventés refusés, build refusé au moment de l'application, mutant sans recontrôle vu par le banc
- [x] `applique` exécute `argv_git(action, chemin, vers, False)` (jamais `commande.split()`), crée avant `git mv` le dossier `cree_dossier` (git -n l'accepte absent, git mv non) — preuve : test_menage_application.py § 8 VERT (git rm et git mv réels sur dépôts jetables, dossier créé avant git mv, rien commité)
- [x] `menage_application.py::applique(...)` : recontrôle juste avant, exécute `git mv` un par un sans shell (`--` devant les chemins, `:(literal)`), s'arrête à la première erreur et dit ce qui est fait ; banc : fichier modifié entre l'aperçu et l'application, destination créée entre-temps, chemin hostile — preuve : § 8 : erreur de git à la 2e ligne = arrêt, 1 fait, fautive nommée, restantes non lancées, dossiers créés pour rien retirés ; git restore annule
- [x] Route `POST /appliquer` avec confirmation explicite (le diff renvoyé par l'aperçu, son empreinte) ; verrou unique ; journal hors dépôt — preuve : test_menage_web.py VERT (400 sans confirme true, 400 sans empreinte, 409 empreinte étrangère, 404 sans rapport) ; journal `applications.jsonl` hors dépôt testé dans § 8
- [x] Lancement de `verifie_references_docs.py` après l'application et affichage de son verdict — preuve : `applique` rend `renvois` {code, sortie} après chaque application (test § 8, contrôleur injecté) ; jamais de correction automatique

## A3 — Page
- [x] Avertissement affiché près du bouton : la contre-vérification ne voit pas un renvoi construit dynamiquement (listes `custom_files_*` de l'ini, glob) ; `git restore --staged --worktree <chemin>` annule une suppression — preuve : texte du bloc « Appliquer un lot » (menage_page.py), sonde Chrome VERT
- [x] Cases à cocher sur les propositions de l'étape 1, bouton « Voir ce que ça ferait », liste des commandes, bouton « Appliquer » grisé tant que l'aperçu n'est pas affiché ; message final : « relisez git status, rien n'est commité » — preuve : test_menage_page_chrome.py VERT : une seule case (suppression sans renvoi), boutons grisés, « Appliquer » grisé sans aperçu, aperçu simulé par git, à blanc, confirmation, résultat, annulation par git restore
- [x] Sonde Chrome avec témoins (bouton actif sans aperçu, texte hostile, case sur une proposition non éligible) — preuve : témoins lot-sans-confirm et lot-apercu-garde détectés ; dépôt jetable, jamais le vrai

## A4 — Rouvrir un rapport sauvegardé (manque constaté le 2026-11-15 : la page redémarrée n'a aucun rapport, donc ni cases ni bloc « Appliquer un lot » ; les rapports ne vivent que sur disque dans `%LOCALAPPDATA%\outils_tasmota\menage\rapports\`)
- [x] Route `GET /rapports` (liste : nom, date, nombre de propositions, passe) et `POST /rapports/ouvrir {nom}` : nom pris dans la liste seulement (jamais un chemin libre), rapport revalidé par `menage_rapport.valide`, contre-vérification refaite par git à l'ouverture (l'état du dépôt a pu changer) ; refus si un audit est en cours ; tests dont nom hostile (`..`, chemin absolu) et rapport illisible — preuve : test_menage_lancement.py et test_menage_web.py VERT (liste, nom hors liste = 404 dont ../ et chemin absolu, rapport illisible ou invalide = 400 sans changer la page, verdict git écrit dans le fichier écarté et refait, 409 pendant un audit, mutant sans contrôle de liste vu)
- [x] Bouton « Rouvrir un rapport » dans la page : liste des rapports sauvegardés, bandeau « rapport du <date>, contre-vérifié maintenant », mêmes cases et même bloc de lot qu'après un audit ; sonde Chrome avec témoin (ouverture d'un rapport sans relancer d'audit, cases visibles) — preuve : test_menage_page_chrome.py VERT (1332 vérifications), témoins rouvre-sans-affichage, rouvre-lot-garde, rouvre-appliquees-gardees, rouvre-sans-attente détectés ; indicateur « Ouverture… » ajouté après constat de l utilisateur (ouverture longue sans retour visuel) ; garde de l aperçu tardif passée à un compteur de génération

## A5 — Essai réel et clôture
- [x] Essai réel sur 1 ou 2 propositions choisies par l'utilisateur (candidats proposés : les deux fichiers verrou Word `~$…docx` de `outils_docs/Electronique/Connecteur ModBus/`), `git restore` ensuite si besoin — preuve : sortie de `git status` — preuve : essai réel du 2026-11-15 par la page, 2 suppressions appliquées (git rm des deux fichiers verrou Word ~$…docx de Connecteur ModBus) puis gardées par l'utilisateur ; git status : 2 lignes D, aucun commit par la page ; au passage : contrôle des renvois résumé en une phrase et bouton Annuler cette application (commit 9fa901709), demandés après l'essai
- [x] Revue (`relecteur-pages-web`, `relecteur-outils-python`), `controleur-secrets`, documentation (README, CLAUDE.md), commit — preuve : deux relectures Opus (pages web, outils Python) et leurs correctifs ; banc web VERT 91, bancs application, vérification, lancement, rapport VERTS, sonde Chrome VERTE (1985 vérifications, 20 témoins détectés, 0 Chrome orphelin) ; controleur-secrets : rien à signaler ; CLAUDE.md (exception des 500 lignes) et README à jour ; commit 8a41ddac4

## A6 — Retour au plan précédent (menage-page)
- [x] Revenir à `tasks/plans/menage-page.md` : cocher A7 (deux audits réels et décision sur la version 2, preuves : rapports de la passe 2 et décision de l'utilisateur), mettre `statut:` à jour si tout est coché, relancer `/suivi` pour rattacher la conversation à ce plan — preuve : A7 de menage-page cochée (voir ce plan)

## Améliorations restantes
- [ ] [projet] Étape 2 (renvois dans les documents) : proposer la mise à jour des renvois dans le même lot
