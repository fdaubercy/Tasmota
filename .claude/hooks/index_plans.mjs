// Index des plans suivis : regenere le tableau de tasks/README.md (objectif, statut, % de chaque plan).
// Les % viennent du parseur partage avec le mod et l'extension (parseur-plan.mjs) : memes chiffres
// que la vue de droite. Seul le bloc entre les deux marqueurs est reecrit, le reste du fichier est garde.
//   node .claude/hooks/index_plans.mjs             -> regenere (silencieux si rien ne change)
//   node .claude/hooks/index_plans.mjs --verifier  -> code 1 si tasks/README.md est en retard sur les plans
// Lance par le hook PostToolUse index_plans_edition.sh a chaque edition d'un plan par Claude.
// Banc : node .claude/hooks/test_index_plans.mjs
import fs from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"
import { analyse, barre } from "../mods/suivi-plan/hooks/parseur-plan.mjs"

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

export function bloc(dossierPlans) {
  const plans = lignes(dossierPlans)
  const r = [DEBUT, "",
    `${plans.length} plans : ` + ["actif", "en-pause", "clos"]
      .map(s => `${plans.filter(p => p.a.meta.statut === s).length} ${s}`).join(", ") + ".", "",
    "| Plan | Objectif principal | Statut | Avancement | Créé | Mis à jour |",
    "|---|---|---|---|---|---|"]
  for (const { nom, a } of plans) {
    const m = a.meta
    const avance = a.global == null ? "—" : `${barre(a.global)} ${a.global} % (${a.fait}/${a.total})`
    r.push(`| [${cellule(a.titre || nom)}](plans/${nom}) | ${cellule(m.objectif) || "_à renseigner (clé `objectif:`)_"} ` +
           `| ${cellule(m.statut) || "?"} | ${avance} | ${cellule(m.cree) || "—"} | ${cellule(m.maj) || "—"} |`)
  }
  r.push("", FIN)
  return r.join("\n")
}

const ENTETE = `# Suivi des plans de travail

Trace des plans de modification du fork (\`tasks/plans/\`, format \`tasks/plans/_FORMAT.md\`).
Avancement = moyenne des % des actions \`## A<n>\`, chaque action pesant autant (même calcul que la
vue « Suivi du plan » de VS Code). Le tableau se met à jour seul dès qu'un plan change (extension VS Code) ;
sans VS Code : \`node .claude/hooks/index_plans.mjs\`.

`

export function regenere(depot, verifier = false) {
  const fichier = path.join(depot, "tasks", "README.md")
  const ancien = fs.existsSync(fichier) ? fs.readFileSync(fichier, "utf8").replace(/\r\n/g, "\n") : ENTETE
  const nouveauBloc = bloc(path.join(depot, "tasks", "plans"))
  const i = ancien.indexOf(DEBUT), j = ancien.indexOf(FIN)
  const nouveau = i >= 0 && j > i
    ? ancien.slice(0, i) + nouveauBloc + ancien.slice(j + FIN.length)
    : ancien.replace(/\n*$/, "\n\n") + nouveauBloc + "\n"
  if (nouveau === ancien) return 0
  if (verifier) { console.error("tasks/README.md est en retard sur tasks/plans/ : node .claude/hooks/index_plans.mjs"); return 1 }
  fs.writeFileSync(fichier, nouveau, "utf8")
  return 0
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const depot = process.env.CLAUDE_PROJECT_DIR || path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..")
  process.exit(regenere(depot, process.argv.includes("--verifier")))
}
