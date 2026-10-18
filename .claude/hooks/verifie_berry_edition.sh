#!/bin/sh
# Hook PostToolUse (Edit | Write | MultiEdit) : filtre rapide devant verifie_berry_edition.py.
# Toute edition qui ne vise pas un .be sort ici, sans lancer Python (cout ~ un sh).
# Les autres passent a verifie_berry_edition.py, qui compile le fichier avec verifie_berry.py.
entree=$(cat)
case "$entree" in
    *.be\"*) ;;
    *) exit 0 ;;
esac
printf '%s' "$entree" | python -I "$CLAUDE_PROJECT_DIR/.claude/hooks/verifie_berry_edition.py"
