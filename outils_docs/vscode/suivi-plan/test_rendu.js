// Banc du rendu de la vue « Suivi du plan » : node outils_docs/vscode/suivi-plan/test_rendu.js
// Code de sortie 0 = vert. Charge le VRAI parseur (copie embarquee ./parseur-plan.mjs si presente,
// sinon .claude/mods/suivi-plan/hooks/parseur-plan.mjs du depot) et rendu.js, puis verifie :
//   1. echappement de tout texte du .md (titre, action, etape, preuve, amelioration, alerte) ;
//   2. CSP stricte et nonce dans page() ;
//   3. data-ligne = numeros de ligne du parseur ; % affiches = % du parseur ;
//   4. memes controles sur le vrai tasks/plans/suivi-plan.md ;
//   5. TEMOIN : une copie de rendu.js dont la ligne MUTANT:echappe est neutralisee, chargee a part,
//      doit faire echouer le controle d'echappement (et la copie intacte, meme montage, le passer).
'use strict'
const fs = require('fs')
const path = require('path')
const Module = require('module')
const { pathToFileURL } = require('url')

const ICI = __dirname
const RACINE = path.resolve(ICI, '..', '..', '..')
const XSS = '<script>alert(1)</script>'

let nbOk = 0
let nbEchecs = 0
function verifie(nom, ok, info) {
  if (ok) nbOk++
  else nbEchecs++
  console.log(`${ok ? 'OK    ' : 'ECHEC '} ${nom}${ok || !info ? '' : '  -> ' + info}`)
}

// Charge une source CommonJS sous un nom de fichier donne, sans l'ecrire sur disque
function chargeSource(source, nomFichier) {
  const m = new Module(nomFichier, module)
  m.filename = nomFichier
  m.paths = Module._nodeModulePaths(path.dirname(nomFichier))
  m._compile(source, nomFichier)
  return m.exports
}

const PLAN_ESSAI = [
  '---',
  'chantier: essai',
  `titre: Titre ${XSS} & "guillemets" 'apostrophes'`,
  'statut: actif',
  'maj: 2026-10-18',
  '---',
  '# Ignoré car titre dans l\'en-tête',
  '',
  `## A1 — Action ${XSS}`,
  `- [x] Étape ${XSS} — preuve : ${XSS} \`code\``,
  '- [ ] Étape simple',
  '  - [x] Imbriquée',
  '',
  '## A2 — Seconde',
  '- [ ] a',
  '- [ ] b',
  '- [x] c',
  '',
  '## A1 — Doublon (alerte)',
  '',
  '## Améliorations restantes',
  `- [ ] [conversation] Amélioration ${XSS}`,
  '- [x] [projet] Faite',
  '- [ ] Sans étiquette',
].join('\n')

// Controles d'echappement : rend la liste des fuites trouvees (vide = vert)
function fuites(R, a) {
  const html = R.rendu(a, `tasks/plans/${XSS}.md`, [{}, {}])
  const r = []
  if (html.includes(XSS)) r.push('balise <script> brute')
  if (/<script/i.test(html)) r.push('<script quelconque dans le fragment')
  if (html.includes('"guillemets"') || html.includes("'apostrophes'")) r.push('guillemets non echappes')
  if (!html.includes('&lt;script&gt;alert(1)&lt;/script&gt;')) r.push('forme echappee absente')
  if (!html.includes('&quot;guillemets&quot;') || !html.includes('&#39;apostrophes&#39;')) r.push('entites " et \' absentes')
  if (/&(?!amp;|lt;|gt;|quot;|#39;|#974[45];)/.test(html)) r.push('& non echappe')
  return r
}

function attributs(html, type, attr) {
  const re = new RegExp(`data-type="${type}"[^>]*?${attr}="(\\d+)"`, 'g')
  return [...html.matchAll(re)].map(m => Number(m[1]))
}

function controleLignesEtPourcents(nom, R, a) {
  const html = R.rendu(a, 'tasks/plans/x.md', [])
  verifie(`${nom} : data-ligne des actions = parseur`,
    JSON.stringify(attributs(html, 'action', 'data-ligne')) === JSON.stringify(a.actions.map(x => x.ligne)),
    `${attributs(html, 'action', 'data-ligne')} vs ${a.actions.map(x => x.ligne)}`)
  const lignesEtapes = a.actions.flatMap(x => x.etapes.map(e => e.ligne))
  verifie(`${nom} : data-ligne des étapes = parseur (${lignesEtapes.length})`,
    JSON.stringify(attributs(html, 'etape', 'data-ligne')) === JSON.stringify(lignesEtapes))
  const lignesAm = a.ameliorations.filter(x => x.portee === 'conversation').concat(a.ameliorations.filter(x => x.portee !== 'conversation')).map(x => x.ligne)
  verifie(`${nom} : data-ligne des améliorations = parseur (${lignesAm.length})`,
    JSON.stringify(attributs(html, 'amelioration', 'data-ligne')) === JSON.stringify(lignesAm))
  const largeurs = [...html.matchAll(/class="remplissage" data-pourcent="(\d+)"/g)].map(m => Number(m[1]))
  const attendu = [a.global ?? 0, ...a.actions.map(x => x.pourcent)]
  verifie(`${nom} : largeurs des barres = % du parseur`, JSON.stringify(largeurs) === JSON.stringify(attendu), `${largeurs} vs ${attendu}`)
  const textes = [...html.matchAll(/data-type="pourcent-action">(\d+) %</g)].map(m => Number(m[1]))
  verifie(`${nom} : % affichés par action = parseur`, JSON.stringify(textes) === JSON.stringify(a.actions.map(x => x.pourcent)))
  const g = /data-type="pourcent-global">([^<]*)</.exec(html)
  verifie(`${nom} : % global affiché = parseur (${a.global})`, g && g[1] === (a.global == null ? '—' : `${a.global} %`), g && g[1])
  verifie(`${nom} : « ${a.fait}/${a.total} étapes » affiché`, html.includes(`${a.fait}/${a.total} étapes`))
}

async function principal() {
  const embarque = path.join(ICI, 'parseur-plan.mjs')
  const cheminParseur = fs.existsSync(embarque) ? embarque
    : path.join(RACINE, '.claude', 'mods', 'suivi-plan', 'hooks', 'parseur-plan.mjs')
  console.log(`Parseur : ${cheminParseur}`)
  const P = await import(pathToFileURL(cheminParseur).href)
  const R = require('./rendu')
  const a = P.analyse(PLAN_ESSAI)

  // 1. Echappement
  const f = fuites(R, a)
  verifie('échappement : aucune fuite sur le plan d\'essai', f.length === 0, f.join(', '))
  verifie('échappement : alerte du parseur présente (A1 en double)', R.rendu(a, 'x.md', []).includes('A1 en double'))
  verifie('`code` rendu en <code>', R.rendu(a, 'x.md', []).includes('<code>code</code>'))
  verifie('bouton « Choisir le plan » si plusieurs plans', R.rendu(a, 'x.md', [{}, {}]).includes('data-action="choisir"'))
  verifie('pas de bouton avec un seul plan', !R.rendu(a, 'x.md', [{}]).includes('data-action="choisir"'))
  verifie('aucun attribut style (CSP)', !/\sstyle=/.test(R.rendu(a, 'x.md', [{}, {}])))

  // 2. Page complete
  const doc = R.page('NONCE123', 'https://cdn.exemple', 'https://cdn.exemple/vue.css', 'https://cdn.exemple/vue.js', '<p>x</p>')
  const csp = /http-equiv="Content-Security-Policy" content="([^"]*)"/.exec(doc)
  const cspTexte = csp ? csp[1].replace(/&#39;/g, "'").replace(/&amp;/g, '&') : ''
  verifie('page : CSP présente', !!csp)
  verifie("page : CSP default-src 'none'", cspTexte.includes("default-src 'none';"))
  verifie('page : CSP script-src par nonce', cspTexte.includes("script-src 'nonce-NONCE123';"))
  verifie('page : CSP style-src = cspSource', cspTexte.includes('style-src https://cdn.exemple;'))
  verifie('page : script porteur du nonce', doc.includes('<script nonce="NONCE123" src="https://cdn.exemple/vue.js">'))
  verifie('page : un seul <script>', (doc.match(/<script/g) || []).length === 1)

  // 3. Lignes et pourcentages
  controleLignesEtPourcents('essai', R, a)
  const vide = P.analyse('# Rien\n')
  verifie('plan sans action : % global « — »', R.rendu(vide, 'x.md', []).includes('data-type="pourcent-global">—<'))
  verifie('aucun plan : message', R.rendu(null, 'tasks/plans', []).includes('Aucun plan'))
  const sans = R.rendu(null, 'tasks/plans', [{}], { conversation: { message: `Rien ${XSS}` } })
  verifie('conversation sans plan : message échappé et consigne /suivi suivre',
    sans.includes('Rien &lt;script&gt;') && !sans.includes(XSS) && sans.includes('/suivi suivre &lt;chantier&gt;'))
  verifie('conversation sans plan : bouton « Choisir le plan » dès un plan', sans.includes('data-action="choisir"'))
  verifie('conversation sans plan, aucun plan au dépôt : pas de bouton',
    !R.rendu(null, 'tasks/plans', [], { conversation: {} }).includes('data-action="choisir"'))
  verifie('conversation sans plan : message par défaut',
    R.rendu(null, 'tasks/plans', [], { conversation: {} }).includes('Cette conversation ne suit aucun plan.'))

  // 4. Le vrai plan du depot
  const reel = path.join(RACINE, 'tasks', 'plans', 'suivi-plan.md')
  if (fs.existsSync(reel)) {
    const ar = P.analyse(fs.readFileSync(reel, 'utf8'))
    console.log(`Plan réel : ${ar.global} %, ${ar.fait}/${ar.total} étapes, ${ar.actions.length} actions`)
    controleLignesEtPourcents('suivi-plan.md', R, ar)
    verifie('suivi-plan.md : aucune fuite', fuites(R, ar).filter(x => x !== 'forme echappee absente' && !x.startsWith('entites')).length === 0)
  } else verifie('tasks/plans/suivi-plan.md présent', false, reel)

  // 5. Temoin : copie intacte verte, copie mutee rouge, dans le meme montage
  const source = fs.readFileSync(path.join(ICI, 'rendu.js'), 'utf8')
  const lignes = source.split('\n')
  const iMutant = lignes.findIndex(l => l.includes('MUTANT:echappe'))
  verifie('témoin : ligne MUTANT:echappe trouvée', iMutant >= 0)
  const intact = chargeSource(source, path.join(ICI, 'rendu_intact_temoin.js'))
  verifie('témoin : copie intacte, échappement vert', fuites(intact, a).length === 0)
  lignes[iMutant] = "  return String(texte ?? '')   // echappement neutralise"
  const mute = chargeSource(lignes.join('\n'), path.join(ICI, 'rendu_mute_temoin.js'))
  const fm = fuites(mute, a)
  verifie('témoin : copie mutée, échappement ROUGE (le banc détecte la régression)', fm.length > 0, 'aucune fuite détectée')
  if (fm.length) console.log(`        fuites détectées sur la copie mutée : ${fm.join(', ')}`)

  console.log(`\n${nbOk} OK, ${nbEchecs} échec(s)`)
  process.exit(nbEchecs ? 1 : 0)
}

principal().catch(e => { console.error(e); process.exit(2) })
