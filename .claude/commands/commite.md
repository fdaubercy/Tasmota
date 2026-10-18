---
description: Commite le travail en cours selon les regles du depot Tasmota (et pousse seulement avec l'argument « pousse »)
argument-hint: "[pousse] [precision sur le perimetre ou le message]"
---

Commite le travail demande dans ce depot, selon ses regles. Arguments : `$ARGUMENTS`
(`pousse` = pousser apres le commit ; tout autre texte precise le perimetre ou le message).

Regles sources, a ne pas contredire : `CLAUDE.md` du depot (section « Commits ») et `tasks/lessons.md`
(entrees du 2026-09-29 et du 2026-10-12 sur les commits).

## 1. Etat des lieux — lecture seule

1. `git status --porcelain` et `git diff --stat HEAD` ; lire le diff des fichiers du perimetre.
2. Classer chaque fichier modifie ou nouveau :
   - **Travail de cette session** (ou designe dans les arguments) : a commiter.
   - **Reecrits par le build** — `platformio_override.ini`, `tasmota/user_config_override.h`,
     `lib/libesp32/berry_custom/src/modules.h` : **toujours inclus** (lecon du 2026-09-29), ne pas
     proposer de les exclure.
   - **`tasmota/tasmota_defines_for_berry.be` et `.h`** : ne PAS les ajouter (mot de passe Wi-Fi en clair,
     le classifieur refuse ; l'utilisateur les commite lui-meme). Le dire en une ligne.
   - **`data/fs/*.be`, `.vscode/settings.json`, ou tout fichier qu'on n'a pas touche dans cette session** :
     ne pas les ajouter sans accord ; les lister et demander.
3. Si un nouveau dossier est ajoute : `git check-ignore -v <dossier>/x` (un nom generique comme `build`
   est ignore par l'amont).

## 2. Controle de secrets — une porte, pas un log

Dans un appel **SEUL**, jamais enchaine au commit, sur les fichiers qui seront ajoutes (hors
`tasmota_defines_for_berry.*`) :

```
git diff HEAD -- <fichiers> | grep -n -i -E "pass(word)?|pwd|secret|token|api[_-]?key|STA_PASS" | sed 's/"[^"]*"/"***"/g'
```

Lire le resultat. Une valeur nouvelle qui ressemble a un secret → s'arreter et demander. Les mots de
passe deja publics de `user_config_override.h` ne bloquent pas (lecon du 2026-09-29).

## 3. Commit

- `git add` des fichiers retenus, **nommes un par un** — jamais `git add -A` ni `git add .`.
- Message **en francais, sans accents**, titre avec prefixe conventionnel (`feat:`, `fix:`, `docs:`,
  `chore:`, `refactor:`, `test:`, portee optionnelle `fix(modbus):`), corps qui dit le pourquoi.
- **Pas de trailer `Co-Authored-By`** (regle du depot, prioritaire).
- Un seul commit par appel d'outil. Plusieurs commits thematiques → plusieurs appels, en verifiant
  le resultat de chacun ; ne jamais les chainer par `&&`.
- Passer le message par un heredoc **bash** (`git commit -F - <<'EOF' ... EOF`) dans l'outil Bash,
  ou par une here-string `@'...'@` dans l'outil PowerShell — jamais l'une dans l'autre.
- Pas de `/graphify --update` : ce depot y deroge.

## 4. Push — seulement si `pousse` figure dans les arguments

- Sinon, ne pas pousser et le rappeler en une ligne (le push n'est jamais auto-autorise ici).
- Avec `pousse` : `git push` sur la branche courante. Jamais `--force` (refuse par les regles `deny`).

## 5. Compte rendu

Hash et titre du ou des commits, fichiers inclus, fichiers laisses de cote et pourquoi (dont les deux
`tasmota_defines_for_berry.*`), etat du push.
