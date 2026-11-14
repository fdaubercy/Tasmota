#!/bin/sh
# Hook PostToolUse (Edit | Write | MultiEdit) : apres l'edition d'un plan de tasks/plans/,
# regenere le tableau d'avancement de tasks/README.md. Toute autre edition sort ici, sans lancer node.
# Seul le champ file_path compte : le contenu edite peut citer tasks/plans/ sans etre un plan.
chemin=$(cat | sed -n 's/.*"file_path" *: *"\([^"]*\)".*/\1/p' | head -n 1)
case "$chemin" in
    *tasks[/\\]plans[/\\]*.md|*tasks\\\\plans\\\\*.md) ;;
    *) exit 0 ;;
esac
node "$CLAUDE_PROJECT_DIR/.claude/hooks/index_plans.mjs" || exit 0
# Organigramme des plans (page web, json, pptx) : meme declencheur, ~3 s, ne bloque jamais.
python "$CLAUDE_PROJECT_DIR/outils_docs/scripts_python/maintenance/organigramme_plans.py" >/dev/null 2>&1 || true
