// Banc des caches de extension.js (lenteurs du 2026-11-13 : chaque bascule d'onglet Claude relisait tous les
// plans et toutes les conversations, l'hote d'extensions se figeait).
//   node outils_docs/vscode/suivi-plan/test_cache.js [dossier de extension.js]     code de sortie 0 = vert
// Charge la VRAIE extension.js avec un faux module vscode, dans un faux depot et un faux ~/.claude
// (dossiers temporaires), et compte les lectures de fichiers. Verifie :
//   1. une 2e bascule vers un onglet deja vu ne relit ni plan ni conversation ;
//   2. un onglet au libelle inconnu fait relire les conversations (conversation neuve) ;
//   3. un plan modifie (veilleur) est relu, et son nouveau % est affiche ;
//   4. un rattachement modifie (veilleur) fait relire les conversations.
// TEMOIN : lance sur l'ancienne extension.js (argument), le controle 1 doit echouer.
'use strict'
const fs = require('fs')
const os = require('os')
const path = require('path')
const Module = require('module')

const EXT = path.resolve(process.argv[2] || __dirname)
const DEPOT = path.resolve(__dirname, '..', '..', '..')
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'banc-suivi-plan-'))
const racine = path.join(tmp, 'depot')
process.env.USERPROFILE = process.env.HOME = path.join(tmp, 'home')   // lu par os.homedir() au chargement
const claude = path.join(process.env.USERPROFILE, '.claude')

// Faux depot : 2 plans + la copie du parseur ; faux ~/.claude : 1 rattachement et son transcript
const plan = (n, coche) => `---\nchantier: ${n}\ntitre: Plan ${n}\nstatut: actif\n---\n# Plan ${n}\n\n## A1 — Faire\n- [${coche}] etape\n- [ ] autre\n`
fs.mkdirSync(path.join(racine, 'tasks', 'plans'), { recursive: true })
fs.writeFileSync(path.join(racine, 'tasks', 'plans', 'alpha.md'), plan('alpha', ' '))
fs.writeFileSync(path.join(racine, 'tasks', 'plans', 'beta.md'), plan('beta', ' '))
const hooks = path.join(racine, '.claude', 'mods', 'suivi-plan', 'hooks')
fs.mkdirSync(hooks, { recursive: true })
fs.copyFileSync(path.join(DEPOT, '.claude', 'mods', 'suivi-plan', 'hooks', 'parseur-plan.mjs'), path.join(hooks, 'parseur-plan.mjs'))
const SESSION = '11111111-2222-3333-4444-555555555555'
fs.mkdirSync(path.join(claude, 'suivi-plan', 'conversations'), { recursive: true })
const rattache = fichier => fs.writeFileSync(path.join(claude, 'suivi-plan', 'conversations', SESSION + '.json'),
  JSON.stringify({ session: SESSION, racine, fichier, horodatage: Date.now() }))
rattache('tasks/plans/alpha.md')
const projet = path.join(claude, 'projects', racine.replace(/[^A-Za-z0-9]/g, '-'))
fs.mkdirSync(projet, { recursive: true })
fs.writeFileSync(path.join(projet, SESSION + '.jsonl'), '{"type":"ai-title","aiTitle":"Essai alpha"}\n')

// Compteurs de lectures (extension.js appelle fs.readFileSync / fs.openSync a chaque fois)
const lu = { plans: 0, conversations: 0 }
const lit = fs.readFileSync, ouvre = fs.openSync
fs.readFileSync = function (f, ...a) {
  const p = String(f)
  if (p.includes(path.join('tasks', 'plans'))) lu.plans++
  if (p.includes(path.join('suivi-plan', 'conversations'))) lu.conversations++
  return lit.call(this, f, ...a)
}
fs.openSync = function (f, ...a) { if (String(f).endsWith('.jsonl')) lu.conversations++; return ouvre.call(this, f, ...a) }

// Faux vscode : ce que activate() et les veilleurs utilisent
class TabInputWebview { constructor(viewType) { this.viewType = viewType } }
let onglet = null
const tabs = [], veilleurs = []
const barre = { text: '', show() {}, hide() {}, dispose() {} }
const rien = () => ({ dispose() {} })
const vscode = {
  workspace: {
    workspaceFolders: [{ uri: { fsPath: racine } }],
    getConfiguration: () => ({ get: k => (k === 'dossier' ? 'tasks/plans' : false) }),
    createFileSystemWatcher: motif => {
      const v = { motif, dispose() {} }
      for (const e of ['onDidChange', 'onDidCreate', 'onDidDelete']) v[e] = f => { v[e + 'F'] = f }
      veilleurs.push(v); return v
    },
    onDidChangeConfiguration: rien,
  },
  RelativePattern: class { constructor(base, motif) { this.base = base; this.pattern = motif } },
  Uri: { file: p => ({ fsPath: p }), joinPath: (u, ...s) => ({ fsPath: path.join(u.fsPath, ...s) }) },
  window: {
    registerWebviewPanelSerializer: rien, registerUriHandler: rien,
    createStatusBarItem: () => barre, createOutputChannel: () => ({ info() {}, dispose() {} }),
    tabGroups: { get activeTabGroup() { return { activeTab: onglet } }, onDidChangeTabs: f => { tabs.push(f); return rien() }, onDidChangeTabGroups: rien },
    showWarningMessage() {}, showErrorMessage() {}, showInformationMessage() {},
  },
  commands: { registerCommand: rien },
  StatusBarAlignment: { Left: 1 }, ViewColumn: { Beside: 2, One: 1 }, TabInputWebview,
}
const charge = Module._load
Module._load = function (demande, ...a) { return demande === 'vscode' ? vscode : charge.call(this, demande, ...a) }

let nbEchecs = 0
function verifie(nom, ok, info) { if (!ok) nbEchecs++; console.log(`${ok ? 'OK    ' : 'ECHEC '} ${nom}${ok ? '' : '  -> ' + info}`) }
const attend = ms => new Promise(r => setTimeout(r, ms))
const ongletClaude = libelle => ({ label: libelle, input: new TabInputWebview('mainThreadWebview-claudeVSCodePanel') })
async function bascule(o) { onglet = o; tabs.forEach(f => f()); await attend(250) }   // anti-rebond de 150 ms
const zero = () => { lu.plans = 0; lu.conversations = 0 }

;(async () => {
  const ext = require(path.join(EXT, 'extension.js'))
  await ext.activate({ subscriptions: [], extensionUri: { fsPath: EXT }, workspaceState: { get() {}, update() {} } })
  const fichier = { label: 'x.md', input: {} }                     // onglet qui n'est pas une conversation
  await bascule(ongletClaude('Essai alpha'))
  verifie('1re bascule : la conversation est reconnue', barre.text.includes('0 %'), `barre « ${barre.text} »`)

  await bascule(fichier); zero()
  await bascule(ongletClaude('Essai alpha'))                        // objet Tab neuf, meme conversation
  verifie('1. 2e bascule : aucun plan relu', lu.plans === 0, `${lu.plans} lecture(s) de plan`)
  verifie('1. 2e bascule : aucune conversation relue', lu.conversations === 0, `${lu.conversations} lecture(s)`)

  zero(); await bascule(ongletClaude('Conversation toute neuve'))
  verifie('2. libelle inconnu : conversations relues', lu.conversations > 0, 'aucune relecture')

  await bascule(ongletClaude('Essai alpha'))
  fs.writeFileSync(path.join(racine, 'tasks', 'plans', 'alpha.md'), plan('alpha', 'x'))
  zero(); veilleurs.find(v => v.motif.pattern === 'tasks/plans/*.md').onDidChangeF(); await attend(300)
  verifie('3. plan modifie : relu', lu.plans > 0, 'aucune relecture')
  verifie('3. plan modifie : nouveau % affiche', barre.text.includes('50 %'), `barre « ${barre.text} »`)

  rattache('tasks/plans/beta.md'); await bascule(fichier); zero()
  veilleurs.find(v => v.motif.pattern === '*.json').onDidChangeF(); await bascule(ongletClaude('Essai alpha'))
  verifie('4. rattachement modifie : conversations relues', lu.conversations > 0, 'aucune relecture')

  fs.rmSync(tmp, { recursive: true, force: true })
  console.log(nbEchecs ? `\n${nbEchecs} ECHEC(S)` : '\nVERT')
  process.exit(nbEchecs ? 1 : 0)
})().catch(e => { console.error(e); process.exit(2) })
