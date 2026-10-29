// Banc de index_plans.mjs : faux depot dans le dossier temporaire, jamais le vrai. Code 0 = vert.
import fs from "node:fs"
import os from "node:os"
import path from "node:path"
import assert from "node:assert/strict"
import { regenere, DEBUT, FIN } from "./index_plans.mjs"

const depot = fs.mkdtempSync(path.join(os.tmpdir(), "index-plans-"))
const plans = path.join(depot, "tasks", "plans")
fs.mkdirSync(plans, { recursive: true })
const plan = coche => `---\ntitre: Essai\nstatut: actif\nobjectif: Tester l'index\nmaj: 2026-10-29\n---\n` +
  `## A1 — Un\n- [x] a\n- [${coche}] b\n## A2 — Deux\n- [x] c\n`
fs.writeFileSync(path.join(plans, "essai.md"), plan(" "))
fs.writeFileSync(path.join(plans, "_FORMAT.md"), "## A1 — pas un plan\n- [ ] x\n")

assert.equal(regenere(depot, true), 1, "fichier absent = en retard")
assert.equal(regenere(depot), 0)
const f = path.join(depot, "tasks", "README.md")
let t = fs.readFileSync(f, "utf8")
assert.match(t, /\| \[Essai\]\(plans\/essai\.md\) \| Tester l'index \| actif \| .* 75 % \(2\/3\) \|/)   // (50 + 100) / 2
assert.ok(!t.includes("pas un plan"), "les fichiers _*.md ne sont pas des plans")
assert.equal(regenere(depot, true), 0, "a jour")

fs.writeFileSync(f, "Intro a la main\n\n" + t.slice(t.indexOf(DEBUT)) + "\nNote finale\n")
fs.writeFileSync(path.join(plans, "essai.md"), plan("x"))
assert.equal(regenere(depot, true), 1, "plan avance = en retard")
regenere(depot)
t = fs.readFileSync(f, "utf8")
assert.match(t, /100 % \(3\/3\)/)
assert.ok(t.startsWith("Intro a la main") && t.endsWith(FIN + "\n\nNote finale\n"),"texte hors bloc garde")

fs.rmSync(depot, { recursive: true })
console.log("index_plans : vert")
