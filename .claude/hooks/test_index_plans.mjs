// Banc de index_plans.mjs : faux depot dans le dossier temporaire, jamais le vrai. Code 0 = vert.
import fs from "node:fs"
import os from "node:os"
import path from "node:path"
import assert from "node:assert/strict"
import { regenere, blocage, sansBilan, DEBUT, FIN } from "./index_plans.mjs"

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
assert.match(t, /\| \[essai\]\(plans\/essai\.md\) \| Tester l'index \| 75 % \(2\/3\) \| — \| 2026-10-29 \|/)   // (50 + 100) / 2
assert.ok(t.includes("### sans famille"), "plan sans famille : groupe de fin")
assert.ok(!t.includes("pas un plan"), "les fichiers _*.md ne sont pas des plans")
assert.ok(!t.includes("polir") && !t.includes("- A1"), "ni cases ni ameliorations recopiees : le detail reste dans le plan")
assert.equal(regenere(depot, true), 0, "a jour")

fs.writeFileSync(f, "Intro a la main\n\n" + t.slice(t.indexOf(DEBUT)) + "\nNote finale\n")
fs.writeFileSync(path.join(plans, "essai.md"), plan("x"))
assert.equal(regenere(depot, true), 1, "plan avance = en retard")
regenere(depot)
t = fs.readFileSync(f, "utf8")
assert.match(t, /100 % \(3\/3\)/)
assert.ok(t.startsWith("Intro a la main") && t.endsWith(FIN + "\n\nNote finale\n"),"texte hors bloc garde")

// Attentes : comptees par etiquette sur les plans non clos ; un plan clos n'a qu'un lien.
assert.equal(blocage("Confirmer l'appareil réel"), "à vous")
assert.equal(blocage("Essai sur le P4"), "sur carte")
assert.equal(blocage("Écrire le banc"), "")
const bloque = `---
titre: Bloque
statut: actif
famille: cave
maj: 2026-10-30
---
## A1 — Un
- [ ] Confirmer avec l'utilisateur
- [ ] Essai sur le P4
- [ ] Coder
`
fs.writeFileSync(path.join(plans, "bloque.md"), bloque)
fs.writeFileSync(path.join(plans, "clos.md"), bloque.replace("actif", "clos"))
regenere(depot)
t = fs.readFileSync(f, "utf8")
assert.match(t, /\| \[bloque\]\(plans\/bloque\.md\) \|[^|]*\| 0 % \(0\/3\) \| 1 à vous, 1 sur carte \| 2026-10-30 \|/)
assert.match(t, /### Plans clos\n\n- cave \(1\) : \[clos\]\(plans\/clos\.md\)/)
assert.ok(t.indexOf("### cave") < t.indexOf("### sans famille") && t.indexOf("### sans famille") < t.indexOf("### Plans clos"), "ordre : familles, sans famille, clos")
assert.equal(regenere(depot, true), 0, "a jour (clos de 2026-10-30 : pas de bilan exigé)")

// Taille : ne depend pas du nombre de cases (500 cases ouvertes = meme index, a quelques chiffres pres).
const taille = () => fs.statSync(f).size
const avant = taille()
fs.writeFileSync(path.join(plans, "gros.md"), `---\ntitre: Gros\nstatut: actif\nfamille: cave\nmaj: 2026-11-01\nobjectif: Gros plan\n---\n## A1 — Un\n` + "- [ ] une case de plus\n".repeat(500))
regenere(depot)
assert.ok(taille() - avant < 250, `une ligne par plan, pas une ligne par case (+${taille() - avant} o)`)
fs.rmSync(path.join(plans, "gros.md"))

// A18 : plan clos depuis le 2026-11-23 sans "## Bilan" = rouge ; avec bilan (hors bloc de code) = vert ; clos avant = ignoré.
const recent = `---\ntitre: Recent\nstatut: clos\nfamille: cave\nmaj: 2026-11-23 (note)\n---\n## A1 — Un\n- [x] fait\n`
fs.writeFileSync(path.join(plans, "recent.md"), recent)
regenere(depot)
assert.equal(regenere(depot, true), 1, "clos recent sans bilan")
assert.deepEqual(sansBilan(plans), ["recent.md"])
fs.writeFileSync(path.join(plans, "recent.md"), recent + "```\n## Bilan\n```\n")
assert.equal(regenere(depot, true), 1, "un Bilan dans un bloc de code ne compte pas")
fs.writeFileSync(path.join(plans, "recent.md"), recent + "\n## Bilan\nCa a marche.\n")
assert.equal(regenere(depot, true), 0, "clos recent avec bilan")

fs.rmSync(depot, { recursive: true })
console.log("index_plans : vert")
