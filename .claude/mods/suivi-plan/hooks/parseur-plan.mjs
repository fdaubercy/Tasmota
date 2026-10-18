// Parseur des plans suivis (tasks/plans/<chantier>.md) - format : tasks/plans/_FORMAT.md
// Source UNIQUE, partagee par le mod suivi-plan (ce dossier) et l'extension VS Code
// fdaubercy.suivi-plan (outils_docs/vscode/suivi-plan/, qui en embarque une copie).
// ESM pur, sans entree/sortie ni import : il recoit du texte et rend des valeurs.
// Banc : node .claude/mods/suivi-plan/tests/test_parseur.mjs (les lignes marquees MUTANT
// sont remplacees par le banc pour verifier qu'il detecte une regression).

const RE_ACTION = /^##\s+A(\d+)\s*[—–\-.:]\s*(.*?)\s*$/
const RE_TITRE2 = /^##\s+(.*?)\s*$/
const RE_TITRE1 = /^#\s+(.*?)\s*$/
const RE_ETAPE = /^(\s*)[-*+]\s+\[( |x|X)\]\s+(.*?)\s*$/
const RE_CLOTURE = /^\s*(```|~~~)/
const RE_PREUVE = /\s+[—–-]\s+preuve\s*:\s*(.*)$/i
const RE_PORTEE = /^\[(conversation|projet)\]\s*/i
const RE_AMELIORATIONS = /^am[ée]liorations\s+restantes/i

// En-tete YAML simple (cle: valeur, commentaire # apres un blanc). Rend [meta, lignesConsommees].
function lisMeta(lignes) {
  const meta = {}
  if (lignes[0] !== "---") return [meta, 0]
  for (let i = 1; i < lignes.length; i++) {
    if (lignes[i] === "---") return [meta, i + 1]
    const m = /^([A-Za-z_][\w-]*)\s*:\s*(.*)$/.exec(lignes[i])
    if (m) meta[m[1]] = m[2].replace(/\s+#.*$/, "").trim()
  }
  return [{}, 0]                                    // en-tete jamais ferme : pas d'en-tete
}

function decoupePreuve(texte) {
  const m = RE_PREUVE.exec(texte)
  return m ? [texte.slice(0, m.index).trim(), m[1].trim()] : [texte.trim(), ""]
}

// Analyse un plan. Lignes numerotees a partir de 1, en-tete compris.
export function analyse(texte) {
  const t = String(texte ?? "").replace(/\r\n?/g, "\n")     // MUTANT:crlf
  const lignes = t.split("\n")
  const [meta, debut] = lisMeta(lignes)
  const actions = []
  const ameliorations = []
  const alertes = []
  let titre = meta.titre || ""
  let section = null                                // "action" | "ameliorations" | "autre"
  let enCode = false

  for (let i = debut; i < lignes.length; i++) {
    const l = lignes[i]
    const ligne = i + 1
    if (RE_CLOTURE.test(l)) { enCode = !enCode; continue }   // MUTANT:bloc-code
    if (enCode) continue

    let m = RE_ACTION.exec(l)
    if (m) {
      const id = "A" + m[1]
      if (actions.some(a => a.id === id)) alertes.push(`${id} en double (ligne ${ligne})`)
      actions.push({ id, titre: m[2], ligne, etapes: [], fait: 0, total: 0, pourcent: 0 })
      section = "action"
      continue
    }
    m = RE_TITRE2.exec(l)
    if (m) { section = RE_AMELIORATIONS.test(m[1]) ? "ameliorations" : "autre"; continue }
    m = RE_TITRE1.exec(l)
    if (m) { if (!titre) titre = m[1]; section = "autre"; continue }

    m = RE_ETAPE.exec(l)
    if (!m) continue
    const fait = m[2] !== " "
    if (section === "action") {
      const [txt, preuve] = decoupePreuve(m[3])
      actions[actions.length - 1].etapes.push({ texte: txt, fait, preuve, ligne, niveau: m[1].length })
    } else if (section === "ameliorations") {
      const p = RE_PORTEE.exec(m[3])
      ameliorations.push({ portee: p ? p[1].toLowerCase() : "projet", texte: m[3].replace(RE_PORTEE, "").trim(), fait, ligne })
    }
  }

  let totFait = 0
  let totTotal = 0
  let somme = 0
  for (const a of actions) {
    a.total = a.etapes.length
    a.fait = a.etapes.filter(e => e.fait).length
    a.pourcent = a.total ? Math.round(a.fait * 100 / a.total) : 0
    if (!a.total) alertes.push(`${a.id} sans sous-étape`)
    totFait += a.fait
    totTotal += a.total
    somme += a.total ? a.fait / a.total : 0
  }
  const n = actions.length
  const global = n ? Math.round(somme * 100 / n) : null      // MUTANT:moyenne
  if (!n) alertes.push("aucune action au format « ## A1 — titre »")
  return { meta, titre, actions, ameliorations, global, fait: totFait, total: totTotal, alertes }
}

// Les n prochaines etapes non faites, dans l'ordre du plan
export function prochaines(a, n = 3) {
  const r = []
  for (const act of a.actions) for (const e of act.etapes) {
    if (!e.fait && r.length < n) r.push({ action: act.id, texte: e.texte, ligne: e.ligne })
  }
  return r
}

// Barre de progression en caracteres pleins/vides ; p null -> vide
export function barre(p, cases = 10) {
  const pleines = p == null ? 0 : Math.max(0, Math.min(cases, Math.round(p * cases / 100)))
  return "█".repeat(pleines) + "░".repeat(cases - pleines)
}

function court(texte, max) {
  const s = String(texte).replace(/`/g, "")
  return s.length > max ? s.slice(0, max - 1) + "…" : s
}

// Action en cours : la premiere qui n'est pas a 100 %
export function actionEnCours(a) {
  return a.actions.find(x => x.total === 0 || x.fait < x.total) || null
}

// Ligne d'avancement d'une ligne (~100 caracteres)
export function ligneStatut(a, chantier) {
  const nom = chantier || a.meta.chantier || slug(a.titre)
  if (a.global == null) return `Plan ${nom} : aucune action`
  const enCours = actionEnCours(a)
  if (!enCours) return `Plan ${nom} ${barre(100)} 100 % · terminé`
  const suite = prochaines(a, 1)[0]
  return court(`Plan ${nom} ${barre(a.global)} ${a.global} % · ${enCours.id} ${enCours.fait}/${enCours.total}` +
               (suite ? ` · prochaine : ${suite.texte}` : ""), 110)
}

// Resume texte (25 lignes au plus) : pour la commande /suivi et le contexte des conversations
export function resume(a, fichier) {
  const r = [`Plan « ${a.titre || "sans titre"} » (${fichier}) : ${a.global == null ? "—" : a.global + " %"}, ` +
             `${a.fait}/${a.total} étapes, statut ${a.meta.statut || "?"}`]
  if (a.actions.length) r.push(a.actions.map(x => `${x.id} ${x.pourcent} %` + (x.total ? ` (${x.fait}/${x.total})` : "")).join(" · "))
  const suite = prochaines(a, 3)
  if (suite.length) {
    r.push("Prochaines étapes :")
    for (const s of suite) r.push(`- ${s.action} ligne ${s.ligne} : ${court(s.texte, 120)}`)
  }
  const restant = a.ameliorations.filter(x => !x.fait)
  if (restant.length) {
    const conv = restant.filter(x => x.portee === "conversation").length
    r.push(`Améliorations restantes : ${conv} [conversation], ${restant.length - conv} [projet]`)
  }
  for (const al of a.alertes.slice(0, 3)) r.push(`Alerte : ${al}`)
  return r.slice(0, 25).join("\n")
}

// Nom de fichier tire d'un titre : minuscules, sans accents, tirets
export function slug(titre) {
  const s = String(titre ?? "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase()
    .replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 50).replace(/-+$/, "")
  return s || "plan"
}

const ORDRE_META = ["chantier", "titre", "statut", "cree", "maj", "source", "reprise"]

function ecrisMeta(meta) {
  const cles = [...ORDRE_META.filter(c => meta[c] != null && meta[c] !== ""),
                ...Object.keys(meta).filter(c => !ORDRE_META.includes(c))]
  return ["---", ...cles.map(c => `${c}: ${meta[c]}`), "---"].join("\n")
}

// Plan brut (sortie du mode plan) -> plan suivi : en-tete complete, statut actif, LF.
// @options : {source, date, chantier}
export function enPlanSuivi(brut, options = {}) {
  const t = String(brut ?? "").replace(/\r\n?/g, "\n")
  const lignes = t.split("\n")
  const [meta, debut] = lisMeta(lignes)
  const corps = lignes.slice(debut).join("\n").replace(/^\n+/, "")
  const a = analyse(t)
  const date = options.date || ""
  meta.chantier = meta.chantier || options.chantier || slug(a.titre)
  if (!meta.titre && a.titre) meta.titre = a.titre
  meta.statut = meta.statut || "actif"
  meta.cree = meta.cree || date
  if (date) meta.maj = date
  if (options.source) meta.source = options.source
  return ecrisMeta(meta) + "\n" + corps.replace(/\n*$/, "\n")
}

const cleEtape = texte => decoupePreuve(texte)[0].replace(/\s+/g, " ").toLowerCase()

// Plan revalide : reporte dans 'nouveau' les coches (et preuves) des etapes de meme texte
// cochees dans 'ancien', et garde la date de creation de l'ancien.
export function fusionneCoches(ancien, nouveau) {
  const a = analyse(ancien)
  const faites = new Map()
  for (const act of a.actions) for (const e of act.etapes) {
    if (e.fait) faites.set(cleEtape(e.texte), e.preuve)
  }
  const lignes = String(nouveau ?? "").replace(/\r\n?/g, "\n").split("\n")
  let enCode = false
  const sortie = lignes.map(l => {
    if (RE_CLOTURE.test(l)) { enCode = !enCode; return l }
    const m = enCode ? null : RE_ETAPE.exec(l)
    if (!m || m[2] !== " " || !faites.has(cleEtape(m[3]))) return l
    const preuve = faites.get(cleEtape(m[3]))
    const [txt, preuveNouvelle] = decoupePreuve(m[3])
    const p = preuveNouvelle || preuve
    return `${m[1]}- [x] ${txt}${p ? " — preuve : " + p : ""}`
  }).join("\n")
  if (a.meta.cree) return sortie.replace(/^(---\n(?:.*\n)*?)cree:.*$/m, `$1cree: ${a.meta.cree}`)
  return sortie
}
