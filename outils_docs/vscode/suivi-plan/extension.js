// Extension VS Code « Suivi du plan » (fdaubercy.suivi-plan) - JS pur, sans dependance.
// Affiche dans une webview a droite de l'editeur l'avancement d'un plan tasks/plans/<chantier>.md
// (format : tasks/plans/_FORMAT.md), plus « Plan 74 % » dans la barre d'etat.
// Le calcul vient du parseur UNIQUE du mod Claude (.claude/mods/suivi-plan/hooks/parseur-plan.mjs),
// dont une copie est embarquee dans le .vsix par installe_suivi_plan.py.
// Plan de la conversation : quand l'onglet actif est une conversation Claude, la vue montre le plan
// que cette conversation suit (rattachements ecrits par le mod, voir conversations.js), ou « aucun
// plan ». Un onglet d'un autre type ne change rien. Le choix manuel vaut jusqu'a la bascule suivante.
'use strict'

const vscode = require('vscode')
const fs = require('fs')
const os = require('os')
const path = require('path')
const crypto = require('crypto')
const { pathToFileURL } = require('url')
const { rendu, page } = require('./rendu')
const C = require('./conversations')

const CLE_CHOIX = 'suiviPlan.choisi'
const CLE_SIGNAL = 'suiviPlan.dernierSignal'
const AGE_MAX_SIGNAL = 5 * 60 * 1000   // un signal plus vieux au demarrage n'ouvre rien
const ECHANGE = path.join(os.homedir(), '.claude', 'suivi-plan')   // signal.json, conversations/
const PROJETS = path.join(os.homedir(), '.claude', 'projects')     // transcripts <session>.jsonl
const RECENTES = 30 * 24 * 3600 * 1000   // conversations non rattachees prises en compte (collisions)

const E = {
  ctx: null, racine: null, parseur: null, panel: null, barre: null, journal: null,
  plans: [], affiche: null, ouvertureAutoFaite: false,
  veilleurs: [], minuterie: null, minuterieSignal: null, minuterieOnglet: null,
  // Conversation active : null = pas de conversation reconnue (choix memorise / automatique),
  // sinon { session, fichier (null = aucun plan), message } ; dernierOnglet evite de refaire le travail
  conv: null, dernierOnglet: null, dernierLibelle: null,
  appris: new WeakMap(),    // onglet (objet Tab de l'API) -> session designee par un message envoye
  transcripts: new Map(),   // session -> chemin du .jsonl
  titres: new Map(),        // chemin du .jsonl -> { mtime, taille, titre }
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

// Plan affiche : celui de la conversation active (null = aucun), sinon choix memorise,
// sinon le plus recent des actifs, sinon le plus recent
function planCourant() {
  if (E.conv) return E.conv.fichier ? E.plans.find(p => p.fichier === E.conv.fichier) || null : null
  const choisi = E.ctx.workspaceState.get(CLE_CHOIX)
  return E.plans.find(p => p.fichier === choisi) ||
    E.plans.find(p => p.a.meta.statut === 'actif') || E.plans[0] || null
}

function nonce() { return crypto.randomBytes(16).toString('base64').replace(/[^A-Za-z0-9]/g, '') }

function contenu() {
  const p = planCourant()
  E.affiche = p
  if (!p && E.conv) {
    const message = E.conv.message ||
      (E.conv.fichier ? `Le plan suivi par cette conversation est introuvable (${E.conv.fichier}).` : '')
    return rendu(null, dossierRel(), E.plans, { conversation: { message } })
  }
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

// Ouvre (ou revele) la vue a droite ; @fichier : plan a afficher (deja valide), facultatif ;
// @conv : la conversation qui le demande (signal du mod), sinon c'est un choix manuel
function ouvreVue(fichier, conv) {
  if (conv) { E.conv = conv; rafraichit() } else if (fichier) {
    E.conv = null
    E.ctx.workspaceState.update(CLE_CHOIX, fichier)
    rafraichit()
  }
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
  E.conv = null                                    // choix manuel : vaut jusqu'a la bascule suivante
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
//     { "racine": "<depot, />", "fichier": "tasks/plans/x.md" | null, "horodatage": <ms>,
//       "session": "<id>", "ouvrir": true|false }
//     fichier null : la conversation ne suit aucun plan ; ouvrir false (message envoye) : la vue
//     suit la conversation si elle est ouverte, sans s'ouvrir ; session/ouvrir absents = ancien mod.
const normeRacine = r => String(r || '').replace(/\\/g, '/').replace(/\/+$/, '').toLowerCase()
const sessionValide = s => (typeof s === 'string' && /^[A-Za-z0-9-]{1,80}$/.test(s) ? s : null)

function lisSignal(auDemarrage) {
  let s
  try { s = JSON.parse(fs.readFileSync(path.join(ECHANGE, 'signal.json'), 'utf8')) } catch { return }
  if (!s || normeRacine(s.racine) !== normeRacine(E.racine)) return
  const h = Number(s.horodatage)
  if (!Number.isFinite(h) || h <= (E.ctx.workspaceState.get(CLE_SIGNAL) || 0)) return
  E.ctx.workspaceState.update(CLE_SIGNAL, h)
  if (auDemarrage && Date.now() - h > AGE_MAX_SIGNAL) return
  const session = sessionValide(s.session)
  const ouvrir = s.ouvrir !== false
  // Onglet actif = conversation Claude : le signal vient-il d'ELLE ? (sa session si elle est reconnue,
  // sinon le libelle que produirait le titre de la session du signal). Oui : la session est apprise a
  // cet onglet (leve une ambiguite de libelle). Non : un signal « message envoye » ou de detachement est
  // ignore - un message mis en file n'est soumis qu'a la fin du tour (constate le 2026-10-18 : 3,6 s
  // apres l'envoi, l'utilisateur etait deja sur un autre onglet). Autre onglet actif : le signal fait foi.
  const o = session ? resoutOnglet() : null
  if (o) {
    const vient = o.session ? o.session === session : C.libelleOnglet(titre(session)) === o.libelle
    if (vient && o.tab && o.etat !== 'apprise') {
      E.appris.set(o.tab, session)
      journal(`onglet « ${o.libelle} » : conversation ${session} apprise`)
    }
    if (!vient && (!ouvrir || s.fichier === null || s.fichier === undefined)) {
      journal(`signal ignoré : conversation ${session}, onglet actif « ${o.libelle} »${o.session ? ` (${o.session})` : ''}`)
      return
    }
  }
  if (s.fichier === null || s.fichier === undefined) {
    if (!session) return
    E.conv = { session, fichier: null }
    journal(`signal : conversation ${session} sans plan`)
    return rafraichit()
  }
  const abs = valideChemin(s.fichier)
  if (!abs) return vscode.window.showWarningMessage(`Suivi du plan : signal ignoré, chemin refusé (${String(s.fichier).slice(0, 120)}).`)
  const fichier = s.fichier.replace(/\\/g, '/')
  if (!ouvrir) {
    if (!session) return
    E.conv = { session, fichier }
    journal(`signal : conversation ${session} -> ${fichier}`)
    return rafraichit()
  }
  if (!reglages().get('ouvrirAuto')) return
  if (!fs.existsSync(abs)) return vscode.window.showWarningMessage(`Suivi du plan : plan introuvable (${s.fichier}).`)
  journal(`signal : ouverture de ${fichier}${session ? ` (conversation ${session})` : ''}`)
  ouvreVue(fichier, session ? { session, fichier } : undefined)
}

// --- Conversation de l'onglet actif

function journal(texte) { try { E.journal?.info(texte) } catch { /* journal ferme */ } }

// Libelle de l'onglet actif s'il est une conversation Claude, sinon null
function ongletClaudeActif() {
  const t = vscode.window.tabGroups.activeTabGroup?.activeTab
  const input = t?.input
  if (!(input instanceof vscode.TabInputWebview)) return null
  return String(input.viewType || '').endsWith(C.TYPE_ONGLET) ? t.label : null
}

// Transcript d'une session : ~/.claude/projects/<un projet>/<session>.jsonl (cache)
function transcript(session) {
  const connu = E.transcripts.get(session)
  if (connu && fs.existsSync(connu)) return connu
  let projets = []
  try { projets = fs.readdirSync(PROJETS) } catch { return null }
  for (const p of projets) {
    const f = path.join(PROJETS, p, session + '.jsonl')
    if (fs.existsSync(f)) { E.transcripts.set(session, f); return f }
  }
  return null
}

// Titre d'une session, lu comme l'extension Claude (64 Ko de tete et de fin), cache par mtime + taille
function titre(session) {
  const f = transcript(session)
  if (!f) return null
  let st
  try { st = fs.statSync(f) } catch { return null }
  const connu = E.titres.get(f)
  if (connu && connu.mtime === st.mtimeMs && connu.taille === st.size) return connu.titre
  let t = null
  let fd
  try {
    fd = fs.openSync(f, 'r')
    const b = Buffer.alloc(C.TAILLE_BLOC)
    const tete = b.toString('utf8', 0, fs.readSync(fd, b, 0, C.TAILLE_BLOC, 0))
    const fin = st.size > C.TAILLE_BLOC ? b.toString('utf8', 0, fs.readSync(fd, b, 0, C.TAILLE_BLOC, st.size - C.TAILLE_BLOC)) : tete
    t = C.titreSession(tete, fin)
  } catch (e) { journal(`transcript illisible ${f} : ${e.message}`) } finally { if (fd !== undefined) fs.closeSync(fd) }
  E.titres.set(f, { mtime: st.mtimeMs, taille: st.size, titre: t })
  return t
}

// Conversations rattachees a un plan de ce depot : [{ session, fichier, titre, horodatage }]
function rattachements() {
  const dossier = path.join(ECHANGE, 'conversations')
  let noms = []
  try { noms = fs.readdirSync(dossier).filter(n => /^[A-Za-z0-9-]{1,80}\.json$/.test(n)) } catch { return [] }
  const r = []
  for (const n of noms) {
    try {
      const c = JSON.parse(fs.readFileSync(path.join(dossier, n), 'utf8'))
      const session = sessionValide(c?.session)
      if (!session || normeRacine(c.racine) !== normeRacine(E.racine)) continue
      const fichier = typeof c.fichier === 'string' && valideChemin(c.fichier) ? c.fichier.replace(/\\/g, '/') : null
      r.push({ session, fichier, titre: titre(session), horodatage: Number(c.horodatage) || 0 })
    } catch { /* fichier en cours d'ecriture : relu a la bascule suivante */ }
  }
  return r
}

// Dossiers de transcripts de ce depot : ~/.claude/projects/<racine, non alphanumeriques -> '-'>
function dossiersProjet() {
  const nom = E.racine.replace(/[^A-Za-z0-9]/g, '-').toLowerCase()
  try { return fs.readdirSync(PROJETS).filter(d => d.toLowerCase() === nom).map(d => path.join(PROJETS, d)) } catch { return [] }
}

// Conversations recentes de ce depot qui ne suivent aucun plan : sans elles, une conversation non
// rattachee dont le libelle d'onglet egale celui d'une rattachee afficherait le plan de l'autre.
function nonRattachees(connues) {
  const r = []
  const limite = Date.now() - RECENTES
  for (const d of dossiersProjet()) {
    let noms = []
    try { noms = fs.readdirSync(d).filter(n => /^[A-Za-z0-9-]{1,80}\.jsonl$/.test(n)) } catch { continue }
    for (const n of noms) {
      const session = n.slice(0, -'.jsonl'.length)
      if (connues.has(session)) continue
      let st
      try { st = fs.statSync(path.join(d, n)) } catch { continue }
      if (st.mtimeMs < limite) continue
      E.transcripts.set(session, path.join(d, n))
      r.push({ session, fichier: null, titre: titre(session), horodatage: st.mtimeMs })
    }
  }
  return r
}

function candidates() {
  const r = rattachements()
  return r.concat(nonRattachees(new Set(r.map(c => c.session))))
}

// Conversation de l'onglet actif, ou null s'il n'est pas une conversation Claude :
// { tab, libelle, etat, session, fichier }, etat = 'apprise' (un message envoye depuis CET onglet l'a
// designee), 'trouvee' (seule conversation a ce libelle, ou toutes au meme plan), 'ambigue', 'inconnue'.
function resoutOnglet() {
  const libelle = ongletClaudeActif()
  if (libelle === null) return null
  const tab = vscode.window.tabGroups.activeTabGroup?.activeTab
  const toutes = candidates()
  const apprise = tab && E.appris.get(tab)
  const c = apprise && toutes.find(x => x.session === apprise && C.libelleOnglet(x.titre) === libelle)
  if (c) return { tab, libelle, etat: 'apprise', session: c.session, fichier: c.fichier }
  const r = C.apparie(libelle, toutes)
  return r.etat === 'trouvee'
    ? { tab, libelle, etat: r.etat, session: r.conversation.session, fichier: r.conversation.fichier }
    : { tab, libelle, etat: r.etat, session: null, fichier: null }
}

// L'onglet actif a change : si c'est une conversation Claude, la vue montre son plan.
// @force : relire meme si l'onglet n'a pas change (rattachement modifie)
function surOnglet(force) {
  const libelle = ongletClaudeActif()
  if (libelle === null) { E.dernierOnglet = null; return }   // fichier, vue du plan... : rien ne change
  const tab = vscode.window.tabGroups.activeTabGroup?.activeTab
  if (!force && tab === E.dernierOnglet && libelle === E.dernierLibelle) return
  E.dernierOnglet = tab
  E.dernierLibelle = libelle
  const o = resoutOnglet()
  if (o.session) {
    E.conv = { session: o.session, fichier: o.fichier }
  } else {
    const message = o.etat === 'ambigue'
      ? `Plusieurs conversations portent le titre « ${libelle} » sans suivre le même plan : envoyez un message dans celle-ci pour que la vue la reconnaisse.`
      : ''
    E.conv = { session: null, fichier: null, message }
  }
  journal(`onglet « ${libelle} » -> ${o.etat}` + (o.session ? ` ${o.session} : ${o.fichier ?? 'aucun plan'}` : ''))
  rafraichit()
}

function planifieOnglet(force) {
  clearTimeout(E.minuterieOnglet)
  E.minuterieOnglet = setTimeout(() => surOnglet(force), 150)
}

function veilleOnglets() {
  E.ctx.subscriptions.push(
    vscode.window.tabGroups.onDidChangeTabs(() => planifieOnglet(false)),     // bascule ou titre renomme
    vscode.window.tabGroups.onDidChangeTabGroups(() => planifieOnglet(false)))
  // Rattachement ecrit par le mod (ExitPlanMode, /suivi suivre, detacher) : relire l'onglet actif
  const dossier = path.join(ECHANGE, 'conversations')
  if (fs.existsSync(dossier)) {
    const v = vscode.workspace.createFileSystemWatcher(new vscode.RelativePattern(vscode.Uri.file(dossier), '*.json'))
    const relit = () => { E.dernierOnglet = null; planifieOnglet(true) }
    v.onDidChange(relit); v.onDidCreate(relit)
    E.ctx.subscriptions.push(v)
  }
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
    { dispose: () => {
      for (const v of E.veilleurs) v.dispose()
      clearTimeout(E.minuterie); clearTimeout(E.minuterieSignal); clearTimeout(E.minuterieOnglet)
    } })
  E.journal = vscode.window.createOutputChannel('Suivi du plan', { log: true })
  ctx.subscriptions.push(E.journal)

  await pret
  if (!E.parseur) {
    vscode.window.showErrorMessage('Suivi du plan : parseur-plan.mjs introuvable (ni dans l\'extension ni dans .claude/mods/suivi-plan/hooks/).')
    return
  }
  if (!E.racine) return
  veillePlans()
  veilleSignal()
  veilleOnglets()
  ctx.subscriptions.push(vscode.workspace.onDidChangeConfiguration(ev => {
    if (ev.affectsConfiguration('suiviPlan.dossier')) { veillePlans(); rafraichit() }
  }))
  rafraichit()
  lisSignal(true)
  surOnglet(true)
  journal(`actif : ${E.racine}, ${E.plans.length} plan(s)`)
}

function deactivate() {}

module.exports = { activate, deactivate }
