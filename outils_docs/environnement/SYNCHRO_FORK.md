# Synchro du fork avec arendst/Tasmota

Tire de `CLAUDE.md` le 2026-11-23 (plan `binomes-berry`, A11).

## Synchro du fork : un hook qui DETECTE, une synchro qui reste manuelle

Depuis le 2026-07-24, un hook `SessionStart` signale au demarrage si le fork a pris
du retard sur `arendst/Tasmota`. Il **detecte, il ne synchronise pas**.

- `.claude/hooks/verifie_synchro_fork.sh` — fetch cible d'`upstream/development`
  **bride a une fois par 24 h**, calcul du retard, une ligne a l'ecran. Silence
  total si le fork est a jour. Ne touche **jamais** a l'arbre de travail et sort
  toujours en 0 : hors ligne, VPN ou amont indisponible, la session demarre
  normalement.
- `.claude/settings.json` — declare le hook. **`.claude/` est suivi par git** pour
  que le dispositif voyage entre postes ; seuls `.claude/settings.local.json`
  (permissions locales) et `.claude/.derniere-verif-synchro` (horodatage) sont
  dans le `.gitignore`.

Le retard est mesure sur la branche `development`, **pas sur `HEAD`** : on travaille
presque toujours sur une branche de chantier.

### Pourquoi le hook ne lance PAS la synchro

Le lancement automatique de `synchronise_fork_tasmota.py` a ete envisage puis
**rejete** (decide le 2026-07-24). Ne pas le reintroduire :

- un hook a un **timeout** ; un merge tue en plein vol laisse un `MERGE_HEAD` et un
  index a moitie ecrit — exactement l'etat conflictuel que le dispositif est cense
  eviter, et cree sans que personne ne regarde l'ecran ;
- le script est ecrit **pour un humain devant un terminal** : il demande confirmation
  avant la synchro distante et avant de pousser (`synchro_fork_question.py::demander`). Dans un
  hook, l'entree standard n'est pas un terminal -> la synchro est abandonnee (EOFError
  lu comme « non ») ;
- contre les conflits, la vraie prevention est la **frequence** — petits paquets, sur
  `development` propre, **avant** d'ouvrir un chantier — pas l'automatisme.

### Que faire quand le hook signale du retard

Basculer sur `development` avec un arbre propre, puis lancer la synchro a la main,
sortie sous les yeux. Une seule commande : diagnostic, nouveautes de l'amont listees
**avant** toute action, controle d'arbre propre, puis deux confirmations (synchro du
fork en ligne, puis push) :

```
python outils_docs/scripts_python/maintenance/synchronise_fork_tasmota.py
```

Repondre « N » a la premiere question = un diagnostic, rien n'est modifie. `--dry-run`
fait de meme sans poser de question. **Ne jamais merger l'amont
dans une branche de chantier** : le hook le rappelle en affichant la branche courante.

Meme chose depuis une **page web** : tache VS Code « Outil : synchro du fork » ou cible Custom
« Synchro du fork (page web) » -> http://127.0.0.1:7500 (`maintenance/synchro_fork_web.py`). Elle lance
les deux scripts (merge et rebase) tels qu'au terminal, leurs questions deviennent des boutons
(`synchro_fork_question.demander`) ; en plus : etat du fork, fichiers modifies et leur diff, journal
et son commit. Le push force du rebase exige de saisir le nom de la branche, verifie cote serveur.
Depuis le 2026-10-27, apres un « Diagnostic seul » reussi, la page affiche un **assistant pas a pas**
(etapes calculees sur le depot local) : voie A = le script de merge, voie B = merge local guide
fichier par fichier si conflit prevu ou commits non pousses. Jamais de rebase, stash, reset ni push
force ; le rebase est replie dans « Avance ». Mode d'emploi : `outils_docs/guides_outils/synchro_fork.md` § « Synchro du fork
(page web) ».
