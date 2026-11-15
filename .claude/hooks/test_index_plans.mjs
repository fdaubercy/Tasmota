// Banc de index_plans.mjs : faux depot dans le dossier temporaire, jamais le vrai. Code 0 = vert.
import fs from "node:fs"
import os from "node:os"
import path from "node:path"
import assert from "node:assert/strict"
import { regenere, blocage, DEBUT, FIN } from "./index_plans.mjs"

const depot = fs.mkdtempSync(path.join(os.tmpdir(), "index-plans-"))
const plans = path.join(depot, "tasks", "plans")
fs.mkdirSync(plans, { recursive: true })
const plan = coche => `---\ntitre: Essai\nstatut: actif\nobjectif: Tester l'index\nmaj: 2026-10-29\n---\n` +
  `## A1 — Un\n- [x] a\n- [${coche}] b\n## A2 — Deux\n- [x] c\n## Améliorations restantes\n- [ ] [projet] polir\n- [x] [projet] deja faite\n`
fs.writeFileSync(path.join(plans, "essai.md"), plan(" "))
fs.writeFileSync(path.join(plans, "_FORMAT.md"), "## A1 — pas un plan\n- [ ] x\n")

assert.equal(regenere(depot, true), 1, "fichier absent = en retard")
assert.equal(regenere(depot), 0)
const f = path.join(depot, "tasks", "README.md")
let t = fs.readFileSync(f, "utf8")
assert.match(t, /\| \[Essai\]\(plans\/essai\.md\) \| Tester l'index \| actif \| .* 75 % \(2\/3\) \|/)   // (50 + 100) / 2
assert.ok(!t.includes("pas un plan"), "les fichiers _*.md ne sont pas des plans")
assert.match(t, /75 % \(2\/3\) \| 1 étape, 1 amélioration \|/, "colonne Reste a faire")
assert.match(t, /#### \[Essai\]\(plans\/essai\.md\) — 75 %\n\n- A1 — Un : b\n- Amélioration \[projet\] : polir\n/, "points restants du plan")
assert.ok(!t.includes(": a\n") && !t.includes("deja faite"), "etape et amelioration faites : absentes")
assert.equal(regenere(depot, true), 0, "a jour")

fs.writeFileSync(f, "Intro a la main\n\n" + t.slice(t.indexOf(DEBUT)) + "\nNote finale\n")
fs.writeFileSync(path.join(plans, "essai.md"), plan("x"))
assert.equal(regenere(depot, true), 1, "plan avance = en retard")
regenere(depot)
t = fs.readFileSync(f, "utf8")
assert.match(t, /100 % \(3\/3\)/)
assert.ok(!t.includes("- A1 — Un : b"), "etape cochee : sortie des points restants")
assert.match(t, /100 % \(3\/3\) \| 1 amélioration \|/, "plan fini, amelioration ouverte : signalee")
assert.ok(t.startsWith("Intro a la main") && t.endsWith(FIN + "\n\nNote finale\n"),"texte hors bloc garde")

// Etiquettes de blocage : section de tete (plans actifs seulement) et marque dans les points restants.
assert.equal(blocage("Confirmer l'appareil réel"), "à vous")
assert.equal(blocage("Essai sur le P4"), "sur carte")
assert.equal(blocage("Écrire le banc"), "")
const bloque = `---
titre: Bloque
statut: actif
maj: 2026-10-30
---
## A1 — Un
- [ ] Confirmer avec l'utilisateur
- [ ] Essai sur le P4
- [ ] Coder
`
fs.writeFileSync(path.join(plans, "bloque.md"), bloque)
fs.writeFileSync(path.join(plans, "clos.md"), bloque.replace("actif", "clos").replace("Bloque", "Clos"))
regenere(depot)
t = fs.readFileSync(f, "utf8")
assert.match(t, /### Attendent un geste hors de Claude[\s\S]*?- \[à vous\] \[Bloque\]\(plans\/bloque\.md\) — A1 — Un : Confirmer/, "section de tete")
assert.match(t, /- \[sur carte\] \[Bloque\]/)
const tete = t.slice(t.indexOf("### Attendent"), t.indexOf("| Plan |"))
assert.ok(!tete.includes("Coder") && !tete.includes("[Clos]"), "ni etape libre ni plan clos dans la section de tete")
assert.ok(t.indexOf("### Attendent") < t.indexOf("| Plan |"), "avant le tableau")
assert.match(t, /- \[à vous\] A1 — Un : Confirmer/, "marque dans les points restants")
assert.equal(regenere(depot, true), 0, "a jour")

fs.rmSync(depot, { recursive: true })
console.log("index_plans : vert")
