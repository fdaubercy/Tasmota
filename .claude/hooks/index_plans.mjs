// Index des plans suivis : regenere tasks/README.md (une ligne par plan actif : objectif, %, attentes ; plans clos en une ligne par famille).
// Les % viennent du parseur partage avec le mod et l'extension (parseur-plan.mjs) : memes chiffres
// que la vue de droite. Seul le bloc entre les deux marqueurs est reecrit, le reste du fichier est garde.
//   node .claude/hooks/index_plans.mjs             -> regenere (silencieux si rien ne change)
//   node .claude/hooks/index_plans.mjs --verifier  -> code 1 si tasks/README.md est en retard ou si un plan clos depuis 2026-11-23 n'a pas de ## Bilan
// Lance par le hook PostToolUse index_plans_edition.sh a chaque edition d'un plan par Claude.
// Banc : node .claude/hooks/test_index_plans.mjs
import fs from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"
import { analyse } from "../mods/suivi-plan/hooks/parseur-plan.mjs"

export const DEBUT = "<!-- debut-index-plans : bloc regenere par .claude/hooks/index_plans.mjs, ne pas editer -->"
export const FIN = "<!-- fin-index-plans -->"
const ORDRE = { actif: 0, "en-pause": 1, clos: 2 }

const cellule = s => String(s ?? "").replace(/\|/g, "\\|").replace(/\s+/g, " ").trim()

export function lignes(dossierPlans) {
  return fs.readdirSync(dossierPlans)
    .filter(n => /\.md$/i.test(n) && !n.startsWith("_"))
    .map(n => ({ nom: n, a: analyse(fs.readFileSync(path.join(dossierPlans, n), "utf8")) }))
    .sort((x, y) => (ORDRE[x.a.meta.statut] ?? 3) - (ORDRE[y.a.meta.statut] ?? 3)
                    || String(y.a.meta.maj).localeCompare(String(x.a.meta.maj)) || x.nom.localeCompare(y.nom))
}

// Ce qui attend un geste hors de Claude, deduit de mots du texte de l'etape (indicatif : un mot-cle, pas une preuve).
export function blocage(texte) {
  if (/confirm|décid|décis|choix|accord|à valider|demander à/i.test(texte)) return "à vous"
  if (/sur (la |une |le |les )?(carte|P4|cuve|esclave|écran|matériel)|essai|à voir|câblage|flash/i.test(texte)) return "sur carte"
  return ""
}
const court = (s, n) => { s = cellule(s); return s.length > n ? s.slice(0, n - 1).trimEnd() + "…" : s }
const nomPlan = nom => nom.replace(/\.md$/i, "")
const lien = nom => `[${nomPlan(nom)}](plans/${nom})`
const jour = m => String(m ?? "").match(/^\d{4}-\d{2}-\d{2}/)?.[0] ?? (cellule(m) || "—")

// Index COURT : une ligne par plan actif ou en pause (groupes par famille), une ligne par famille pour les plans clos.
// Ni cases ni gestes recopies : le detail est dans le plan lui-meme (lien de la premiere colonne).
export function bloc(dossierPlans) {
  const plans = lignes(dossierPlans)
  const ouverts = plans.filter(p => p.a.meta.statut !== "clos"), clos = plans.filter(p => p.a.meta.statut === "clos")
  const familles = ps => [...new Set(ps.map(p => cellule(p.a.meta.famille) || "sans famille"))]
    .sort((x, y) => (x === "sans famille") - (y === "sans famille") || x.localeCompare(y))
  const deLaFamille = (ps, f) => ps.filter(p => (cellule(p.a.meta.famille) || "sans famille") === f)
  const r = [DEBUT, "",
    `${plans.length} plans : ` + ["actif", "en-pause", "clos"]
      .map(s => `${plans.filter(p => p.a.meta.statut === s).length} ${s}`).join(", ") + ".", ""]
  for (const f of familles(ouverts)) {
    r.push(`### ${f}`, "", "| Plan | Objectif | Avancement | Attend | Mis à jour |", "|---|---|---|---|---|")
    for (const { nom, a } of deLaFamille(ouverts, f)) {
      const m = a.meta
      const attend = {}
      for (const act of a.actions) for (const e of act.etapes) if (!e.fait && blocage(e.texte)) attend[blocage(e.texte)] = (attend[blocage(e.texte)] ?? 0) + 1
      const avance = (a.global == null ? "—" : `${a.global} % (${a.fait}/${a.total})`) + (m.statut === "en-pause" ? ", en pause" : "")
      r.push(`| ${lien(nom)} | ${court(m.objectif, 110) || "_à renseigner (clé `objectif:`)_"} | ${avance} ` +
             `| ${Object.entries(attend).map(([k, n]) => `${n} ${k}`).join(", ") || "—"} | ${jour(m.maj)} |`)
    }
    r.push("")
  }
  if (clos.length) {
    r.push("### Plans clos", "")
    for (const f of familles(clos)) r.push(`- ${f} (${deLaFamille(clos, f).length}) : ` + deLaFamille(clos, f).map(p => lien(p.nom)).join(", "))
    r.push("")
  }
  r.push(FIN)
  return r.join("\n")
}

// A18 : un plan clos depuis le 2026-11-23 doit porter une section `## Bilan` (les plans clos avant n'en ont pas : transition).
export const BILAN_DEPUIS = "2026-11-23"
export function sansBilan(dossierPlans) {
  return lignes(dossierPlans)
    .filter(({ nom, a }) => a.meta.statut === "clos" && jour(a.meta.maj) >= BILAN_DEPUIS)
    .filter(({ nom }) => !/^##\s+Bilan\s*$/m.test(fs.readFileSync(path.join(dossierPlans, nom), "utf8").replace(/```[\s\S]*?```/g, "")))
    .map(p => p.nom)
}

const ENTETE = `# Suivi des plans de travail

Trace des plans de modification du fork (\`tasks/plans/\`, format \`tasks/plans/_FORMAT.md\`).
Une ligne par plan actif, les plans clos en une ligne par famille. Le détail (étapes, preuves) est dans le plan.
Avancement = moyenne des % des actions \`## A<n>\` (même calcul que la vue « Suivi du plan » de VS Code).
Mise à jour seule dès qu'un plan change (extension VS Code) ; sans VS Code : \`node .claude/hooks/index_plans.mjs\`.

`

export function regenere(depot, verifier = false) {
  const fichier = path.join(depot, "tasks", "README.md")
  const ancien = fs.existsSync(fichier) ? fs.readFileSync(fichier, "utf8").replace(/\r\n/g, "\n") : ENTETE
  const nouveauBloc = bloc(path.join(depot, "tasks", "plans"))
  const i = ancien.indexOf(DEBUT), j = ancien.indexOf(FIN)
  const nouveau = i >= 0 && j > i
    ? ancien.slice(0, i) + nouveauBloc + ancien.slice(j + FIN.length)
    : ancien.replace(/\n*$/, "\n\n") + nouveauBloc + "\n"
  if (verifier) {
    const manque = sansBilan(path.join(depot, "tasks", "plans"))
    if (manque.length) console.error(`Plan(s) clos sans section "## Bilan" (obligatoire depuis ${BILAN_DEPUIS}) : ${manque.join(", ")}`)
    if (nouveau !== ancien) console.error("tasks/README.md est en retard sur tasks/plans/ : node .claude/hooks/index_plans.mjs")
    return manque.length || nouveau !== ancien ? 1 : 0
  }
  if (nouveau !== ancien) fs.writeFileSync(fichier, nouveau, "utf8")
  return 0
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const depot = process.env.CLAUDE_PROJECT_DIR || path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..")
  process.exit(regenere(depot, process.argv.includes("--verifier")))
}
