# Sous-agents de ce dépôt

Relevé du 2026-11-14. Les agents du dépôt vivent dans `.claude/agents/` (un fichier par agent, versionné).
Aucun agent personnel dans `~/.claude/agents/`.

## Agents du dépôt

| Agent | Modèle | Outils | Quand le lancer | Modifie des fichiers |
|---|---|---|---|---|
| `relecteur-berry` | sonnet | Read, Grep, Glob, Bash | Après modification de `.be`, avant commit ou téléversement : charte des logs, RAM/heap, règles du dépôt, bancs Berry | Non |
| `relecteur-pages-web` | sonnet | Read, Grep, Glob, Bash | Après modification d'une page web (outils PC générés par Python, pages `data/sd`) : XSS, anti-CSRF, SSRF, état, JS valide, mode sombre, sondes Chrome | Non |
| `relecteur-pcb` | opus | Read, Grep, Glob, Bash | Avant commande ou après grosse modification d'un PCB KiCad (schéma, placement, routage, sérigraphie, fabrication) ; reçoit le `.kicad_pcb` et le `_persist.json` | Non |
| `placeur-pcb` | opus | Read, Grep, Glob, Bash, Write, Edit | Après les réponses à la question groupée de la skill `pcb-tasmota` : premier jet de placement, carte non routée et rendus | Oui (générateur, carte, rendus) ; ne route pas, n'exporte pas, ne commite pas |
| `verificateur-solidification` | sonnet (effort medium) | Read, Grep, Glob, Bash | Après modification d'un `.be` de `data/fs`, avant commit ou build : builtin masqué, `custom_berry_solidify`, `globs`, ordre de l'autoexec, `banc_demarrage` | Non |
| `controleur-secrets` | opus (effort high) | Read, Grep, Glob, Bash | Avant commit ou push (dépôt public) : secrets dans le diff, l'index, les journaux, l'historique à pousser ; n'affiche jamais une valeur | Non |
| `relecteur-outils-python` | sonnet (effort medium) | Read, Grep, Glob, Bash | Après modification d'un outil de `scripts_python/` (hors page web) : écriture atomique, gardes de build, secrets, entrées, exceptions des 500 lignes, banc lancé | Non |
| `verificateur-plans` | haiku (effort low) | Read, Grep, Glob, Bash | Après des cases cochées dans `tasks/plans/*.md` : preuves vraies, pourcentages, `tasks/README.md` | Non |
| `analyste-journaux-build` | sonnet (effort medium) | Read, Grep, Glob, Bash | Après un échec de `pio run` : première erreur, cause connue ou hypothèse, depuis les journaux ; ne lance aucun build | Non |
| `diagnostic-synchro-fork` | sonnet (effort medium) | Read, Grep, Glob, Bash | Quand le hook signale du retard : nouveautés amont, conflits prévus (`git merge-tree`), voie recommandée ; ne synchronise jamais | Non |
| `relecteur-docs` | haiku (effort low) | Read, Grep, Glob, Bash | Après un chantier ou avant un commit de docs : renvois `fichier::fonction`, chemins, exceptions des 500 lignes, carte des documents | Non |

| `preparateur-push` | opus (effort high) | Read, Grep, Glob, Bash | Avant tout push (appele par `/commite pousse`) : plage des commits, secrets sur toute la plage, branche, retard d'origin, commits d'autres sessions ; verdict et commande de push, ne pousse jamais | Non (mémoire locale seulement) |
| `auditeur-menage` | sonnet (effort medium) | Read, Grep, Glob, Bash | Par `/menage` ou la page « Ménage du dépôt » (:7995), une fois par mois ou après un gros chantier : orphelins, restes, doublons, reclassements, en proposition avec ce que chacune casserait | Non (mémoire locale seulement) |

## Mémoire des agents (2026-11-14)

Six des sept premiers agents, plus `auditeur-menage` et `preparateur-push`, ont `memory: local` : un dossier `.claude/agent-memory-local/<agent>/` (ignoré par git, propre à ce poste),
dont le début de `MEMORY.md` est injecté à chaque lancement. Ils y notent ce qui les aurait aidés (faux positif, piège, commande qui marche).
Exclu volontairement : `controleur-secrets` (jamais de mémoire sur des secrets).
Réserves : la doc (code.claude.com/docs/en/sub-agents) active alors Read, Write et Edit pour l'agent ; ils restent en lecture seule
sur le dépôt par CONSIGNE, non par restriction technique. Version d'introduction du champ non confirmée ; sans effet si l'auto mémoire est coupée.
La mémoire ne suit pas d'un poste à l'autre (`local`) ; passer à `project` la versionnerait, donc la rendrait publique.

## Agents natifs de Claude Code (disponibles partout)

`general-purpose`, `Explore`, `Plan`, `claude`, `claude-code-guide`, `statusline-setup`, `web-fetch`.

## Skills voisines

`bancs` (quel banc lancer), `logs-cartes` (lecture des logs), `tasmota-berry` (écrire du Berry), `pcb-tasmota` (PCB), `lvgl-haspmota` (écrans).

## Ajouter un agent

Créer `.claude/agents/<nom>.md` avec un frontmatter `name`, `description`, `tools`, `model` (et `effort` si besoin), puis ajouter une ligne au tableau ci-dessus.
Ne rien mettre d'autre que des agents dans ce dossier : tout `.md` qui s'y trouve est lu comme un agent.
