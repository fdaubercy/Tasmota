// PowerPoint de l'organigramme des plans : synthese (frise par semaine) + une diapo par famille.
// Usage : node organigramme_pptx.mjs plans.json sortie.pptx
// pptxgenjs est cherche dans %LOCALAPPDATA%\outils_tasmota\organigramme\node_modules (hors depot) :
//   cd %LOCALAPPDATA%\outils_tasmota\organigramme && npm install pptxgenjs@3.12.0
import { createRequire } from "node:module"
import { readFileSync } from "node:fs"
import { join } from "node:path"

const base = join(process.env.LOCALAPPDATA || process.env.HOME, "outils_tasmota", "organigramme", "package.json")
const PptxGenJS = createRequire(base)("pptxgenjs")
const [, , entree, sortie] = process.argv
const D = JSON.parse(readFileSync(entree, "utf-8"))
const COUL = ["1F6FB2", "7A5CB8", "C0561E", "2A8A5A", "B08400", "C0397A"]
const cles = Object.keys(D.familles)
const fr = s => s.slice(8) + "/" + s.slice(5, 7)
const FOND = { actif: "FFFFFF", clos: "ECEFF3", "en-pause": "FDF1E8" }

const pptx = new PptxGenJS()
pptx.layout = "LAYOUT_16x9"
pptx.title = "Organigramme des plans"

function titre(s, texte, sous) {
  s.background = { color: "F6F7F9" }
  s.addText(texte, { x: 0.4, y: 0.2, w: 9.2, h: 0.4, fontFace: "Calibri", fontSize: 20, bold: true, color: "1B2430" })
  if (sous) s.addText(sous, { x: 0.4, y: 0.6, w: 9.2, h: 0.3, fontFace: "Calibri", fontSize: 10, color: "5D6877" })
}

// --- Synthese : lignes = familles, colonnes = semaines de creation
{
  const s = pptx.addSlide()
  const actifs = D.plans.filter(p => p.statut === "actif").length
  titre(s, "Synthèse : " + D.plans.length + " plans en 4 semaines",
    actifs + " actifs, " + D.plans.filter(p => p.statut === "clos").length + " clos. Chaque case liste les plans créés dans la semaine ; un nom ouvre son plan.")
  const debut = new Date("2026-10-18T00:00:00")
  const sem = p => Math.min(3, Math.floor((new Date(p.cree + "T00:00:00") - debut) / 864e5 / 7))
  const ent = ["18-24 oct.", "25-31 oct.", "1-7 nov.", "8-14 nov."]
  const x0 = 1.9, lw = 1.95, y0 = 1.0, hh = 0.25
  ent.forEach((e, i) => s.addText(e, { x: x0 + i * lw, y: y0, w: lw - 0.05, h: hh, fontSize: 9, bold: true, align: "center", color: "FFFFFF", fill: { color: "3A4656" }, fontFace: "Calibri" }))
  const hl = 0.7
  cles.forEach((k, i) => {
    const y = y0 + hh + 0.05 + i * (hl + 0.04)
    s.addText(D.familles[k], { x: 0.4, y, w: 1.45, h: hl, fontSize: 9, bold: true, color: "FFFFFF", fill: { color: COUL[i] }, fontFace: "Calibri", valign: "middle" })
    for (let w = 0; w < 4; w++) {
      const ps = D.plans.filter(p => p.famille === k && sem(p) === w)
      const runs = ps.length ? ps.flatMap((p, j) => [{ text: p.nom + (j < ps.length - 1 ? "  " : ""), options: { hyperlink: { url: p.url }, color: p.statut === "actif" ? "1B2430" : "8A94A3", bold: p.statut === "actif", fontSize: 6.5 } }]) : [{ text: "", options: {} }]
      s.addText(runs, { x: x0 + w * lw, y, w: lw - 0.05, h: hl, fill: { color: "FFFFFF" }, line: { color: "D5DAE1", width: 0.5 }, valign: "top", fontFace: "Calibri", margin: 3 })
    }
  })
  s.addText("Gras = actif · gris = clos. Détail et liens : une diapo par famille.", { x: 0.4, y: 5.2, w: 9, h: 0.25, fontSize: 8, color: "5D6877", fontFace: "Calibri" })
}

// --- Une diapo par famille : arbre parent -> enfant, vignette cliquable
cles.forEach((k, i) => {
  const s = pptx.addSlide()
  const ps = D.plans.filter(p => p.famille === k)
  const noms = new Set(ps.map(p => p.nom))
  const enfants = n => ps.filter(p => p.parent === n)
  const racines = ps.filter(p => !p.parent || !noms.has(p.parent))
  const ordre = []
  const marche = (p, d) => { ordre.push({ p, d }); enfants(p.nom).forEach(c => marche(c, d + 1)) }
  racines.forEach(r => marche(r, 0))
  titre(s, D.familles[k] + " (" + ps.length + " plans)", "Cliquez sur une vignette pour ouvrir le plan. Trait plein = actif, pâle = clos. Plans voisins dans les notes.")
  const parCol = 8, h = 0.5, pas = 0.58, w = 3.0
  const pos = new Map()
  ordre.forEach(({ p, d }, r) => {
    const col = Math.floor(r / parCol), lig = r % parCol
    const x = 0.4 + col * 4.7 + d * 0.4, y = 1.05 + lig * pas
    pos.set(p.nom, { x, y, col })
  })
  ordre.forEach(({ p }) => {
    const q = pos.get(p.nom), pa = p.parent && pos.get(p.parent)
    if (pa && pa.col === q.col) {
      s.addShape(pptx.ShapeType.line, { x: pa.x + 0.15, y: pa.y + h, w: 0, h: q.y + h / 2 - pa.y - h, line: { color: "9AA5B4", width: 1 } })
      s.addShape(pptx.ShapeType.line, { x: pa.x + 0.15, y: q.y + h / 2, w: q.x - pa.x - 0.15, h: 0, line: { color: "9AA5B4", width: 1 } })
    }
  })
  ordre.forEach(({ p }) => {
    const q = pos.get(p.nom)
    s.addText([
      { text: p.nom, options: { bold: true, fontSize: 9, hyperlink: { url: p.url }, color: "1B2430", breakLine: true } },
      { text: fr(p.cree) + " → " + fr(p.maj) + " · " + p.pct + " % · " + p.statut, options: { fontSize: 7, color: "5D6877" } }],
      { x: q.x, y: q.y, w, h, fill: { color: FOND[p.statut] || "FFFFFF" }, line: { color: COUL[i], width: p.statut === "actif" ? 2.25 : 0.75, dashType: p.statut === "en-pause" ? "dash" : "solid" }, fontFace: "Calibri", valign: "middle", margin: 4 })
  })
  s.addNotes(ps.map(p => p.nom + " : " + p.objectif + (p.liens.length ? " [liens : " + p.liens.join(", ") + "]" : "") + (p.specs.length ? " [spec : " + p.specs.join(", ") + "]" : "")).join("\n"))
})

await pptx.writeFile({ fileName: sortie })
console.log("pptx ecrit :", sortie)
