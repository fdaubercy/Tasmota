# Suivi du plan (extension VS Code locale)

Affiche, dans une vue a droite de l'editeur, l'avancement du plan `tasks/plans/<chantier>.md`
(format : `tasks/plans/_FORMAT.md`) : % global, % et etapes de chaque action (clic = ouvre la
ligne a gauche), ameliorations restantes, alertes. Rafraichie a chaque enregistrement du plan ;
`Plan 74 %` dans la barre d'etat. S'ouvre aussi sur le signal du mod Claude `suivi-plan`
(`~/.claude/suivi-plan/signal.json`) ou par `vscode://fdaubercy.suivi-plan/ouvrir?fichier=tasks/plans/x.md`.

Calcul : parseur unique `.claude/mods/suivi-plan/hooks/parseur-plan.mjs`, copie dans le `.vsix`.

**Installation** (chaque poste, et apres toute modification de l'extension ou du parseur) :
`python outils_docs/scripts_python/maintenance/installe_suivi_plan.py --verifier` (`--etat` :
diagnostic ; `--mod` : installe aussi le mod Claude ; `--help` : repli manuel).

**Commandes** : « Suivi du plan : ouvrir à droite », « Suivi du plan : choisir le plan ».
**Reglages** : `suiviPlan.dossier` (`tasks/plans`), `suiviPlan.ouvrirAuto` (true), `suiviPlan.ouvrirAvecConversation`
(true : la vue s'ouvre d'elle-meme quand la conversation Claude active suit un plan - message envoye ou bascule vers
son onglet -, une fois par conversation et par fenetre ; refermee a la main, elle reste fermee pour cette conversation).

Developpement : `code --extensionDevelopmentPath=outils_docs/vscode/suivi-plan .` ;
banc du rendu : `node outils_docs/vscode/suivi-plan/test_rendu.js`.
