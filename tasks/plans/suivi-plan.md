---
chantier: suivi-plan
titre: Suivi des plans de travail (extension VS Code + mod)
objectif: Suivre l'avancement des plans en % dans une vue VS Code à droite, partagée entre conversations et postes
statut: clos
cree: 2026-10-18
maj: 2026-10-18
source: reprendre-serialized-firefly.md
---
# Suivi des plans de travail (extension VS Code + mod)

## Contexte
L'utilisateur veut suivre l'avancement des plans de Claude dans une **fenêtre fractionnée à droite**
de VS Code (comme l'aperçu Markdown de sa capture) : actions correctrices, **% par action** (sous-étapes
cochées / total), % global, améliorations restantes (conversation / projet), le tout **partagé entre
conversations et entre ses deux postes**. Décisions prises : extension VS Code locale + mod Claude ;
plans dans `tasks/plans/<chantier>.md` suivis par git ; % = sous-étapes cochées.
Contraintes de l'API des mods 2.1.301 : aucune API pour ouvrir un éditeur/aperçu VS Code ; un `Pane` de
mod se dessine dans la conversation, jamais à droite de l'éditeur → la vue de droite est une **webview
d'extension VS Code** ; deux bandes `AbovePrompt` se masquent (meteo-contexte en a une) → ligne
d'avancement par `$.ui.status` (une par plugin, sans collision). Ce plan-ci sert de premier exemple du format.

## A1 — Format et parseur (E0)
- [x] `tasks/plans/_FORMAT.md` : en-tête YAML (`chantier`, `titre`, `statut: actif|en-pause|clos`, `cree`, `maj`, `source`, `reprise`), actions `## A<n> — titre`, sous-étapes `- [ ]` / `- [x] … — preuve : …`, `## Améliorations restantes` étiquetées `[conversation]` / `[projet]` — preuve : tasks/plans/_FORMAT.md écrit
- [x] Parseur unique `.claude/mods/suivi-plan/hooks/parseur-plan.mjs` (ESM pur, sans E/S) : `analyse`, `prochaines`, `barre`, `ligneStatut`, `resume`, `slug`, `enPlanSuivi`, `fusionneCoches` ; ignore les blocs de code, normalise CRLF, action sans étape = 0 % + alerte — preuve : test_parseur.mjs 24/24
- [x] Vecteurs communs `tests/vecteurs/*.md` + `tests/attendus.json` ; banc `node .claude/mods/suivi-plan/tests/test_parseur.mjs` (code 0 = vert) avec 3 mutants qui doivent échouer (crlf, bloc de code, moyenne) — preuve : 3 mutants détectés, attendu faussé rejeté

## A2 — Premier plan réel (E1)
- [x] Recopier ce plan dans `tasks/plans/suivi-plan.md` (dossier créé) ; parseur sans alerte, % attendu — preuve : resume() = 0 alerte, 23 étapes en 6 actions

## A3 — Extension VS Code `outils_docs/vscode/suivi-plan/` (E2)
- [x] `package.json` (`fdaubercy.suivi-plan` 0.1.0, activation `workspaceContains:tasks/plans/*.md`, `onUri`, commandes « Suivi du plan : ouvrir à droite » / « choisir le plan », réglages `dossier`, `ouvrirAuto`) — preuve : package.json 48 lignes, accepté par code --install-extension
- [x] `extension.js` (JS pur, < 300 lignes) : FileSystemWatcher `tasks/plans/*.md` (anti-rebond 200 ms), webview `ViewColumn.Beside` unique + sérialiseur (revient au redémarrage), barre d'état `Plan 74 %`, UriHandler `vscode://fdaubercy.suivi-plan/ouvrir?fichier=…` (chemin validé sous `tasks/plans/`), surveillance du signal `%USERPROFILE%/.claude/suivi-plan/signal.json` (filtré par `racine`), clic étape → `.md` à la ligne, à gauche — preuve : extension.js 283 lignes, essai avec faux module vscode vert (signal, URI, 8 chemins refusés)
- [x] `rendu.js` (pur, échappe tout le texte du .md) + `media/vue.css` (variables du thème VS Code : clair/sombre seuls) + `media/vue.js` (mise à jour sans recharger, défilement gardé) ; CSP stricte avec nonce — preuve : test_rendu.js : échappement, CSP, nonce ; vue.js exécuté dans Chrome headless sans erreur
- [x] Vue : en-tête (titre, statut, maj, barre du % global), une carte par action (barre, n/total, étapes ☑/☐ + preuve en grisé), améliorations restantes en 2 colonnes, alertes ; sélecteur si plusieurs plans actifs — preuve : test_rendu.js : % et data-ligne = parseur, sur suivi-plan.md réel
- [x] `test_rendu.js` (node) : échappement de `<script>`, CSP, nonce, numéros de ligne — preuve : node test_rendu.js 32/32, copie mutée rouge

## A4 — Installation sur chaque poste (E3)
- [x] `outils_docs/scripts_python/maintenance/installe_suivi_plan.py` (stdlib, idempotent, modèle `corrige_reglages_vscode.py`) : `--etat`, défaut = construit le `.vsix` (zipfile, parseur copié dedans) + `code --install-extension --force`, `--verifier`, `--mod` (marketplace `mods-tasmota` + `claude.cmd plugin install suivi-plan@mods-tasmota`) ; repli : copie dans `%USERPROFILE%\.vscode\extensions\` — preuve : installe_suivi_plan.py --verifier : listé 0.1.0, parseur embarqué = source
- [x] `CLAUDE.md` « MONTER UN NOUVEAU POSTE » : § 4 Suivi des plans (`--verifier --mod`) — preuve : CLAUDE.md « ### 4. Suivi des plans »

## A5 — Mod Claude `.claude/mods/suivi-plan/` (E4)
- [x] `plugin.json` 0.1.0, `hooks/hooks.json`, `hooks/suivi-plan.mjs` (< 300 lignes, modèle `meteo-contexte.mjs`, `on(...)`/`$.x.y(...)` en toutes lettres), entrée dans `.claude/mods/.claude-plugin/marketplace.json` — preuve : plugin validate : Validation passed ; entrée marketplace.json
- [x] Garde : n'agit que si `<racine>/tasks/plans` existe (mod installé pour tous les projets) — preuve : test TEMOIN racine sans tasks/plans (mutant sans garde : 1 échec)
- [x] `tool.call` ExitPlanMode : recopie `r.result.plan` dans `tasks/plans/<chantier>.md` (`statut: actif`, `fusionneCoches` si plan revalidé), écrit le signal (la vue s'ouvre à droite), renvoie un `context` « Plan suivi : … » (+ avertissement si aucun `## A<n>`) ; rien pour un sous-agent, un refus ou une erreur — preuve : tests recopie, revalidation, suffixe -2, isAgent/refus/plan vide
- [x] `prompt.attachment` `{ type: 'plan_mode' }` (variante `full`) : ajoute la consigne de format au rappel du mode plan — preuve : test « consigne seulement full » (mutant : 1 échec)
- [x] `prompt.context` : bloc `suiviPlan` (plan actif, % par action, 3 prochaines étapes, améliorations, règle de coche avec preuve), ≤ 25 lignes → chaque nouvelle conversation connaît le plan — preuve : test bloc suiviPlan ≤ 25 lignes
- [x] Ligne `$.ui.status` « Plan <chantier> ███████░░░ 74 % · A2 3/5 · prochaine : … », recalculée à `session.start`, `turn.complete` (hors sous-agent), après tout Edit/Write d'un plan, et toutes les 30 s (`$.clock.every`, réarmée après rechargement) — preuve : test ligne de statut : session.start, minuterie 30 s, effacement
- [x] Rappel doux (`context`) si une étape est cochée sans « — preuve : » — preuve : test coche sans preuve → context
- [x] Commande `/suivi` (`/plan` est intégrée) : résumé, `liste`, `activer <c>`, `clore [<c>]`, `ouvrir` — preuve : tests /suivi : résumé, liste, ouvrir, clore (CRLF gardés), ../ refusé
- [x] Tests : `claude.cmd plugin validate` + `claude.cmd plugin test` (fs et résultat d'ExitPlanMode simulés par hooks : écriture + context, sous-agent ignoré, racine sans plans ignorée, bloc prompt.context, consigne seulement en `full`, `/suivi`, statut, coche sans preuve) — preuve : claude plugin test 14/14, revérifié dans le fil principal

## A6 — Intégration (E5)
- [x] `CLAUDE.md` : section courte « Plans de travail suivis », point 6 de « AU DÉMARRAGE », carte des documents (extension, mod, script, `tasks/plans/`). Il fait déjà 512 lignes (> 500) : garder les ajouts compacts et le signaler — preuve : point 6, « Plans » dans Demandes récurrentes, 3 entrées de la carte ; CLAUDE.md passe à 533 lignes
- [x] `.claude/commands/fin-de-session.md` : étape « plan actif » (cocher avec preuve, verser le reste dans Améliorations restantes, `clos` à 100 %, ligne `Plan : … — N %` dans le mini-export) — preuve : section « 2 bis. Plan actif »
- [x] Mémoire `project_suivi_plan.md` + pointeur `MEMORY.md` ; proposer (sans modifier) l'ajout de la lecture des plans actifs dans la commande globale `/reprise-session` — preuve : memory/project_suivi_plan.md + MEMORY.md ; proposition faite dans le compte rendu du 2026-10-18

## Améliorations restantes
- [ ] [projet] Bande composée meteo-contexte + suivi-plan (les deux appellent `next(e)`) — après validation de la v1
- [ ] [projet] Outil appelable par Claude pour cocher, seulement si les coches mal formées se répètent
- [ ] [conversation] Regarder la vue à l'écran : à droite, thèmes clair/sombre, mise à jour < 1 s, barre d'état, restauration au redémarrage
- [ ] [conversation] Installer le mod (installe_suivi_plan.py --mod) puis confirmer à l'écran : ligne de statut dans le panneau Claude, bloc suiviPlan dans une nouvelle conversation, recopie + ouverture de la vue après un mode plan, /suivi accepté
- [ ] [conversation] Build et flash du P4 avec les correctifs « voie ModBus » (fait par l'utilisateur), puis commit sur demande

## Vérification
- Parseur : banc node vert, 3 mutants détectés, `attendus.json` faussé → rouge.
- Mod : validate + test verts ; puis bout en bout dans le panneau Claude : mode plan factice approuvé → fichier dans `tasks/plans/`, vue ouverte à droite, ligne de statut visible (à confirmer à l'écran), nouvelle conversation qui connaît le plan.
- Extension : `test_rendu.js` vert, puis lancement réel (`code --extensionDevelopmentPath=…`) et **l'utilisateur regarde** : vue à droite, % conformes, coche enregistrée reflétée < 1 s, clic → bonne ligne, barre d'état, thème clair/sombre, URI valide ouvre / `../` ignoré, vue restaurée au redémarrage. Un banc simulé ne prouve aucun rendu.
- Installation : `installe_suivi_plan.py --verifier` vert, puis sur le second poste.
Ni commit ni push sans demande ; fichiers < 500 lignes ; `.vscode/` non touché.
