# Synchro du fork (page web)

Tiré de `outils_docs/README.md` le 2026-11-23 (plan `binomes-berry`, A20). Aiguillage : `outils_docs/INDEX.md`.

## Synchro du fork (page web)

La page lance les scripts de synchro (`maintenance/synchronise_fork_tasmota.py`, merge, et sa variante rebase) tels
qu'au terminal ; leurs questions deviennent des boutons. Depuis le 2026-10-27, elle propose en plus un **assistant pas
à pas**. Conception : [spec](../../docs/superpowers/specs/2026-10-27-assistant-synchro-fork-design.md) ; plan :
`tasks/plans/assistant-synchro-fork.md`.

### Lancer la page

- **Tuile de l'annuaire** (http://127.0.0.1:7600), groupe « Déploiement ».
- **Tâche VS Code** : `Ctrl+Maj+P` > Run Task > « Outil : synchro du fork ».
- **Cible PlatformIO** « Synchro du fork (page web) » dans *Custom* (jamais pendant un build).

Port **7500**, lien à jeton depuis un autre appareil, comme les autres outils (`acces_web.py`).

### L'assistant

Il s'affiche **après un « Diagnostic seul » réussi** (ou dès le chargement si un merge lancé par lui est en cours),
sous la sortie du diagnostic. Il travaille sur le **dépôt local** : `git fetch` de l'amont et d'origin, puis une liste
d'étapes verticale, une seule dépliée à la fois. Après chaque action, tout est recalculé à partir du dépôt.

1. **Pas d'opération git en cours** : un merge ou un rebase qui n'est pas le sien bloque (merge : « Abandonner » proposé ;
   rebase : à finir au terminal).
2. **Branche `development`** : bouton « Basculer » si l'arbre est propre.
3. **Arbre propre** : fichiers modifiés classés — **rouge** « touché aussi par l'amont », « sans recouvrement »,
   « réécrit par le build ». Chaque fichier a une case (toutes cochées au départ) : un message, puis
   « Commiter la sélection » (`git commit -m <message> -- <fichiers cochés>`, le reste de l'index ne part pas ;
   accents retirés du message, règle du dépôt). Ou `/commite`, puis « Revérifier ».
4. **Nouveautés de l'amont** (information) : commits et fichiers touchés.
5. **Fichiers touchés des deux côtés** (information) : vue trois colonnes base / mon fork / l'amont.
6. **Prévision du merge** (`git merge-tree`) : sans conflit, ou la liste des fichiers en conflit. Elle choisit la voie.
7. **Voie A** (sans conflit et rien à pousser) : lance le script de merge réel ; ses questions « Synchroniser ? » et
   « Pousser ? » restent les siennes.
   **Voie B** (conflit prévu, ou commits locaux non poussés) : « Rattraper origin » si besoin (avance rapide), puis
   « Lancer le merge » (`git merge --no-ff --no-commit`), et pour chaque fichier en conflit : *Garder le mien*,
   *Prendre l'amont*, *Ouvrir dans VS Code* puis *Marquer résolu* (refusé s'il reste des marqueurs). Conflit de
   suppression : *Garder le fichier* / *Le supprimer*. « Terminer le merge » commite et écrit le journal ;
   « Abandonner » (confirmé) remet le dépôt dans son état d'avant.
8. **Commiter le journal** (`HISTORIQUE_SYNCHRO_FORK.md`), puis **Pousser** : confirmation, `git push origin development`,
   délai de 120 s.

Retard nul et rien à pousser : une ligne « fork à jour », les commits d'avance sont normaux.

### Ce qu'il ne fait jamais

- `--force`, `stash`, `reset`, `rebase` (le rebase est replié dans la section **Avancé**, à lancer soi-même).
- Une action sans clic, hormis le fetch ; chaque bouton affiche la commande git exacte.
- Commiter autre chose que le merge en cours, le journal ou les fichiers cochés à l'étape « Arbre propre » ; jamais
  de commit pendant un merge.
- Agir pendant un build (refus, et refus aussi si la détection est impossible), pendant qu'un script tourne, ou sur
  un merge qu'il n'a pas lancé (marque `.git/synchro-fork-assistant`, datée par `MERGE_HEAD`).
- Tuer un merge en plein vol : un délai dépassé est signalé, rien n'est arrêté.

**Pendant un merge de l'assistant, aucune autre session (Claude ou terminal) ne doit commiter ni abandonner le
merge** : un commit emporterait le merge à moitié résolu. La page le verrait ensuite comme un état étranger.

### Bancs

Dans `outils_docs/scripts_python/maintenance/` (code de sortie 0 = vert) : `test_synchro_fork_assistant.py`,
`test_synchro_fork_fusion.py`, `test_synchro_fork_fusion_suite.py`, `test_synchro_fork_web.py`, et la sonde Chrome
`test_synchro_fork_page_chrome.py`. Ils travaillent sur un faux dépôt temporaire (`faux_depot_synchro.py`) ; les
commandes git d'écriture sont limitées par `liste_blanche_git_synchro.py`.
