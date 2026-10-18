---
chantier: plan-par-conversation
titre: La vue de droite suit le plan de la conversation active
statut: clos
cree: 2026-10-18
maj: 2026-10-18
source: bright-mixing-phoenix.md
---
# La vue de droite suit le plan de la conversation active

## Contexte
Demande du 2026-10-18 : quand on passe d'une conversation Claude à une autre, la vue « Suivi du plan »
(extension `fdaubercy.suivi-plan`) doit afficher le plan suivi par CETTE conversation. Aujourd'hui elle
montre le choix mémorisé ou le plan actif le plus récent, quelle que soit la conversation.

Décisions de l'utilisateur (2026-10-18) :
- conversation qui ne suit aucun plan → la vue affiche « aucun plan » (avec le bouton de choix) ;
- rattachement automatique (plan validé par ExitPlanMode, plan édité, `/suivi ouvrir`) **plus**
  `/suivi suivre <chantier>` pour rattacher à la main (et `/suivi detacher`).

Faits mesurés (extension Claude 2.1.301, `~/.vscode/extensions/anthropic.claude-code-2.1.301-win32-x64`) :
- chaque conversation est un onglet webview `claudeVSCodePanel` ; son libellé = titre de la session,
  tronqué par `uL1` (> 25 caractères → 24 premiers + « … » ; sans titre → « Claude Code ») ;
- le titre vit dans le transcript `~/.claude/projects/<projet>/<sessionId>.jsonl`, lignes
  `{"type":"ai-title","aiTitle":…}` réécrites régulièrement (et `custom-title` si renommée) : la fin
  du fichier porte le titre courant ;
- côté mod, aucun événement ne signale qu'un onglet devient visible (`session.attach/detach` = surfaces
  distantes) ; chaque onglet est un processus Claude distinct ; `$.session.id()` = nom du transcript.

Mécanisme retenu, à deux voies :
1. **Bascule d'onglet** (immédiate, sans rien taper) : l'extension écoute `window.tabGroups`, lit le
   libellé de l'onglet Claude actif, le compare au libellé calculé des conversations rattachées.
2. **Message envoyé** (filet, couvre aussi la barre latérale et les titres ambigus) : à chaque
   `prompt.submit`, le mod écrit le signal avec le plan de sa conversation, sans ouvrir la vue.

Contrat de fichiers (sous `%USERPROFILE%\.claude\suivi-plan\`) :
- `conversations/<sessionId>.json` = `{ session, racine, fichier, horodatage }` (un fichier par
  conversation : pas de course entre processus ; `fichier: null` = détachée) ;
- `signal.json` gagne `session` et `ouvrir` (absent = `true`, compatibilité) ; `fichier: null` = aucun plan.

## A1 — Mod : rattacher un plan à la conversation
- [x] `ecrisRattachement($, racine, fichier|null)` dans `.claude/mods/suivi-plan/hooks/suivi-plan.mjs` (fichier `conversations/<id>.json`, `$.session.id()`) — preuve : suivi-plan.mjs ecrisRattachement ; banc mod 16/16
- [x] Rattachement automatique : `recopiePlan` (ExitPlanMode), Edit/Write d'un plan (`planVise`), `/suivi ouvrir` — preuve : tests « recopie » et « etape cochee » (RATTACHE) ; mutant 2 detecte
- [x] `/suivi suivre <chantier>` et `/suivi detacher` (+ usage et `argumentHint` à jour) — preuve : test « /suivi suivre et detacher » vert
- [x] `prompt.submit` : signal `{ racine, fichier, session, ouvrir: false }` avec le plan rattaché (ou `null`), hors sous-agent — preuve : test « message envoye » vert ; mutant 1 detecte
- [x] Version du mod montée dans `.claude-plugin/plugin.json` (0.2.0) — preuve : plugin.json 0.2.0 ; « updated from 0.1.0 to 0.2.0 »

## A2 — Mod : banc
- [x] Cas ajoutés à `hooks/suivi-plan.test.ts` : rattachement par ExitPlanMode, par Edit, par `/suivi suivre`, détachement, signal de `prompt.submit` (`ouvrir: false`) — preuve : 16 pass 0 fail
- [x] Témoin : racine sans `tasks/plans` → aucun fichier de rattachement écrit — preuve : TEMOIN etendu (prompt.submit + /suivi detacher) vert
- [x] `claude.cmd plugin validate` et `claude.cmd plugin test .claude/mods/suivi-plan` verts — preuve : « Validation passed » ; 16 pass 0 fail

## A3 — Extension : reconnaître la conversation active
- [x] Module pur `outils_docs/vscode/suivi-plan/conversations.js` : libellé d'onglet (règle `uL1`), titre depuis la fin d'un transcript (custom-title > ai-title), appariement libellé → rattachement (ambigu → aucun) — preuve : test_conversations.js 22 OK
- [x] Banc `test_conversations.js` (node), avec mutant sur la troncature ; ajouté à `EXCLUS` de `installe_suivi_plan.py` — preuve : témoin MUTANT:troncature détecté ; EXCLUS de installe_suivi_plan.py:63
- [x] `extension.js` : écoute `tabGroups.onDidChangeTabs` / `onDidChangeTabGroups`, onglet actif `claudeVSCodePanel` → plan de la conversation ; onglet non Claude → vue inchangée — preuve : essai de fumée (faux vscode) VERT, mutant détecté (4 échecs)
- [x] Lecture des rattachements (`conversations/*.json` de la même racine) et des transcripts (`~/.claude/projects/*/<id>.jsonl`, 64 Ko de fin, cache par mtime+taille) — preuve : essai de fumée : 3 conversations trouvées par titre de transcript
- [x] Journal `LogOutputChannel` « Suivi du plan » : une ligne par bascule (libellé, session trouvée, plan) — preuve : essai de fumée : une ligne par bascule au journal

## A4 — Extension : affichage et signal
- [x] État « conversation sans plan » dans `rendu.js` (message + bouton « Choisir le plan ») et cas au banc `test_rendu.js` — preuve : test_rendu.js 36 OK
- [x] `lisSignal` : champs `session` / `ouvrir` ; `ouvrir: false` → met à jour la vue si elle est ouverte, ne l'ouvre pas ; `fichier: null` → « aucun plan » — preuve : essai de fumée, 5 cas de signal ; journal réel 13:28:50 et 13:29:15 « signal : conversation … » ; correctif 0.2.1 (signal d'une autre conversation ignoré), témoin neutralisé = 2 échecs
- [x] Le choix manuel (`Choisir le plan`) reste possible ; la bascule suivante vers un onglet Claude le remplace — preuve : choisirPlan remet E.conv à null ; surOnglet réévalue au retour sur une conversation
- [x] Version de l'extension montée (`package.json` 0.2.0), réinstallée par `installe_suivi_plan.py --verifier --mod` dans le profil « Frédéric » — preuve : installe_suivi_plan.py --verifier : « Installation prouvee », profil Frédéric

## A5 — Vérification réelle et documentation
- [x] Deux conversations ouvertes, chacune rattachée à un plan différent : la bascule d'onglet change la vue (journal « Suivi du plan » + capture de l'utilisateur) — preuve : journal « Suivi du plan » du 2026-10-18 13:19:13-21 : graphiques-web, modbus-garage, graphiques-web selon l'onglet ; 4 rattachements dans conversations/
- [x] Conversation sans plan : la vue affiche « aucun plan » ; onglet de fichier : vue inchangée — preuve : journal 13:17:19 « Désactiver la journalisa… » -> inconnue (rendu « aucun plan » : test_rendu.js) ; onglet de fichier sans effet : essai de fumée
- [x] `tasks/plans/_FORMAT.md` (§ règles d'usage) et le bloc `.claude/mods/` de `CLAUDE.md` mis à jour (rattachement, `/suivi suivre`) — preuve : _FORMAT.md § Plan d'une conversation ; CLAUDE.md, bloc .claude/mods/suivi-plan

## Améliorations restantes
- [x] [projet] Ligne d'avancement (`$.ui.status`) et bloc `suiviPlan` du contexte centrés sur le plan de la conversation — preuve : mod 0.3.0, majStatut + blocContexte ; test « plan de la conversation : ligne d avancement et bloc » ; mutant B détecté (2 échecs) ; banc 18/18
- [x] [projet] Collision de libellés avec une conversation NON rattachée (même 24 premiers caractères) : non détectée — preuve : extension 0.3.0 : conversations non rattachées des 30 derniers jours + conversation apprise par onglet ; essai de fumée 20 cas VERT, mutants 1 (3 échecs) et 2 (2 échecs) ; collision réelle relevée : « Explore this codebase an… » ×2
- [x] [projet] Signal du mod écrit après `await next(e)` (3,6 s mesurées) : l'écrire avant accélérerait la voie « message envoyé » — preuve : signal écrit avant next ; test « signal ecrit AVANT que le moteur ne recoive le message » ; mutant A détecté
- [x] [projet] Panneau Claude dans la barre latérale : pas d'onglet, seule la voie « message envoyé » joue — preuve : limite d'API documentée (CLAUDE.md, bloc de l'extension) ; couverte par le signal « message envoyé » (appliqué quand l'onglet actif n'est pas une conversation) et la ligne d'avancement de la conversation

## Vérification
- Bancs : `claude.cmd plugin test .claude/mods/suivi-plan`, `node .claude/mods/suivi-plan/tests/test_parseur.mjs`,
  `node outils_docs/vscode/suivi-plan/test_rendu.js`, `node outils_docs/vscode/suivi-plan/test_conversations.js`
  (chaque banc avec son témoin qui doit échouer).
- Réel : mise à jour du mod (`claude.cmd plugin marketplace update mods-tasmota` puis
  `claude.cmd plugin update suivi-plan@mods-tasmota`), extension réinstallée dans le profil actif,
  puis bascule entre deux onglets de conversation dans la fenêtre flottante ; lecture du journal
  « Suivi du plan » (fichier de log de l'hôte d'extensions) et regard de l'utilisateur sur la vue.
  Point à prouver en premier : `tabGroups` voit bien les onglets de la fenêtre flottante.
