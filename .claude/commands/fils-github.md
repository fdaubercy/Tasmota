---
description: Fils GitHub suivis (reponses signalees au demarrage) : etat, relever, desactiver, activer, ajouter, retirer
argument-hint: "[etat|relever|desactiver|activer|ajouter <url> [sujet]|retirer <url>]"
---
Lance `python "$CLAUDE_PROJECT_DIR/.claude/hooks/fils_github.py" --<action> [arguments]` selon `$ARGUMENTS`
(sans argument : `--etat`). Exemples : `/fils-github desactiver`, `/fils-github ajouter https://github.com/o/r/issues/12 sujet`.
Rends la sortie en francais, en une ou deux lignes. Ne modifie rien d'autre.
