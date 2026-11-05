import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Action, SousAgent, Tache } from '../types'

// Volet « Sous-agents » : un bloc par sous-agent de la conversation (tache en cours, pourcentage tire de sa liste
// TodoWrite, duree, outils appeles). Le pourcentage n'existe que si l'agent tient sa liste : chaque lancement recoit
// une consigne qui le lui demande (agent.spawn).

const PANE = 'sous-agents'
const TITRE = 'Sous-agents'
const GARDE_FINI_MS = 60_000 // un agent fini reste affiche (grise) une minute
const SONDE_MS = 2_000
const FINIS = ['completed', 'failed', 'killed']
const JOURNAL = 8 // actions gardees par agent
const LARGEUR_TEXTE = 110

export const CONSIGNE =
  "[Suivi de progression] Si l'outil TodoWrite t'est disponible : dès le début, découpe ton travail en 3 à 10 " +
  "tâches avec TodoWrite, puis tiens la liste à jour (une seule tâche in_progress, chaque tâche passée à completed " +
  "dès qu'elle est finie). L'utilisateur suit ta progression dans un volet d'après cette liste. Sans TodoWrite, " +
  'ignore cette consigne.\n\n'

// Changer l'etiquette quand les champs de SousAgent changent : elle refuse ce qu'une version precedente a garde.
const agents = atom({ plugin: 'suivi-sous-agents', key: 'agents' } as const, [] as SousAgent[], { shape: 'agents-1' })
const horloge = atom({ plugin: 'suivi-sous-agents', key: 'horloge' } as const, 0)
const ferme = atom({ plugin: 'suivi-sous-agents', key: 'ferme' } as const, false)

export function pourcentage(taches?: Tache[]): number | undefined {
  if (!taches || taches.length === 0) return undefined
  return Math.round((100 * taches.filter(t => t.status === 'completed').length) / taches.length)
}

export function duree(ms: number): string {
  const s = Math.max(0, Math.floor(ms / 1000))
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const ss = String(s % 60).padStart(2, '0')
  return h > 0 ? `${h} h ${String(m).padStart(2, '0')}` : `${m}:${ss}`
}

export function barre(pct: number, largeur = 20): string {
  const plein = Math.round((pct / 100) * largeur)
  return '█'.repeat(plein) + '░'.repeat(largeur - plein)
}

export function court(s: string, n = LARGEUR_TEXTE): string {
  const un = s.replace(/\s+/g, ' ').trim()
  return un.length > n ? un.slice(0, n - 1) + '…' : un
}

// Fin de chemin lisible : les deux derniers elements (« outils_pc/build_page.py »).
function finChemin(c: string): string {
  return c.replace(/\\/g, '/').split('/').filter(Boolean).slice(-2).join('/')
}

// Le detail d'un appel d'outil, tel qu'on veut le lire sous l'agent : la description ou la commande d'un shell, le
// fichier lu ou ecrit, le motif cherche, l'adresse, la skill, le sous-agent lance...
export function detail(tool: string, args: Record<string, unknown>): string {
  const s = (k: string) => (typeof args[k] === 'string' ? (args[k] as string) : '')
  if (tool === 'Bash' || tool === 'PowerShell') return s('description') || s('command')
  if (s('file_path') || s('notebook_path')) return finChemin(s('file_path') || s('notebook_path'))
  if (tool === 'Grep') return s('pattern') + (s('path') ? ' dans ' + finChemin(s('path')) : '')
  if (tool === 'Glob') return s('pattern')
  if (tool === 'Agent') return s('description')
  if (tool === 'Skill') return s('skill')
  if (tool === 'SendMessage') return s('summary') || s('to')
  return s('description') || s('url') || s('query') || s('pattern') || s('command') || ''
}

// Ajoute une action au journal (les JOURNAL dernieres) ou met a jour celle de meme id.
export function note(journal: Action[] | undefined, action: Action): Action[] {
  const l = journal ?? []
  return l.some(x => x.id === action.id) ? l.map(x => (x.id === action.id ? action : x)) : [...l, action].slice(-JOURNAL)
}

// Agents a montrer : en cours, ou finis depuis moins d'une minute ; les en-cours d'abord.
export function visibles(liste: SousAgent[], maintenant: number): SousAgent[] {
  const garde = liste.filter(a => a.fin === undefined || maintenant - a.fin < GARDE_FINI_MS)
  return [...garde.filter(a => a.fin === undefined), ...garde.filter(a => a.fin !== undefined)]
}

// Ajoute l'agent au suivi (une fois) et ouvre le volet, sauf s'il a été fermé à la main.
async function suit($: EngineInterface, id: string, description: string, type: string) {
  const debut = await $.clock.now()
  await update($, agents, l =>
    l.some(a => a.id === id) ? l : [...l, { id, description, type, debut, statut: 'running', outils: 0 }].slice(-30),
  )
  if (!(await read($, ferme))) void $.ui.open({ id: PANE, title: TITRE })
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({ name: 'sous-agents', description: 'Ouvre le volet de suivi des sous-agents' })
    // Sonde : statut de chaque agent (fin comprise) et horloge des durees ; ne fait rien quand rien n'est affiche.
    $.clock.every(SONDE_MS, () => {
      void (async () => {
        const maintenant = await $.clock.now()
        const liste = await read($, agents)
        if (!liste.some(a => a.fin === undefined || maintenant - a.fin < GARDE_FINI_MS)) {
          if (liste.length > 0) await update($, agents, () => [])
          return
        }
        const connus = await $.agent.list()
        await update($, agents, l =>
          l
            .map(a => {
              const info = connus.find(c => c.id === a.id)
              if (!info || a.fin !== undefined) return a
              const fini = FINIS.includes(info.status)
              return { ...a, statut: info.status, fin: fini ? maintenant : undefined }
            })
            .filter(a => a.fin === undefined || maintenant - a.fin < GARDE_FINI_MS),
        )
        await update($, horloge, () => maintenant)
      })()
    })
    return next(e)
  })

  on('command.run', { command: 'sous-agents' }, async $ => {
    await update($, ferme, () => false)
    await $.ui.open({ id: PANE, title: TITRE })
    return { text: 'Volet des sous-agents ouvert.' }
  })

  // Ferme a la main : il ne se rouvre plus de lui-meme dans cette conversation (/sous-agents le rouvre).
  on('ui.close', async ($, e, next) => {
    if (e.id === PANE && e.origin.kind === 'person') await update($, ferme, () => true)
    return next(e)
  }).catch(($, e, next) => next(e)) // un incident du mod ne bloque jamais l'action suivie

  on('agent.spawn', async ($, e, next) => {
    const r = await next({ ...e, prompt: CONSIGNE + e.prompt })
    if (r.deny !== undefined || !r.agentId) return r
    await suit($, r.agentId, e.description, e.subagentType)
    return r
  }).catch(($, e, next) => next(e)) // un incident du mod ne bloque jamais l'action suivie

  on('tool.call', async ($, e, next) => {
    const id = e.agentId
    if (id !== undefined) {
      // Agent pas encore connu (lancement au premier plan dont agent.spawn n'a pas encore rendu la main, ou lancé
      // avant un rechargement du mod) : retrouvé dans la liste des agents ; inconnu de la liste (workflow) = ignoré.
      if (!(await read($, agents)).some(a => a.id === id)) {
        const info = (await $.agent.list()).find(c => c.id === id)
        if (info) await suit($, id, info.description, info.type)
      }
      const taches = e.tool === 'TodoWrite' ? e.todos : undefined
      const action: Action | undefined =
        e.tool === 'TodoWrite'
          ? undefined
          : { id: e.tool_use_id ?? String(Math.random()), genre: 'outil', texte: court(`${e.tool} · ${detail(e.tool, e as unknown as Record<string, unknown>)}`), etat: 'cours' }
      await update($, agents, l =>
        l.map(a =>
          a.id === id
            ? { ...a, outils: a.outils + 1, dernierOutil: e.tool, ...(taches ? { taches } : {}), ...(action ? { journal: note(a.journal, action) } : {}) }
            : a,
        ),
      )
      const r = await next(e)
      if (action) {
        const fin: Action = { ...action, etat: r.deny !== undefined || ('isError' in r && r.isError) ? 'erreur' : 'ok' }
        await update($, agents, l => l.map(a => (a.id === id ? { ...a, journal: note(a.journal, fin) } : a)))
      }
      return r
    }
    return next(e)
  }).catch(($, e, next) => next(e)) // un incident du mod ne bloque jamais l'action suivie

  // Remarques : le texte qu'un sous-agent ecrit entre deux outils (fin de chaque pas de son tour).
  on('turn.step', async function* ($, e, next) {
    const r = yield* next(e)
    const id = e.agentId
    if (id !== undefined && r.answer.trim()) {
      try {
        const action: Action = { id: `${e.turnId}:${e.index}`, genre: 'remarque', texte: court(r.answer), etat: 'ok' }
        await update($, agents, l => l.map(a => (a.id === id ? { ...a, journal: note(a.journal, action) } : a)))
      } catch {
        // le suivi ne doit jamais gener le tour de l'agent
      }
    }
    return r
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text } = $.ui.resolve(e)
    await read($, horloge) // relu pour redessiner les durees a chaque sonde
    const maintenant = await $.clock.now()
    const liste = visibles(await read($, agents), maintenant)
    if (liste.length === 0) return <Text dimColor>Aucun sous-agent en cours.</Text>
    return (
      <Box flexDirection="column">
        {liste.map(a => {
          const fini = a.fin !== undefined
          const pct = pourcentage(a.taches)
          const enCours = a.taches?.find(t => t.status === 'in_progress')
          const etat = !fini ? '●' : a.statut === 'completed' ? '✓' : '✗'
          return (
            <Box flexDirection="column" marginBottom={1}>
              <Text bold={!fini} dimColor={fini}>
                {etat} {a.description}
              </Text>
              <Text dimColor>
                {'  '}
                {a.type} · {duree((a.fin ?? maintenant) - a.debut)} · {a.outils} outil{a.outils > 1 ? 's' : ''}
                {fini ? ` · ${a.statut === 'completed' ? 'terminé' : a.statut}` : ''}
              </Text>
              {pct !== undefined && (
                <Text dimColor={fini} color={fini ? undefined : 'success'}>
                  {'  '}
                  {barre(pct)} {pct} % ({a.taches!.filter(t => t.status === 'completed').length}/{a.taches!.length})
                </Text>
              )}
              {!fini && enCours && <Text>{'  ▸ '}{enCours.activeForm}</Text>}
              {!fini && pct === undefined && a.dernierOutil && <Text dimColor>{'  dernier outil : '}{a.dernierOutil}</Text>}
              {!fini &&
                a.taches?.map(t => (
                  <Text dimColor={t.status !== 'in_progress'}>
                    {'    '}
                    {t.status === 'completed' ? '☑' : t.status === 'in_progress' ? '▸' : '☐'} {t.content}
                  </Text>
                ))}
              {!fini && (a.journal?.length ?? 0) > 0 && <Text dimColor>{'  Activité :'}</Text>}
              {!fini &&
                a.journal?.map(x => (
                  <Text
                    dimColor={x.etat === 'ok' && x.genre === 'outil'}
                    italic={x.genre === 'remarque'}
                    color={x.etat === 'erreur' ? 'error' : x.etat === 'cours' ? 'suggestion' : undefined}
                  >
                    {'    '}
                    {x.genre === 'remarque' ? '💬' : x.etat === 'cours' ? '⏵' : x.etat === 'erreur' ? '✗' : '✓'} {x.texte}
                  </Text>
                ))}
            </Box>
          )
        })}
      </Box>
    )
  })
}
