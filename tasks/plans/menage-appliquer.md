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

## Décisions de conception (à valider par l'utilisateur avant A2)
- **Périmètre minimal** : seule l'étape 1 du plan d'action de la page est applicable (aucun renvoi dans les documents, le code ou
  la configuration, vérifié par git, vérification disponible, chemin existant, destination libre, fichier suivi et propre).
  Les étapes 2 à 4 restent manuelles.
- **Actions** : `deplacer` (git mv) et `supprimer` (git rm) seulement. Jamais `archiver`, jamais un dossier d'un coup, jamais un chemin hors de la liste cochée.
- **Réversibilité** : tout passe par git, rien n'est commité par la page. L'utilisateur relit `git status` et commite lui-même ; `git restore --staged --worktree` annule.
- **Garde-fous** : refus pendant un build ; refus si le fichier est modifié ou non suivi ; refus si la destination existe ; contre-vérification refaite
  juste avant l'application (l'état a pu changer depuis l'audit) ; en-tête anti-CSRF et nom d'hôte comme les autres routes ; une seule application à la fois.
- **Fin de chantier** : revenir au plan `menage-page` (A5 ci-dessous), demande de l'utilisateur du 2026-11-15.
- **Après** : `verifie_references_docs.py` est lancé et sa sortie affichée ; les renvois cassés sont listés, jamais corrigés seuls.

## A1 — Aperçu d'un lot (lecture seule)
- [ ] `menage_application.py::previsualise(ids, rapport, racine)` : pour chaque proposition cochée, vérifie l'éligibilité (règles ci-dessus), rend les commandes git exactes et le motif de chaque refus ; aucun effet — banc avec faux dépôt, cas hostiles et mutants
- [ ] Route `POST /appliquer/apercu` : refuse hors rapport en cours, ids inconnus, build en cours ; rend le diff (commandes + fichiers touchés)

## A2 — Application
- [ ] `menage_application.py::applique(...)` : recontrôle juste avant, exécute `git mv` ou `git rm` un par un sans shell (`--` devant les chemins, `:(literal)`), s'arrête à la première erreur et dit ce qui est fait ; banc : fichier modifié entre l'aperçu et l'application, destination créée entre-temps, chemin hostile
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
