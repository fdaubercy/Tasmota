#!/bin/sh
# Hook SessionStart (matcher « compact ») : juste apres un compactage du contexte, rappelle de
# remettre a jour la reprise du chantier, pendant que le detail est encore frais.
# 25 sessions sur 55 compactees (audit du 2026-10-17) : c'est la que le fil se perd.
# Sa sortie est ajoutee au contexte de la session. Ne modifie rien, sort toujours en 0.
cd "$CLAUDE_PROJECT_DIR" 2>/dev/null || exit 0
echo "RAPPEL (contexte compacte) : si un chantier est en cours, mettre a jour MAINTENANT son"
echo "fichier tasks/reprise-*.md (encadre « SI TU REPRENDS A FROID » : prochaine action, ce qui reste),"
echo "et consigner dans tasks/lessons.md toute correction de l'utilisateur pas encore notee."
echo "Pour preparer une passation vers une nouvelle conversation : /fin-de-session."
modifies=$(git status --short 2>/dev/null | head -15)
[ -n "$modifies" ] && printf 'Fichiers modifies non commites :\n%s\n' "$modifies"
exit 0
