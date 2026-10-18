// Extension VS Code « Suivi du plan » (fdaubercy.suivi-plan) - JS pur, sans dependance.
// Affiche dans une webview a droite de l'editeur l'avancement d'un plan tasks/plans/<chantier>.md
// (format : tasks/plans/_FORMAT.md), plus « Plan 74 % » dans la barre d'etat.
// Le calcul vient du parseur UNIQUE du mod Claude (.claude/mods/suivi-plan/hooks/parseur-plan.mjs),
// dont une copie est embarquee dans le .vsix par installe_suivi_plan.py.
'use strict'

const vscode = require('vscode')
const fs = require('fs')
const os = require('os')
const path = require('path')
const crypto = require('crypto')
const { pathToFileURL } = require('url')
const { rendu, page } = require('./rendu')

const CLE_CHOIX = 'suiviPlan.choisi'
const CLE_SIGNAL = 'suiviPlan.dernierSignal'
const AGE_MAX_SIGNAL = 5 * 60 * 1000   // un signal plus vieux au demarrage n'ouvre rien

const E = {
  ctx: null, racine: null, parseur: null, panel: null, barre: null,
  plans: [], affiche: null, ouvertureAutoFaite: false,
  veilleurs: [], minuterie: null, minuterieSignal: null,
}

const reglages = () => vscode.workspace.getConfiguration('suiviPlan')
const dossierRel = () => String(reglages().get('dossier') || 'tasks/plans').replace(/\\/g, '/').replace(/^\/+|\/+$/g, '')
const media = () => vscode.Uri.joinPath(E.ctx.extensionUri, 'media')

// Parseur : copie embarquee (.vsix), sinon celle du depot (mode developpement)
async function chargeParseur() {
  const candidats = [path.join(__dirname, 'parseur-plan.mjs')]
  if (E.racine) candidats.push(path.join(E.racine, '.claude', 'mods', 'suivi-plan', 'hooks', 'parseur-plan.mjs'))
  for (const c of candidats.filter(f => fs.existsSync(f))) {
    try { return await import(pathToFileURL(c).href) } catch (e) {
      // Repli si l'hote refuse import() : le parseur n'a ni import ni E/S, on le compile tel quel
      try {
        const src = fs.readFileSync(c, 'utf8').replace(/^export\s+/gm, '')
        return new Function(src + '\nreturn { analyse, prochaines, actionEnCours }')()
      } catch (e2) { console.error('suivi-plan : parseur illisible', c, e, e2) }
    }
  }
  return null
}

function racineDuTravail() {
  const dossiers = vscode.workspace.workspaceFolders || []
  const avecPlans = dossiers.find(d => fs.existsSync(path.join(d.uri.fsPath, dossierRel())))
  return (avecPlans || dossiers[0])?.uri.fsPath || null
}

// Chemin relatif valide -> chemin absolu, sinon null : sous <racine>/<dossier>/, .md, sans .., pas un _*.md
function valideChemin(rel) {
  if (!E.racine || typeof rel !== 'string' || !rel) return null
  const norm = rel.replace(/\\/g, '/')
  if (norm.split('/').includes('..') || !/\.md$/i.test(norm) || path.isAbsolute(norm) || /^[a-z]:/i.test(norm)) return null
  const base = path.resolve(E.racine, dossierRel())
  const abs = path.resolve(E.racine, norm)
  if (path.dirname(abs).toLowerCase() !== base.toLowerCase() || path.basename(abs).startsWith('_')) return null
  return abs
}

// Liste des plans : fichiers .md du dossier, sauf _*.md ; plus recent d'abord
function listePlans() {
  const base = path.join(E.racine, dossierRel())
  let noms = []
  try { noms = fs.readdirSync(base).filter(n => /\.md$/i.test(n) && !n.startsWith('_')) } catch { return [] }
  const plans = []
  for (const nom of noms) {
    const abs = path.join(base, nom)
    try {
      const a = E.parseur.analyse(fs.readFileSync(abs, 'utf8'))
      plans.push({ fichier: dossierRel() + '/' + nom, abs, mtime: fs.statSync(abs).mtimeMs, a })
    } catch (e) { console.error('suivi-plan : lecture impossible', abs, e) }
  }
  return plans.sort((x, y) => y.mtime - x.mtime)
}

// Plan affiche : choix memorise, sinon le plus recent des actifs, sinon le plus recent
function planCourant() {
  const choisi = E.ctx.workspaceState.get(CLE_CHOIX)
  return E.plans.find(p => p.fichier === choisi) ||
    E.plans.find(p => p.a.meta.statut === 'actif') || E.plans[0] || null
}

function nonce() { return crypto.randomBytes(16).toString('base64').replace(/[^A-Za-z0-9]/g, '') }

function contenu() {
  const p = planCourant()
  E.affiche = p
  return rendu(p ? p.a : null, p ? p.fichier : dossierRel(), E.plans)
}

function htmlComplet(panel) {
  const w = panel.webview
  return page(nonce(), w.cspSource, w.asWebviewUri(vscode.Uri.joinPath(media(), 'vue.css')).toString(),
    w.asWebviewUri(vscode.Uri.joinPath(media(), 'vue.js')).toString(), contenu())
}

function majBarre() {
  const p = planCourant()
  if (!p || !E.plans.some(x => x.a.meta.statut === 'actif')) { E.barre.hide(); return }
  const g = p.a.global == null ? '—' : p.a.global + ' %'
  const suite = E.parseur.prochaines(p.a, 1)[0]
  E.barre.text = `$(checklist) Plan ${g}`
  const info = `${p.a.titre || p.fichier}` + (suite ? ` — prochaine : ${suite.texte}` : ' — terminé')
  E.barre.tooltip = info.replace(/`/g, '').slice(0, 200)
  E.barre.show()
}

function majVue() {
  if (!E.panel) return
  const html = contenu()
  const p = E.affiche
  E.panel.title = p ? `Plan · ${p.a.meta.chantier || path.basename(p.fichier, '.md')}` : 'Plan'
  E.panel.webview.postMessage({ type: 'maj', html })
}

function rafraichit() {
  if (!E.racine || !E.parseur) return
  E.plans = listePlans()
  majBarre()
  majVue()
}

function brancheVue(panel) {
  E.panel = panel
  panel.webview.options = { enableScripts: true, localResourceRoots: [media()] }
  panel.webview.html = htmlComplet(panel)
  panel.onDidDispose(() => { if (E.panel === panel) E.panel = null })
  panel.webview.onDidReceiveMessage(m => recoitMessage(m))
}

// Ouvre (ou revele) la vue a droite ; @fichier : plan a afficher (deja valide), facultatif
function ouvreVue(fichier) {
  if (fichier) { E.ctx.workspaceState.update(CLE_CHOIX, fichier); rafraichit() }
  if (E.panel) { E.panel.reveal(vscode.ViewColumn.Beside, true); majVue(); return }
  brancheVue(vscode.window.createWebviewPanel('suiviPlan.vue', 'Plan',
    { viewColumn: vscode.ViewColumn.Beside, preserveFocus: true },
    { enableScripts: true, localResourceRoots: [media()], retainContextWhenHidden: false }))
  majVue()
}

async function recoitMessage(m) {
  if (!m || typeof m !== 'object') return
  if (m.type === 'pret') return majVue()           // la webview (re)chargee demande l'etat courant
  if (m.type === 'choisir') return choisirPlan()
  if (m.type === 'ouvrir' && E.affiche) {
    const ligne = Math.trunc(Number(m.ligne))
    if (!Number.isFinite(ligne) || ligne < 1) return
    await vscode.window.showTextDocument(vscode.Uri.file(E.affiche.abs), {
      viewColumn: vscode.ViewColumn.One, preview: false,
      selection: new vscode.Range(ligne - 1, 0, ligne - 1, 0),
    })
  }
}

async function choisirPlan() {
  rafraichit()
  if (!E.plans.length) return vscode.window.showInformationMessage(`Suivi du plan : aucun plan dans ${dossierRel()}.`)
  const auto = { label: '$(sync) Automatique', description: 'le plus récemment modifié des plans actifs', fichier: null }
  const items = [auto, ...E.plans.map(p => ({
    label: p.a.titre || path.basename(p.fichier),
    description: `${p.a.global == null ? '—' : p.a.global + ' %'} · ${p.a.meta.statut || '?'}`,
    detail: p.fichier, fichier: p.fichier,
  }))]
  const choix = await vscode.window.showQuickPick(items, { placeHolder: 'Plan à afficher' })
  if (!choix) return
  await E.ctx.workspaceState.update(CLE_CHOIX, choix.fichier || undefined)
  rafraichit()
  ouvreVue()
}

// Un plan cree ou modifie (anti-rebond 200 ms). Ouverture auto : une seule fois par fenetre.
function surModification() {
  clearTimeout(E.minuterie)
  E.minuterie = setTimeout(() => {
    rafraichit()
    if (!E.panel && reglages().get('ouvrirAuto') && !E.ouvertureAutoFaite && E.plans.length) {
      E.ouvertureAutoFaite = true
      ouvreVue()
    }
  }, 200)
}

function veillePlans() {
  for (const v of E.veilleurs.splice(0)) v.dispose()
  const v = vscode.workspace.createFileSystemWatcher(new vscode.RelativePattern(E.racine, dossierRel() + '/*.md'))
  v.onDidChange(surModification); v.onDidCreate(surModification); v.onDidDelete(surModification)
  E.veilleurs.push(v)
}

// --- Fichier signal du mod Claude : ~/.claude/suivi-plan/signal.json
//     { "racine": "<depot, />", "fichier": "tasks/plans/x.md", "horodatage": <ms> }
const normeRacine = r => String(r || '').replace(/\\/g, '/').replace(/\/+$/, '').toLowerCase()

function lisSignal(auDemarrage) {
  let s
  try { s = JSON.parse(fs.readFileSync(path.join(os.homedir(), '.claude', 'suivi-plan', 'signal.json'), 'utf8')) } catch { return }
  if (!s || normeRacine(s.racine) !== normeRacine(E.racine)) return
  const h = Number(s.horodatage)
  if (!Number.isFinite(h) || h <= (E.ctx.workspaceState.get(CLE_SIGNAL) || 0)) return
  E.ctx.workspaceState.update(CLE_SIGNAL, h)
  if (auDemarrage && Date.now() - h > AGE_MAX_SIGNAL) return
  if (!reglages().get('ouvrirAuto')) return
  const abs = valideChemin(s.fichier)
  if (!abs) return vscode.window.showWarningMessage(`Suivi du plan : signal ignoré, chemin refusé (${String(s.fichier).slice(0, 120)}).`)
  if (!fs.existsSync(abs)) return vscode.window.showWarningMessage(`Suivi du plan : plan introuvable (${s.fichier}).`)
  ouvreVue(s.fichier.replace(/\\/g, '/'))
}

function surSignal() {
  clearTimeout(E.minuterieSignal)
  E.minuterieSignal = setTimeout(() => lisSignal(false), 200)
}

// Veilleurs NON recursifs (aucun « / » dans le motif) : ~/.claude porte des milliers de fichiers
// de conversation ; on veille le dossier suivi-plan s'il existe, sinon sa creation dans ~/.claude.
function veilleSignal() {
  const claude = path.join(os.homedir(), '.claude')
  const dossier = path.join(claude, 'suivi-plan')
  if (fs.existsSync(dossier)) {
    const v = vscode.workspace.createFileSystemWatcher(new vscode.RelativePattern(vscode.Uri.file(dossier), 'signal.json'))
    v.onDidChange(surSignal); v.onDidCreate(surSignal)
    E.ctx.subscriptions.push(v)
  } else if (fs.existsSync(claude)) {
    const v = vscode.workspace.createFileSystemWatcher(new vscode.RelativePattern(vscode.Uri.file(claude), 'suivi-plan'))
    v.onDidCreate(() => { v.dispose(); veilleSignal(); surSignal() })
    E.ctx.subscriptions.push(v)
  }
}

async function activate(ctx) {
  E.ctx = ctx
  E.racine = racineDuTravail()
  const pret = chargeParseur().then(p => { E.parseur = p })

  // Enregistre AVANT tout await : VS Code peut restaurer la vue des l'activation
  ctx.subscriptions.push(vscode.window.registerWebviewPanelSerializer('suiviPlan.vue', {
    async deserializeWebviewPanel(panel) {
      await pret
      if (E.panel && E.panel !== panel) { panel.dispose(); return }
      if (E.parseur) E.plans = listePlans()
      brancheVue(panel)
      majVue()
    },
  }))
  ctx.subscriptions.push(vscode.window.registerUriHandler({
    handleUri(uri) {
      if (uri.path.replace(/\/+$/, '') !== '/ouvrir') return
      const rel = new URLSearchParams(uri.query).get('fichier')
      const abs = valideChemin(rel)
      if (!abs || !fs.existsSync(abs)) {
        return vscode.window.showWarningMessage(`Suivi du plan : lien ignoré, plan refusé ou introuvable (${String(rel).slice(0, 120)}).`)
      }
      pret.then(() => ouvreVue(rel.replace(/\\/g, '/')))
    },
  }))
  E.barre = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100)
  E.barre.command = 'suiviPlan.ouvrir'
  ctx.subscriptions.push(E.barre,
    vscode.commands.registerCommand('suiviPlan.ouvrir', () => pret.then(() => { rafraichit(); ouvreVue() })),
    vscode.commands.registerCommand('suiviPlan.choisir', () => pret.then(choisirPlan)),
    { dispose: () => { for (const v of E.veilleurs) v.dispose(); clearTimeout(E.minuterie); clearTimeout(E.minuterieSignal) } })

  await pret
  if (!E.parseur) {
    vscode.window.showErrorMessage('Suivi du plan : parseur-plan.mjs introuvable (ni dans l\'extension ni dans .claude/mods/suivi-plan/hooks/).')
    return
  }
  if (!E.racine) return
  veillePlans()
  veilleSignal()
  ctx.subscriptions.push(vscode.workspace.onDidChangeConfiguration(ev => {
    if (ev.affectsConfiguration('suiviPlan.dossier')) { veillePlans(); rafraichit() }
  }))
  rafraichit()
  lisSignal(true)
}

function deactivate() {}

module.exports = { activate, deactivate }
