import { expect, test } from 'claude-code/testing'

import { barre, duree, pourcentage, visibles } from './register'

const PANE = {
  plugin: 'suivi-sous-agents',
  component: 'Pane',
  requestId: 'sous-agents',
  props: {
    title: 'Sous-agents',
    isFocused: false,
    bodyColumns: 60,
    placement: 'dock',
    scroll: { offset: 0, bodyRows: 30 },
    view: {},
  },
} as const

test('fonctions pures : pourcentage, durée, barre, visibles', async () => {
  expect(pourcentage(undefined)).toBe(undefined)
  expect(pourcentage([])).toBe(undefined)
  const t = (status: 'pending' | 'in_progress' | 'completed') => ({ content: 'x', status, activeForm: 'x' })
  expect(pourcentage([t('completed'), t('in_progress'), t('pending'), t('pending')])).toBe(25)
  expect(duree(65_000)).toBe('1:05')
  expect(duree(3_725_000)).toBe('1 h 02')
  expect(barre(50, 10)).toBe('█████░░░░░')
  const a = (id: string, fin?: number) => ({ id, description: id, type: 'g', debut: 0, statut: 'running', outils: 0, fin })
  expect(visibles([a('fini', 2_000), a('vieux', 0), a('actif')], 61_000).map(x => x.id)).toEqual(['actif', 'fini'])
})

test('un sous-agent lancé reçoit la consigne, ses outils et sa liste de tâches sont suivis', async ($, on) => {
  let prompt = ''
  let ouvert = 0
  on('command.register', () => ({ value: { command: 'sous-agents' } }))
  on('ui.open', () => {
    ouvert++
    return { value: { isPlaced: true } }
  })
  on('agent.list', () => ({ value: [] }))
  on('clock.now', () => ({ value: 10_000 }))
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  on('agent.spawn', (_, e) => {
    prompt = e.prompt
    return { model: 'sonnet', agentId: 'a1' }
  })
  on('tool.call', () => ({ result: {} }))

  await $.session.start({ cwd: '/', surface: 'desktop', isInteractive: true })
  await $.agent.spawn({
    prompt: 'Fais le travail', description: 'Implémenter A7', subagentType: 'general-purpose', tool_use_id: 't1',
    provider: { plugin: 'engine', tier: 'core' }, parentModel: 'opus', background: true, fork: false,
  })
  expect(prompt.startsWith('[Suivi de progression]')).toBe(true)
  expect(prompt.endsWith('Fais le travail')).toBe(true)
  expect(ouvert).toBe(1)

  await $.tool.call({ tool: 'Read', file_path: '/x', agentId: 'a1' })
  await $.tool.call({
    tool: 'TodoWrite',
    agentId: 'a1',
    todos: [
      { content: 'Banc rouge', status: 'completed', activeForm: 'Écrit le banc rouge' },
      { content: 'Code', status: 'in_progress', activeForm: 'Écrit le code' },
      { content: 'Banc vert', status: 'pending', activeForm: 'Lance le banc' },
      { content: 'Commit', status: 'pending', activeForm: 'Commite' },
    ],
  })
  await $.tool.call({ tool: 'Bash', command: 'ls' }) // fil principal : pas compté

  for (const surface of ['terminal', 'desktop'] as const) {
    const ui = await $.ui.mount({ ...PANE, surface })
    expect((await ui.find({ type: 'Text', text: /Implémenter A7/ }))?.text).toBe('● Implémenter A7')
    expect((await ui.find({ type: 'Text', text: /outils/ }))?.text).toContain('2 outils')
    expect((await ui.find({ type: 'Text', text: /%/ }))?.text).toContain('25 % (1/4)')
    expect((await ui.find({ type: 'Text', text: /▸ Écrit le code/ }))?.text).toBe('  ▸ Écrit le code')
    await ui.unmount()
  }
})

test('sans sous-agent, le volet le dit', async ($, on) => {
  on('clock.now', () => ({ value: 10_000 }))
  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  expect((await ui.find({ type: 'Text' }))?.text).toBe('Aucun sous-agent en cours.')
  await ui.unmount()
})
