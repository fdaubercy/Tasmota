// Banc du mod suivi-plan : claude.cmd plugin test .claude/mods/suivi-plan
// L'environnement de test n'a ni fichiers ni processus : les hooks du test, places sous le plugin,
// tiennent lieu de moteur (fs.*, session.root, ui.status, command.register, resultat des outils).
// TEMOIN : « racine sans tasks/plans » exige qu'aucun fichier ne soit ecrit ; sans la garde, le meme
// scenario ecrit (le cas « recopie » le prouve) et ce test echoue.
import { test, expect, mock } from 'claude-code/testing'
import type { Engine } from 'claude-code/testing'
import type { On } from 'claude-code'

const RACINE = 'C:/projet'
const PLANS = `${RACINE}/tasks/plans`
const PROFIL = 'C:\\Users\\moi'
const SIGNAL = 'C:/Users/moi/.claude/suivi-plan/signal.json'
const SOURCE = 'C:\\Users\\moi\\.claude\\plans\\plan-joyeux.md'
const SESSION = 'sess-1'
const RATTACHE = `C:/Users/moi/.claude/suivi-plan/conversations/${SESSION}.json`

const BRUT = '# Mon plan\n\n## Contexte\nTexte.\n\n## A1 — Faire\n- [ ] étape x\n- [ ] étape y\n\n## Améliorations restantes\n- [ ] [projet] plus tard\n'
const ESSAI = [
  '---', 'chantier: essai', "titre: Plan d'essai", 'statut: actif', 'cree: 2026-10-01', 'maj: 2026-10-01', '---',
  "# Plan d'essai", '', '## A1 — Première action', '- [x] étape faite — preuve : banc vert', '- [ ] étape à faire', '',
  '## A2 — Deuxième action', '- [ ] autre étape', '', '## Améliorations restantes', '- [ ] [conversation] reste à voir', '',
].join('\n')

type Fichier = { texte: string; mtimeMs: number }
let horloge = 1000                    // commun a tous les tests : un mtime ne se repete jamais

// Monde simule : fichiers en memoire, dossiers deduits des fichiers (ou declares), journal des ecritures.
function monde(on: On, fichiers: Record<string, string>, dossiers: string[] = [PLANS]) {
  const fs = new Map<string, Fichier>()
  const norm = (p: string) => p.replace(/\\/g, '/')
  for (const [k, v] of Object.entries(fichiers)) fs.set(k, { texte: v, mtimeMs: ++horloge })
  const estDossier = (p: string) => dossiers.includes(p) || [...fs.keys()].some((k) => k.startsWith(`${p}/`))
  const statuts: (string | undefined)[] = []
  const vuAuMoteur: (string | null)[] = []   // signal present quand le message atteint le moteur
  const ecritures: string[] = []
  const commandes: string[] = []
  on('session.root', () => ({ value: RACINE.replace(/\//g, '\\') }))
  on('fs.exists', ($, e) => ({ value: fs.has(norm(e.path)) || estDossier(norm(e.path)) }))
  on('fs.read', ($, e) => {
    const f = fs.get(norm(e.path))
    return f ? { value: f.texte } : { deny: `ENOENT ${e.path}` }
  })
  on('fs.write', ($, e) => {
    fs.set(norm(e.path), { texte: e.text, mtimeMs: ++horloge })
    ecritures.push(norm(e.path))
    return { value: undefined }
  })
  on('fs.list', ($, e) => {
    const d = `${norm(e.path)}/`
    const entrees = [...fs.entries()].filter(([k]) => k.startsWith(d) && !k.slice(d.length).includes('/'))
      .map(([k, f]) => ({ name: k.slice(d.length), kind: 'file' as const, size: f.texte.length, mtimeMs: f.mtimeMs, isLink: false }))
    return { value: entrees }
  })
  on('ui.status', ($, e) => {
    statuts.push(e.text)
    return { value: undefined }
  })
  on('command.register', ($, e) => {
    commandes.push(e.name)
    return { value: { command: e.name } }
  })
  on('session.id', () => ({ value: SESSION }))
  on('session.start', ($, e) => ({ cwd: e.cwd }))
  on('prompt.submit', ($, e) => {
    vuAuMoteur.push(fs.get('C:/Users/moi/.claude/suivi-plan/signal.json')?.texte ?? null)
    return { text: e.text }
  })
  on('turn.complete', ($, e) => ({ text: e.answer }))
  on('prompt.context', ($, e) => ({ blocks: e.blocks }))
  on('prompt.attachment', ($, e) => ({ text: e.text }))
  mock.env(on, { USERPROFILE: PROFIL })
  const temps = mock.clock(on, { now: 0 })
  // Edit / Write executes sur le monde simule (resultat minimal : le plugin ne le lit pas)
  on('tool.call', { tool: 'Edit' }, ($, e) => {
    const f = fs.get(norm(e.file_path))
    if (!f) return { deny: 'absent' }
    fs.set(norm(e.file_path), { texte: f.texte.replace(e.old_string, e.new_string), mtimeMs: ++horloge })
    return { result: {} as never }
  })
  on('tool.call', { tool: 'Write' }, ($, e) => {
    fs.set(norm(e.file_path), { texte: e.content, mtimeMs: ++horloge })
    return { result: {} as never }
  })
  const plans = () => ecritures.filter((p) => p.startsWith(`${PLANS}/`))
  return { fs, statuts, vuAuMoteur, ecritures, commandes, temps, plans, lire: (p: string) => fs.get(p)?.texte ?? '' }
}

const demarre = ($: Engine) => $.session.start({ cwd: RACINE, surface: 'terminal', isInteractive: true })
// Commande tapee par la personne : origine et presentation que le moteur estampille.
const suivi = ($: Engine, args: string) =>
  $.command.run({ command: 'suivi', args, origin: { kind: 'composer' }, presentation: { isFullscreen: false, columns: 100 } })
const approuve = (on: On, result: Record<string, unknown>) =>
  on('tool.call', { tool: 'ExitPlanMode' }, () => ({ result: { isAgent: false, ...result } as never }))

test('recopie un plan approuve : fichier, context, signal, ligne de statut', async ($, on) => {
  const m = monde(on, { [`${PLANS}/_FORMAT.md`]: '# format' })
  approuve(on, { plan: BRUT, filePath: SOURCE })
  await demarre($)
  const r = await $.tool.call({ tool: 'ExitPlanMode' })
  const texte = m.lire(`${PLANS}/mon-plan.md`)
  expect(texte).toContain('chantier: mon-plan')
  expect(texte).toContain('statut: actif')
  expect(texte).toContain('source: plan-joyeux.md')
  expect(texte).toContain('## A1 — Faire')
  expect(r.context?.[0]).toContain('Plan suivi : tasks/plans/mon-plan.md (1 actions, 0 %)')
  expect(r.context?.length).toBe(1)
  const signal = JSON.parse(m.lire(SIGNAL))
  expect(signal.racine).toBe(RACINE)
  expect(signal.fichier).toBe('tasks/plans/mon-plan.md')
  expect(typeof signal.horodatage).toBe('number')
  expect(m.statuts.at(-1)).toMatch(/^Plan mon-plan ░+ 0 % · A1 0\/2 · prochaine : étape x/)
  expect(signal.session).toBe(SESSION)
  expect(signal.ouvrir).toBe(true)
  expect(JSON.parse(m.lire(RATTACHE))).toMatchObject({ session: SESSION, racine: RACINE, fichier: 'tasks/plans/mon-plan.md' })
})

test('plan revalide : coches gardees ; meme nom, autre source : suffixe -2', async ($, on) => {
  const deja = '---\nchantier: mon-plan\nstatut: actif\ncree: 2026-09-01\nsource: plan-joyeux.md\n---\n# Mon plan\n\n## A1 — Faire\n- [x] étape x — preuve : commit abc\n- [ ] étape y\n'
  const m = monde(on, { [`${PLANS}/mon-plan.md`]: deja })
  approuve(on, { plan: BRUT, filePath: SOURCE })
  await demarre($)
  await $.tool.call({ tool: 'ExitPlanMode' })
  const texte = m.lire(`${PLANS}/mon-plan.md`)
  expect(texte).toContain('- [x] étape x — preuve : commit abc')
  expect(texte).toContain('cree: 2026-09-01')
  expect(m.fs.has(`${PLANS}/mon-plan-2.md`)).toBe(false)

  m.fs.set(`${PLANS}/mon-plan.md`, { texte: deja.replace('plan-joyeux.md', 'autre.md'), mtimeMs: ++horloge })
  await $.tool.call({ tool: 'ExitPlanMode' })
  expect(m.lire(`${PLANS}/mon-plan-2.md`)).toContain('chantier: mon-plan-2')
  expect(m.lire(`${PLANS}/mon-plan.md`)).toContain('source: autre.md')
})

test('plan sans action : avertissement de format dans le context', async ($, on) => {
  monde(on, {})
  approuve(on, { plan: '# Idée\n\n1. faire ceci\n2. puis cela\n', filePath: SOURCE })
  const r = await $.tool.call({ tool: 'ExitPlanMode' })
  expect(r.context?.[1]).toContain('_FORMAT.md avant de commencer')
})

for (const [cas, result] of [
  ['plan de sous-agent (isAgent)', { plan: BRUT, isAgent: true }],
  ['attente du chef d equipe', { plan: BRUT, awaitingLeaderApproval: true }],
  ['plan vide', { plan: null }],
] as const) {
  test(`rien n est ecrit : ${cas}`, async ($, on) => {
    const m = monde(on, {})
    approuve(on, result)
    const r = await $.tool.call({ tool: 'ExitPlanMode' })
    expect(m.ecritures).toEqual([])
    expect(r.context).toBeUndefined()
  })
}

test('rien n est ecrit : appel refuse', async ($, on) => {
  const m = monde(on, {})
  on('tool.call', { tool: 'ExitPlanMode' }, () => ({ deny: 'refuse par l utilisateur' }))
  const r = await $.tool.call({ tool: 'ExitPlanMode' })
  expect(r.deny).toBe('refuse par l utilisateur')
  expect(m.ecritures).toEqual([])
})

// TEMOIN de la garde : meme scenario que le premier test, mais la racine n'a pas de tasks/plans.
test('TEMOIN racine sans tasks/plans : aucune ecriture, aucune ligne, aucun bloc, aucune commande', async ($, on) => {
  const m = monde(on, {}, [])
  approuve(on, { plan: BRUT, filePath: SOURCE })
  await demarre($)
  const r = await $.tool.call({ tool: 'ExitPlanMode' })
  const ctx = await $.prompt.context({ blocks: [{ name: 'currentDate', text: 'x' }] })
  await $.prompt.submit({ text: 'bonjour' })
  await suivi($, 'detacher')
  const att = await $.prompt.attachment({ type: 'plan_mode', text: 'RAPPEL', origin: { kind: 'engine' }, detail: { reminder: 'full', planFilePath: SOURCE, hasPlan: false } })
  expect(m.ecritures).toEqual([])
  expect(r.context).toBeUndefined()
  expect(m.statuts.filter((s) => s !== undefined)).toEqual([])
  expect(m.commandes).toEqual([])
  expect(ctx.blocks.map((b) => b.name)).toEqual(['currentDate'])
  expect(att.text).toBe('RAPPEL')
})

test('prompt.context : bloc suiviPlan pour le plan actif, rien pour un plan clos', async ($, on) => {
  const m = monde(on, { [`${PLANS}/essai.md`]: ESSAI })
  const r = await $.prompt.context({ blocks: [{ name: 'currentDate', text: 'x' }] })
  const bloc = r.blocks.find((b) => b.name === 'suiviPlan')
  expect(bloc?.text).toContain("Plan « Plan d'essai » (tasks/plans/essai.md) : 25 %")
  expect(bloc?.text).toContain('coche une étape seulement après')
  expect((bloc?.text ?? '').split('\n').length <= 25).toBe(true)

  m.fs.set(`${PLANS}/essai.md`, { texte: ESSAI.replace('statut: actif', 'statut: clos'), mtimeMs: ++horloge })
  const r2 = await $.prompt.context({ blocks: [] })
  expect(r2.blocks).toEqual([])
})

test('prompt.attachment plan_mode : consigne ajoutee seulement au rappel full', async ($, on) => {
  monde(on, {})
  const rappel = (reminder: 'full' | 'sparse') =>
    $.prompt.attachment({ type: 'plan_mode', text: 'RAPPEL', origin: { kind: 'engine' }, detail: { reminder, planFilePath: SOURCE, hasPlan: false } })
  const plein = await rappel('full')
  expect(plein.text).toContain('RAPPEL\n\nFormat du plan')
  expect(plein.text).toContain('tasks/plans/_FORMAT.md')
  expect(plein.text).toContain('[conversation] ou [projet]')
  expect((await rappel('sparse')).text).toBe('RAPPEL')
})

test('/suivi : resume, liste, ouvrir, clore (fins de ligne gardees)', async ($, on) => {
  const crlf = ESSAI.replace(/\n/g, '\r\n')
  const m = monde(on, { [`${PLANS}/essai.md`]: crlf, [`${PLANS}/vieux.md`]: '---\nchantier: vieux\nstatut: clos\n---\n# Vieux\n' })
  await demarre($)
  expect(m.commandes).toEqual(['suivi'])
  const resume = await suivi($, '')
  expect(resume.text).toContain("Plan « Plan d'essai »")
  expect(resume.text).toContain('A1 50 % (1/2) · A2 0 % (0/1)')
  const liste = await suivi($, 'liste')
  expect(liste.text).toContain('- essai · actif · 25 % (tasks/plans/essai.md)')
  expect(liste.text).toContain('- vieux · clos · 0 % (tasks/plans/vieux.md)')
  const ouvrir = await suivi($, 'ouvrir')
  expect(ouvrir.text).toContain('vscode://fdaubercy.suivi-plan/ouvrir?fichier=tasks/plans/essai.md')
  expect(JSON.parse(m.lire(SIGNAL)).fichier).toBe('tasks/plans/essai.md')
  const clore = await suivi($, 'clore')
  expect(clore.text).toContain('statut clos')
  const texte = m.lire(`${PLANS}/essai.md`)
  expect(texte).toContain('statut: clos\r\n')
  expect(texte).not.toContain('maj: 2026-10-01')
  expect(texte.replace(/\r\n/g, '').includes('\n')).toBe(false)
  // « ouvrir » a rattache essai a la conversation : sa ligne et son resume restent montres, meme clos
  expect(m.statuts.at(-1)).toMatch(/^Plan essai /)
  expect((await suivi($, '')).text).toContain('statut clos')
  await suivi($, 'detacher')
  expect(m.statuts.at(-1)).toBeUndefined()                // detachee, et plus aucun plan actif
  expect((await suivi($, '')).text).toContain('Aucun plan actif.')
  expect((await suivi($, 'activer ../../secret')).text).toContain('introuvable')
})

test('ligne de statut : session.start, turn.complete, puis minuterie de 30 s', async ($, on) => {
  const m = monde(on, { [`${PLANS}/essai.md`]: ESSAI })
  await demarre($)
  expect(m.statuts.at(-1)).toMatch(/^Plan essai ███░+ 25 % · A1 1\/2 · prochaine : étape à faire$/)
  m.fs.set(`${PLANS}/essai.md`, { texte: ESSAI.replace('- [ ] étape à faire', '- [x] étape à faire — preuve : ok'), mtimeMs: ++horloge })
  await m.temps.advance(30000)
  expect(m.statuts.at(-1)).toMatch(/ 50 % · A2 0\/1 · prochaine : autre étape$/)
  m.fs.set(`${PLANS}/essai.md`, { texte: ESSAI.replace('statut: actif', 'statut: en-pause'), mtimeMs: ++horloge })
  await $.turn.complete({ answer: 'fini', durationMs: 1, isAborted: false, turnId: 't1', reason: 'answer' })
  expect(m.statuts.at(-1)).toBeUndefined()
})

test('etape cochee sans preuve : rappel doux ; avec preuve ou hors plan : rien', async ($, on) => {
  const m = monde(on, { [`${PLANS}/essai.md`]: ESSAI, [`${PLANS}/_FORMAT.md`]: '## A1 — x\n- [ ] y\n' })
  const chemin = 'C:\\projet\\tasks\\plans\\essai.md'
  const sans = await $.tool.call({ tool: 'Edit', file_path: chemin, old_string: '- [ ] étape à faire', new_string: '- [x] étape à faire' })
  expect(sans.context?.[0]).toContain('Étape cochée sans preuve dans tasks/plans/essai.md : « étape à faire »')
  const avec = await $.tool.call({ tool: 'Edit', file_path: chemin, old_string: '- [ ] autre étape', new_string: '- [x] autre étape — preuve : banc' })
  expect(avec.context).toBeUndefined()
  const format = await $.tool.call({ tool: 'Edit', file_path: `${PLANS}/_FORMAT.md`, old_string: '- [ ] y', new_string: '- [x] y' })
  expect(format.context).toBeUndefined()
  // un plan edite (pas cree) : pas de signal, mais la conversation le suit desormais
  expect(m.ecritures.filter((p) => p !== RATTACHE)).toEqual([])
  expect(JSON.parse(m.lire(RATTACHE)).fichier).toBe('tasks/plans/essai.md')
})

test('plan cree par Write : signal ecrit', async ($, on) => {
  const m = monde(on, {})
  await $.tool.call({ tool: 'Write', file_path: `${PLANS}/neuf.md`, content: ESSAI.replace('essai', 'neuf') })
  expect(JSON.parse(m.lire(SIGNAL)).fichier).toBe('tasks/plans/neuf.md')
  expect(m.statuts.at(-1)).toMatch(/^Plan neuf /)
})

const PLAN_B = ESSAI.replace(/Plan d'essai/g, 'Plan B').replace('chantier: essai', 'chantier: autre')

test('/suivi suivre et detacher : rattachement, resume du plan suivi, signaux', async ($, on) => {
  const m = monde(on, { [`${PLANS}/essai.md`]: ESSAI, [`${PLANS}/autre.md`]: PLAN_B })   // autre = plus recent
  await demarre($)
  expect((await suivi($, '')).text).toContain('Plan « Plan B »')               // sans rattachement : le plus recent
  expect((await suivi($, 'suivre')).text).toContain('Usage : /suivi suivre <chantier>')
  const r = await suivi($, 'suivre essai')
  expect(r.text).toContain('Cette conversation suit tasks/plans/essai.md')
  expect(JSON.parse(m.lire(RATTACHE)).fichier).toBe('tasks/plans/essai.md')
  expect(JSON.parse(m.lire(SIGNAL))).toMatchObject({ fichier: 'tasks/plans/essai.md', session: SESSION, ouvrir: true })
  expect((await suivi($, '')).text).toContain("Plan « Plan d'essai »")          // le plan suivi passe devant
  expect((await suivi($, 'ouvrir')).text).toContain('fichier=tasks/plans/essai.md')
  expect((await suivi($, 'suivre ../../secret')).text).toContain('introuvable')
  const d = await suivi($, 'detacher')
  expect(d.text).toContain('ne suit plus tasks/plans/essai.md')
  expect(JSON.parse(m.lire(RATTACHE)).fichier).toBeNull()
  expect(JSON.parse(m.lire(SIGNAL))).toMatchObject({ fichier: null, ouvrir: false })
  expect((await suivi($, 'detacher')).text).toContain('ne suivait aucun plan')
  expect(m.lire(`${PLANS}/essai.md`)).toBe(ESSAI)                               // le plan lui-meme intact
})

test('message envoye : signal sans ouverture avec le plan de la conversation', async ($, on) => {
  const m = monde(on, { [`${PLANS}/essai.md`]: ESSAI, [`${PLANS}/autre.md`]: PLAN_B })
  await $.prompt.submit({ text: 'bonjour' })
  expect(JSON.parse(m.lire(SIGNAL))).toMatchObject({ racine: RACINE, fichier: null, session: SESSION, ouvrir: false })
  await suivi($, 'suivre essai')
  await $.prompt.submit({ text: 'et maintenant ?' })
  expect(JSON.parse(m.lire(SIGNAL))).toMatchObject({ fichier: 'tasks/plans/essai.md', ouvrir: false })
  // rattachement d'une autre racine, ou plan disparu : aucun plan
  m.fs.set(RATTACHE, { texte: JSON.stringify({ session: SESSION, racine: 'D:/ailleurs', fichier: 'tasks/plans/essai.md' }), mtimeMs: ++horloge })
  await $.prompt.submit({ text: 'x' })
  expect(JSON.parse(m.lire(SIGNAL)).fichier).toBeNull()
  m.fs.set(RATTACHE, { texte: JSON.stringify({ session: SESSION, racine: RACINE, fichier: 'tasks/plans/efface.md' }), mtimeMs: ++horloge })
  await $.prompt.submit({ text: 'x' })
  expect(JSON.parse(m.lire(SIGNAL)).fichier).toBeNull()
})

test('message envoye : signal ecrit AVANT que le moteur ne recoive le message', async ($, on) => {
  const m = monde(on, { [`${PLANS}/essai.md`]: ESSAI })
  await suivi($, 'suivre essai')
  m.fs.delete(SIGNAL)
  await $.prompt.submit({ text: 'bonjour' })
  expect(m.vuAuMoteur.length).toBe(1)
  expect(JSON.parse(m.vuAuMoteur[0] ?? 'null')).toMatchObject({ fichier: 'tasks/plans/essai.md', ouvrir: false })
})

test('plan de la conversation : ligne d avancement et bloc de contexte le montrent d abord', async ($, on) => {
  const m = monde(on, { [`${PLANS}/essai.md`]: ESSAI, [`${PLANS}/autre.md`]: PLAN_B })   // autre = plus recent
  await demarre($)
  expect(m.statuts.at(-1)).toMatch(/^Plan autre /)                              // sans rattachement
  const sans = (await $.prompt.context({ blocks: [] })).blocks.find((b) => b.name === 'suiviPlan')?.text ?? ''
  expect(sans).not.toContain('Plan suivi par cette conversation')
  expect(sans.indexOf('Plan B') < sans.indexOf("Plan d'essai")).toBe(true)
  await suivi($, 'suivre essai')
  expect(m.statuts.at(-1)).toMatch(/^Plan essai /)                              // le plan suivi passe devant
  const avec = (await $.prompt.context({ blocks: [] })).blocks.find((b) => b.name === 'suiviPlan')?.text ?? ''
  expect(avec.startsWith("Plan suivi par cette conversation :\nPlan « Plan d'essai »")).toBe(true)
  expect(avec).toContain('Plan « Plan B »')
  expect(avec.split('\n').length <= 25).toBe(true)
  await suivi($, 'detacher')
  expect(m.statuts.at(-1)).toMatch(/^Plan autre /)
})

// Panneau de l'app : props que le moteur estampille pour un Pane place a droite.
const PANNEAU = {
  plugin: 'suivi-plan',
  component: 'Pane',
  requestId: 'suivi-plan',
  props: { title: 'Suivi du plan', isFocused: false, bodyColumns: 60, placement: 'dock', scroll: { offset: 0, bodyRows: 40 }, view: {} },
} as const

test('panneau : /suivi ouvrir le demande, il montre le plan et se redessine apres une coche', async ($, on) => {
  const m = monde(on, { [`${PLANS}/essai.md`]: ESSAI })
  const ouverts: string[] = []
  on('ui.open', ($, e) => {
    ouverts.push(e.id)
    return { value: { isPlaced: true } }
  })
  await demarre($)
  await suivi($, 'ouvrir')
  expect(ouverts).toEqual(['suivi-plan'])
  for (const surface of ['desktop', 'terminal'] as const) {
    const ui = await $.ui.mount({ ...PANNEAU, surface })
    expect((await ui.find({ type: 'Text', text: /^Plan d'essai$/ }))?.text).toBe("Plan d'essai")
    expect((await ui.find({ type: 'Text', text: /étapes$/ }))?.text).toBe('25 % · 1/3 étapes')
    expect((await ui.find({ type: 'Text', text: /preuve/ }))?.text).toBe('   preuve : banc vert')
    await ui.unmount()
  }
  m.fs.set(`${PLANS}/essai.md`, { texte: ESSAI.replace('- [ ] étape à faire', '- [x] étape à faire — preuve : ok'), mtimeMs: ++horloge })
  await m.temps.advance(30000)
  const ui = await $.ui.mount({ ...PANNEAU, surface: 'desktop' })
  expect((await ui.find({ type: 'Text', text: /étapes$/ }))?.text).toBe('50 % · 2/3 étapes')
  await ui.unmount()
})

test('panneau sans plan suivi ni actif : invitation a /suivi suivre', async ($, on) => {
  monde(on, {})
  await demarre($)
  const ui = await $.ui.mount({ ...PANNEAU, surface: 'desktop' })
  expect((await ui.find({ type: 'Text', text: /^Aucun plan$/ }))?.text).toBe('Aucun plan')
  expect((await ui.find({ type: 'Text', text: /suivi suivre/ }))?.text).toContain('/suivi suivre <chantier>')
  await ui.unmount()
})
