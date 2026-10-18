// Banc du parseur des plans suivis : node .claude/mods/suivi-plan/tests/test_parseur.mjs
// Code de sortie 0 = vert. Trois verifications en une passe :
//   1. chaque vecteur (tests/vecteurs/*.md), en LF puis en CRLF, contre tests/attendus.json ;
//   2. les fonctions annexes (prochaines, barre, ligneStatut, resume, slug, enPlanSuivi, fusionneCoches) ;
//   3. TEMOINS : un attendu fausse doit etre rejete, et chaque ligne MUTANT du parseur, remplacee
//      par une version fautive, doit faire echouer au moins un vecteur (sinon le banc ne mesure rien).
import { readFileSync, readdirSync } from "node:fs"
import { dirname, join } from "node:path"
import { fileURLToPath, pathToFileURL } from "node:url"

const ici = dirname(fileURLToPath(import.meta.url))
const cheminParseur = join(ici, "..", "hooks", "parseur-plan.mjs")
const P = await import(pathToFileURL(cheminParseur).href)
const attendus = JSON.parse(readFileSync(join(ici, "attendus.json"), "utf8"))
const vecteurs = Object.fromEntries(readdirSync(join(ici, "vecteurs")).filter(f => f.endsWith(".md"))
  .map(f => [f, readFileSync(join(ici, "vecteurs", f), "utf8").replace(/\r\n?/g, "\n")]))

let nbOk = 0
let nbEchecs = 0
function verifie(nom, ok, info = "") {
  if (ok) nbOk++
  else nbEchecs++
  console.log(`${ok ? "OK    " : "ECHEC "} ${nom}${ok || !info ? "" : "  -> " + info}`)
}

const projette = a => ({
  titre: a.titre, chantier: a.meta.chantier ?? null, global: a.global, fait: a.fait, total: a.total,
  actions: a.actions.map(x => [x.id, x.fait, x.total, x.pourcent, x.ligne]),
  ameliorations: a.ameliorations.map(x => [x.portee, x.fait]),
  nbAlertes: a.alertes.length,
  preuves: a.actions.flatMap(x => x.etapes.filter(e => e.preuve).map(e => e.preuve)),
})

// Rend la liste des ecarts [nom, attendu, obtenu] d'un parseur sur tous les vecteurs
function ecarts(parseur, references) {
  const r = []
  for (const [f, texte] of Object.entries(vecteurs)) {
    const ref = references[f]
    if (!ref) { r.push([f, "attendu absent", ""]); continue }
    for (const [forme, t] of [["LF", texte], ["CRLF", texte.replace(/\n/g, "\r\n")]]) {
      let obtenu
      try { obtenu = JSON.stringify(projette(parseur.analyse(t))) } catch (e) { obtenu = "exception " + e.message }
      if (obtenu !== JSON.stringify(ref)) r.push([`${f} (${forme})`, JSON.stringify(ref), obtenu])
    }
  }
  return r
}

// --- 1. Vecteurs ---
const ecartsReels = ecarts(P, attendus)
for (const f of Object.keys(vecteurs)) {
  const siens = ecartsReels.filter(e => e[0].startsWith(f + " "))
  verifie(`vecteur ${f} (LF et CRLF)`, siens.length === 0, siens.map(e => `${e[0]} attendu ${e[1]} obtenu ${e[2]}`).join(" | "))
}

// --- 2. Fonctions annexes ---
const nominal = P.analyse(vecteurs["nominal.md"])
const suite = P.prochaines(nominal, 3)
verifie("prochaines : 1re = A1 « étape à faire » ligne 14", suite[0]?.action === "A1" && suite[0]?.texte === "étape à faire" && suite[0]?.ligne === 14, JSON.stringify(suite[0]))
verifie("prochaines : 3 au plus, dans l'ordre (A1, A1, A2)", suite.map(s => s.action).join() === "A1,A1,A2", JSON.stringify(suite))
verifie("barre(50) = 5 pleines / 5 vides", P.barre(50) === "█████░░░░░", P.barre(50))
verifie("barre(null) = vide", P.barre(null) === "░░░░░░░░░░", P.barre(null))
const ligne = P.ligneStatut(nominal)
verifie("ligneStatut : chantier, %, action en cours, prochaine", ligne.startsWith("Plan essai") && ligne.includes("50 %") && ligne.includes("A1 2/4") && ligne.includes("prochaine : étape à faire"), ligne)
verifie("ligneStatut d'un plan fini : terminé", P.ligneStatut(P.analyse("# X\n## A1 — a\n- [x] b\n")).includes("100 % · terminé"))
verifie("ligneStatut d'un plan vide : aucune action", P.ligneStatut(P.analyse(vecteurs["vide.md"])).includes("aucune action"))
const res = P.resume(nominal, "tasks/plans/essai.md")
verifie("resume : % global, actions, prochaines, améliorations ; 25 lignes au plus",
  res.includes("50 %") && res.includes("A1 50 % (2/4)") && res.includes("Prochaines étapes") && res.includes("1 [conversation], 1 [projet]") && res.split("\n").length <= 25, res)
verifie("slug : accents, guillemets, espaces", P.slug("Fin des correctifs « voie ModBus »") === "fin-des-correctifs-voie-modbus", P.slug("Fin des correctifs « voie ModBus »"))
verifie("slug d'un titre vide = plan", P.slug("") === "plan")

const brut = "# Suivi des plans : extension\r\n\r\n## A1 — Parseur\r\n- [ ] écrire\r\n"
const suivi = P.enPlanSuivi(brut, { source: "abc.md", date: "2026-10-18" })
const aSuivi = P.analyse(suivi)
verifie("enPlanSuivi : en-tête créé (chantier, statut actif, dates, source), LF",
  aSuivi.meta.chantier === "suivi-des-plans-extension" && aSuivi.meta.statut === "actif" && aSuivi.meta.cree === "2026-10-18" &&
  aSuivi.meta.maj === "2026-10-18" && aSuivi.meta.source === "abc.md" && !suivi.includes("\r") && aSuivi.actions.length === 1, suivi)
const garde = P.analyse(P.enPlanSuivi("---\nchantier: mien\nstatut: en-pause\ncree: 2026-01-01\n---\n# T\n", { date: "2026-10-18" }))
verifie("enPlanSuivi : garde chantier, statut et date de création existants",
  garde.meta.chantier === "mien" && garde.meta.statut === "en-pause" && garde.meta.cree === "2026-01-01" && garde.meta.maj === "2026-10-18", JSON.stringify(garde.meta))

const ancien = "---\nchantier: c\ncree: 2026-10-01\n---\n# T\n## A1 — a\n- [x] Étape  faite — preuve : p1\n- [ ] autre\n"
const nouveau = "---\nchantier: c\ncree: 2026-10-18\n---\n# T\n## A1 — a\n  - [ ] étape faite\n- [ ] autre\n- [ ] nouvelle\n"
const fusion = P.fusionneCoches(ancien, nouveau)
const aFusion = P.analyse(fusion)
verifie("fusionneCoches : coche et preuve reportées (casse, espaces), indentation gardée",
  fusion.includes("  - [x] étape faite — preuve : p1") && aFusion.fait === 1 && aFusion.total === 3, fusion)
verifie("fusionneCoches : date de création de l'ancien gardée", aFusion.meta.cree === "2026-10-01", JSON.stringify(aFusion.meta))
verifie("témoin fusionneCoches : étape absente de l'ancien reste à faire", fusion.includes("- [ ] nouvelle") && fusion.includes("- [ ] autre"), fusion)

// --- 3. Témoins ---
const fausses = JSON.parse(JSON.stringify(attendus))
fausses["nominal.md"].global = 51
verifie("témoin : un attendu faussé (global 51) est rejeté", ecarts(P, fausses).length > 0)

const MUTANTS = {
  "crlf": '  const t = String(texte ?? "")',
  "bloc-code": "    if (false) { continue }",
  "moyenne": "  const global = n ? Math.round(totFait * 100 / Math.max(1, totTotal)) : null",
}
const source = readFileSync(cheminParseur, "utf8").replace(/\r\n?/g, "\n").split("\n")
for (const [nom, remplacement] of Object.entries(MUTANTS)) {
  const i = source.findIndex(l => l.includes("// MUTANT:" + nom))
  if (i < 0) { verifie(`témoin mutant ${nom} : ligne marquée trouvée`, false, "marqueur absent du parseur"); continue }
  const mute = [...source]
  mute[i] = remplacement
  const M = await import("data:text/javascript;base64," + Buffer.from(mute.join("\n")).toString("base64"))
  const e = ecarts(M, attendus)
  verifie(`témoin mutant ${nom} : détecté par les vecteurs`, e.length > 0, "aucun vecteur n'échoue")
}

console.log(`\nTEST_PARSEUR: ${nbEchecs ? "ECHEC" : "OK"} (${nbOk + nbEchecs} tests, ${nbEchecs} echec(s))`)
process.exit(nbEchecs ? 1 : 0)
