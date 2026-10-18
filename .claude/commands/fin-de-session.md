---
description: Prepare la passation vers une nouvelle conversation (reprise du chantier, lecons, memoire, mini-export lu par /reprise-session)
argument-hint: "[sujet court de la session]"
---

Prepare la passation de cette conversation vers une nouvelle. Sujet : `$ARGUMENTS` (sinon, le deduire).
But : que la conversation suivante reparte **a froid** avec le minimum de contexte, sans rien perdre.
Ne rien commiter (proposer `/commite` a la fin). Rester bref : ce qui est ecrit sera relu en entier.

## 1. Inventaire — lecture seule

- Lister les demandes de l'utilisateur dans cette conversation, dans l'ordre.
- Pour chacune : statut ✅ finalisee / 🔶 partielle / ❌ a faire, avec une **preuve verifiable**
  (hash de commit, fichier:ligne, sortie de test). Pas de ✅ sans preuve.
- Reperer toute action interrompue en cours d'execution (build, edition non relue, script lance).
- `git status --short` : fichiers modifies non commites, et qui les a modifies (cette session ou l'utilisateur).

## 2. Reprise du chantier

Pour chaque chantier touche (`tasks/reprise-*.md`, voir la carte des documents du CLAUDE.md du depot) :
mettre a jour l'encadre de tete « SI TU REPRENDS A FROID » — etat, **prochaine action**, ce qui reste,
decisions tranchees dans cette session. Remplacer ce qui est perime au lieu d'empiler.

## 3. Lecons et memoire

- `tasks/lessons.md` : ajouter (append uniquement) chaque correction de l'utilisateur pas encore notee,
  au format `[AAAA-MM-JJ] | ce qui s'est mal passe | regle a suivre`.
- Memoire du projet : creer ou mettre a jour un fichier seulement pour un fait durable et non derivable
  du depot (decision, preference, piege d'environnement), et son pointeur dans `MEMORY.md`.

## 4. Mini-export de passation

Ecrire `tasks/export-session-AAAA-MM-JJ-<sujet>.md` (c'est la que `/reprise-session` le cherche),
**60 lignes au plus** :

```
# Passation — <sujet> — <date heure>
Branche : <branche> · Dernier commit : <hash titre> · Non commites : <liste courte>

| # | Demande | Statut | Preuve | Reste a faire |
|---|---------|--------|--------|---------------|

## Actions interrompues
## Prochaine action (une seule, precise)
## A lire en premier (fichiers, dans l'ordre)
## Pieges rencontres dans cette session
```

## 5. Compte rendu a l'utilisateur

- Fichiers mis a jour (reprise, lecons, memoire, export).
- Ce qui n'est pas commite → proposer `/commite`.
- La ligne a coller dans la nouvelle conversation : `/reprise-session C:\Users\fdaub\Documents\Github\Tasmota`

> Declenchable depuis le mod `meteo-contexte` (`.claude/mods/`) : bouton « Preparer la passation »
> affiche a partir de 50 % de contexte (2026-10-18). Evolution possible : porter la commande elle-meme
> dans le mod, pour minimiser encore le contexte.
