---
chantier: menage-appliquer
titre: Ménage du dépôt, version 2 : appliquer un lot de propositions sans impact depuis la page
objectif: Depuis la page Ménage, appliquer par git mv et git rm les seules propositions dont git confirme qu'aucun fichier ne les cite, après un diff, avec refus pendant un build, sur fichier modifié ou destination prise, puis contrôle des renvois des documents.
statut: actif
cree: 2026-11-15
maj: 2026-11-15
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
- [x] `menage_application.py::previsualise(ids, rapport, racine)` : pour chaque proposition cochée, vérifie l'éligibilité (règles ci-dessus), rend les commandes git exactes et le motif de chaque refus ; aucun effet — banc avec faux dépôt, cas hostiles et mutants — preuve : test_menage_application.py VERT (cas hostiles, aperçu sans effet sur l'arbre et l'index, 3 mutants vus par le banc ; un trou réel trouvé et corrigé : destination hors dépôt)
- [x] Route `POST /appliquer/apercu` : refuse hors rapport en cours, ids inconnus, build en cours ; rend le diff (commandes + fichiers touchés) — preuve : test_menage_web.py VERT (404 sans rapport, 409 pendant un build, 400 lot vide, refus archiver et supprimer)

## A2 — Application
- [ ] Garde-fous d'exécution relevés par la relecture de A1 : argv construit `["git","mv","--",chemin,vers]` (jamais en découpant la chaîne `commande`), `GIT_LITERAL_PATHSPECS=1`, `previsualise` REFAIT à l'application avec empreinte et HEAD identiques à l'aperçu, refus d'un build à CE moment-là
- [ ] `menage_application.py::applique(...)` : recontrôle juste avant, exécute `git mv` un par un sans shell (`--` devant les chemins, `:(literal)`), s'arrête à la première erreur et dit ce qui est fait ; banc : fichier modifié entre l'aperçu et l'application, destination créée entre-temps, chemin hostile
- [ ] Route `POST /appliquer` avec confirmation explicite (le diff renvoyé par l'aperçu, son empreinte) ; verrou unique ; journal hors dépôt
- [ ] Lancement de `verifie_references_docs.py` après l'application et affichage de son verdict

## A3 — Page
- [ ] Cases à cocher sur les propositions de l'étape 1, bouton « Voir ce que ça ferait », liste des commandes, bouton « Appliquer » grisé tant que l'aperçu n'est pas affiché ; message final : « relisez git status, rien n'est commité »
- [ ] Sonde Chrome avec témoins (bouton actif sans aperçu, texte hostile, case sur une proposition non éligible)

## A4 — Essai réel et clôture
- [ ] Essai réel sur 1 ou 2 propositions choisies par l'utilisateur, `git restore` ensuite si besoin — preuve : sortie de `git status`
- [ ] Revue (`relecteur-pages-web`, `relecteur-outils-python`), `controleur-secrets`, documentation (README, CLAUDE.md), commit

## A5 — Retour au plan précédent (menage-page)
- [ ] Revenir à `tasks/plans/menage-page.md` : cocher A7 (deux audits réels et décision sur la version 2, preuves : rapports de la passe 2 et décision de l'utilisateur), mettre `statut:` à jour si tout est coché, relancer `/suivi` pour rattacher la conversation à ce plan

## Améliorations restantes
- [ ] [projet] Étape 2 (renvois dans les documents) : proposer la mise à jour des renvois dans le même lot
