#!/bin/sh
# Hook PreToolUse (Bash | PowerShell) : filtre rapide devant garde_build.py.
# Toute commande sans « pio » ni « platformio » sort ici, sans lancer Python (cout ~ un sh).
# Les autres passent a garde_build.py, qui refuse un `pio run` pendant un build en cours.
entree=$(cat)
case "$entree" in
    *pio*|*platformio*) ;;
    *) exit 0 ;;
esac
printf '%s' "$entree" | python -I "$CLAUDE_PROJECT_DIR/.claude/hooks/garde_build.py"
