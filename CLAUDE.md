# Tasmota (fork personnel) — regles de ce depot

> Ces regles ne valent QUE pour ce depot. Elles completent `~/.claude/CLAUDE.md`
> et, en cas de contradiction, elles priment ici.

## Pre-commit : PAS de graphify

**`/graphify --update` ne doit PAS etre lance avant un commit sur ce depot.**

La regle globale l'impose sur mes projets ; ce depot y deroge explicitement (decide le
2026-07-15). Raison : il n'y a **pas de `graphify-out/`** ici, donc rien a mettre a jour ;
et en construire une carte sur un depot de la taille de Tasmota (~15 000 fichiers amont)
serait un chantier sans rapport avec le travail mene.

Ordre de commit sur ce depot : `git add` puis `git commit`. Rien d'autre.

Si une carte de connaissances est creee un jour ici, revoir cette regle.

## Commits

- Messages **sans accents** (precedent d'encodage casse).
- **Pas** de trailer `Co-Authored-By`.
- **Ne jamais pousser** sans demande explicite : le push n'est pas auto-autorise sur ce depot.

## Fichiers a ne jamais toucher sans accord

- `data/fs/*.be` — modules en cours d'ecriture par l'utilisateur.
- `.vscode/settings.json` — suivi par git **et** present en amont : toute modif entrera
  en conflit a chaque synchronisation du fork. Les reglages VS Code personnels vont dans le
  profil actif (`%APPDATA%\Code\User\profiles/<id>/settings.json`), pas ici.

## Vigilances de build

- Un build reecrit `tasmota/user_config_override.h` (`increment_config_holder`) et
  `platformio_override.ini` (`adapteParametresPlatformio_override`). Sauvegarder avant une
  serie de builds experimentaux.
- **Ne jamais lancer un build en parallele de celui de l'utilisateur** : deux `pio` ecrivant
  `tasmota/tasmota.ino.cpp` se plantent mutuellement.
- Pour surveiller un build en redirigeant la sortie, poser `PYTHONIOENCODING=utf-8` :
  sinon Python passe en cp1252, le `✔` du script pre-build tue le thread de recopie de pio,
  et **toute** la sortie est perdue. Ne pas « corriger » le script de l'utilisateur pour ca.

## Journal des lecons

`tasks/lessons.md` — a lire en debut de session, a completer apres chaque correction.
